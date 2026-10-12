"""Incident detection, alert deduplication and incident lifecycle.

Deterministic threshold-based detection first — no ML anomaly system
unless the repository ships one.  Repeated incidents are grouped by a
dedup key so thousands of identical alerts collapse into one incident
carrying ``firstSeen`` / ``lastSeen`` / ``count`` / ``traceIds`` /
``recoveryState``.

Lifecycle states:

    DETECTED → ACKNOWLEDGED → INVESTIGATING → MITIGATING
             → RECOVERED → RESOLVED  (or ESCALATED)
"""

from __future__ import annotations

import enum
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_observability.errors import Severity


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY_CRITICAL = "SECURITY_CRITICAL"

    @property
    def rank(self) -> int:
        return {
            AlertSeverity.INFO: 0,
            AlertSeverity.NOTICE: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.ERROR: 3,
            AlertSeverity.CRITICAL: 4,
            AlertSeverity.SECURITY_CRITICAL: 5,
        }[self]


class IncidentState(str, enum.Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RECOVERED = "RECOVERED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


@dataclass
class Incident:
    key: str
    severity: AlertSeverity
    component: str
    message: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    count: int = 1
    trace_ids: List[str] = field(default_factory=list)
    state: IncidentState = IncidentState.DETECTED
    recovery_state: str = ""
    incident_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "key": self.key,
            "severity": self.severity.value,
            "component": self.component,
            "message": self.message,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "count": self.count,
            "trace_ids": self.trace_ids[-10:],
            "state": self.state.value,
            "recovery_state": self.recovery_state,
        }


AlertHandler = Callable[[Incident], None]


@dataclass
class ThresholdRule:
    """Deterministic incident-detection rule."""

    name: str
    metric: str          # metric name or error_type to watch
    threshold: float
    window_seconds: float = 300.0
    severity: AlertSeverity = AlertSeverity.WARNING
    component: str = ""
    op: str = "gte"      # "gte" | "gt"


