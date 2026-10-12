"""Computer-use state machine (Step 18).

Every execution run maintains an explicit state:

    IDLE → OBSERVING → PLANNING → WAITING_FOR_PERMISSION → EXECUTING
         → VERIFYING → COMPLETED
    EXECUTING → RECOVERING → EXECUTING | FAILED
    any active state → CANCELLED (emergency stop)

The machine is strict: invalid transitions raise :class:`InvalidTransition`.
A fatal verification failure transitions to FAILED and **never** continues to
a new action.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class ComputerUseState(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    PLANNING = "PLANNING"
    WAITING_FOR_PERMISSION = "WAITING_FOR_PERMISSION"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    ACTIVE_STATES = frozenset({
        OBSERVING, PLANNING, WAITING_FOR_PERMISSION, EXECUTING,
        VERIFYING, RECOVERING,
    })
    TERMINAL_STATES = frozenset({COMPLETED, FAILED, CANCELLED})


class InvalidTransition(Exception):
    pass


# Valid transitions. Emergency stop (→ CANCELLED) is always allowed from any
# non-terminal state, including IDLE (a session that has not started can be
# cancelled).
_TRANSITIONS: Dict[ComputerUseState, Set[ComputerUseState]] = {
    ComputerUseState.IDLE: {
        ComputerUseState.OBSERVING, ComputerUseState.PLANNING,
        ComputerUseState.EXECUTING,
    },
    ComputerUseState.OBSERVING: {ComputerUseState.PLANNING, ComputerUseState.OBSERVING},
    ComputerUseState.PLANNING: {
        ComputerUseState.WAITING_FOR_PERMISSION, ComputerUseState.EXECUTING,
        ComputerUseState.COMPLETED,
    },
    ComputerUseState.WAITING_FOR_PERMISSION: {
        ComputerUseState.EXECUTING, ComputerUseState.COMPLETED,
    },
    ComputerUseState.EXECUTING: {
        ComputerUseState.VERIFYING, ComputerUseState.RECOVERING,
        ComputerUseState.COMPLETED, ComputerUseState.FAILED,
    },
    ComputerUseState.VERIFYING: {
        ComputerUseState.EXECUTING, ComputerUseState.COMPLETED,
        ComputerUseState.RECOVERING, ComputerUseState.FAILED,
    },
    ComputerUseState.RECOVERING: {
        ComputerUseState.EXECUTING, ComputerUseState.FAILED,
    },
    ComputerUseState.COMPLETED: set(),
    ComputerUseState.FAILED: set(),
    ComputerUseState.CANCELLED: set(),
}


class StateMachine:
    """State container enforcing the transition table."""

    def __init__(self, initial: ComputerUseState = ComputerUseState.IDLE) -> None:
        self._state = initial
        self._history: list[ComputerUseState] = [initial]

    @property
    def state(self) -> ComputerUseState:
        return self._state

    @property
    def history(self) -> list[ComputerUseState]:
        return list(self._history)

    def transition(self, target: ComputerUseState) -> None:
        """Move to ``target``; raise InvalidTransition on illegal moves."""
        if target == self._state:
            return
        if target is ComputerUseState.CANCELLED and self._state not in ComputerUseState.TERMINAL_STATES:
            # Emergency stop is always allowed from any non-terminal state,
            # including IDLE (a run that never started is trivially cancelled).
            self._state = target
            self._history.append(target)
            return
        allowed = _TRANSITIONS.get(self._state, set())
        if self._state in ComputerUseState.TERMINAL_STATES:
            raise InvalidTransition(
                f"cannot transition from terminal state {self._state.value}"
            )
        if target not in allowed:
            raise InvalidTransition(
                f"invalid transition {self._state.value} → {target.value}"
            )
        self._state = target
        self._history.append(target)

    def enter(self, target: ComputerUseState) -> None:
        """Alias for :meth:`transition`."""
        self.transition(target)

    def can_stop(self) -> bool:
        """True when emergency stop is allowed right now."""
        return self._state in ComputerUseState.ACTIVE_STATES

    def is_terminal(self) -> bool:
        return self._state in ComputerUseState.TERMINAL_STATES