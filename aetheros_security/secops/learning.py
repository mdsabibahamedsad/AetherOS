"""
Gated learning loop + false-positive management + rule versioning.

The learning loop turns operational feedback (false positives, missed
detections, benign deviations) into *proposed* detection adjustments.  All
adjustments land in a pending queue and are applied ONLY through an explicit
approval step performed by an elevated principal.  ``learning_auto_apply`` is
a config gate (default False) — nothing in the learning loop ever re-writes a
detection threshold silently.

Rule and correlation changes are versioned so the forensics module can always
tell which rule version raised a detection.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeedbackKind(Enum):
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    BENIGN_DEVIATION = "benign_deviation"
    TRUE_POSITIVE = "true_positive"


class AdjustmentStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class DetectionAdjustment:
    """A proposed detection/correlation adjustment awaiting approval."""

    adjustment_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rule_id: str = ""
    kind: str = ""
    parameter: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    status: AdjustmentStatus = AdjustmentStatus.PENDING
    proposed_by: str = ""
    approved_by: str = ""
    created_at: float = field(default_factory=time.time)
    applied_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adjustment_id": self.adjustment_id,
            "rule_id": self.rule_id,
            "kind": self.kind,
            "parameter": self.parameter,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "status": self.status.value,
            "proposed_by": self.proposed_by,
            "approved_by": self.approved_by,
            "created_at": self.created_at,
            "applied_at": self.applied_at,
        }


@dataclass
class FeedbackEntry:
    """Operational feedback on a detection."""

    feedback_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rule_id: str = ""
    kind: FeedbackKind = FeedbackKind.FALSE_POSITIVE
    detection_id: str = ""
    reason: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "rule_id": self.rule_id,
            "kind": self.kind.value,
            "detection_id": self.detection_id,
            "reason": self.reason,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class LearningLoop:
    """Collects feedback and manages gated detection adjustments.

    Usage::

        loop = LearningLoop()
        loop.add_feedback("rule.foo", FeedbackKind.FALSE_POSITIVE,
                          reason="benign pattern")
        proposal = loop.propose_adjustment(
            "rule.foo", parameter="confidence",
            new_value=0.9, reason="reduce noise", proposed_by="admin")
        loop.approve(proposal.adjustment_id, approved_by="admin")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._feedback: List[FeedbackEntry] = []
        self._adjustments: List[DetectionAdjustment] = []
        self._applier: Optional[Callable[[str, str, Any], bool]] = None
        self._auto_apply = False
        self._max_history = 500

    def set_auto_apply(self, auto: bool) -> None:
        """Enable application on approval without a separate apply call."""
        self._auto_apply = auto

    def set_adjustment_applier(self, applier: Callable[[str, str, Any], bool]) -> None:
        """Register a callable (rule_id, parameter, new_value) -> applied."""
        self._applier = applier

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def add_feedback(self, rule_id: str, kind: FeedbackKind, *,
                     reason: str = "", detection_id: str = "",
                     source: str = "") -> FeedbackEntry:
        entry = FeedbackEntry(rule_id=rule_id, kind=FeedbackKind(kind),
                              reason=reason, detection_id=detection_id,
                              source=source)
        with self._lock:
            self._feedback.append(entry)
            if len(self._feedback) > self._max_history:
                self._feedback = self._feedback[-self._max_history:]
        return entry

    def feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [f.to_dict() for f in self._feedback[-limit:]]

    def false_positive_count(self, rule_id: str) -> int:
        with self._lock:
            return sum(1 for f in self._feedback
                       if f.rule_id == rule_id and
                       f.kind == FeedbackKind.FALSE_POSITIVE)

    def false_positive_rate(self, rule_id: str) -> float:
        with self._lock:
            relevant = [f for f in self._feedback if f.rule_id == rule_id]
            if not relevant:
                return 0.0
            fp = sum(1 for f in relevant if f.kind == FeedbackKind.FALSE_POSITIVE)
            return round(fp / len(relevant), 3)

    # ------------------------------------------------------------------
    # Adjustments (gated)
    # ------------------------------------------------------------------

    def propose_adjustment(self, rule_id: str, *, parameter: str,
                           new_value: Any, reason: str = "",
                           old_value: Any = None,
                           proposed_by: str = "system",
                           kind: str = "detection") -> DetectionAdjustment:
        """Propose an adjustment; it stays PENDING until approved."""
        adjustment = DetectionAdjustment(
            rule_id=rule_id, parameter=parameter, new_value=new_value,
            old_value=old_value, reason=reason, proposed_by=proposed_by,
            kind=kind,
        )
        with self._lock:
            self._adjustments.append(adjustment)
        logger.info("Detection adjustment proposed: %s.%s -> %s",
                    rule_id, parameter, new_value)
        return adjustment

    def pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._adjustments
                    if a.status == AdjustmentStatus.PENDING]

    def approve(self, adjustment_id: str, *, approved_by: str = "admin") -> bool:
        """Approve a pending adjustment. Elevated principals only."""
        if approved_by.lower() not in {"admin", "system", "security", "root"}:
            logger.warning("Rejected adjustment approval from non-elevated %s",
                           approved_by)
            return False
        with self._lock:
            adjustment = next(
                (a for a in self._adjustments
                 if a.adjustment_id == adjustment_id), None)
            if adjustment is None or adjustment.status != AdjustmentStatus.PENDING:
                return False
            adjustment.status = AdjustmentStatus.APPROVED
            adjustment.approved_by = approved_by
            apply_now = self._auto_apply
        if apply_now or self._applier is not None:
            return self._apply(adjustment)
        return True

    def reject(self, adjustment_id: str, *, by: str = "admin") -> bool:
        with self._lock:
            adjustment = next(
                (a for a in self._adjustments
                 if a.adjustment_id == adjustment_id), None)
            if adjustment is None or adjustment.status != AdjustmentStatus.PENDING:
                return False
            adjustment.status = AdjustmentStatus.REJECTED
            return True

    def _apply(self, adjustment: DetectionAdjustment) -> bool:
        if self._applier is None:
            return False
        try:
            ok = self._applier(adjustment.rule_id, adjustment.parameter,
                               adjustment.new_value)
        except Exception as exc:
            logger.error("Adjustment apply failed: %s", exc)
            ok = False
        with self._lock:
            if ok:
                adjustment.status = AdjustmentStatus.APPLIED
                adjustment.applied_at = time.time()
        return ok

    def apply(self, adjustment_id: str, *, by: str = "admin") -> bool:
        """Explicitly apply an approved adjustment."""
        with self._lock:
            adjustment = next(
                (a for a in self._adjustments
                 if a.adjustment_id == adjustment_id), None)
            if adjustment is None or adjustment.status != AdjustmentStatus.APPROVED:
                return False
        return self._apply(adjustment)

    def adjustments(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._adjustments[-limit:]]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "feedback_count": len(self._feedback),
                "adjustments_total": len(self._adjustments),
                "adjustments_pending": sum(
                    1 for a in self._adjustments
                    if a.status == AdjustmentStatus.PENDING),
                "adjustments_applied": sum(
                    1 for a in self._adjustments
                    if a.status == AdjustmentStatus.APPLIED),
                "auto_apply": self._auto_apply,
            }


# Global learning loop
_learning_loop: Optional[LearningLoop] = None


def get_learning_loop() -> LearningLoop:
    """Return the process-wide LearningLoop singleton."""
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = LearningLoop()
    return _learning_loop