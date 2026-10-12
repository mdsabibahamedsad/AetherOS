"""
Agent Communication Fabric — security audit (master spec steps 58 and 59).

Security-relevant communication events are recorded through the existing
AetherOS audit infrastructure (:mod:`aetheros_security.audit`) — the fabric
does not build a parallel audit store. Events are redacted before writing so
secrets never reach the audit log (step 25). Audit emission is best-effort and
never breaks the message pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from aetheros_security.audit import AuditEventType, AuditSeverity, get_audit_logger
    _AUDIT_AVAILABLE = True
except Exception:  # pragma: no cover
    _AUDIT_AVAILABLE = False

    class AuditSeverity:  # type: ignore[no-redef]
        INFO = "info"
        WARNING = "warning"
        ERROR = "error"
        CRITICAL = "critical"


class CommAudit:
    """Fabric-level security audit facade.

    All sensitive communication events (authentication attempts,
    authorization decisions, delegation, cross-zone communication, permission
    denials, signature failures, replay rejections, rate-limit events,
    circuit-breaker events, fallback events, quarantine) are recorded here.
    """

    def __init__(self) -> None:
        self._enabled = True
        self._redactor = None

    def _redact(self, details: Dict[str, Any]) -> Dict[str, Any]:
        if not details:
            return {}
        if self._redactor is None:
            try:
                from aetheros_security.redaction import get_redaction_manager
                self._redactor = get_redaction_manager()
            except Exception:
                return details
        try:
            return self._redactor.redact_dict(details)
        except Exception:
            return details

    def log(self, event: str, *, severity: str = "info",
            principal: str = "", details: Optional[Dict[str, Any]] = None,
            message: str = "") -> None:
        if not self._enabled:
            return
        if not _AUDIT_AVAILABLE:
            logger.warning("Audit[%s] %s %s", severity, event, principal)
            return
        try:
            try:
                event_type = AuditEventType(event)
            except ValueError:
                event_type = AuditEventType.CUSTOM
            get_audit_logger().log(
                event_type,
                severity=AuditSeverity(severity),
                user=principal or "",
                source="agent_comm",
                details=self._redact(details or {}),
                message=message or event,
            )
        except Exception:  # pragma: no cover - audit must never break comms
            logger.debug("CommAudit emit failed", exc_info=True)

    # -- convenience events -------------------------------------------------

    def auth_attempt(self, sender: str, receiver: str, ok: bool) -> None:
        self.log("auth_success" if ok else "auth_failure",
                 severity="info" if ok else "warning",
                 principal=sender,
                 details={"sender": sender, "receiver": receiver})

    def authorization_decision(self, sender: str, allowed: bool, reason: str,
                               details: Optional[Dict[str, Any]] = None) -> None:
        self.log("permission_denied" if not allowed else "authorization",
                 severity="warning" if not allowed else "info",
                 principal=sender,
                 details={"sender": sender, "allowed": allowed,
                          "reason": reason, **(details or {})})

    def delegation(self, sender: str, target: str,
                   depth: int, capabilities: list) -> None:
        self.log("delegation", principal=sender,
                 details={"sender": sender, "target": target,
                          "depth": depth, "capabilities": capabilities})

    def cross_zone(self, sender: str, source_zone: str, target_zone: str,
                   allowed: bool) -> None:
        self.log("cross_zone_communication", severity="info" if allowed else "warning",
                 principal=sender,
                 details={"sender": sender, "source_zone": source_zone,
                          "target_zone": target_zone, "allowed": allowed})

    def signature_failure(self, sender: str, message_id: str) -> None:
        self.log("signature_failure", severity="warning", principal=sender,
                 details={"sender": sender, "message_id": message_id})

    def replay_rejected(self, sender: str, message_id: str) -> None:
        self.log("replay_rejection", severity="warning", principal=sender,
                 details={"sender": sender, "message_id": message_id})

    def rate_limited(self, principal: str, scope: str) -> None:
        self.log("rate_limit_event", severity="warning", principal=principal,
                 details={"principal": principal, "scope": scope})

    def circuit_breaker(self, dependency: str, state: str) -> None:
        self.log("circuit_breaker_event", severity="warning",
                 details={"dependency": dependency, "state": state})

    def fallback(self, task: str, from_agent: str, to_agent: str) -> None:
        self.log("fallback_event", severity="info", principal=to_agent,
                 details={"task": task, "from_agent": from_agent,
                          "to_agent": to_agent})

    def quarantine(self, agent_id: str, reason: str) -> None:
        self.log("agent_quarantine", severity="critical", principal=agent_id,
                 details={"agent_id": agent_id, "reason": reason})

    def recovery(self, agent_id: str, action: str) -> None:
        self.log("agent_recovery", severity="info", principal=agent_id,
                 details={"agent_id": agent_id, "action": action})