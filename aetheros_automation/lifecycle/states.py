from __future__ import annotations

from enum import Enum


class LifecycleState(Enum):
    """Unified agent/task lifecycle states.

    Mirrors the orchestrator's ``OrchestratorState`` plus the review/archive
    terminal states required by the unified runtime spec:

        Idle → Planning → Executing → Waiting → Reviewing → Completed → Archived
    """

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    PAUSED = "paused"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = frozenset(
    {LifecycleState.COMPLETED, LifecycleState.ARCHIVED, LifecycleState.FAILED, LifecycleState.CANCELLED}
)

ACTIVE_STATES = frozenset(
    {
        LifecycleState.PLANNING,
        LifecycleState.EXECUTING,
        LifecycleState.WAITING,
        LifecycleState.REVIEWING,
        LifecycleState.PAUSED,
        LifecycleState.BLOCKED,
    }
)

# state -> set of allowed next states
TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.IDLE: frozenset(
        {
            LifecycleState.PLANNING,
            LifecycleState.EXECUTING,
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
        }
    ),
    LifecycleState.PLANNING: frozenset(
        {
            LifecycleState.EXECUTING,
            LifecycleState.WAITING,
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
        }
    ),
    LifecycleState.EXECUTING: frozenset(
        {
            LifecycleState.WAITING,
            LifecycleState.REVIEWING,
            LifecycleState.PAUSED,
            LifecycleState.BLOCKED,
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
        }
    ),
    LifecycleState.WAITING: frozenset(
        {
            LifecycleState.EXECUTING,
            LifecycleState.BLOCKED,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.REVIEWING: frozenset(
        {
            LifecycleState.EXECUTING,
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.BLOCKED,
            LifecycleState.CANCELLED,
        }
    ),
    LifecycleState.COMPLETED: frozenset({LifecycleState.ARCHIVED, LifecycleState.EXECUTING}),
    LifecycleState.ARCHIVED: frozenset({LifecycleState.IDLE}),
    LifecycleState.PAUSED: frozenset(
        {
            LifecycleState.EXECUTING,
            LifecycleState.BLOCKED,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.BLOCKED: frozenset(
        {
            LifecycleState.EXECUTING,
            LifecycleState.WAITING,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.FAILED: frozenset({LifecycleState.EXECUTING, LifecycleState.ARCHIVED}),
    LifecycleState.CANCELLED: frozenset({LifecycleState.ARCHIVED, LifecycleState.IDLE}),
}
