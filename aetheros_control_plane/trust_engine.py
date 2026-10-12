"""Trust engine (§6-7). Multi-dimensional, evidence-weighted.

Trust is NEVER one arbitrary number internally: each of the 10 dimensions
carries its own 0..1 score; the outcome derives from the weighted floor
plus policy floors. Outcomes always carry machine-readable reasons.
Trust levels T0..T5 are earned via evidence; nothing auto-assigns high
trust (§7). Admins may override level semantics via ``level_thresholds``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import (TRUST_DIMENSIONS, TrustAssessment, TrustEvidence,
                     TrustLevel, TrustOutcome, trust_at_least)


@dataclass
class TrustRecord:
    identity_id: str
    level: TrustLevel = TrustLevel.T0_UNKNOWN
    evidence: List[TrustEvidence] = field(default_factory=list)
    quarantined: bool = False
    updated_at: float = field(default_factory=time.time)


class TrustEngine:
    def __init__(self, level_thresholds: Optional[Dict[str, float]] = None):
        # floor score required to EARN each level (admin-customizable, §7).
        self.level_thresholds = level_thresholds or {
            "T1": 0.15, "T2": 0.40, "T3": 0.60, "T4": 0.80, "T5": 0.95,
        }
        self._records: Dict[str, TrustRecord] = {}
        self._events: List[dict] = []

    # -- evidence ----------------------------------------------------------
    def record(self) -> Dict[str, TrustRecord]:
        return self._records

    def add_evidence(self, identity_id: str, dimension: str, score: float,
                     reason: str = "", source: str = "",
                     weight: float = 1.0) -> TrustRecord:
        assert dimension in TRUST_DIMENSIONS, f"unknown dimension {dimension}"
        rec = self._records.setdefault(identity_id, TrustRecord(identity_id))
        rec.evidence.append(TrustEvidence(
            dimension=dimension, score=max(0.0, min(1.0, score)),
            weight=weight, reason=reason, source=source))
        rec.updated_at = time.time()
        self._events.append({"type": "trust.evidence", "identity": identity_id,
                             "dimension": dimension, "at": rec.updated_at})
        return rec

    def penalize(self, identity_id: str, dimension: str,
                 reason: str) -> TrustRecord:
        return self.add_evidence(identity_id, dimension, 0.0, reason,
                                 source="behavior-monitor", weight=2.0)

    # -- assessment ----------------------------------------------------------
    def assess(self, identity_id: str,
               required: TrustLevel = TrustLevel.T2_VERIFIED) -> TrustAssessment:
        rec = self._records.get(identity_id)
        per_dim: Dict[str, float] = {}
        reasons: List[str] = []
        if rec is None:
            return TrustAssessment(identity_id, {}, TrustOutcome.DENY,
                                   ["no trust record: unknown identity"],
                                   required, TrustLevel.T0_UNKNOWN)
        if rec.quarantined:
            return TrustAssessment(identity_id, {}, TrustOutcome.QUARANTINE,
                                   ["identity quarantined"], required,
                                   rec.level)
        for dim in TRUST_DIMENSIONS:
            items = [e for e in rec.evidence if e.dimension == dim]
            if not items:
                per_dim[dim] = 0.0
                continue
            w = sum(e.weight for e in items)
            per_dim[dim] = sum(e.score * e.weight for e in items) / w
        floor = min(per_dim.values()) if per_dim else 0.0
        earned = self._level_for_floor(floor)
        rec.level = earned
        reasons.append(f"floor={floor:.2f} earned={earned.value}")
        for dim, v in per_dim.items():
            if v < 0.3:
                reasons.append(f"weak dimension: {dim}={v:.2f}")
        if not trust_at_least(earned, required):
            return TrustAssessment(identity_id, per_dim, TrustOutcome.DENY,
                                   reasons + [f"requires {required.value}"],
                                   required, earned)
        if earned in (TrustLevel.T0_UNKNOWN, TrustLevel.T1_UNVERIFIED):
            return TrustAssessment(identity_id, per_dim,
                                   TrustOutcome.REQUIRE_APPROVAL,
                                   reasons + ["low trust: approval required"],
                                   required, earned)
        if any(v < 0.4 for v in per_dim.values()):
            return TrustAssessment(identity_id, per_dim,
                                   TrustOutcome.ALLOW_WITH_LIMITS,
                                   reasons + ["limits: weak dimensions"],
                                   required, earned)
        return TrustAssessment(identity_id, per_dim, TrustOutcome.ALLOW,
                               reasons, required, earned)

    def _level_for_floor(self, floor: float) -> TrustLevel:
        level = TrustLevel.T0_UNKNOWN
        for name, lvl in (("T1", TrustLevel.T1_UNVERIFIED),
                          ("T2", TrustLevel.T2_VERIFIED),
                          ("T3", TrustLevel.T3_TRUSTED),
                          ("T4", TrustLevel.T4_HIGH_TRUST),
                          ("T5", TrustLevel.T5_SYSTEM_TRUST)):
            if floor >= self.level_thresholds.get(name, 1.0):
                level = lvl
        return level

    def quarantine(self, identity_id: str, reason: str) -> None:
        rec = self._records.setdefault(identity_id, TrustRecord(identity_id))
        rec.quarantined = True
        self._events.append({"type": "trust.quarantined",
                             "identity": identity_id, "reason": reason,
                             "at": time.time()})

    def release(self, identity_id: str) -> None:
        rec = self._records.setdefault(identity_id, TrustRecord(identity_id))
        rec.quarantined = False
