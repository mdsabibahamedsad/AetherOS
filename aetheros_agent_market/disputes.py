"""Dispute engine (spec section 18).

Lifecycle: open -> under_review -> evidence_requested -> resolved |
refunded | rejected | escalated. Evidence is immutable (referenced by
id, never embedded). Transitions are validated; every change appends
history. Resolution actions (refund) execute through the payment
provider + ledger, never by editing state.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

_TRANSITIONS = {
    "open": {"under_review", "rejected", "escalated"},
    "under_review": {"evidence_requested", "resolved", "refunded", "rejected", "escalated"},
    "evidence_requested": {"under_review", "resolved", "refunded", "rejected", "escalated"},
    "resolved": set(),
    "refunded": set(),
    "rejected": set(),
    "escalated": {"under_review", "resolved", "refunded", "rejected"},
}


class DisputeEngine:
    def __init__(self, home: Path) -> None:
        self._disputes = JsonStore(Path(home) / "disputes.json")

    def open(self, dispute: S.Dispute, opened_by: str = "") -> S.Dispute:
        errors = dispute.validate()
        if errors:
            raise ValueError(f"invalid dispute: {errors}")
        if not dispute.dispute_id:
            dispute.dispute_id = S.new_id("dispute")
        dispute.status = "open"
        dispute.history.append({"at": time.time(), "to": "open",
                                "by": opened_by, "note": dispute.description[:300]})
        self._disputes.put(dispute.dispute_id, dispute.to_dict())
        return dispute

    def get(self, dispute_id: str) -> Optional[S.Dispute]:
        raw = self._disputes.get(dispute_id)
        return S.Dispute.from_dict(raw) if raw else None

    def list(self, status: str = "") -> List[S.Dispute]:
        out = []
        for raw in self._disputes.values():
            d = S.Dispute.from_dict(raw)
            if status and d.status != status:
                continue
            out.append(d)
        return sorted(out, key=lambda d: d.created_at, reverse=True)

    def transition(self, dispute_id: str, to: str, by: str = "",
                   note: str = "") -> S.Dispute:
        d = self.get(dispute_id)
        if d is None:
            raise KeyError(f"unknown dispute: {dispute_id}")
        if to not in _TRANSITIONS.get(d.status, set()):
            raise ValueError(f"illegal dispute transition {d.status} -> {to}")
        d.status = to
        d.history.append({"at": time.time(), "to": to, "by": by, "note": note[:500]})
        d.updated_at = time.time()
        self._disputes.put(dispute_id, d.to_dict())
        return d

    def attach_evidence(self, dispute_id: str, evidence_id: str,
                        by: str = "") -> S.Dispute:
        d = self.get(dispute_id)
        if d is None:
            raise KeyError(f"unknown dispute: {dispute_id}")
        if d.status in ("resolved", "refunded", "rejected"):
            raise ValueError(f"dispute {d.status} is terminal; evidence frozen")
        if evidence_id not in d.evidence_ids:
            d.evidence_ids.append(evidence_id)
        d.history.append({"at": time.time(), "to": d.status, "by": by,
                          "note": f"evidence attached: {evidence_id}"})
        d.updated_at = time.time()
        self._disputes.put(dispute_id, d.to_dict())
        return d

    def resolve(self, dispute_id: str, resolution: str,
                refund_fn: Optional[Callable[[S.Dispute], None]] = None,
                by: str = "") -> S.Dispute:
        """Resolve; if resolution demands a refund, execute it via the
        provided callback (provider.refund + ledger) BEFORE marking refunded."""
        d = self.get(dispute_id)
        if d is None:
            raise KeyError(f"unknown dispute: {dispute_id}")
        d.resolution = resolution[:2000]
        if resolution.startswith("refund"):
            if refund_fn is None:
                raise ValueError("refund resolution requires a refund callback")
            refund_fn(d)  # must succeed or the dispute is NOT marked refunded
            return self.transition(dispute_id, "refunded", by=by, note=resolution)
        return self.transition(dispute_id, "resolved", by=by, note=resolution)
