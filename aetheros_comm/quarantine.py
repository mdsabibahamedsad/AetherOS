"""
Agent Communication Fabric — quarantine and recovery (master spec steps 60
and 61).

When an agent spoofs identity, repeatedly violates authorization, sends
malformed messages, attempts privilege escalation, or triggers abnormal
traffic / security controls, the fabric quarantines it: privileged requests
stop, temporary authorization is revoked, communication is blocked, evidence
is preserved, and the security runtime is notified.

Recovery from quarantine is policy-controlled — trust is never restored
automatically (step 61). Re-activation requires health, identity, and
configuration validation plus an explicit security review.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .audit import CommAudit

logger = logging.getLogger(__name__)


@dataclass
class QuarantineRecord:
    agent_id: str
    reason: str
    evidence: List[str] = field(default_factory=list)
    quarantined_at: float = field(default_factory=time.time)
    violations: int = 1


class QuarantineController:
    """Tracks violations and enforces the quarantine / recovery lifecycle."""

    #: Violation thresholds that trigger quarantine.
    MAX_AUTHORIZATION_VIOLATIONS = 3
    MAX_MALFORMED_MESSAGES = 5
    MAX_SECURITY_VIOLATIONS = 2

    def __init__(self, audit: Optional[CommAudit] = None) -> None:
        self._audit = audit or CommAudit()
        self._records: Dict[str, QuarantineRecord] = {}
        self._counters: Dict[str, Dict[str, int]] = {}
        self._recoveries: Dict[str, int] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Violation accounting (step 60: "repeatedly ...")
    # ------------------------------------------------------------------

    def record_violation(self, agent_id: str, kind: str,
                         evidence: str = "") -> bool:
        """Record a violation; returns True if it triggers quarantine."""
        with self._lock:
            counters = self._counters.setdefault(agent_id, {})
            counters[kind] = counters.get(kind, 0) + 1
            if counters[kind] >= self._threshold(kind):
                self._quarantine_locked(agent_id, kind, evidence)
                return True
        return False

    @staticmethod
    def _threshold(kind: str) -> int:
        return {
            "authorization": QuarantineController.MAX_AUTHORIZATION_VIOLATIONS,
            "malformed": QuarantineController.MAX_MALFORMED_MESSAGES,
            "security": QuarantineController.MAX_SECURITY_VIOLATIONS,
        }.get(kind, 5)

    # ------------------------------------------------------------------
    # Quarantine (step 60)
    # ------------------------------------------------------------------

    def quarantine(self, agent_id: str, reason: str,
                   evidence: Optional[List[str]] = None,
                   registry=None) -> bool:
        """Quarantine an agent immediately (bypasses violation counting)."""
        with self._lock:
            self._quarantine_locked(agent_id, reason,
                                    "; ".join(evidence or []))
        if registry is not None:
            registry.quarantine(agent_id)
        return True

    def _quarantine_locked(self, agent_id: str, reason: str,
                           evidence: str) -> None:
        record = self._records.get(agent_id)
        if record is None:
            record = QuarantineRecord(agent_id=agent_id, reason=reason)
            self._records[agent_id] = record
        else:
            record.violations += 1
            if evidence:
                record.evidence.append(evidence)
        logger.warning("Agent quarantined: %s (%s)", agent_id, reason)
        self._audit.quarantine(agent_id, reason)

    def is_quarantined(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._records

    def get_record(self, agent_id: str) -> Optional[QuarantineRecord]:
        with self._lock:
            return self._records.get(agent_id)

    def list_quarantined(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"agent_id": r.agent_id, "reason": r.reason,
                 "quarantined_at": r.quarantined_at,
                 "violations": r.violations, "evidence": list(r.evidence)}
                for r in self._records.values()
            ]

    # ------------------------------------------------------------------
    # Recovery (step 61) — policy-controlled reactivation
    # ------------------------------------------------------------------

    def recovery_required(self, agent_id: str) -> bool:
        return self.is_quarantined(agent_id)

    def reactivate(self, agent_id: str, *, health_ok: bool,
                   identity_ok: bool, config_ok: bool,
                   security_review: bool, registry=None) -> bool:
        """Re-activate a quarantined agent only when every gate passes.

        Trust is never restored automatically (step 61). All four gates must
        be explicitly satisfied.
        """
        with self._lock:
            if agent_id not in self._records:
                return False
            if not (health_ok and identity_ok and config_ok and security_review):
                self._recoveries[agent_id] = self._recoveries.get(agent_id, 0) + 1
                logger.warning(
                    "Recovery for %s denied: health=%s identity=%s config=%s "
                    "security_review=%s", agent_id, health_ok, identity_ok,
                    config_ok, security_review)
                return False
            del self._records[agent_id]
            self._counters.pop(agent_id, None)
        if registry is not None:
            registry.reactivate(agent_id)
        self._audit.recovery(agent_id, "reactivated")
        logger.info("Agent %s reactivated after security review", agent_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "quarantined": list(self._records.keys()),
                "count": len(self._records),
                "recovery_attempts": dict(self._recoveries),
            }