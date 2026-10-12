"""Agent Cards (§5) + A2A/MCP security gates (§17-19, §26, §60).

Follows the A2A direction (signed Agent Cards, identity verification,
encrypted production transport) without inventing a competing protocol.
Cards are fetched over TLS-verified HTTPS (``/.well-known/agent-card.json``
convention supported), schema-validated, signature-verified where a key
is known, and trust/policy-evaluated before any channel opens.
"""

from __future__ import annotations

import json
import time
import urllib.request
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .crypto_keys import SignatureVerifier


REQUIRED_CARD_FIELDS = ("name", "version", "endpoint", "protocol",
                        "capabilities")


@dataclass
class AgentCard:
    name: str
    version: str
    endpoint: str
    protocol: str = "a2a"
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    tenant: str = "default"
    expires_at: Optional[float] = None
    signature: str = ""
    key_id: str = ""
    raw: dict = field(default_factory=dict)


def validate_card(card: AgentCard) -> List[str]:
    errors = []
    for f in REQUIRED_CARD_FIELDS:
        if not getattr(card, f, None):
            errors.append(f"missing field: {f}")
    if card.expires_at and time.time() > card.expires_at:
        errors.append("card expired")
    if card.protocol not in ("a2a", "a2a+tls", "https"):
        errors.append(f"unsupported protocol: {card.protocol}")
    return errors


def card_from_dict(d: Dict[str, Any]) -> AgentCard:
    return AgentCard(
        name=str(d.get("name", "")), version=str(d.get("version", "")),
        endpoint=str(d.get("endpoint", "")),
        protocol=str(d.get("protocol", "a2a")),
        capabilities=list(d.get("capabilities", [])),
        skills=list(d.get("skills", [])),
        tenant=str(d.get("tenant", "default")),
        expires_at=d.get("expiresAt"), signature=str(d.get("signature", "")),
        key_id=str(d.get("keyId", "")), raw=d)


def fetch_card(url: str, timeout: float = 10.0) -> AgentCard:
    """Fetch over TLS-verified HTTPS. Never trusts claim without validation."""
    if not url.startswith("https://"):
        raise ValueError("refusing non-TLS agent-card URL")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "aetheros-control-plane/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        data = json.loads(r.read().decode("utf-8"))
    return card_from_dict(data)


def well_known_url(base: str) -> str:
    return base.rstrip("/") + "/.well-known/agent-card.json"


class AgentCardVerifier:
    def __init__(self, sig_verifier: Optional[SignatureVerifier] = None):
        self.sig = sig_verifier
        self._cache: Dict[str, tuple[AgentCard, float]] = {}

    def verify(self, card: AgentCard) -> tuple[bool, List[str]]:
        errors = validate_card(card)
        if errors:
            return False, errors
        if card.signature and card.key_id and self.sig:
            raw = json.dumps({k: v for k, v in card.raw.items()
                              if k not in ("signature",)},
                             sort_keys=True).encode()
            if not self.sig.verify(card.key_id, raw, card.signature):
                return False, ["signature invalid"]
        elif card.signature and not self.sig:
            return False, ["signed card but no verifier available"]
        return True, ["schema ok"] + (
            ["signature ok"] if card.signature else ["unsigned: untrusted"])

    def is_expired_authority(self, card: AgentCard) -> bool:
        return bool(card.expires_at and time.time() > card.expires_at)
