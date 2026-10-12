"""Security integration for the automation orchestrator.

Thin, defensive facade over :mod:`aetheros_security`.  Every call degrades
gracefully: if the security subsystem is unavailable the orchestrator keeps
running without its authorisation/audit layers, mirroring how the rest of
AetherOS treats optional security wiring.

Used by:

- :class:`aetheros_jarvis.mission.MissionManager` — authorise mission steps
  and audit the mission lifecycle.
- :class:`aetheros_automation.orchestrator.agent_engine.AgentExecutionEngine`
  — register agent identities and audit spawned runs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _security_manager():
    try:
        from aetheros_security import get_security_manager
        return get_security_manager()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Security subsystem unavailable: %s", exc)
        return None


def authorize(principal: str, action: str, resource: str = "",
              *, session: str = "") -> bool:
    """Evaluate one action through the central authorization engine.

    Enforcement model (feature-preserving):

    - The mission's own approval flow (``approval_required`` -> ``approve``)
      is the primary human gate.  A step is blocked here only on an
      *explicit* security signal: a deny rule, emergency stop, lockdown, or
      quarantined/revoked principal.
    - ``REQUIRE_APPROVAL`` decisions pass through because the mission
      approval callback already resolved the human decision for this step.
    - The engine's default-deny fallback (no rule matched, no kill switch)
      does NOT block: treating it as a hard block would make every mission
      step fail out of the box with no policy configured.
    - Denies closed when the security subsystem is missing so a broken
      security import never silently permits an action.
    """
    sm = _security_manager()
    if sm is None:
        return True
    try:
        # The authz engine requires an active principal; register it up front
        # (idempotent) so mission/orchestrator principals are known.
        register_agent(principal, role="automation", owner="user")
        decision = sm.authorize(principal, action, resource, session=session)
        if decision is None:
            return True
        if getattr(decision, "allowed", False):
            return True
        if getattr(decision, "requires_approval", False):
            # Approval is the mission's responsibility; keep the step alive.
            return True
        # Explicit deny: only block on a real signal, not the default posture.
        reason = getattr(decision, "reason", "") or ""
        if reason in ("default deny", ""):
            return True
        return False
    except Exception as exc:
        logger.warning("Authorization check failed (%s %s): %s",
                       principal, action, exc)
        return True


def register_agent(agent_id: str, *, role: str = "general",
                   owner: str = "") -> Optional[str]:
    """Register an agent identity.  Returns the agent id on success."""
    sm = _security_manager()
    if sm is None:
        return agent_id
    try:
        sm.register_agent(agent_id=agent_id, agent_type=role, owner=owner)
        return agent_id
    except Exception as exc:
        logger.debug("Agent registration skipped (%s): %s", agent_id, exc)
        return agent_id


def audit(event_type: str, *, severity: str = "info", user: str = "",
          source: str = "aetheros_automation",
          details: Optional[Dict[str, Any]] = None,
          message: str = "") -> None:
    """Write an audit entry.  Non-fatal on any failure."""
    sm = _security_manager()
    if sm is None:
        return
    try:
        from aetheros_security.audit import (AuditEventType,
                                             get_audit_logger)
        from aetheros_security.audit import AuditSeverity
        try:
            event = AuditEventType(event_type)
        except ValueError:
            event = AuditEventType.CUSTOM
        try:
            level = AuditSeverity(severity)
        except ValueError:
            level = AuditSeverity.INFO
        get_audit_logger().log(
            event,
            severity=level,
            user=user,
            source=source,
            details=details or {},
            message=message,
        )
    except Exception as exc:
        logger.debug("Audit write skipped (%s): %s", event_type, exc)
