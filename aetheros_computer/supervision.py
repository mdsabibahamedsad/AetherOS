"""
Supervision state machine + user takeover / login handoff
(Master 15 Phases 21, 28, 58, 59).

States: NORMAL → WATCH → PAUSED → USER_TAKEOVER → SAFE_MODE → EMERGENCY_STOP

Contract:
- Actions with risk ≥ R2 are refused while PAUSED or USER_TAKEOVER.
- ``request_login_handoff`` transitions to USER_TAKEOVER and carries NO secret
  material — the user completes auth out-of-band; the agent only learns that
  handoff finished.
- ``complete_takeover`` returns to NORMAL but sets ``must_reobserve=True``
  (Phase 59): the next execute() MUST observe before acting, and an unexpected
  screen fingerprint forces STOP→RE-PLAN rather than blind continuation.
"""

from __future__ import annotations

import enum
import hashlib
import threading
import time
from typing import Any, Callable, Dict, Optional


class SupervisionState(enum.Enum):
    NORMAL = "normal"
    WATCH = "watch"                    # user actively supervising sensitive flow
    PAUSED = "paused"
    USER_TAKEOVER = "user_takeover"
    SAFE_MODE = "safe_mode"
    EMERGENCY_STOP = "emergency_stop"


_BLOCKING_STATES = frozenset({SupervisionState.PAUSED,
                              SupervisionState.USER_TAKEOVER,
                              SupervisionState.EMERGENCY_STOP})


def _screen_fingerprint(fingerprint_fn: Optional[Callable[[], str]]) -> str:
    """Fingerprint of current screen/page state, provided by host runtime."""
    if fingerprint_fn is None:
        return ""
    try:
        return str(fingerprint_fn()) or ""
    except Exception:
        return ""


class SupervisionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = SupervisionState.NORMAL
        self._must_reobserve = False
        self._last_fingerprint = ""
        self._handoff_started_at: Optional[float] = None
        self._fingerprint_fn: Optional[Callable[[], str]] = None

    # -- wiring ------------------------------------------------------------
    def set_fingerprint_fn(self, fn: Callable[[], str]) -> None:
        """Host injects a cheap screen/page-state hash provider."""
        self._fingerprint_fn = fn

    # -- state transitions ---------------------------------------------------
    def state(self) -> SupervisionState:
        with self._lock:
            return self._state

    def set_state(self, new: SupervisionState) -> SupervisionState:
        with self._lock:
            prev, self._state = self._state, new
            if new == SupervisionState.NORMAL and prev in (
                SupervisionState.SAFE_MODE, SupervisionState.EMERGENCY_STOP,
                SupervisionState.WATCH,
            ):
                self._must_reobserve = True
        return new

    def request_watch(self) -> None:
        self.set_state(SupervisionState.WATCH)

    def pause(self) -> None:
        self.set_state(SupervisionState.PAUSED)

    def resume(self) -> None:
        """Resume from pause: re-observation is forced (Phase 59)."""
        with self._lock:
            if self._state != SupervisionState.PAUSED:
                return
            self._state = SupervisionState.NORMAL
            self._must_reobserve = True

    # -- Phase 58: login / MFA / CAPTCHA handoff -----------------------------
    def request_login_handoff(self, reason: str, auth_type: str,
                              timeout_seconds: float = 300.0) -> Dict[str, Any]:
        """Pause the agent and hand control to the user.

        No credential material is accepted or returned — ever.
        """
        with self._lock:
            self._state = SupervisionState.USER_TAKEOVER
            self._handoff_started_at = time.time()
        return {
            "type": "login_handoff",
            "reason": str(reason)[:300],
            "auth_type": str(auth_type),          # password|mfa|captcha|security_key
            "state": self.state().value,
            "started_at": self._handoff_started_at,
            "expires_at": time.time() + max(30.0, timeout_seconds),
        }

    def complete_takeover(self, observed_changed: Optional[bool] = None) -> Dict[str, Any]:
        """User finished auth/manual step → back to NORMAL + forced re-observe."""
        fp_now = _screen_fingerprint(self._fingerprint_fn)
        with self._lock:
            changed = observed_changed
            if changed is None and self._last_fingerprint and fp_now:
                changed = fp_now != self._last_fingerprint
            self._state = SupervisionState.NORMAL
            self._must_reobserve = True   # Phase 59: never assume unchanged screen
            self._handoff_started_at = None
        return {"state": self.state().value, "must_reobserve": True,
                "screen_changed": bool(changed)}

    # -- gating consumed by Dispatcher ---------------------------------------
    def allows_action(self, risk_value: int) -> Dict[str, Any]:
        with self._lock:
            st = self._state
            must_reobs = self._must_reobserve
        if st == SupervisionState.EMERGENCY_STOP:
            return {"allowed": False, "reason": "emergency stop active"}
        if st in (SupervisionState.PAUSED, SupervisionState.USER_TAKEOVER):
            return {"allowed": False, "reason": f"supervision state={st.value}"}
        if st == SupervisionState.USER_TAKEOVER:
            pass
        if st == SupervisionState.WATCH and risk_value >= 3:
            # WATCH mode: high-impact still needs the normal approval path;
            # WATCH itself only adds visibility, it never weakens controls.
            pass
        return {"allowed": True, "reason": "",
                "must_reobserve_first": must_reobs}

    def consume_reobserve_flag(self) -> bool:
        with self._lock:
            flag = self._must_reobserve
            self._must_reobserve = False
        return flag

    def note_observation(self, fingerprint: str) -> None:
        with self._lock:
            self._last_fingerprint = fingerprint


# Process-wide instance (computer-use runs inside one agent process).
_manager: Optional[SupervisionManager] = None
_mgr_lock = threading.Lock()


def get_supervision() -> SupervisionManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = SupervisionManager()
        return _manager


def reset_supervision() -> None:
    global _manager
    with _mgr_lock:
        _manager = SupervisionManager()


__all__ = [
    "SupervisionState",
    "SupervisionManager",
    "get_supervision",
    "reset_supervision",
]
