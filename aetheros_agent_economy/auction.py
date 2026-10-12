"""Capability auction abstraction (spec section 9).

Optional bidding over the REAL Quote/Offer/Contract machinery: providers
submit price/capacity/SLA/availability/estimates, AetherOS compares.
This is offer comparison, NOT a financial auction — no clearing price,
no winner-pays dynamics, no real auction infrastructure is claimed.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore


@dataclass
class Bid:
    bid_id: str = ""
    round_id: str = ""
    agent_id: str = ""
    service_id: str = ""
    price_minor: int = 0
    currency: str = "USD"
    capacity: Dict[str, Any] = field(default_factory=dict)
    sla: Dict[str, Any] = field(default_factory=dict)
    availability: str = "unknown"
    execution_estimate_s: Optional[float] = None
    quote_id: str = ""       # backing market Quote, when present
    offer_id: str = ""       # backing market Offer, when present
    at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bid":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"


class AuctionRound:
    """One comparison round. Deterministic ranking by explicit rule."""

    RULES = ("lowest_price", "fastest_estimate", "best_sla")

    def __init__(self, home: Path, capability_id: str,
                 rule: str = "lowest_price",
                 currency: str = "USD") -> None:
        if rule not in self.RULES:
            raise ValueError(f"bad rule: {rule!r}")
        self._store = JsonStore(Path(home) / "auction_rounds.json")
        self.round_id = _new_id("round")
        self.capability_id = capability_id
        self.rule = rule
        self.currency = currency
        self._bids: List[Bid] = []
        self.open = True

    def submit(self, bid: Bid) -> Bid:
        if not self.open:
            raise ValueError("round closed")
        if not bid.agent_id or not bid.service_id:
            raise ValueError("agent_id and service_id required")
        if not isinstance(bid.price_minor, int) or bid.price_minor < 0 \
                or isinstance(bid.price_minor, bool):
            raise ValueError("price_minor must be a non-negative int")
        if bid.currency != self.currency:
            raise ValueError(
                f"cross-currency bid {bid.currency} refused (round is {self.currency})")
        if not bid.bid_id:
            bid.bid_id = _new_id("bid")
        bid.round_id = self.round_id
        self._bids.append(bid)
        return bid

    def rank(self) -> List[Dict[str, Any]]:
        """Rank WITHOUT side effects. Ties break by agent_id (deterministic)."""
        rows = []
        for b in self._bids:
            key = b.price_minor
            if self.rule == "fastest_estimate":
                key = b.execution_estimate_s if b.execution_estimate_s is not None \
                    else float("inf")
            elif self.rule == "best_sla":
                key = -len(b.sla)  # more declared SLA terms ranks first; ties by price
                rows.append((key, b.price_minor, b.agent_id, b))
                continue
            rows.append((key, b.price_minor, b.agent_id, b))
        rows.sort(key=lambda r: (r[0], r[1], r[2]))
        return [{"rank": i + 1, "bid": b.to_dict()} for i, (_, _, _, b) in enumerate(rows)]

    def close(self, selected_bid_id: str = "",
              reason: str = "") -> Dict[str, Any]:
        """Close the round. Selection is a comparison outcome recorded for
        audit — actual procurement still goes through quote/contract/budget
        gates (this layer never spends)."""
        self.open = False
        ranked = self.rank()
        selected = next((r for r in ranked if r["bid"]["bid_id"] == selected_bid_id), None)
        record = {"round_id": self.round_id, "capability_id": self.capability_id,
                  "rule": self.rule, "currency": self.currency,
                  "bids": [b.to_dict() for b in self._bids],
                  "ranking": [{"rank": r["rank"], "bid_id": r["bid"]["bid_id"],
                               "agent_id": r["bid"]["agent_id"],
                               "price_minor": r["bid"]["price_minor"]} for r in ranked],
                  "selected_bid_id": selected_bid_id if selected else "",
                  "reason": reason[:500], "at": time.time(),
                  "note": "comparison only; procurement requires quote/contract/budget gates"}
        self._store.put(self.round_id, record)
        return record
