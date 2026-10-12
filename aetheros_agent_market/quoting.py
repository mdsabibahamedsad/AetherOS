"""Quoting engine (spec section 14).

Paid execution requires a provider quote BEFORE authorization. Quotes
are verified deterministically (schema, expiry, amount sanity vs
offer/contract, signature presence when claimed) — never silently
converted from free to paid.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

# Suspicious jump vs reference price that forces policy review (sec 107).
PRICE_DEVIATION_FLAG = 10.0


def canonical_offer_bytes(offer: S.Offer) -> bytes:
    d = offer.to_dict()
    d.pop("signature", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_offer_signature(offer: S.Offer) -> Dict[str, Any]:
    """Best-effort deterministic check: presence + format + binding.

    Full cryptographic verification happens when the signer's public key
    is available via the bound marketplace identity; otherwise the
    result is explicit (unverified, never trusted).
    """
    if not offer.signature:
        return {"signed": False, "verified": False,
                "reason": "no signature present"}
    if not offer.signer_fp:
        return {"signed": True, "verified": False,
                "reason": "signature present but signer unknown"}
    if len(offer.signature) < 64:
        return {"signed": True, "verified": False,
                "reason": "malformed signature"}
    try:
        from aetheros_network.identity import verify_signature  # type: ignore
        # NOTE: requires raw public key bytes; fingerprint alone cannot
        # verify. Treated as unverified until key material is bound.
        return {"signed": True, "verified": False,
                "reason": "signer key material not bound; cannot verify"}
    except Exception:
        return {"signed": True, "verified": False,
                "reason": "verification backend unavailable"}


class QuotingEngine:
    def __init__(self, home: Path) -> None:
        self._quotes = JsonStore(Path(home) / "quotes.json")

    def record_quote(self, quote: S.Quote) -> S.Quote:
        errors = quote.validate()
        if errors:
            raise ValueError(f"invalid quote: {errors}")
        for raw in self._quotes.values():
            if raw.get("idempotency_key") == quote.idempotency_key:
                return S.Quote.from_dict(raw)
        self._quotes.put(quote.quote_id, quote.to_dict())
        return quote

    def get(self, quote_id: str) -> Optional[S.Quote]:
        raw = self._quotes.get(quote_id)
        return S.Quote.from_dict(raw) if raw else None

    def bind_contract(self, quote_id: str, contract_id: str) -> S.Quote:
        """Stamp the contract id once the contract exists (quote precedes
        contract by design; binding keeps tx <-> contract traceable)."""
        quote = self.get(quote_id)
        if quote is None:
            raise KeyError(f"unknown quote: {quote_id}")
        quote.contract_id = contract_id
        self._quotes.put(quote_id, quote.to_dict())
        return quote

    def verify_quote(self, quote: S.Quote,
                     contract: Optional[S.DelegationContract] = None,
                     offer: Optional[S.Offer] = None) -> Dict[str, Any]:
        """Deterministic verification. Returns {ok, reasons, flags}."""
        reasons: List[str] = []
        flags: List[str] = []
        errors = quote.validate()
        if errors:
            return {"ok": False, "reasons": errors, "flags": flags}
        if quote.is_expired:
            reasons.append("quote expired")
        if contract is not None:
            if quote.currency != contract.currency:
                reasons.append(f"currency mismatch: quote {quote.currency} vs contract {contract.currency}")
            if quote.total_minor > contract.budget_minor and contract.budget_minor:
                reasons.append(f"quote total {quote.total_minor} exceeds contract budget {contract.budget_minor}")
            if quote.contract_id and quote.contract_id != contract.contract_id:
                reasons.append("quote bound to a different contract")
            # Free task must never silently become paid.
            if contract.price_minor == 0 and quote.total_minor > 0:
                reasons.append("free contract converted to paid quote: rejected")
        if offer is not None:
            if quote.service_id != offer.service_id:
                reasons.append("quote service differs from offer service")
            if offer.price_minor > 0 and quote.price_minor > offer.price_minor * PRICE_DEVIATION_FLAG:
                flags.append(f"price {quote.price_minor} deviates >{PRICE_DEVIATION_FLAG}x from offer {offer.price_minor}: policy review required")
            if offer.is_expired:
                reasons.append("underlying offer expired")
            if offer.status != "open":
                reasons.append(f"offer is {offer.status}")
        if quote.signature and not quote.signer_fp:
            flags.append("quote signed but signer unknown: treat as unverified")
        return {"ok": not reasons, "reasons": reasons, "flags": flags}