class IncidentDetector:
    """Detects incidents, deduplicates alerts, tracks lifecycle.

    Usage::

        det = get_incident_detector()
        det.add_rule(ThresholdRule("error_spike", "aetheros.error.count", 5.0, window_seconds=60))
        det.record_error(error_type="RATE_LIMIT", component="model", trace_id="...")
        det.record_latency("model", 12000.0)
        incidents = det.active_incidents()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._incidents: Dict[str, Incident] = {}
        self._resolved: deque = deque(maxlen=200)
        self._handlers: List[AlertHandler] = []
        self._rules: List[ThresholdRule] = []
        self._recent: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=2000)
        )
        self._latency_samples: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add_rule(self, rule: ThresholdRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def clear_rules(self) -> None:
        with self._lock:
            self._rules.clear()

    def subscribe(self, handler: AlertHandler) -> None:
        self._handlers.append(handler)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_error(
        self,
        *,
        error_type: str = "INTERNAL_ERROR",
        component: str = "",
        message: str = "",
        trace_id: str = "",
        severity: Optional[AlertSeverity] = None,
    ) -> Optional[Incident]:
        """Record an error; deduplicate into an incident by key."""
        severity = severity or self._severity_for(error_type)
        key = f"error:{error_type}:{component or 'unknown'}"
        incident = self._touch(
            key,
            severity=severity,
            component=component or "unknown",
            message=message or f"{error_type} in {component or 'unknown'}",
            trace_id=trace_id,
        )
        with self._lock:
            self._recent[key].append(time.time())
        # Check configured rules for this error type
        self._check_rules(component=component, error_type=error_type)
        return incident

    def record_latency(self, component: str, value_ms: float,
                       trace_id: str = "") -> None:
        """Record a latency sample; detect spikes via threshold rules."""
        with self._lock:
            self._latency_samples[component].append(value_ms)
        self._check_rules(component=component, latency_ms=value_ms,
                          trace_id=trace_id)

    def record_queue_depth(self, queue: str, depth: int) -> None:
        with self._lock:
            key = f"queue_depth:{queue}"
            self._recent[key].append((time.time(), depth))

    def record_security_event(self, event_type: str, *, message: str = "",
                              trace_id: str = "") -> Optional[Incident]:
        """Security events are never sampled or dropped; always retained."""
        return self.record_error(
            error_type=event_type or "SECURITY_ERROR",
            component="security",
            message=message,
            trace_id=trace_id,
            severity=AlertSeverity.SECURITY_CRITICAL,
        )

    # ------------------------------------------------------------------
    # Incident lifecycle
    # ------------------------------------------------------------------

    def acknowledge(self, key: str) -> bool:
        with self._lock:
            incident = self._incidents.get(key)
            if incident and incident.state == IncidentState.DETECTED:
                incident.state = IncidentState.ACKNOWLEDGED
                return True
            return False

    def set_state(self, key: str, state: IncidentState) -> bool:
        with self._lock:
            incident = self._incidents.get(key)
            if not incident:
                return False
            incident.state = state
            return True

    def mark_recovered(self, key: str, recovery_state: str = "recovered") -> bool:
        with self._lock:
            incident = self._incidents.get(key)
            if not incident:
                return False
            incident.state = IncidentState.RECOVERED
            incident.recovery_state = recovery_state
            return True

    def resolve(self, key: str) -> bool:
        with self._lock:
            incident = self._incidents.pop(key, None)
            if incident:
                incident.state = IncidentState.RESOLVED
                self._resolved.append(incident)
                return True
            return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active_incidents(self) -> List[Incident]:
        with self._lock:
            return sorted(
                [i for i in self._incidents.values()
                 if i.state not in (IncidentState.RESOLVED, IncidentState.RECOVERED)],
                key=lambda i: i.last_seen, reverse=True,
            )

    def get(self, key: str) -> Optional[Incident]:
        with self._lock:
            return self._incidents.get(key)

    def resolved_incidents(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [i.to_dict() for i in list(self._resolved)[-limit:]]

    def summary(self) -> Dict[str, Any]:
        active = self.active_incidents()
        return {
            "active": [i.to_dict() for i in active],
            "active_count": len(active),
            "by_severity": {
                s.value: sum(1 for i in active if i.severity == s)
                for s in AlertSeverity
            },
            "resolved_recent": len(self._resolved),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _touch(self, key: str, *, severity: AlertSeverity, component: str,
               message: str, trace_id: str) -> Incident:
        now = time.time()
        with self._lock:
            incident = self._incidents.get(key)
            if incident is None:
                incident = Incident(
                    key=key, severity=severity, component=component,
                    message=message,
                )
                self._incidents[key] = incident
                self._notify(incident)
            else:
                incident.count += 1
                incident.last_seen = now
                if trace_id:
                    incident.trace_ids.append(trace_id)
        return incident

    def _check_rules(self, *, component: str = "", error_type: str = "",
                     latency_ms: float = 0.0, trace_id: str = "") -> None:
        now = time.time()
        with self._lock:
            rules = list(self._rules)
        for rule in rules:
            if rule.component and rule.component != component:
                continue
            try:
                if rule.metric == "latency_ms" and latency_ms:
                    self._maybe_raise(rule, latency_ms, component, trace_id)
                elif rule.metric == "error_rate":
                    rate = self._error_rate(component, rule.window_seconds)
                    self._maybe_raise(rule, rate, component, trace_id)
                elif rule.metric == "error_count":
                    count = self._error_count(component, rule.window_seconds)
                    self._maybe_raise(rule, count, component, trace_id)
            except Exception:
                continue

    def _error_rate(self, component: str, window: float) -> float:
        now = time.time()
        with self._lock:
            samples = [
                t for key, timestamps in self._recent.items()
                if key.startswith("error:") and key.endswith(f":{component or 'unknown'}")
                for t in timestamps
            ]
        # Use a simple recent-window error count as a proxy rate.
        return sum(1 for t in samples if now - t <= window)

    def _error_count(self, component: str, window: float) -> float:
        return self._error_rate(component, window)

    def _maybe_raise(self, rule: ThresholdRule, value: float,
                     component: str, trace_id: str) -> None:
        exceeded = value >= rule.threshold if rule.op in ("gte", "gt") \
            else value <= rule.threshold
        if not exceeded:
            return
        key = f"rule:{rule.name}"
        incident = self._touch(
            key,
            severity=rule.severity,
            component=rule.component or component or "unknown",
            message=f"threshold {rule.name} exceeded: {value:g} >= {rule.threshold:g}",
            trace_id=trace_id,
        )
        if incident.state in (IncidentState.RESOLVED, IncidentState.RECOVERED):
            incident.state = IncidentState.DETECTED

    def _severity_for(self, error_type: str) -> AlertSeverity:
        upper = error_type.upper()
        if "SECURITY" in upper or "AUTH" in upper:
            return AlertSeverity.SECURITY_CRITICAL
        if "RATE" in upper or "RESOURCE" in upper:
            return AlertSeverity.WARNING
        return AlertSeverity.ERROR

    def _notify(self, incident: Incident) -> None:
        for handler in list(self._handlers):
            try:
                handler(incident)
            except Exception:
                pass


_incident_detector: Optional[IncidentDetector] = None


def get_incident_detector() -> IncidentDetector:
    """Return the process-wide IncidentDetector singleton."""
    global _incident_detector
    if _incident_detector is None:
        _incident_detector = IncidentDetector()
    return _incident_detector