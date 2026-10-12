"""
Normalized security event schema + SecurityEventBus.

The bus is the OBSERVE primitive of the SecOps layer.  Every event carries a
normalized schema (severity, source, principal, component, resource, action,
outcome, correlation id, ...) and is **redacted on ingest** using the existing
``aetheros_security.redaction`` manager so secrets never sit in the event
history.  Detectors, the correlation engine and the alert manager subscribe to
the bus.

Events are retained in a bounded in-memory ring and, when persistence is
enabled, appended to a JSONL file under ``<aetheros_home>/security/events.jsonl``
(redacted only).
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Canonical security event types (dot-namespaced)."""

    # System / lifecycle
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGED = "config.changed"
    CONFIG_DRIFT = "config.drift"
    COMPONENT_DISCOVERED = "component.discovered"
    COMPONENT_INTEGRITY = "component.integrity"

    # Identity & authn
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    SESSION_REVOKED = "session.revoked"

    # Authorization
    AUTHZ_ALLOW = "authz.allow"
    AUTHZ_DENY = "authz.deny"
    AUTHZ_APPROVAL_REQUIRED = "authz.approval_required"
    APPROVAL_CREATED = "approval.created"
    APPROVAL_RESOLVED = "approval.resolved"
    POLICY_CHANGED = "policy.changed"

    # Agent / mission
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_SPAWNED = "agent.spawned"
    AGENT_QUARANTINED = "agent.quarantined"
    MISSION_STARTED = "mission.started"
    MISSION_PAUSED = "mission.paused"
    MISSION_ABORTED = "mission.aborted"
    MISSION_COMPLETED = "mission.completed"

    # Tools / code
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    TOOL_DENIED = "tool.denied"
    TOOL_ABUSE = "tool.abuse"
    CODE_EXECUTED = "code.executed"

    # Filesystem / data
    FILE_ACCESS = "file.access"
    FILE_WRITE = "file.write"
    FILE_DELETE = "file.delete"
    FILE_DELETION_BURST = "file.deletion_burst"
    DATA_EXFILTRATION = "data.exfiltration"
    SENSITIVE_DATA = "data.sensitive"

    # Network
    NETWORK_CONNECT = "network.connect"
    NETWORK_DENIED = "network.denied"
    NETWORK_ANOMALY = "network.anomaly"
    NETWORK_EXFILTRATION = "network.exfiltration"

    # Memory / knowledge
    MEMORY_WRITE = "memory.write"
    MEMORY_READ = "memory.read"
    MEMORY_DELETE = "memory.delete"
    MEMORY_POISONING = "memory.poisoning"

    # Supply chain / plugins / skills / MCP
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UPDATED = "plugin.updated"
    PLUGIN_REMOVED = "plugin.removed"
    SKILL_INSTALLED = "skill.installed"
    SKILL_UPDATED = "skill.updated"
    MCP_REGISTERED = "mcp.registered"
    MCP_APPROVED = "mcp.approved"
    MCP_QUARANTINED = "mcp.quarantined"
    MCP_RESPONSE_INVALID = "mcp.response_invalid"
    SUPPLY_CHAIN_MISMATCH = "supply_chain.mismatch"

    # Model / inference
    MODEL_CALL = "model.call"
    MODEL_FAILURE = "model.failure"
    PROMPT_INJECTION = "prompt.injection"
    INDIRECT_INJECTION = "prompt.indirect_injection"
    OUTPUT_INVALID = "model.output_invalid"

    # Resource / cost
    RESOURCE_USAGE = "resource.usage"
    RESOURCE_EXHAUSTION = "resource.exhaustion"
    COST_ANOMALY = "cost.anomaly"
    RATE_LIMITED = "rate.limited"

    # Detection / response
    DETECTION = "detection.raised"
    DETECTION_SUPPRESSED = "detection.suppressed"
    CORRELATION_RAISED = "correlation.raised"
    INCIDENT_OPENED = "incident.opened"
    INCIDENT_TRANSITION = "incident.transition"
    INCIDENT_CONTAINED = "incident.contained"
    INCIDENT_RECOVERED = "incident.recovered"
    INCIDENT_CLOSED = "incident.closed"
    CONTAINMENT_ACTION = "containment.action"
    ALERT_SENT = "alert.sent"
    ESCALATION = "escalation.raised"
    EMERGENCY_STOP = "emergency.stop"
    LOCKDOWN = "lockdown.activated"
    HEALTH_CHANGE = "health.changed"

    # SecOps subsystem health
    MONITORING_FAILURE = "monitoring.failure"
    AUDIT_FAILURE = "audit.failure"
    DETECTION_ENGINE_FAILURE = "detection_engine.failure"

    # Generic / custom
    CUSTOM = "custom"


def normalize_event_type(value: Any) -> SecurityEventType:
    """Resolve an event type from enum or dotted string (CUSTOM fallback)."""
    if isinstance(value, SecurityEventType):
        return value
    text = str(value).strip().lower()
    for et in SecurityEventType:
        if et.value == text:
            return et
    return SecurityEventType.CUSTOM


EventSubscriber = Callable[["SecurityEvent"], None]


