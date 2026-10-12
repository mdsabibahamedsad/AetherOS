"""SessionManager — isolated run sessions (Steps 7, 21).

Each computer-use run gets:

* a unique ``session_id`` with its own state machine, loop detector, and
  audit binding;
* an isolated browser session handle (opaque ``task_id`` — the browser
  engine keeps its own isolation; cookies/tokens are never exposed upward);
* a cancellation/stop channel (STOP / CANCEL / PAUSE / RESUME /
  EMERGENCY STOP).

Emergency stop is a per-session flag the manager checks between actions and
that adapters can check mid-action where technically possible.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from aetheros_actions.state import ComputerUseState, StateMachine


class StopSignal(str, Enum):
    NONE = "NONE"
    STOP = "STOP"
    CANCEL = "CANCEL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    EMERGENCY_STOP = "EMERGENCY_STOP"


def _new_sid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class ComputerUseSession:
    """One isolated computer-use run."""

    session_id: str = field(default_factory=_new_sid)
    agent_id: str = ""
    autonomy_level: Any = None  # AutonomyLevel (from .permissions), resolved lazily
    state: StateMachine = field(default_factory=StateMachine)
    browser_session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    _signal: StopSignal = StopSignal.NONE
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # ── stop / pause / cancel (Step 21) ──────────────────────────────

    def request(self, signal: StopSignal) -> None:
        with self._lock:
            self._signal = signal
            if signal == StopSignal.EMERGENCY_STOP:
                # Emergency stop cancels the session even if it never started
                # (IDLE), so a cancelled session can never be reused.
                try:
                    self.state.transition(ComputerUseState.CANCELLED)
                except Exception:  # noqa: BLE001
                    pass

    def stop(self) -> None:       self.request(StopSignal.STOP)
    def cancel(self) -> None:     self.request(StopSignal.CANCEL)
    def pause(self) -> None:      self.request(StopSignal.PAUSE)
    def resume(self) -> None:     self.request(StopSignal.RESUME)
    def emergency_stop(self) -> None: self.request(StopSignal.EMERGENCY_STOP)

    @property
    def signal(self) -> StopSignal:
        with self._lock:
            return self._signal

    def should_stop(self) -> bool:
        with self._lock:
            return self._signal in (StopSignal.STOP, StopSignal.CANCEL,
                                    StopSignal.EMERGENCY_STOP)

    def is_paused(self) -> bool:
        with self._lock:
            return self._signal == StopSignal.PAUSE

    def clear_stop(self) -> None:
        with self._lock:
            if self._signal in (StopSignal.STOP, StopSignal.CANCEL):
                self._signal = StopSignal.NONE

    def set_autonomy(self, level: Any) -> None:
        self.autonomy_level = level


class SessionManager:
    """Registry of live computer-use sessions + stop fan-out."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ComputerUseSession] = {}
        self._lock = threading.RLock()

    def create(
        self,
        agent_id: str = "",
        autonomy_level: Any = None,
    ) -> ComputerUseSession:
        # AutonomyLevel may live in aetheros_actions.permissions; keep the
        # import here to avoid a circular dependency at module import time.
        from aetheros_actions.permissions import AutonomyLevel  # noqa: PLC0415
        if autonomy_level is None:
            autonomy_level = AutonomyLevel.SAFE_AUTONOMOUS
        if isinstance(autonomy_level, int) and not hasattr(autonomy_level, "value"):
            autonomy_level = AutonomyLevel(int(autonomy_level))
        session = ComputerUseSession(
            agent_id=agent_id,
            autonomy_level=autonomy_level,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[ComputerUseSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def list(self) -> List[ComputerUseSession]:
        with self._lock:
            return list(self._sessions.values())

    def stop_all(self, signal: StopSignal = StopSignal.EMERGENCY_STOP) -> int:
        """Fan out a stop to every live session; returns how many were stopped."""
        with self._lock:
            sessions = list(self._sessions.values())
        for s in sessions:
            s.request(signal)
        return len(sessions)


__all__ = ["ComputerUseSession", "SessionManager", "StopSignal"]