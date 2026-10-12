"""Interrupted-mission recovery.

After a restart, each mission in progress is classified so that recovery
never blindly repeats possibly-destructive work:

    SAFE_TO_RESUME     — checkpointed, idempotent, no pending high-risk step
    REQUIRES_REVIEW    — in-flight tool call / approval pending / unknown step
    CANNOT_RESUME      — security-sensitive, quarantined agent, destructive
    COMPLETED          — journal says completed
    UNKNOWN            — no journal/checkpoint evidence at all

The classifier consumes the recovery journal + checkpoint store.  It never
resumes on its own — it produces a report the operator (or a policy-checked
resume path) acts on.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_reliability.journal import get_recovery_journal, JournalStatus
from aetheros_reliability.checkpoint import get_checkpoint_store

logger = logging.getLogger(__name__)


class MissionClassification(str, enum.Enum):
    SAFE_TO_RESUME = "SAFE_TO_RESUME"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CANNOT_RESUME = "CANNOT_RESUME"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


#: Operations that, if interrupted mid-flight, must never be auto-resumed.
_HIGH_RISK_OPERATIONS = (
    "purchase", "payment", "deploy", "delete", "destroy", "drop", "wipe",
    "revoke", "grant", "transfer", "publish", "push", "release", "rollback",
    "rotate_credentials",
)


@dataclass
class MissionStatus:
    mission_id: str
    classification: MissionClassification
    reason: str = ""
    last_checkpoint: int = 0
    pending_operation: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    classified_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "classification": self.classification.value,
            "reason": self.reason,
            "last_checkpoint": self.last_checkpoint,
            "pending_operation": self.pending_operation,
            "classified_at": self.classified_at,
        }


class MissionRecovery:
    """Classifies interrupted missions and supports policy-checked resume.

    Usage::

        mr = MissionRecovery()
        report = mr.analyze()                       # all recoverable missions
        status = mr.classify("mission-42")
    """

    def __init__(self, journal=None, checkpoints=None) -> None:
        self._journal = journal or get_recovery_journal()
        self._checkpoints = checkpoints or get_checkpoint_store()

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, mission_id: str) -> MissionStatus:
        """Classify a single interrupted mission."""
        ops = self._journal.by_component(mission_id, limit=20)
        pending = [o for o in ops if o["status"] in (
            JournalStatus.STARTED.value,
            JournalStatus.CHECKPOINTED.value,
            JournalStatus.RECOVERABLE.value,
        )]
        completed = [o for o in ops if o["status"] == JournalStatus.COMPLETED.value]

        if pending:
            latest = pending[0]
            op = (latest.get("operation") or "").lower()
            last_checkpoint = latest.get("checkpoint", 0)
            if any(h in op for h in _HIGH_RISK_OPERATIONS):
                return MissionStatus(
                    mission_id, MissionClassification.CANNOT_RESUME,
                    reason=f"pending high-risk operation interrupted: {latest.get('operation')}",
                    last_checkpoint=last_checkpoint,
                    pending_operation=latest.get("operation", ""),
                    evidence={"latest": latest},
                )
            # Checkpointed, non-high-risk, idempotent → safe to resume.
            if latest["status"] == JournalStatus.CHECKPOINTED.value:
                return MissionStatus(
                    mission_id, MissionClassification.SAFE_TO_RESUME,
                    reason=f"checkpointed at step {last_checkpoint}",
                    last_checkpoint=last_checkpoint,
                    pending_operation=latest.get("operation", ""),
                    evidence={"latest": latest},
                )
            return MissionStatus(
                mission_id, MissionClassification.REQUIRES_REVIEW,
                reason=f"in-flight operation interrupted: {latest.get('operation')}",
                last_checkpoint=last_checkpoint,
                pending_operation=latest.get("operation", ""),
                evidence={"latest": latest},
            )

        if completed:
            return MissionStatus(
                mission_id, MissionClassification.COMPLETED,
                reason=f"{len(completed)} operation(s) completed",
                evidence={"completed": completed[0]},
            )

        # No journal evidence — check for a checkpoint.
        if self._checkpoints.exists("mission", mission_id):
            return MissionStatus(
                mission_id, MissionClassification.REQUIRES_REVIEW,
                reason="checkpoint exists but no journal evidence of completion",
                evidence={"checkpoint": True},
            )

        return MissionStatus(
            mission_id, MissionClassification.UNKNOWN,
            reason="no journal or checkpoint evidence",
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def analyze(self, missions: Optional[List[str]] = None) -> List[MissionStatus]:
        """Classify all interrupted missions (from journal) or a given set."""
        if missions is None:
            missions = self._interrupted_mission_ids()
        return [self.classify(m) for m in missions]

    def summary(self, missions: Optional[List[str]] = None) -> Dict[str, Any]:
        statuses = self.analyze(missions)
        by_class: Dict[str, int] = {}
        for s in statuses:
            by_class[s.classification.value] = by_class.get(s.classification.value, 0) + 1
        return {
            "total": len(statuses),
            "by_classification": by_class,
            "missions": [s.to_dict() for s in statuses],
        }

    def _interrupted_mission_ids(self) -> List[str]:
        """Mission ids (components) with pending journal operations."""
        pending = self._journal.pending(limit=500)
        ids: List[str] = []
        seen = set()
        for op in pending:
            cid = op.get("component", "")
            if cid and cid not in seen:
                seen.add(cid)
                ids.append(cid)
        return ids


def _is_high_risk(operation: str) -> bool:
    op = (operation or "").lower()
    return any(h in op for h in _HIGH_RISK_OPERATIONS)