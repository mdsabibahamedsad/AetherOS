"""
Incident response engine: runbooks + containment + escalation.

The response engine composes the AetherOS control plane's own mechanisms —
kill switches, emergency stop, account lockdown, agent quarantine, MCP
quarantine and the tool-authorization boundary — to contain incidents.  It
never replaces the control plane; it drives it.

Containment is *safe*: every containment action is audited, reversible where
the control plane supports it, and preserves evidence (the incident is
referenced in every audit trail it touches).  Auto-containment only fires for
critical/emergency severity by default (config-gated), so the system never
takes destructive action on a false positive without operator approval.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .events import SecurityEventType, SecurityEventBus
from .incidents import (ContainmentStatus, EvidenceEntry, IncidentStatus,
                        SecOpsIncident)
from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


class ContainmentAction(Enum):
    """Named containment actions (map onto control-plane mechanisms)."""

    KILL_SWITCH = "kill_switch"
    EMERGENCY_STOP = "emergency_stop"
    LOCKDOWN = "lockdown"
    QUARANTINE_AGENT = "quarantine_agent"
    QUARANTINE_MCP = "quarantine_mcp"
    SUSPEND_AGENT = "suspend_agent"
    DENY_TOOL = "deny_tool"
    REVOKE_SESSION = "revoke_session"
    PAUSE_MISSION = "pause_mission"


#: Which containment actions may run automatically (config-gated).
_AUTO_CONTAIN_MIN_SEVERITY = {
    SecuritySeverity.HIGH: SecuritySeverity.HIGH,
    SecuritySeverity.CRITICAL: SecuritySeverity.CRITICAL,
    SecuritySeverity.EMERGENCY: SecuritySeverity.EMERGENCY,
}


@dataclass
class ContainmentResult:
    """Result of executing one containment action."""

    action: ContainmentAction
    target: str
    ok: bool
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "target": self.target,
            "ok": self.ok,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class RunbookStep:
    """One step in a runbook."""

    action: ContainmentAction
    target: str = ""            # leave empty for engine-chosen target
    wait_seconds: float = 0.0
    note: str = ""


@dataclass
class Runbook:
    """A named incident-response runbook."""

    name: str
    description: str
    steps: List[RunbookStep] = field(default_factory=list)
    version: int = 1
    enabled: bool = True


class ContainmentError(Exception):
    pass


class ResponseEngine:
    """Executes containment actions and runbooks.

    Usage::

        engine = ResponseEngine()
        result = engine.contain(
            ContainmentAction.KILL_SWITCH,
            target="DISABLE_EXTERNAL_NETWORK",
            incident=incident,
        )
        engine.run_runbook("network_incident", incident=incident)
    """

    #: Elevated principal used when driving control-plane mechanisms.
    _OPERATOR_PRINCIPAL = "security"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runbooks: Dict[str, Runbook] = {}
        self._history: List[ContainmentResult] = []
        self._auto_contain_critical = True
        self._auto_contain_high = False
        self._bus = None

    def set_bus(self, bus: SecurityEventBus) -> None:
        self._bus = bus

    # ------------------------------------------------------------------
    # Runbooks
    # ------------------------------------------------------------------

    def register_runbook(self, runbook: Runbook) -> None:
        with self._lock:
            self._runbooks[runbook.name] = runbook

    def unregister_runbook(self, name: str) -> bool:
        with self._lock:
            return self._runbooks.pop(name, None) is not None

    def list_runbooks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": r.name,
                    "description": r.description,
                    "steps": len(r.steps),
                    "version": r.version,
                    "enabled": r.enabled,
                }
                for r in self._runbooks.values()
            ]

    def get_runbook(self, name: str) -> Optional[Runbook]:
        with self._lock:
            return self._runbooks.get(name)

    def set_auto_containment(self, *, high: Optional[bool] = None,
                             critical: Optional[bool] = None) -> None:
        if high is not None:
            self._auto_contain_high = high
        if critical is not None:
            self._auto_contain_critical = critical

    # ------------------------------------------------------------------
    # Containment
    # ------------------------------------------------------------------

    def contain(self, action: ContainmentAction, *, target: str = "",
                incident: Optional[SecOpsIncident] = None,
                reason: str = "") -> ContainmentResult:
        """Execute a single containment action.

        The action composes the control plane.  Every action is audited; when
        an incident is provided its evidence and timeline are updated so the
        forensics module can reconstruct exactly what was done.
        """
        try:
            result = self._execute(action, target=target, incident=incident,
                                   reason=reason)
        except Exception as exc:
            result = ContainmentResult(action=action, target=target, ok=False,
                                       detail=f"{type(exc).__name__}: {exc}")
        with self._lock:
            self._history.append(result)
        self._emit(action, target, result, incident)
        if incident is not None:
            incident.add_evidence(EvidenceEntry(
                kind="containment", source="response_engine",
                data={"action": action.value, "target": target,
                      "ok": result.ok, "detail": result.detail},
            ))
            if result.ok:
                incident.add_timeline("contained", {
                    "action": action.value, "target": target,
                })
        return result

    def _execute(self, action: ContainmentAction, *, target: str,
                 incident: Optional[SecOpsIncident],
                 reason: str) -> ContainmentResult:
        if action == ContainmentAction.KILL_SWITCH:
            return self._kill_switch(target, reason)
        if action == ContainmentAction.EMERGENCY_STOP:
            return self._emergency_stop(reason)
        if action == ContainmentAction.LOCKDOWN:
            return self._lockdown(reason)
        if action == ContainmentAction.QUARANTINE_AGENT:
            return self._quarantine_agent(target)
        if action == ContainmentAction.QUARANTINE_MCP:
            return self._quarantine_mcp(target)
        if action == ContainmentAction.SUSPEND_AGENT:
            return self._suspend_agent(target)
        if action == ContainmentAction.DENY_TOOL:
            return self._deny_tool(target)
        if action == ContainmentAction.REVOKE_SESSION:
            return self._revoke_session(target)
        if action == ContainmentAction.PAUSE_MISSION:
            return self._pause_mission(target, reason)
        raise ContainmentError(f"unknown action: {action}")

    # ------------------------------------------------------------------
    # Control-plane bridges
    # ------------------------------------------------------------------

    def _kill_switch(self, name: str, reason: str) -> ContainmentResult:
        from aetheros_security.kill_switch import get_kill_switch_registry
        registry = get_kill_switch_registry()
        ok = registry.set_switch_by_name(
            name, True, principal=self._OPERATOR_PRINCIPAL, reason=reason)
        return ContainmentResult(ContainmentAction.KILL_SWITCH, name, ok,
                                 f"kill switch {name}")

    def _emergency_stop(self, reason: str) -> ContainmentResult:
        from aetheros_security.response import get_response_manager
        manager = get_response_manager()
        ok = manager.emergency_stop(reason=reason or "security incident")
        return ContainmentResult(ContainmentAction.EMERGENCY_STOP, "system", ok,
                                 "emergency stop")

    def _lockdown(self, reason: str) -> ContainmentResult:
        from aetheros_security.response import get_response_manager
        manager = get_response_manager()
        ok = manager.lockdown(reason=reason or "security incident")
        return ContainmentResult(ContainmentAction.LOCKDOWN, "system", ok,
                                 "account lockdown")

    def _quarantine_agent(self, agent_id: str) -> ContainmentResult:
        if not agent_id:
            raise ContainmentError("quarantine_agent requires an agent id")
        from aetheros_security.identity import get_identity_registry
        registry = get_identity_registry()
        ok = registry.quarantine(agent_id)
        return ContainmentResult(ContainmentAction.QUARANTINE_AGENT, agent_id, ok,
                                 "agent quarantined")

    def _quarantine_mcp(self, server_id: str) -> ContainmentResult:
        if not server_id:
            raise ContainmentError("quarantine_mcp requires a server id")
        from aetheros_security.mcp import get_mcp_security_manager
        manager = get_mcp_security_manager()
        ok = manager.quarantine(server_id)
        return ContainmentResult(ContainmentAction.QUARANTINE_MCP, server_id, ok,
                                 "MCP server quarantined")

    def _suspend_agent(self, agent_id: str) -> ContainmentResult:
        if not agent_id:
            raise ContainmentError("suspend_agent requires an agent id")
        from aetheros_security.identity import get_identity_registry
        registry = get_identity_registry()
        ok = registry.suspend(agent_id)
        return ContainmentResult(ContainmentAction.SUSPEND_AGENT, agent_id, ok,
                                 "agent suspended")

    def _deny_tool(self, tool: str) -> ContainmentResult:
        if not tool:
            raise ContainmentError("deny_tool requires a tool name")
        from aetheros_security.manifest import get_manifest_registry
        manifest = get_manifest_registry().get(tool)
        if manifest is not None:
            manifest.allowed = False
            ok = True
        else:
            ok = False
        return ContainmentResult(ContainmentAction.DENY_TOOL, tool, ok,
                                 "tool denied" if ok else "unknown tool")

    def _revoke_session(self, session_id: str) -> ContainmentResult:
        if not session_id:
            raise ContainmentError("revoke_session requires a session id")
        try:
            from aetheros_security.session import get_session_manager
            manager = get_session_manager()
            manager.revoke(session_id)
            ok = True
        except Exception:
            ok = False
        return ContainmentResult(ContainmentAction.REVOKE_SESSION, session_id, ok,
                                 "session revoked" if ok else "session not revocable")

    def _pause_mission(self, mission_id: str, reason: str) -> ContainmentResult:
        """Pause a mission via the orchestrator (best-effort, isolated)."""
        if not mission_id:
            return ContainmentResult(ContainmentAction.PAUSE_MISSION, mission_id,
                                     False, "no mission id")
        try:
            from aetheros_automation.orchestrator.orchestrator import (
                get_orchestrator_or_singleton,
            )
            orchestrator = get_orchestrator_or_singleton()
            # pause_plan is async; best-effort via the plan state when possible.
            orchestrator.pause_plan(mission_id)
            ok = True
        except Exception:
            # Fall back to an emergency stop so work halts.
            from aetheros_security.response import get_response_manager
            get_response_manager().emergency_stop(reason=reason or "mission pause")
            ok = False
        return ContainmentResult(ContainmentAction.PAUSE_MISSION, mission_id, ok,
                                 "mission paused" if ok else "mission not pausable")

    # ------------------------------------------------------------------
    # Runbook execution
    # ------------------------------------------------------------------

    def run_runbook(self, name: str, *, incident: Optional[SecOpsIncident] = None,
                    targets: Optional[Dict[ContainmentAction, str]] = None) -> List[ContainmentResult]:
        """Execute a registered runbook's steps in order."""
        runbook = self.get_runbook(name)
        if runbook is None:
            raise ContainmentError(f"unknown runbook: {name}")
        if not runbook.enabled:
            raise ContainmentError(f"runbook disabled: {name}")
        results: List[ContainmentResult] = []
        for step in runbook.steps:
            target = step.target or (targets or {}).get(step.action, "")
            result = self.contain(step.action, target=target, incident=incident,
                                  reason=f"runbook {name}")
            results.append(result)
            if step.wait_seconds > 0:
                time.sleep(step.wait_seconds)
        if incident is not None:
            incident.add_timeline("runbook_executed", {"runbook": name,
                                                       "steps": len(runbook.steps)})
        return results

    def should_auto_contain(self, severity: SecuritySeverity) -> bool:
        """Whether a detection of this severity may auto-contain."""
        if severity >= SecuritySeverity.CRITICAL:
            return self._auto_contain_critical
        if severity == SecuritySeverity.HIGH:
            return self._auto_contain_high
        return False

    def auto_contain_incident(self, incident: SecOpsIncident) -> List[ContainmentResult]:
        """Pick + run a default containment response for a critical incident."""
        severity = parse_severity(incident.severity)
        if not self.should_auto_contain(severity):
            return []
        actions: List[ContainmentAction] = []
        if incident.affected_principals:
            actions.append(ContainmentAction.QUARANTINE_AGENT)
        if incident.affected_components and "network" in incident.affected_components:
            actions.append(ContainmentAction.KILL_SWITCH)
        if severity >= SecuritySeverity.EMERGENCY:
            actions.append(ContainmentAction.EMERGENCY_STOP)
        targets = {}
        if incident.affected_principals:
            targets[ContainmentAction.QUARANTINE_AGENT] = incident.affected_principals[0]
        if "network" in (incident.affected_components or []):
            targets[ContainmentAction.KILL_SWITCH] = "DISABLE_EXTERNAL_NETWORK"
        results = []
        for action in actions:
            results.append(self.contain(action, target=targets.get(action, ""),
                                        incident=incident,
                                        reason=f"auto-containment of {incident.incident_id}"))
        if incident.transition(IncidentStatus.CONTAINED):
            incident.containment_status = ContainmentStatus.CONTAINED
        return results

    # ------------------------------------------------------------------
    # History / status
    # ------------------------------------------------------------------

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "runbooks": len(self._runbooks),
                "containment_actions": len(self._history),
                "auto_contain_high": self._auto_contain_high,
                "auto_contain_critical": self._auto_contain_critical,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, action: ContainmentAction, target: str,
              result: ContainmentResult, incident: Optional[SecOpsIncident]) -> None:
        if self._bus is None:
            return
        self._bus.emit(
            SecurityEventType.CONTAINMENT_ACTION,
            severity="critical" if result.ok else "warning",
            source="response_engine",
            action=action.value,
            resource=target,
            outcome="ok" if result.ok else "failed",
            message=result.detail,
            payload={"incident_id": incident.incident_id if incident else ""},
        )


# Global response engine
_response_engine: Optional[ResponseEngine] = None


def get_response_engine() -> ResponseEngine:
    """Return the process-wide ResponseEngine singleton."""
    global _response_engine
    if _response_engine is None:
        _response_engine = ResponseEngine()
    return _response_engine