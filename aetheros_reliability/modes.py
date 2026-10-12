"""Safe Mode / Recovery Mode / Degraded Mode controllers.

* **Safe Mode** minimizes plugins, third-party integrations, autonomous
  execution and network access — while keeping diagnostics, recovery,
  configuration repair and user support available.
* **Recovery Mode** enables diagnostics, restore-backup, config repair,
  installation verification, crash-report viewing and update rollback.
* **Degraded Mode** is the runtime posture the health layer enters when a
  dependency is unavailable (safe partial operation).

Modes are process-wide singletons exposed via ``get_mode_controller()``.
Entering/leaving is audited and reflected in the recovery state machine.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AetherOSMode(str, enum.Enum):
    NORMAL = "normal"
    SAFE_MODE = "safe_mode"
    RECOVERY_MODE = "recovery_mode"
    DEGRADED = "degraded"


@dataclass
class ModeEntry:
    mode: AetherOSMode
    entered_at: float
    reason: str
    operator: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode.value, "entered_at": self.entered_at,
                "reason": self.reason, "operator": self.operator}


class ModeController:
    """Tracks and enforces the current operating mode.

    Usage::

        mc = get_mode_controller()
        mc.enter_safe_mode(reason="crash loop")
        mc.active()            # AetherOSMode.SAFE_MODE
        mc.exit_safe_mode()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mode = AetherOSMode.NORMAL
        self._history: List[ModeEntry] = []
        self._hooks: Dict[AetherOSMode, List[callable]] = {}
        self._degraded_components: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Mode transitions
    # ------------------------------------------------------------------

    def enter_safe_mode(self, reason: str = "", operator: bool = False) -> bool:
        return self._enter(AetherOSMode.SAFE_MODE, reason, operator)

    def enter_recovery_mode(self, reason: str = "", operator: bool = False) -> bool:
        return self._enter(AetherOSMode.RECOVERY_MODE, reason, operator)

    def enter_degraded(self, component: str, reason: str) -> None:
        with self._lock:
            self._degraded_components[component] = reason
            if self._mode == AetherOSMode.NORMAL:
                self._mode = AetherOSMode.DEGRADED

    def clear_degraded(self, component: str) -> None:
        with self._lock:
            self._degraded_components.pop(component, None)
            if not self._degraded_components and self._mode == AetherOSMode.DEGRADED:
                self._mode = AetherOSMode.NORMAL

    def exit_safe_mode(self) -> bool:
        return self._enter(AetherOSMode.NORMAL, "exited safe mode", operator=True)

    def exit_recovery_mode(self) -> bool:
        return self._enter(AetherOSMode.NORMAL, "exited recovery mode", operator=True)

    def _enter(self, mode: AetherOSMode, reason: str, operator: bool) -> bool:
        with self._lock:
            if self._mode == mode:
                return False
            prev = self._mode
            self._mode = mode
            self._history.append(ModeEntry(mode, time.time(), reason, operator))
            hooks = list(self._hooks.get(mode, []))
        logger.info("Mode: %s → %s (%s)%s", prev.value, mode.value,
                    reason or "no reason", " [operator]" if operator else "")
        self._sync_state_machine(mode, reason)
        for hook in hooks:
            try:
                hook(mode, reason)
            except Exception:
                logger.exception("mode hook failed")
        return True

    def on_enter(self, mode: AetherOSMode, hook: callable) -> None:
        with self._lock:
            self._hooks.setdefault(mode, []).append(hook)

    def _sync_state_machine(self, mode: AetherOSMode, reason: str) -> None:
        try:
            from aetheros_reliability.states import (
                RecoveryState, get_recovery_state_machine,
            )
            sm = get_recovery_state_machine()
            if mode == AetherOSMode.SAFE_MODE:
                sm.enter(RecoveryState.SAFE_MODE, reason, force=True)
            elif mode == AetherOSMode.RECOVERY_MODE:
                sm.enter(RecoveryState.RECOVERY_MODE, reason, force=True)
            elif mode == AetherOSMode.NORMAL:
                if sm.state in (RecoveryState.SAFE_MODE, RecoveryState.RECOVERY_MODE):
                    sm.enter(RecoveryState.NORMAL, reason, force=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active(self) -> AetherOSMode:
        with self._lock:
            return self._mode

    def is_safe_mode(self) -> bool:
        return self.active() == AetherOSMode.SAFE_MODE

    def is_recovery_mode(self) -> bool:
        return self.active() == AetherOSMode.RECOVERY_MODE

    def is_degraded(self) -> bool:
        return self.active() == AetherOSMode.DEGRADED

    def degraded_components(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._degraded_components)

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [e.to_dict() for e in self._history[-limit:]]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "mode": self._mode.value,
                "degraded_components": dict(self._degraded_components),
                "history": [e.to_dict() for e in self._history[-10:]],
            }


_controller: Optional[ModeController] = None
_controller_lock = threading.Lock()


def get_mode_controller() -> ModeController:
    """Return the process-wide ModeController singleton."""
    global _controller
    if _controller is None:
        with _controller_lock:
            if _controller is None:
                _controller = ModeController()
    return _controller