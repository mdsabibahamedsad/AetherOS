"""Root-cause analysis for repeated failures.

Tracks failure chains: trigger → first failure → dependency → propagation →
recovery attempts → final outcome.  Confidence is never overclaimed:

    CONFIRMED  — reproduced, exact line/path identified, fix verified
    LIKELY     — strong evidence, dominant hypothesis
    POSSIBLE   — plausible, no decisive evidence
    UNKNOWN    — insufficient evidence

The analyzer NEVER asserts root cause without evidence.  It aggregates
recovery events and watchdog failures and emits hypotheses with confidence.
"""

from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RCAConfidence(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class FailureAnalysis:
    component: str
    trigger: str = ""
    first_failure: float = 0.0
    occurrences: int = 0
    dependencies: List[str] = field(default_factory=list)
    propagation: List[str] = field(default_factory=list)
    recovery_attempts: int = 0
    recovery_outcomes: List[str] = field(default_factory=list)
    final_outcome: str = ""
    confidence: RCAConfidence = RCAConfidence.UNKNOWN
    hypothesis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "trigger": self.trigger,
            "first_failure": self.first_failure,
            "occurrences": self.occurrences,
            "dependencies": self.dependencies,
            "propagation": self.propagation,
            "recovery_attempts": self.recovery_attempts,
            "recovery_outcomes": self.recovery_outcomes,
            "final_outcome": self.final_outcome,
            "confidence": self.confidence.value,
            "hypothesis": self.hypothesis,
        }


class RootCauseAnalyzer:
    """Aggregates failure evidence per component and derives hypotheses.

    Usage::

        rca = get_root_cause_analyzer()
        rca.record(component="gateway", failure_type="CRASH", trigger="oom")
        rca.record_recovery("gateway", "success")
        analysis = rca.analyze("gateway")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._failures: Dict[str, FailureAnalysis] = {}
        self._recent_events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, component: str, failure_type: str,
               trigger: str = "", dependency: str = "") -> None:
        now = time.time()
        with self._lock:
            fa = self._failures.setdefault(component, FailureAnalysis(
                component=component, first_failure=now,
            ))
            fa.occurrences += 1
            fa.trigger = trigger or fa.trigger
            fa.final_outcome = failure_type
            if dependency and dependency not in fa.dependencies:
                fa.dependencies.append(dependency)
            self._recent_events.append({
                "component": component, "type": failure_type,
                "trigger": trigger, "dependency": dependency, "at": now,
            })
            self._recent_events = self._recent_events[-500:]

    def record_recovery(self, component: str, outcome: str) -> None:
        with self._lock:
            fa = self._failures.setdefault(component, FailureAnalysis(component=component))
            fa.recovery_attempts += 1
            fa.recovery_outcomes.append(outcome)
            fa.final_outcome = outcome

    def record_propagation(self, component: str, affected: str) -> None:
        with self._lock:
            fa = self._failures.setdefault(component, FailureAnalysis(component=component))
            if affected not in fa.propagation:
                fa.propagation.append(affected)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self, component: str) -> Optional[FailureAnalysis]:
        with self._lock:
            fa = self._failures.get(component)
            if fa is None:
                return None
            # Derive confidence from evidence.
            fa.confidence = self._confidence_for(fa)
            fa.hypothesis = self._hypothesis_for(fa)
            return FailureAnalysis(**fa.to_dict())

    def analyze_all(self) -> List[Dict[str, Any]]:
        return [self.analyze(c).to_dict() for c in self.components()]

    def components(self) -> List[str]:
        with self._lock:
            return sorted(self._failures.keys())

    # ------------------------------------------------------------------
    # Confidence derivation (conservative)
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_for(fa: FailureAnalysis) -> RCAConfidence:
        if fa.occurrences >= 3 and fa.recovery_attempts >= 3:
            return RCAConfidence.LIKELY
        if fa.occurrences >= 1 and fa.trigger:
            return RCAConfidence.POSSIBLE
        return RCAConfidence.UNKNOWN

    @staticmethod
    def _hypothesis_for(fa: FailureAnalysis) -> str:
        parts = []
        if fa.trigger:
            parts.append(f"trigger: {fa.trigger}")
        if fa.dependencies:
            parts.append(f"dependencies: {', '.join(fa.dependencies)}")
        if fa.propagation:
            parts.append(f"propagation: {', '.join(fa.propagation)}")
        if fa.recovery_outcomes:
            parts.append(f"recovery: {', '.join(fa.recovery_outcomes[-5:])}")
        return "; ".join(parts) if parts else "insufficient evidence"

    def summary(self) -> Dict[str, Any]:
        analyses = self.analyze_all()
        return {
            "total": len(analyses),
            "confirmed": sum(1 for a in analyses if a["confidence"] == "CONFIRMED"),
            "likely": sum(1 for a in analyses if a["confidence"] == "LIKELY"),
            "possible": sum(1 for a in analyses if a["confidence"] == "POSSIBLE"),
            "unknown": sum(1 for a in analyses if a["confidence"] == "UNKNOWN"),
            "analyses": analyses,
        }


_rca: Optional[RootCauseAnalyzer] = None
_rca_lock = threading.Lock()


def get_root_cause_analyzer() -> RootCauseAnalyzer:
    """Return the process-wide RootCauseAnalyzer singleton."""
    global _rca
    if _rca is None:
        with _rca_lock:
            if _rca is None:
                _rca = RootCauseAnalyzer()
    return _rca