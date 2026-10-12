"""
User alerting: dedup, throttling, escalation, notification.

The alert manager turns *actionable* detections/incidents into user-facing
alerts with deduplication (same alert key inside a window collapses to one
alert carrying a count), throttling (cooldown between repeated alerts) and
escalation (severity/time-based).  User delivery composes the existing
notification hooks: the observability incident detector and the security
response manager's notifier.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .events import SecurityEventType, SecurityEventBus
from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    NONE = "none"
    NOTIFY = "notify"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class UserAlert:
    """A user-facing alert."""

    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key: str = ""
    title: str = ""
    message: str = ""
    severity: SecuritySeverity = SecuritySeverity.INFO
    count: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    escalation: EscalationLevel = EscalationLevel.NOTIFY
    incident_id: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "key": self.key,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "escalation": self.escalation.value,
            "incident_id": self.incident_id,
            "source": self.source,
        }


AlertHandler = Callable[[UserAlert], None]


class AlertManager:
    """Deduplicating, throttling, escalating alert manager.

    Usage::

        am = AlertManager()
        am.register_handler(lambda alert: print(alert.title))
        am.alert(key="auth_failure_alice", title="Auth failures",
                 message="...", severity="high", incident_id="...")
    """

    def __init__(self, *, cooldown_seconds: float = 300.0,
                 dedup_window_seconds: float = 300.0,
                 escalate_after_seconds: float = 1800.0) -> None:
        self._lock = threading.RLock()
        self._handlers: List[AlertHandler] = []
        self._active: Dict[str, UserAlert] = {}
        self._history: List[UserAlert] = []
        self._cooldown: Dict[str, float] = {}
        self._cooldown_seconds = cooldown_seconds
        self._dedup_window = dedup_window_seconds
        self._escalate_after = escalate_after_seconds
        self._max_history = 500
        self._bus = None

    def set_bus(self, bus: SecurityEventBus) -> None:
        self._bus = bus

    def register_handler(self, handler: AlertHandler) -> None:
        with self._lock:
            self._handlers.append(handler)

    def unregister_handler(self, handler: AlertHandler) -> bool:
        with self._lock:
            try:
                self._handlers.remove(handler)
                return True
            except ValueError:
                return False

    # ------------------------------------------------------------------
    # Alerting
    # ------------------------------------------------------------------

    def alert(self, *, key: str, title: str, message: str = "",
              severity: Any = SecuritySeverity.WARNING,
              incident_id: str = "", source: str = "") -> Optional[UserAlert]:
        """Emit a user alert, honoring dedup + cooldown.

        Returns the alert when delivered (or coalesced), None when throttled.
        """
        sev = parse_severity(severity)
        now = time.time()
        with self._lock:
            # Cooldown check: if we alerted this key too recently, skip.
            last = self._cooldown.get(key, 0.0)
            if now - last < self._cooldown_seconds:
                return None
            existing = self._active.get(key)
            if existing is not None and now - existing.first_seen <= self._dedup_window:
                existing.count += 1
                existing.last_seen = now
                existing.severity = max(existing.severity, sev, key=lambda s: s.rank)
                alert = existing
            else:
                alert = UserAlert(
                    key=key, title=title, message=message, severity=sev,
                    incident_id=incident_id, source=source,
                )
                self._active[key] = alert
            self._cooldown[key] = now
            handlers = list(self._handlers)
        self._deliver(alert)
        for handler in handlers:
            try:
                handler(alert)
            except Exception:
                logger.debug("Alert handler failed", exc_info=True)
        return alert

    def escalate(self, alert_id: str, level: EscalationLevel,
                 *, reason: str = "") -> bool:
        """Escalate an active alert to a higher level."""
        with self._lock:
            alert = next((a for a in self._active.values()
                          if a.alert_id == alert_id), None)
            if alert is None:
                return False
            alert.escalation = level
            self._history.append(UserAlert(
                key=alert.key, title=alert.title,
                message=f"ESCALATED: {alert.message} ({reason})",
                severity=alert.severity, escalation=level,
                incident_id=alert.incident_id, source="alert_manager",
            ))
        return True

    def promote_active(self, *, min_age_seconds: Optional[float] = None) -> List[UserAlert]:
        """Promote stale high-severity alerts to critical escalation."""
        promoted: List[UserAlert] = []
        threshold = min_age_seconds if min_age_seconds is not None else self._escalate_after
        now = time.time()
        with self._lock:
            for alert in list(self._active.values()):
                if alert.severity >= SecuritySeverity.HIGH and \
                        now - alert.first_seen >= threshold and \
                        alert.escalation == EscalationLevel.NOTIFY:
                    alert.escalation = EscalationLevel.CRITICAL
                    promoted.append(alert)
        return promoted

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._active.values()]

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._history[-limit:]]

    def acknowledge(self, key: str) -> bool:
        with self._lock:
            alert = self._active.pop(key, None)
            if alert is None:
                return False
            alert.count += 1
            self._history.append(alert)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": len(self._active),
                "delivered": len(self._history),
                "handlers": len(self._handlers),
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _deliver(self, alert: UserAlert) -> None:
        if self._bus is not None:
            self._bus.emit(
                SecurityEventType.ALERT_SENT,
                severity=alert.severity,
                source="alert_manager",
                resource=alert.key,
                message=f"{alert.title} ({alert.count}x)",
                payload={"alert_id": alert.alert_id,
                         "incident_id": alert.incident_id},
            )
        # Compose with observability: always retain security events.
        try:
            from aetheros_observability.service import get_observability_service
            obs = get_observability_service()
            obs.event("security.alert", component="secops",
                      message=alert.title,
                      payload={"severity": alert.severity.value,
                               "count": alert.count},
                      severity=alert.severity.value.upper())
        except Exception:
            pass


# Global alert manager
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Return the process-wide AlertManager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager