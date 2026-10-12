"""
Kill Switches and Safe Shutdown for AetherOS
============================================

Policy-controlled kill switches that immediately and deterministically stop
classes of behavior (master security spec steps 48-50).

Named switches::

    DISABLE_AUTONOMOUS_ACTIONS   block autonomous / unattended missions
    DISABLE_EXTERNAL_NETWORK     block outbound network access
    DISABLE_TOOL_EXECUTION       block tool execution
    DISABLE_AGENT_DELEGATION     block spawning subagents
    DISABLE_REMOTE_CONTROL       block remote-control / gateway actions
    DISABLE_MODEL_PROVIDER       block model inference calls

Kill switches are policy-controlled: only an elevated principal may flip one,
every transition is audited, and they never auto-reset.

Usage::

    from aetheros_security.kill_switch import (
        KillSwitch, get_kill_switch_registry,
    )

    registry = get_kill_switch_registry()
    registry.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
                        principal="admin", reason="incident")
    registry.is_active(KillSwitch.DISABLE_TOOL_EXECUTION)   # True
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KillSwitch(Enum):
    """Named policy-controlled kill switches (step 49)."""
    DISABLE_AUTONOMOUS_ACTIONS = "disable_autonomous_actions"
    DISABLE_EXTERNAL_NETWORK = "disable_external_network"
    DISABLE_TOOL_EXECUTION = "disable_tool_execution"
    DISABLE_AGENT_DELEGATION = "disable_agent_delegation"
    DISABLE_REMOTE_CONTROL = "disable_remote_control"
    DISABLE_MODEL_PROVIDER = "disable_model_provider"


@dataclass
class KillSwitchState:
    """Current state of one kill switch."""
    switch: KillSwitch
    active: bool = False
    principal: str = ""
    reason: str = ""
    toggled_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "switch": self.switch.value,
            "active": self.active,
            "principal": self.principal,
            "reason": self.reason,
            "toggled_at": self.toggled_at,
        }


class KillSwitchError(Exception):
    """Raised for invalid kill-switch operations."""


class KillSwitchRegistry:
    """Registry of policy-controlled kill switches.

    Flipping a switch requires an elevated principal (or the system).
    Transitions are audited and never silently reset.
    """

    #: Principals considered authoritative enough to flip switches.
    _ELEVATED_PRINCIPALS = {"admin", "system", "security", "root"}

    def __init__(self) -> None:
        self._states: Dict[KillSwitch, KillSwitchState] = {
            switch: KillSwitchState(switch=switch) for switch in KillSwitch
        }
        self._history: List[Dict[str, Any]] = []

    def is_active(self, switch: KillSwitch) -> bool:
        return self._states.get(switch, KillSwitchState(switch=switch)).active

    def is_active_name(self, name: str) -> bool:
        try:
            return self.is_active(KillSwitch(name))
        except ValueError:
            return False

    def active_switches(self) -> List[str]:
        return [k.value for k, v in self._states.items() if v.active]

    def set_switch(self, switch: KillSwitch, active: bool,
                   *, principal: str, reason: str = "") -> bool:
        """Flip a kill switch. Returns True on success.

        Raises:
            KillSwitchError: When the principal is not elevated or the switch
                is unknown.
        """
        if principal not in self._ELEVATED_PRINCIPALS:
            raise KillSwitchError(
                f"principal '{principal}' cannot flip kill switches")
        state = self._states.get(switch)
        if state is None:
            raise KillSwitchError(f"unknown kill switch: {switch}")
        if state.active == active:
            return False  # no change
        state.active = active
        state.principal = principal
        state.reason = reason
        state.toggled_at = time.time()
        self._history.append(state.to_dict())
        self._emit_audit("kill_switch", principal, switch, active, reason)
        logger.warning("Kill switch %s %s by %s (%s)",
                       switch.value, "ACTIVATED" if active else "DEACTIVATED",
                       principal, reason)
        return True

    def set_switch_by_name(self, name: str, active: bool,
                           *, principal: str, reason: str = "") -> bool:
        try:
            return self.set_switch(KillSwitch(name), active,
                                   principal=principal, reason=reason)
        except ValueError as exc:
            raise KillSwitchError(f"unknown kill switch: {name}") from exc

    def status(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._states.values()]

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        return {
            "switches": len(self._states),
            "active": len(self.active_switches()),
            "active_names": self.active_switches(),
        }

    @staticmethod
    def _emit_audit(event_type: str, principal: str, switch: KillSwitch,
                    active: bool, reason: str) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(
                event,
                severity=AuditSeverity.CRITICAL if active else AuditSeverity.INFO,
                user=principal,
                source="kill_switch",
                details={"switch": switch.value, "active": active, "reason": reason},
                message=f"Kill switch {switch.value} {'on' if active else 'off'}",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Safe shutdown
# ---------------------------------------------------------------------------

@dataclass
class ShutdownPlan:
    """What a safe shutdown would / did do (step 50)."""
    stop_new_privileged_actions: bool = False
    cancel_active_agents: bool = False
    checkpoint_state: bool = False
    preserve_audit_evidence: bool = False
    notify_user: bool = False
    enter_safe_state: bool = False
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stop_new_privileged_actions": self.stop_new_privileged_actions,
            "cancel_active_agents": self.cancel_active_agents,
            "checkpoint_state": self.checkpoint_state,
            "preserve_audit_evidence": self.preserve_audit_evidence,
            "notify_user": self.notify_user,
            "enter_safe_state": self.enter_safe_state,
            "steps": list(self.steps),
        }


class SafeShutdownService:
    """Performs a controlled safe shutdown without destroying state.

    Safe shutdown:
        1. Activates kill switches that block new privileged actions.
        2. Signals the emergency-stop/response layer to halt agents.
        3. Records the shutdown plan (audit evidence preserved).
        4. Does NOT delete user data, memory, or session history.
    """

    def __init__(self) -> None:
        self._registry = get_kill_switch_registry()
        self._shutdowns: List[Dict[str, Any]] = []

    def run(self, *, principal: str = "system",
            reason: str = "safe shutdown") -> Dict[str, Any]:
        plan = ShutdownPlan()
        plan.stop_new_privileged_actions = True
        plan.enter_safe_state = True
        plan.preserve_audit_evidence = True
        plan.notify_user = True

        # 1. Block autonomous actions + tool execution + delegation.
        for switch in (KillSwitch.DISABLE_AUTONOMOUS_ACTIONS,
                       KillSwitch.DISABLE_TOOL_EXECUTION,
                       KillSwitch.DISABLE_AGENT_DELEGATION,
                       KillSwitch.DISABLE_EXTERNAL_NETWORK):
            try:
                changed = self._registry.set_switch(
                    switch, True, principal=principal,
                    reason=f"safe shutdown: {reason}")
                if changed:
                    plan.steps.append(f"activated {switch.value}")
            except KillSwitchError as exc:
                plan.steps.append(f"could not activate {switch.value}: {exc}")

        # 2. Propagate to the response layer (emergency stop, no state loss).
        try:
            from aetheros_security.response import get_response_manager
            ok = get_response_manager().emergency_stop(reason=reason)
            plan.cancel_active_agents = ok
            plan.steps.append("emergency stop active" if ok else "emergency stop failed")
        except Exception as exc:
            plan.steps.append(f"response layer unavailable: {exc}")

        record = {"at": time.time(), "principal": principal, "reason": reason,
                  **plan.to_dict()}
        self._shutdowns.append(record)
        self._emit_audit("safe_shutdown", principal, reason)
        return record

    def shutdowns(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._shutdowns[-limit:])

    @staticmethod
    def _emit_audit(event_type: str, principal: str, reason: str) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(
                event,
                severity=AuditSeverity.CRITICAL,
                user=principal,
                source="safe_shutdown",
                details={"reason": reason},
                message="Safe shutdown executed",
            )
        except Exception:
            pass


# Global singletons
_kill_switch_registry: KillSwitchRegistry | None = None
_safe_shutdown_service: SafeShutdownService | None = None


def get_kill_switch_registry() -> KillSwitchRegistry:
    """Return the global KillSwitchRegistry singleton."""
    global _kill_switch_registry
    if _kill_switch_registry is None:
        _kill_switch_registry = KillSwitchRegistry()
    return _kill_switch_registry


def get_safe_shutdown_service() -> SafeShutdownService:
    """Return the global SafeShutdownService singleton."""
    global _safe_shutdown_service
    if _safe_shutdown_service is None:
        _safe_shutdown_service = SafeShutdownService()
    return _safe_shutdown_service