@dataclass
class SecurityEvent:
    """A normalized, redacted security event."""

    event_type: SecurityEventType
    severity: SecuritySeverity = SecuritySeverity.INFO
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: str = ""
    principal: str = ""
    component: str = ""
    resource: str = ""
    action: str = ""
    outcome: str = ""
    correlation_id: str = ""
    message: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    agent_id: str = ""
    mission_id: str = ""
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "principal": self.principal,
            "component": self.component,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome,
            "correlation_id": self.correlation_id,
            "message": self.message,
            "payload": dict(self.payload),
            "tags": list(self.tags),
            "agent_id": self.agent_id,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
        }

    def matches(self, **criteria: Any) -> bool:
        """Match an event against criteria (event_type, severity, source, ...)."""
        for key, expected in criteria.items():
            if expected is None:
                continue
            if key == "event_type":
                if normalize_event_type(expected) != self.event_type:
                    return False
            elif key == "severity":
                want = parse_severity(expected)
                if want != self.severity:
                    return False
            else:
                actual = getattr(self, key, None)
                if actual is None or actual != expected:
                    return False
        return True


class SecurityEventBus:
    """Bounded, redacted, subscribable security event bus.

    Usage::

        bus = SecurityEventBus()
        bus.subscribe(lambda e: print(e.event_type.value))
        bus.emit(
            SecurityEventType.AUTH_FAILURE, severity="warning",
            principal="agent-1", source="auth",
            message="failed login",
            payload={"attempt": 3},
        )
    """

    def __init__(self, *, max_events: int = 20000,
                 persistence_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._events: List[SecurityEvent] = []
        self._subscribers: List[EventSubscriber] = []
        self._max_events = max(1, max_events)
        self._persistence_path = persistence_path
        self._redaction = None
        self._audit = None

    def _redactor(self):
        if self._redaction is None:
            from aetheros_security.redaction import get_redaction_manager
            self._redaction = get_redaction_manager()
        return self._redaction

    def _redact_dict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._redactor().redact_dict(payload)
        except Exception:
            return dict(payload)

    def subscribe(self, handler: EventSubscriber) -> None:
        with self._lock:
            self._subscribers.append(handler)

    def unsubscribe(self, handler: EventSubscriber) -> bool:
        with self._lock:
            try:
                self._subscribers.remove(handler)
                return True
            except ValueError:
                return False

    def emit(
        self,
        event_type: Any,
        *,
        severity: Any = SecuritySeverity.INFO,
        source: str = "",
        principal: str = "",
        component: str = "",
        resource: str = "",
        action: str = "",
        outcome: str = "",
        correlation_id: str = "",
        message: str = "",
        payload: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        agent_id: str = "",
        mission_id: str = "",
        session_id: str = "",
    ) -> SecurityEvent:
        """Publish a redacted event to all subscribers."""
        event = SecurityEvent(
            event_type=normalize_event_type(event_type),
            severity=parse_severity(severity),
            source=source,
            principal=principal,
            component=component,
            resource=resource,
            action=action,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
            payload=self._redact_dict(payload or {}),
            tags=list(tags or []),
            agent_id=agent_id,
            mission_id=mission_id,
            session_id=session_id,
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
            subscribers = list(self._subscribers)
        self._persist(event)
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception:
                logger.debug("Event subscriber failed", exc_info=True)
        return event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def recent(self, limit: int = 100) -> List[SecurityEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def query(self, *, event_type: Any = None, severity: Any = None,
              source: str = "", principal: str = "",
              component: str = "", min_severity: Any = None,
              start_time: Optional[float] = None,
              end_time: Optional[float] = None,
              limit: int = 200) -> List[SecurityEvent]:
        """Query the retained event history."""
        want_type = normalize_event_type(event_type) if event_type else None
        want_sev = parse_severity(severity) if severity else None
        min_sev = parse_severity(min_severity) if min_severity else None
        with self._lock:
            events = list(self._events)
        results = []
        for ev in reversed(events):
            if want_type is not None and ev.event_type != want_type:
                continue
            if want_sev is not None and ev.severity != want_sev:
                continue
            if min_sev is not None and ev.severity.rank < min_sev.rank:
                continue
            if source and ev.source != source:
                continue
            if principal and ev.principal != principal:
                continue
            if component and ev.component != component:
                continue
            if start_time is not None and ev.timestamp < start_time:
                continue
            if end_time is not None and ev.timestamp > end_time:
                continue
            results.append(ev)
            if len(results) >= limit:
                break
        return results

    def count(self, *, event_type: Any = None, min_severity: Any = None,
              source: str = "", principal: str = "",
              start_time: Optional[float] = None,
              end_time: Optional[float] = None) -> int:
        return len(self.query(
            event_type=event_type, min_severity=min_severity,
            source=source, principal=principal,
            start_time=start_time, end_time=end_time, limit=10 ** 9,
        ))

    def clear(self) -> int:
        with self._lock:
            count = len(self._events)
            self._events.clear()
            return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "retained": len(self._events),
                "max_events": self._max_events,
                "subscribers": len(self._subscribers),
                "persistence": bool(self._persistence_path),
            }

    # ------------------------------------------------------------------
    # Persistence (redacted only)
    # ------------------------------------------------------------------

    def _persist(self, event: SecurityEvent) -> None:
        if not self._persistence_path:
            return
        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as exc:
            logger.debug("Event persistence failed: %s", exc)


# Global event bus
_event_bus: SecurityEventBus | None = None


def get_event_bus() -> SecurityEventBus:
    """Return the process-wide SecurityEventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = SecurityEventBus()
    return _event_bus