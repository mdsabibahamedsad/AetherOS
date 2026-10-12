"""Example external provider (test/dev reference, NOT production).

Implements a fixed-price quote + in-memory settlement by composing the
built-in machinery. Shows exactly which methods a real integration must
provide. Amounts are minor units; no real money moves here.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_agent_market import schemas as S
from aetheros_agent_market.payments import _BaseProvider


class FixedPriceProvider(_BaseProvider):
    """Fixed price per service id. Reference implementation only."""

    def __init__(self, home: Path, prices: Optional[Dict[str, int]] = None) -> None:
        super().__init__(home, "external:fixed-price")
        self.prices = prices or {}

    def quote(self, service_id: str, inputs: Dict[str, Any]) -> S.Quote:
        if service_id not in self.prices:
            from aetheros_agent_market.payments import PaymentError
            raise PaymentError(f"no price configured for {service_id}")
        return S.Quote(
            quote_id=S.new_id("quote"), service_id=service_id,
            agent_id=str(inputs.get("agent_id", "")),
            price_minor=self.prices[service_id], currency="USD",
            estimated_duration_s=60.0, included_retries=1,
            expires_at=time.time() + 600,
            idempotency_key=S.new_id("idem"))

    def authorize(self, quote: S.Quote, idempotency_key: str) -> S.Transaction:
        from aetheros_agent_market.payments import PaymentError
        existing = self._by_idem(idempotency_key)
        if existing:
            return existing
        return self._save(S.Transaction(
            transaction_id=S.new_id("tx"), contract_id=quote.contract_id,
            agent_id=quote.agent_id, provider=self.name,
            amount_minor=quote.total_minor, currency=quote.currency,
            status="authorized", idempotency_key=idempotency_key))

    def capture(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        from aetheros_agent_market.payments import PaymentError
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        existing = self._by_idem(f"capture:{idempotency_key}")
        if existing is not None and existing.transaction_id == transaction_id \
                and existing.status == "captured":
            return existing
        if tx.status != "authorized":
            raise PaymentError(f"cannot capture from {tx.status}")
        tx.status = "captured"
        saved = self._save(tx)
        self._idem[f"capture:{idempotency_key}"] = saved.transaction_id
        return saved

    def refund(self, transaction_id: str, amount_minor: Optional[int],
               idempotency_key: str, reason: str = "") -> S.Transaction:
        from aetheros_agent_market.payments import PaymentError
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status not in ("authorized", "captured"):
            raise PaymentError(f"cannot refund from {tx.status}")
        tx.status = "refunded"
        return self._save(tx)

    def void(self, transaction_id: str, idempotency_key: str) -> S.Transaction:
        from aetheros_agent_market.payments import PaymentError
        tx = self.get_transaction(transaction_id)
        if tx is None:
            raise PaymentError("unknown transaction")
        if tx.status != "authorized":
            raise PaymentError(f"cannot void from {tx.status}")
        tx.status = "voided"
        return self._save(tx)
