"""Recovery state machine for AetherOS.

Implements the ten-state recovery lifecycle:

    NORMAL → DEGRADED → FAILURE_DETECTED → DIAGNOSING → RECOVERING
           → VERIFYING → RECOVERED   (or)   FAILED_RECOVERY
    DEGRADED / FAILED_RECOVERY → SAFE_MODE → RECOVERY_MODE → NORMAL

Transitions are validated; ``force`` is reserved for operator-driven entry
into SAFE_MODE / RECOVERY_MODE and for recovery paths that must move out of a
terminal-ish state deliberately.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class RecoveryState(str, enum.Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    FAILURE_DETECTED = "failure_detected"
    DIAGNOSING = "diagnosing"
    RECOVERING = "recovering"
    VERIFYING = "verifying"
    RECOVERED = "recovered"
    FAILED_RECOVERY = "failed_recovery"
    SAFE_MODE = "safe_mode"
    RECOVERY_MODE = "recovery_mode"


#: Allowed transitions.  SAFE_MODE / RECOVERY_MODE are reachable from most
#: non-NORMAL states via ``force`` (operator-initiated).
_TRANSITIONS: Dict[RecoveryState, frozenset] = {
    RecoveryState.NORMAL: frozenset({
        RecoveryState.DEGRADED,
        RecoveryState.FAILURE_DETECTED,
        RecoveryState.RECOVERING,
    }),
    RecoveryState.DEGRADED: frozenset({
        RecoveryState.NORMAL,
        RecoveryState.FAILURE_DETECTED,
        RecoveryState.RECOVERING,
    }),
    RecoveryState.FAILURE_DETECTED: frozenset({
        RecoveryState.DIAGNOSING,
        RecoveryState.DEGRADED,
        RecoveryState.NORMAL,
    }),
    RecoveryState.DIAGNOSING: frozenset({
        RecoveryState.RECOVERING,
        RecoveryState.FAILURE_DETECTED,
        RecoveryState.DEGRADED,
        RecoveryState.NORMAL,
    }),
    RecoveryState.RECOVERING: frozenset({
        RecoveryState.VERIFYING,
        RecoveryState.FAILED_RECOVERY,
        RecoveryState.DEGRADED,
    }),
    RecoveryState.VERIFYING: frozenset({
        RecoveryState.RECOVERED,
        RecoveryState.FAILED_RECOVERY,
        RecoveryState.DEGRADED,
    }),
    RecoveryState.RECOVERED: frozenset({
        RecoveryState.NORMAL,
        RecoveryState.DEGRADED,
    }),
    RecoveryState.FAILED_RECOVERY: frozenset({
        RecoveryState.DEGRADED,
        RecoveryState.RECOVERING,
    }),
    RecoveryState.SAFE_MODE: frozenset({
        RecoveryState.NORMAL,
        RecoveryState.RECOVERY_MODE,
        RecoveryState.DEGRADED,
    }),
    RecoveryState.RECOVERY_MODE: frozenset({
        RecoveryState.NORMAL,
        RecoveryState.SAFE_MODE,
        RecoveryState.DEGRADED,
    }),
}


@dataclass
class StateTransition:
    from_state: RecoveryState
    to_state: RecoveryState
    reason: str = ""
    operator: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "reason": self.reason,
            "operator": self.operator,
            "timestamp": self.timestamp,
        }


class RecoveryStateMachine:
    """Thread-safe recovery state machine with transition validation.

    Usage::

        sm = RecoveryStateMachine()
        sm.enter(RecoveryState.FAILURE_DETECTED, reason="gateway crash")
        sm.enter(RecoveryState.DIAGNOSING)
        sm.enter(RecoveryState.RECOVERING)
        sm.enter(RecoveryState.VERIFYING)
        sm.enter(RecoveryState.RECOVERED)
        print(sm.state)  # RecoveryState.RECOVERED
    """

    def __init__(self, initial: RecoveryState = RecoveryState.NORMAL) -> None:
        self._lock = threading.RLock()
        self._state = initial
        self._history: list[StateTransition] = []
        self._listeners: list[Callable[[StateTransition], None]] = []
        self._entered_at = time.time()

    @property
    def state(self) -> RecoveryState:
        with self._lock:
            return self._state

    @property
    def since(self) -> float:
        return time.time() - self._entered_at

    def on_transition(self, listener: Callable[[StateTransition], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def can_enter(self, target: RecoveryState) -> bool:
        with self._lock:
            return target in _TRANSITIONS.get(self._state, frozenset()) or target == self._state

    def enter(
        self,
        target: RecoveryState,
        reason: str = "",
        force: bool = False,
    ) -> StateTransition:
        """Move to *target*.  ``force`` bypasses transition validation for
        operator-initiated moves (safe/recovery mode entry, recovery paths).
        """
        with self._lock:
            current = self._state
            if target == current:
                return StateTransition(current, target, reason, force, time.time())
            if not force and not self.can_enter(target):
                raise ValueError(
                    f"Illegal recovery-state transition: "
                    f"{current.value} → {target.value}"
                )
            record = StateTransition(current, target, reason, force, time.time())
            self._state = target
            self._entered_at = time.time()
            self._history.append(record)
            listeners = list(self._listeners)
        logger.info(
            "Recovery state: %s → %s (%s)%s",
            record.from_state.value, record.to_state.value, reason or "no reason",
            " [operator]" if force else "",
        )
        for listener in listeners:
            try:
                listener(record)
            except Exception:
                logger.exception("Recovery state listener failed")
        return record

    def history(self, limit: int = 50) -> list[Dict[str, Any]]:
        with self._lock:
            return [t.to_dict() for t in self._history[-limit:]]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "since": round(self.since, 2),
                "history": [t.to_dict() for t in self._history[-20:]],
            }

    def in_recovery(self) -> bool:
        with self._lock:
            return self._state in (
                RecoveryState.FAILURE_DETECTED,
                RecoveryState.DIAGNOSING,
                RecoveryState.RECOVERING,
                RecoveryState.VERIFYING,
            )


_singleton_lock = threading.Lock()
_state_machine: Optional[RecoveryStateMachine] = None


def get_recovery_state_machine() -> RecoveryStateMachine:
    """Return the process-wide recovery state machine singleton."""
    global _state_machine
    if _state_machine is None:
        with _singleton_lock:
            if _state_machine is None:
                _state_machine = RecoveryStateMachine()
    return _state_machine