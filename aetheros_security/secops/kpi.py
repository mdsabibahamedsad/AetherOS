"""
Security KPIs (MTTD, MTTR, detection quality).

KPIs are computed **only from real data** the SecOps layer has recorded —
never fabricated.  MTTD (mean time to detect) measures the gap between the
first anomalous event and the incident creation; MTTR (mean time to resolve)
measures incident open -> resolved duration; detection quality uses the
learning loop's false-positive feedback.

An incident with no recorded detection/creation provenance is excluded from
MTTD rather than assigned a fabricated value.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from .incidents import IncidentStatus, IncidentStore
from .learning import FeedbackKind, LearningLoop

logger = logging.getLogger(__name__)


class SecurityKPIs:
    """Deterministic KPIs over the incident store + learning loop.

    Usage::

        kpi = SecurityKPIs()
        kpi.set_incident_store(store)
        kpi.set_learning_loop(loop)
        report = kpi.report()
    """

    def __init__(self) -> None:
        self._store: Optional[IncidentStore] = None
        self._learning: Optional[LearningLoop] = None
        self._start_time = time.time()

    def set_incident_store(self, store: IncidentStore) -> None:
        self._store = store

    def set_learning_loop(self, loop: LearningLoop) -> None:
        self._learning = loop

    # ------------------------------------------------------------------
    # MTTD / MTTR
    # ------------------------------------------------------------------

    def _incidents(self) -> List[Any]:
        if self._store is None:
            return []
        # Iterate the store's full list by asking for a large limit.
        return self._store.list(limit=10 ** 9)

    def mttd_seconds(self) -> Optional[float]:
        """Mean time to detect across incidents with detection provenance.

        Detection latency = incident.created_at - first recorded evidence
        (or first event ref) timestamp.  Incidents with no provenance are
        excluded — never assigned a fabricated value.
        """
        if self._store is None:
            return None
        latencies = []
        for inc in self._store.all_incidents():
            earliest = inc.created_at
            if inc.evidence:
                earliest = min(earliest, min(e.timestamp for e in inc.evidence))
            first_event = self._first_event_timestamp(inc)
            if first_event:
                earliest = min(earliest, first_event)
            if earliest >= inc.created_at and not inc.evidence and not first_event:
                continue  # no provenance
            latencies.append(max(0.0, inc.created_at - earliest))
        if not latencies:
            return None
        return round(sum(latencies) / len(latencies), 2)

    def _first_event_timestamp(self, incident: Any) -> Optional[float]:
        """Resolve the earliest bus-event timestamp among the incident's refs.

        Composes the event bus when available; returns None if not wired.
        """
        if not getattr(incident, "event_ids", None):
            return None
        try:
            from aetheros_security.secops.events import get_event_bus
            bus = get_event_bus()
        except Exception:
            return None
        earliest = None
        for event_id in incident.event_ids:
            for ev in bus.recent(limit=10000):
                if ev.event_id == event_id:
                    if earliest is None or ev.timestamp < earliest:
                        earliest = ev.timestamp
                    break
        return earliest

    def mttr_seconds(self) -> Optional[float]:
        """Mean time to resolve for resolved incidents."""
        durations = []
        for inc in self._incidents():
            if inc["status"] != IncidentStatus.RESOLVED.value:
                continue
            closed = inc.get("closed_at") or 0.0
            created = inc.get("created_at") or 0.0
            if closed and created and closed >= created:
                durations.append(closed - created)
        if not durations:
            return None
        return round(sum(durations) / len(durations), 2)

    def incident_counts(self) -> Dict[str, Any]:
        counts = {"total": 0, "open": 0, "resolved": 0, "by_severity": {}}
        for inc in self._incidents():
            counts["total"] += 1
            if inc["status"] == IncidentStatus.RESOLVED.value:
                counts["resolved"] += 1
            else:
                counts["open"] += 1
            sev = inc["severity"]
            counts["by_severity"][sev] = counts["by_severity"].get(sev, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Detection quality (from learning-loop feedback)
    # ------------------------------------------------------------------

    def detection_quality(self) -> Dict[str, Any]:
        if self._learning is None:
            return {"false_positive_rate": None, "feedback_count": 0}
        feedback = self._learning.feedback(limit=10 ** 9)
        if not feedback:
            return {"false_positive_rate": None, "feedback_count": 0}
        fp = sum(1 for f in feedback if f["kind"] == FeedbackKind.FALSE_POSITIVE.value)
        return {
            "false_positive_rate": round(fp / len(feedback), 3),
            "feedback_count": len(feedback),
        }

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self) -> Dict[str, Any]:
        mttd = self.mttd_seconds()
        mttr = self.mttr_seconds()
        quality = self.detection_quality()
        return {
            "generated_at": time.time(),
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "mttd_seconds": mttd,
            "mttr_seconds": mttr,
            "mttd_missing_provenance": mttd is None,
            "incidents": self.incident_counts(),
            "detection_quality": quality,
        }


# Global KPIs
_kpis: Optional[SecurityKPIs] = None


def get_security_kpis() -> SecurityKPIs:
    """Return the process-wide SecurityKPIs singleton."""
    global _kpis
    if _kpis is None:
        _kpis = SecurityKPIs()
    return _kpis