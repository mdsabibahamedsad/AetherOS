"""Research state machine with observable transitions.

Every transition is validated against an explicit table and emitted to all
registered observers, so research progress is inspectable and persistable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from agent.research.models import TaskStatus


ALLOWED_TRANSITIONS = {
    TaskStatus.CREATED: {
        TaskStatus.PLANNING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.PLANNING: {
        TaskStatus.SEARCHING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.SEARCHING: {
        TaskStatus.COLLECTING,
        TaskStatus.SEARCHING,
        TaskStatus.SYNTHESIZING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
        TaskStatus.COMPLETED,
    },
    TaskStatus.COLLECTING: {
        TaskStatus.READING,
        TaskStatus.VERIFYING,
        TaskStatus.SEARCHING,
        TaskStatus.COLLECTING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.READING: {
        TaskStatus.EXTRACTING,
        TaskStatus.VERIFYING,
        TaskStatus.COLLECTING,
        TaskStatus.READING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.EXTRACTING: {
        TaskStatus.VERIFYING,
        TaskStatus.READING,
        TaskStatus.EXTRACTING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.SYNTHESIZING,
        TaskStatus.SEARCHING,
        TaskStatus.EXTRACTING,
        TaskStatus.VERIFYING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.SYNTHESIZING: {
        TaskStatus.REVIEWING,
        TaskStatus.SEARCHING,
        TaskStatus.COMPLETED,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.REVIEWING: {
        TaskStatus.COMPLETED,
        TaskStatus.SEARCHING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.PAUSED: {
        TaskStatus.PLANNING,
        TaskStatus.SEARCHING,
        TaskStatus.COLLECTING,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
}

TERMINAL_STATES = frozenset(
    {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)


class IllegalTransition(Exception):
    def __init__(self, current: TaskStatus, target: TaskStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal research state transition: {current.value} -> {target.value}"
        )


@dataclass
class StateTransition:
    task_id: str
    from_status: str
    to_status: str
    timestamp: float = field(default_factory=time.time)
    detail: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


Observer = Callable[[StateTransition], None]


class ResearchStateMachine:
    """Guards and records status transitions for one ResearchTask."""

    def __init__(self, task_id: str, initial: TaskStatus = TaskStatus.CREATED):
        self.task_id = task_id
        self.status = initial
        self.history: List[StateTransition] = []
        self._observers: List[Observer] = []

    def observe(self, callback: Observer) -> None:
        self._observers.append(callback)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    def can_transition(self, target: TaskStatus) -> bool:
        return target in ALLOWED_TRANSITIONS.get(self.status, set())

    def transition(
        self,
        target: TaskStatus,
        detail: str = "",
        timestamp: Optional[float] = None,
    ) -> StateTransition:
        if not isinstance(target, TaskStatus):
            raise TypeError(f"target must be TaskStatus, got {type(target)!r}")
        if not self.can_transition(target):
            raise IllegalTransition(self.status, target)
        event = StateTransition(
            task_id=self.task_id,
            from_status=self.status.value,
            to_status=target.value,
            detail=detail,
            timestamp=time.time() if timestamp is None else timestamp,
        )
        self.status = target
        self.history.append(event)
        for observer in self._observers:
            observer(event)
        return event
