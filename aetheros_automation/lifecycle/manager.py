from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from aetheros_automation.lifecycle.states import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    LifecycleState,
)

logger = logging.getLogger(__name__)


@dataclass
class TransitionRecord:
    from_state: LifecycleState
    to_state: LifecycleState
    reason: str = ""
    timestamp: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class AgentLifecycle:
    """A unified, validated lifecycle state machine for agents and tasks.

    Tracks one entity (a task, a plan, or an agent) through the canonical
    Idle → Planning → Executing → Waiting → Reviewing → Completed → Archived
    flow, validating every transition and notifying listeners on change.
    """

    def __init__(self, entity_id: str, initial: LifecycleState = LifecycleState.IDLE) -> None:
        self.entity_id = entity_id
        self._state = initial
        self._history: list[TransitionRecord] = []
        self._listeners: list[Callable[[TransitionRecord], None]] = []
        self._metadata: dict[str, Any] = {}
        self._created_at = time.time()

    # ── properties ──────────────────────────────────────────────

    @property
    def state(self) -> LifecycleState:
        return self._state

    @property
    def history(self) -> list[TransitionRecord]:
        return list(self._history)

    @property
    def is_active(self) -> bool:
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def age_seconds(self) -> float:
        return time.time() - self._created_at

    # ── public API ──────────────────────────────────────────────

    def on_transition(self, listener: Callable[[TransitionRecord], None]) -> None:
        self._listeners.append(listener)

    def can_transition(self, target: LifecycleState) -> bool:
        return target in TRANSITIONS.get(self._state, frozenset())

    def allowed_next(self) -> list[LifecycleState]:
        return list(TRANSITIONS.get(self._state, frozenset()))

    def transition(
        self,
        target: LifecycleState,
        reason: str = "",
        force: bool = False,
    ) -> TransitionRecord:
        """Move to *target*. Raises ``ValueError`` on an invalid transition
        unless *force* is set (used for recovery / restart paths)."""
        if target == self._state:
            return TransitionRecord(target, target, reason, time.time())
        if not force and not self.can_transition(target):
            raise ValueError(
                f"Illegal lifecycle transition for {self.entity_id}: "
                f"{self._state.value} → {target.value}"
            )
        record = TransitionRecord(self._state, target, reason, time.time())
        self._state = target
        self._history.append(record)
        logger.debug(
            "Lifecycle %s: %s → %s (%s)",
            self.entity_id, record.from_state.value, record.to_state.value, reason,
        )
        for listener in self._listeners:
            try:
                listener(record)
            except Exception:
                logger.exception("Lifecycle listener failed for %s", self.entity_id)
        return record

    def snapshot(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "state": self._state.value,
            "active": self.is_active,
            "terminal": self.is_terminal,
            "created_at": self._created_at,
            "age_seconds": round(self.age_seconds, 2),
            "history": [r.as_dict() for r in self._history],
            "metadata": dict(self._metadata),
        }

    def describe(self) -> str:
        return f"{self.entity_id}: {self._state.value} ({len(self._history)} transitions)"


class LifecycleRegistry:
    """In-memory registry of all lifecycle trackers, keyed by entity id."""

    def __init__(self) -> None:
        self._trackers: dict[str, AgentLifecycle] = {}

    def get(self, entity_id: str) -> AgentLifecycle | None:
        return self._trackers.get(entity_id)

    def create(self, entity_id: str, initial: LifecycleState = LifecycleState.IDLE) -> AgentLifecycle:
        tracker = AgentLifecycle(entity_id, initial=initial)
        self._trackers[entity_id] = tracker
        return tracker

    def ensure(self, entity_id: str) -> AgentLifecycle:
        return self._trackers.setdefault(entity_id, AgentLifecycle(entity_id))

    def snapshot(self) -> list[dict[str, Any]]:
        return [t.snapshot() for t in self._trackers.values()]

    def active(self) -> list[AgentLifecycle]:
        return [t for t in self._trackers.values() if t.is_active]

    def summarize(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for tracker in self._trackers.values():
            counts[tracker.state.value] = counts.get(tracker.state.value, 0) + 1
        return {
            "total": len(self._trackers),
            "active": len(self.active()),
            "by_state": counts,
        }
