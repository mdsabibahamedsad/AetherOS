"""
Self-protection: the SecOps layer cannot be disabled by agents.

Self-protection guarantees:

    - agents (non-elevated principals) cannot disable monitoring, audit,
      detection, or the deterministic authorization boundary;
    - only elevated principals (admin/system/security/root) may flip
      security controls;
    - every attempt to disable a control is audited and raises a detection
      (policy-bypass signal);
    - the self-protection guard itself is a no-op for elevated principals.

The guard is advisory-but-strong: it refuses the mutation at the SecOps
boundary and composes the control plane's kill-switch elevation rule.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Any, Dict, Optional

from .events import SecurityEventType, SecurityEventBus

logger = logging.getLogger(__name__)


class ProtectedControl(Enum):
    MONITORING = "monitoring"
    AUDIT = "audit"
    DETECTION = "detection"
    AUTHZ = "authz"
    SECOPS = "secops"


#: Elevated principals permitted to mutate security controls.
_ELEVATED_PRINCIPALS = {"admin", "system", "security", "root"}


class SelfProtectionError(Exception):
    """Raised when a non-elevated principal tries to disable a control."""


class SelfProtectionGuard:
    """Refuses security-control mutations from non-elevated principals.

    Usage::

        guard = SelfProtectionGuard()
        guard.set_bus(bus)
        guard.check(ProtectedControl.AUDIT, principal="agent-1")   # raises
        guard.check(ProtectedControl.AUDIT, principal="admin")     # ok
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bus: Optional[SecurityEventBus] = None
        self._protected = {c: True for c in ProtectedControl}
        self._denials: list = []

    def set_bus(self, bus: SecurityEventBus) -> None:
        self._bus = bus

    def is_elevated(self, principal: str) -> bool:
        return (principal or "").lower() in _ELEVATED_PRINCIPALS

    def check(self, control: ProtectedControl, *, principal: str,
              action: str = "disable", reason: str = "") -> None:
        """Raise SelfProtectionError when the principal may not mutate it."""
        control = ProtectedControl(control)
        if not self._protected[control]:
            return  # control already open (explicitly allowed by operator)
        if self.is_elevated(principal):
            return
        self._record_denial(control, principal, action, reason)
        raise SelfProtectionError(
            f"principal '{principal}' may not {action} security control "
            f"'{control.value}'")

    def can_disable(self, control: ProtectedControl, *, principal: str) -> bool:
        """Non-raising variant used by the orchestrator."""
        try:
            self.check(control, principal=principal, action="disable")
            return True
        except SelfProtectionError:
            return False

    def open_control(self, control: ProtectedControl, *, principal: str,
                     reason: str = "") -> bool:
        """Explicitly open a protected control (elevated principals only)."""
        control = ProtectedControl(control)
        if not self.is_elevated(principal):
            self._record_denial(control, principal, "open", reason)
            raise SelfProtectionError(
                f"principal '{principal}' may not open control '{control.value}'")
        self._protected[control] = False
        return True

    def close_control(self, control: ProtectedControl) -> None:
        self._protected[ProtectedControl(control)] = True

    def protected_status(self) -> Dict[str, bool]:
        with self._lock:
            return {c.value: v for c, v in self._protected.items()}

    def denials(self, limit: int = 50) -> list:
        with self._lock:
            return list(self._denials[-limit:])

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "protected": {c.value: v for c, v in self._protected.items()},
                "denials": len(self._denials),
            }

    def _record_denial(self, control: ProtectedControl, principal: str,
                       action: str, reason: str) -> None:
        entry = {
            "control": control.value,
            "principal": principal,
            "action": action,
            "reason": reason,
            "timestamp": time.time(),
        }
        with self._lock:
            self._denials.append(entry)
        logger.warning(
            "Self-protection denial: principal=%s tried to %s %s (%s)",
            principal, action, control.value, reason or "no reason")
        if self._bus is not None:
            self._bus.emit(
                SecurityEventType.AUTHZ_DENY,
                severity="high",
                source="self_protection",
                principal=principal,
                action=f"self_protection.{action}",
                resource=control.value,
                outcome="denied",
                message=f"self-protection blocked {principal} from {action}ing {control.value}",
            )


# Global self-protection guard
_self_protection: Optional[SelfProtectionGuard] = None


def get_self_protection_guard() -> SelfProtectionGuard:
    """Return the process-wide SelfProtectionGuard singleton."""
    global _self_protection
    if _self_protection is None:
        _self_protection = SelfProtectionGuard()
    return _self_protection