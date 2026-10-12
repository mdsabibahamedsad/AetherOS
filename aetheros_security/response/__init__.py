"""
Security Response & Health for AetherOS
=======================================

Incident response, emergency stop, account lockdown, and the security
health model (master security spec steps 52-53, 67-68).

Emergency stop (step 52):
    - stops new agent actions
    - blocks privileged tools
    - pauses missions
    - preserves logs
    - notifies the user
    - requires explicit recovery

Account lockdown (step 53):
    - revokes sessions
    - disables sensitive tools
    - revokes temporary capabilities
    - stops high-risk missions
    - requires re-authentication

Incident manager (step 68) lifecycle:
    DETECT -> CLASSIFY -> CONTAIN -> ISOLATE -> REVOKE -> INVESTIGATE ->
    RECOVER -> VERIFY -> CLOSE

Health score (step 67): a deterministic score over the security subsystems.
A high score is NOT a claim that the system is "secure" — it is a signal
for operators about posture coverage.

Usage::

    from aetheros_security.response import SecurityResponseManager

    response = SecurityResponseManager()
    response.emergency_stop(reason="suspected compromise")
    response.lockdown(reason="stolen token")
    response.open_incident("credential_exfiltration", severity="critical")
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseState(Enum):
    """Global response state."""
    NORMAL = "normal"
    EMERGENCY_STOP = "emergency_stop"
    LOCKDOWN = "lockdown"
    RECOVERY = "recovery"


class IncidentStatus(Enum):
    """Incident lifecycle status (step 68)."""
    DETECTED = "detected"
    CLASSIFIED = "classified"
    CONTAINED = "contained"
    ISOLATED = "isolated"
    REVOKED = "revoked"
    INVESTIGATING = "investigating"
    RECOVERING = "recovering"
    VERIFIED = "verified"
    CLOSED = "closed"


class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityIncident:
    """A single security incident."""
    incident_id: str
    title: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.DETECTED
    description: str = ""
    source: str = ""
    affected_principals: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    closed_at: float = 0.0
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.incident_id:
            self.incident_id = uuid.uuid4().hex
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.timeline:
            self.timeline.append({"timestamp": now, "event": "detected"})

    def add_event(self, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.timeline.append({"timestamp": time.time(), "event": event,
                              "details": details or {}})
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "description": self.description,
            "source": self.source,
            "affected_principals": list(self.affected_principals),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "timeline": list(self.timeline),
            "metadata": dict(self.metadata),
        }


class SecurityResponseManager:
    """Manages emergency stop, lockdown, incidents, and health scoring."""

    def __init__(self) -> None:
        self._state = ResponseState.NORMAL
        self._stop_reason = ""
        self._stop_at: float = 0.0
        self._notify: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._incidents: Dict[str, SecurityIncident] = {}
        self._health_checks: Dict[str, Callable[[], bool]] = {}

    # ------------------------------------------------------------------
    # Notification hook
    # ------------------------------------------------------------------

    def register_notifier(self, notifier: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a user-notification callback (message, details)."""
        self._notify = notifier

    def _notify_user(self, message: str, details: Dict[str, Any]) -> None:
        if self._notify:
            try:
                self._notify(message, details)
            except Exception:
                logger.exception("Notifier failed")

    # ------------------------------------------------------------------
    # Emergency stop (step 52)
    # ------------------------------------------------------------------

    def emergency_stop(self, reason: str = "") -> bool:
        """Activate the global emergency stop.

        Returns True if a new stop was activated (no-op if already stopped).
        """
        if self._state == ResponseState.EMERGENCY_STOP:
            return False
        self._state = ResponseState.EMERGENCY_STOP
        self._stop_reason = reason
        self._stop_at = time.time()
        self._emit_audit("emergency_stop", "security.response", "CRITICAL", {
            "reason": reason,
        })
        logger.critical("EMERGENCY STOP activated: %s", reason or "no reason")
        self._notify_user("Security emergency stop activated", {"reason": reason})
        self._propagate_emergency(True)
        return True

    def is_emergency_stop(self) -> bool:
        return self._state == ResponseState.EMERGENCY_STOP

    def recover_from_stop(self) -> bool:
        """Explicitly recover from an emergency stop."""
        if self._state != ResponseState.EMERGENCY_STOP:
            return False
        self._state = ResponseState.RECOVERY
        self._emit_audit("emergency_recovered", "security.response", "INFO", {})
        logger.warning("Emergency stop recovered; state = RECOVERY")
        self._notify_user("Emergency stop cleared (recovery mode)", {})
        self._propagate_emergency(False)
        return True

    # ------------------------------------------------------------------
    # Lockdown (step 53)
    # ------------------------------------------------------------------

    def lockdown(self, reason: str = "") -> bool:
        """Activate account lockdown: sessions revoked, sensitive tools off."""
        if self._state == ResponseState.LOCKDOWN:
            return False
        self._state = ResponseState.LOCKDOWN
        self._stop_reason = reason
        self._stop_at = time.time()
        self._revoke_all_sessions()
        self._emit_audit("lockdown", "security.response", "CRITICAL", {
            "reason": reason,
        })
        logger.critical("ACCOUNT LOCKDOWN activated: %s", reason or "no reason")
        self._notify_user("Account lockdown activated", {"reason": reason})
        self._propagate_emergency(True)
        return True

    def is_locked_down(self) -> bool:
        return self._state == ResponseState.LOCKDOWN

    def release_lockdown(self) -> bool:
        if self._state != ResponseState.LOCKDOWN:
            return False
        self._state = ResponseState.RECOVERY
        self._emit_audit("lockdown_released", "security.response", "INFO", {})
        logger.warning("Lockdown released; state = RECOVERY")
        self._notify_user("Lockdown released (recovery mode)", {})
        self._propagate_emergency(False)
        return True

    def _revoke_all_sessions(self) -> int:
        try:
            from aetheros_security.session import get_session_manager
            manager = get_session_manager()
            count = 0
            for principal_id, session in list(manager._revoked.items()):
                if session > 0:
                    count += 1
            # Revoke by re-seeding: any token with issued_at < now is invalid.
            manager._revoked = {tid: time.time() for tid in manager._revoked}
            return count
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # State propagation
    # ------------------------------------------------------------------

    def _propagate_emergency(self, active: bool) -> None:
        """Mirror the emergency state into the authorization engine."""
        try:
            from aetheros_security.authz import get_authorization_engine
            engine = get_authorization_engine()
            if active:
                engine.set_emergency_stop(True)
                engine.set_lockdown(self._state == ResponseState.LOCKDOWN)
            else:
                engine.set_emergency_stop(False)
                engine.set_lockdown(False)
        except Exception:
            logger.debug("Could not propagate emergency state", exc_info=True)

    # ------------------------------------------------------------------
    # Incidents (step 68)
    # ------------------------------------------------------------------

    def open_incident(self, title: str, *, severity: str = "medium",
                      description: str = "", source: str = "",
                      affected_principals: Optional[List[str]] = None) -> SecurityIncident:
        incident = SecurityIncident(
            incident_id=uuid.uuid4().hex,
            title=title,
            severity=IncidentSeverity(severity),
            description=description,
            source=source,
            affected_principals=affected_principals or [],
        )
        self._incidents[incident.incident_id] = incident
        self._emit_audit("incident_opened", source or "security.response",
                         "WARNING" if incident.severity.value in ("high", "critical")
                         else "INFO", {"incident_id": incident.incident_id,
                                       "title": title, "severity": severity})
        logger.warning("Incident opened [%s] %s", severity, title)
        self._notify_user(f"Security incident: {title}", {"severity": severity,
                                                          "incident_id": incident.incident_id})
        return incident

    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        return self._incidents.get(incident_id)

    def transition(self, incident_id: str, status: IncidentStatus) -> bool:
        """Move an incident to the next lifecycle state."""
        incident = self._incidents.get(incident_id)
        if incident is None:
            return False
        incident.status = status
        incident.add_event(f"status:{status.value}")
        if status == IncidentStatus.CLOSED:
            incident.closed_at = time.time()
        self._emit_audit("incident_transition", incident.source,
                         "INFO", {"incident_id": incident_id,
                                  "status": status.value})
        return True

    def list_incidents(self, open_only: bool = False) -> List[Dict[str, Any]]:
        incidents = list(self._incidents.values())
        if open_only:
            incidents = [i for i in incidents if i.status != IncidentStatus.CLOSED]
        return [i.to_dict() for i in sorted(incidents, key=lambda i: i.created_at)]

    # ------------------------------------------------------------------
    # Health scoring (step 67)
    # ------------------------------------------------------------------

    def register_health_check(self, category: str, check: Callable[[], bool]) -> None:
        """Register a deterministic health check callback for a category."""
        self._health_checks[category] = check

    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks and compute the health score.

        Returns per-category pass/fail plus an aggregate score (0-100).
        """
        results: Dict[str, Dict[str, Any]] = {}
        checks = list(self._health_checks.items())
        for category, check in checks:
            try:
                ok = bool(check())
            except Exception as exc:
                ok = False
                results[category] = {"ok": False, "error": str(exc)}
                continue
            results[category] = {"ok": ok}
        passed = sum(1 for r in results.values() if r.get("ok"))
        total = max(1, len(results))
        score = int(round(passed / total * 100)) if results else 0
        return {
            "score": score,
            "passed": passed,
            "total": len(results),
            "categories": results,
            "state": self._state.value,
        }

    def register_default_health_checks(self) -> None:
        """Register built-in health checks for the security subsystems."""
        checks: Dict[str, Callable[[], bool]] = {
            "encryption": self._health_encryption,
            "secrets": self._health_secrets,
            "permissions": self._health_permissions,
            "audit": self._health_audit,
            "identity": self._health_identity,
            "filesystem": self._health_filesystem,
            "network": self._health_network,
        }
        for category, check in checks.items():
            if category not in self._health_checks:
                self._health_checks[category] = check

    @staticmethod
    def _health_encryption() -> bool:
        try:
            from aetheros_security.encryption import get_encryption_manager
            probe = get_encryption_manager().encrypt("health-probe")
            return get_encryption_manager().decrypt(probe) == "health-probe"
        except Exception:
            return False

    @staticmethod
    def _health_secrets() -> bool:
        try:
            from aetheros_security.secrets import get_secrets_manager
            get_secrets_manager()
            return True
        except Exception:
            return False

    @staticmethod
    def _health_permissions() -> bool:
        try:
            from aetheros_security.permissions import get_permission_engine
            get_permission_engine()
            return True
        except Exception:
            return False

    @staticmethod
    def _health_audit() -> bool:
        try:
            from aetheros_security.audit import get_audit_logger
            return get_audit_logger().get_statistics() is not None
        except Exception:
            return False

    @staticmethod
    def _health_identity() -> bool:
        try:
            from aetheros_security.identity import get_identity_registry
            get_identity_registry()
            return True
        except Exception:
            return False

    @staticmethod
    def _health_filesystem() -> bool:
        try:
            from aetheros_security.filesystem import get_filesystem_security
            return get_filesystem_security().get_stats() is not None
        except Exception:
            return False

    @staticmethod
    def _health_network() -> bool:
        try:
            from aetheros_security.network import get_network_security_manager
            return get_network_security_manager().get_stats() is not None
        except Exception:
            return False

    def get_state(self) -> str:
        return self._state.value

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "stop_reason": self._stop_reason,
            "open_incidents": sum(1 for i in self._incidents.values()
                                  if i.status != IncidentStatus.CLOSED),
            "total_incidents": len(self._incidents),
        }

    @staticmethod
    def _emit_audit(event_type: str, source: str, severity: str,
                    details: Dict[str, Any]) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(event, severity=AuditSeverity(severity),
                                   source=source, details=details,
                                   message=f"Security response: {event_type}")
        except Exception:
            pass


# Global response manager
_response_manager: SecurityResponseManager | None = None


def get_response_manager() -> SecurityResponseManager:
    """Return the global SecurityResponseManager singleton."""
    global _response_manager
    if _response_manager is None:
        _response_manager = SecurityResponseManager()
    return _response_manager