"""Task Lifecycle Management for AetherOS Orchestration Layer.

Implements Phase 7 of Master Prompt 11: task lifecycle states and transitions.

Provides:
- State machine for task lifecycle with validated transitions
- Event hooks for lifecycle events
- Automatic timestamps and audit trail
- Integration with TaskSpec
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from agent.orchestration.event_stream import (
    AgentEvent,
    EventType,
    get_event_stream,
)
from agent.orchestration.types import (
    TaskSpec,
    TaskStatus,
    TaskPriority,
    TaskBudget,
    AgentRole,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Transition Validation
# =============================================================================

# Valid transitions: from_status -> set of valid to_status
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING,
        TaskStatus.BLOCKED,
        TaskStatus.VERIFYING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.PAUSED,
        TaskStatus.REQUIRES_APPROVAL,
    },
    TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT},
    TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.VERIFYING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.REQUIRES_APPROVAL},
    TaskStatus.REQUIRES_APPROVAL: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.PAUSED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    # Terminal states - no transitions out
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
    TaskStatus.TIMEOUT: set(),
    TaskStatus.EMERGENCY_STOPPED: set(),
}


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if a status transition is valid."""
    return to_status in VALID_TRANSITIONS.get(from_status, set())


def is_terminal_status(status: TaskStatus) -> bool:
    """Check if a task status is terminal (no further transitions)."""
    return status in {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.TIMEOUT,
        TaskStatus.EMERGENCY_STOPPED,
    }


# =============================================================================
# Lifecycle Events
# =============================================================================


class LifecycleEventType(Enum):
    """Types of lifecycle events."""

    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_PLANNING = "task_planning"
    TASK_READY = "task_ready"
    TASK_STARTED = "task_started"
    TASK_WAITING = "task_waiting"
    TASK_BLOCKED = "task_blocked"
    TASK_VERIFYING = "task_verifying"
    TASK_REQUIRES_APPROVAL = "task_requires_approval"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMED_OUT = "task_timed_out"
    TASK_EMERGENCY_STOPPED = "task_emergency_stopped"
    TASK_APPROVED = "task_approved"
    TASK_DENIED = "task_denied"
    TASK_ASSIGNED = "task_assigned"
    TASK_UNASSIGNED = "task_unassigned"
    TASK_RETRY = "task_retry"


@dataclass
class LifecycleEvent:
    """Event in the task lifecycle."""

    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    event_type: LifecycleEventType = LifecycleEventType.TASK_CREATED
    from_status: Optional[TaskStatus] = None
    to_status: TaskStatus = TaskStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "from_status": self.from_status.value if self.from_status else None,
            "to_status": self.to_status.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "metadata": self.metadata,
        }


# =============================================================================
# Task Lifecycle Manager
# =============================================================================


class TaskLifecycleManager:
    """Manages task lifecycle transitions with validation and event emission."""

    def __init__(self):
        self._tasks: Dict[str, TaskSpec] = {}
        self._event_log: List[LifecycleEvent] = []
        self._max_events = 10000
        self._callbacks: Dict[LifecycleEventType, List[Callable[[LifecycleEvent], None]]] = {}
        self._lock = asyncio.Lock()

    # ── Task Registry ──────────────────────────────────────────────────

    def register_task(self, task: TaskSpec) -> None:
        """Register a task for lifecycle management."""
        self._tasks[task.task_id] = task
        self._emit_event(LifecycleEvent(
            task_id=task.task_id,
            event_type=LifecycleEventType.TASK_CREATED,
            from_status=None,
            to_status=task.status,
            message=f"Task created: {task.goal[:80]}",
        ))

    def unregister_task(self, task_id: str) -> bool:
        """Remove a task from lifecycle management."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[TaskSpec]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    # ── State Transitions ──────────────────────────────────────────────

    async def transition(
        self,
        task_id: str,
        to_status: TaskStatus,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Transition a task to a new status with validation.

        Returns True if transition was successful.
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for transition")
                return False

            from_status = task.status

            # Validate transition
            if not can_transition(from_status, to_status):
                logger.warning(
                    f"Invalid transition for task {task_id}: {from_status.value} -> {to_status.value}"
                )
                return False

            # Update task
            old_status = task.status
            task.status = to_status
            task.updated_at = time.time()

            # Update timestamps based on new status
            self._update_timestamps(task, to_status)

            # Emit lifecycle event
            self._emit_event(LifecycleEvent(
                task_id=task.task_id,
                event_type=self._status_to_event_type(to_status),
                from_status=from_status,
                to_status=to_status,
                message=message or f"Task transitioned from {from_status.value} to {to_status.value}",
                metadata=metadata or {},
            ))

            # Emit canonical agent event
            event_stream = await get_event_stream(task_id)
            agent_event = AgentEvent(
                task_id=task_id,
                event_type=EventType(self._status_to_event_type_name(to_status)),
                payload={
                    "from_status": from_status.value if from_status else "",
                    "to_status": to_status.value,
                    "message": message,
                },
                metadata=metadata or {},
            )
            event_stream.emit(EventType(self._status_to_event_type_name(to_status)), {
                "from_status": from_status.value if from_status else "",
                "to_status": to_status.value,
                "message": message,
            })

            logger.info(f"Task {task_id}: {from_status.value} -> {to_status.value} ({message})")
            return True

    @staticmethod
    def _status_to_event_type_name(status: TaskStatus) -> str:
        """Convert TaskStatus to EventType name."""
        mapping = {
            TaskStatus.QUEUED: "task.queued",
            TaskStatus.PLANNING: "task.planning",
            TaskStatus.READY: "task.ready",
            TaskStatus.RUNNING: "task.started",
            TaskStatus.WAITING: "task.waiting",
            TaskStatus.BLOCKED: "task.blocked",
            TaskStatus.VERIFYING: "task.verifying",
            TaskStatus.COMPLETED: "task.completed",
            TaskStatus.FAILED: "task.failed",
            TaskStatus.CANCELLED: "task.cancelled",
            TaskStatus.PAUSED: "task.paused",
            TaskStatus.REQUIRES_APPROVAL: "task.requires_approval",
            TaskStatus.TIMEOUT: "task.timed_out",
            TaskStatus.EMERGENCY_STOPPED: "task.emergency_stopped",
            TaskStatus.EXPIRED: "task.expired",
        }
        return mapping.get(status, "task.created")

    def _update_timestamps(self, task: TaskSpec, status: TaskStatus) -> None:
        """Update relevant timestamps based on status."""
        now = time.time()
        if status == TaskStatus.RUNNING and task.started_at == 0:
            task.started_at = now
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = time.time()
        elif status == TaskStatus.PAUSED:
            task.metadata["paused_at"] = now
        elif status == TaskStatus.READY and task.assigned_agent:
            task.metadata["assigned_at"] = now

    def _status_to_event_type(self, status: TaskStatus) -> LifecycleEventType:
        """Map task status to lifecycle event type."""
        mapping = {
            TaskStatus.QUEUED: LifecycleEventType.TASK_QUEUED,
            TaskStatus.PLANNING: LifecycleEventType.TASK_PLANNING,
            TaskStatus.READY: LifecycleEventType.TASK_READY,
            TaskStatus.RUNNING: LifecycleEventType.TASK_STARTED,
            TaskStatus.WAITING: LifecycleEventType.TASK_WAITING,
            TaskStatus.BLOCKED: LifecycleEventType.TASK_BLOCKED,
            TaskStatus.VERIFYING: LifecycleEventType.TASK_VERIFYING,
            TaskStatus.REQUIRES_APPROVAL: LifecycleEventType.TASK_REQUIRES_APPROVAL,
            TaskStatus.PAUSED: LifecycleEventType.TASK_PAUSED,
            TaskStatus.COMPLETED: LifecycleEventType.TASK_COMPLETED,
            TaskStatus.FAILED: LifecycleEventType.TASK_FAILED,
            TaskStatus.CANCELLED: LifecycleEventType.TASK_CANCELLED,
            TaskStatus.TIMEOUT: LifecycleEventType.TASK_TIMED_OUT,
            TaskStatus.EMERGENCY_STOPPED: LifecycleEventType.TASK_EMERGENCY_STOPPED,
        }
        return mapping.get(status, LifecycleEventType.TASK_CREATED)

    # ── Convenience Methods ────────────────────────────────────────────

    async def queue_task(self, task_id: str, message: str = "") -> bool:
        """Queue a pending task."""
        return await self.transition(task_id, TaskStatus.QUEUED, message)

    async def start_planning(self, task_id: str, message: str = "") -> bool:
        """Start planning phase."""
        return await self.transition(task_id, TaskStatus.PLANNING, message)

    async def mark_ready(self, task_id: str, message: str = "") -> bool:
        """Mark task as ready for execution."""
        return await self.transition(task_id, TaskStatus.READY, message)

    async def start_task(self, task_id: str, message: str = "") -> bool:
        """Start task execution."""
        return await self.transition(task_id, TaskStatus.RUNNING, message)

    async def pause_task(self, task_id: str, message: str = "") -> bool:
        """Pause a running task."""
        return await self.transition(task_id, TaskStatus.PAUSED, message)

    async def resume_task(self, task_id: str, message: str = "") -> bool:
        """Resume a paused task."""
        return await self.transition(task_id, TaskStatus.RUNNING, message)

    async def block_task(self, task_id: str, reason: str = "") -> bool:
        """Block a task waiting for external condition."""
        return await self.transition(task_id, TaskStatus.BLOCKED, f"Blocked: {reason}")

    async def unblock_task(self, task_id: str, message: str = "") -> bool:
        """Unblock a task and resume execution."""
        return await self.transition(task_id, TaskStatus.RUNNING, message)

    async def verify_task(self, task_id: str, message: str = "") -> bool:
        """Mark task as under verification."""
        return await self.transition(task_id, TaskStatus.VERIFYING, message)

    async def complete_task(self, task_id: str, message: str = "", result: Any = None) -> bool:
        """Mark task as completed successfully."""
        task = self._tasks.get(task_id)
        if task:
            task.result = result
        return await self.transition(task_id, TaskStatus.COMPLETED, message)

    async def fail_task(self, task_id: str, error: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Mark task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.error = error
            if metadata:
                task.metadata.update(metadata)
        return await self.transition(task_id, TaskStatus.FAILED, error)

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel a task."""
        return await self.transition(task_id, TaskStatus.CANCELLED, f"Cancelled: {reason}")

    async def timeout_task(self, task_id: str, message: str = "") -> bool:
        """Mark task as timed out."""
        return await self.transition(task_id, TaskStatus.TIMEOUT, message)

    async def emergency_stop(self, task_id: str, reason: str = "") -> bool:
        """Emergency stop a task."""
        return await self.transition(task_id, TaskStatus.EMERGENCY_STOPPED, reason)

    async def request_approval(self, task_id: str, reason: str = "") -> bool:
        """Mark task as requiring approval."""
        task = self._tasks.get(task_id)
        if task:
            task.approval_state = "pending"
        return await self.transition(task_id, TaskStatus.REQUIRES_APPROVAL, reason)

    async def approve_task(self, task_id: str, message: str = "") -> bool:
        """Approve a task that was waiting for approval."""
        task = self._tasks.get(task_id)
        if task:
            task.approval_state = "approved"
        return await self.transition(task_id, TaskStatus.RUNNING, f"Approved: {message}")

    async def deny_task(self, task_id: str, reason: str = "") -> bool:
        """Deny approval for a task."""
        task = self._tasks.get(task_id)
        if task:
            task.approval_state = "denied"
        return await self.transition(task_id, TaskStatus.FAILED, f"Denied: {reason}")

    def assign_agent(self, task_id: str, agent_id: str, model: str = "") -> bool:
        """Assign an agent to a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.assigned_agent = task.assigned_agent
        if model:
            task.assigned_model = model
        task.updated_at = time.time()
        self._emit_event(LifecycleEvent(
            task_id=task_id,
            event_type=LifecycleEventType.TASK_ASSIGNED,
            from_status=task.status,
            to_status=task.status,
            message=f"Assigned to agent {task_id}",
            metadata={"agent_id": agent_id, "model": model},
        ))
        return True

    def unassign_agent(self, task_id: str) -> bool:
        """Unassign agent from task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.assigned_agent = ""
        task.assigned_model = ""
        task.updated_at = time.time()
        self._emit_event(LifecycleEvent(
            task_id=task_id,
            event_type=LifecycleEventType.TASK_UNASSIGNED,
            from_status=task.status,
            to_status=task.status,
            message="Agent unassigned",
        ))
        return True

    async def retry_task(self, task_id: str, reason: str = "") -> bool:
        """Retry a failed task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False

        # Reset error and verification state
        task.error = ""
        task.verification_state = "pending"
        task.approval_state = "none"
        task.retry_count = task.metadata.get("retry_count", 0) + 1
        task.metadata["retry_count"] = task.metadata.get("retry_count", 0) + 1

        return await self.transition(task_id, TaskStatus.READY, f"Retry: {reason}")

    # ── Event System ───────────────────────────────────────────────────

    def _emit_event(self, event: LifecycleEvent) -> None:
        """Emit a lifecycle event to callbacks and log."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]

        # Call callbacks
        callbacks = self._callbacks.get(event.event_type, [])
        for callback in self._callbacks.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.warning(f"Lifecycle callback failed: {e}")

    def register_callback(
        self,
        event_type: LifecycleEventType,
        callback: Callable[[LifecycleEvent], None],
    ) -> None:
        """Register a callback for lifecycle events."""
        self._callbacks.setdefault(event_type, []).append(callback)

    def unregister_callback(
        self,
        event_type: LifecycleEventType,
        callback: Callable[[LifecycleEvent], None],
    ) -> bool:
        """Unregister a callback."""
        if event_type in self._callbacks:
            try:
                self._callbacks[event_type].remove(callback)
                return True
            except ValueError:
                return False
        return False

    def get_event_history(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[LifecycleEventType] = None,
        limit: int = 100,
    ) -> List[LifecycleEvent]:
        """Get filtered event history."""
        events = self._event_log
        if task_id:
            events = [e for e in events if e.task_id == task_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_task_history(self, task_id: str) -> List[LifecycleEvent]:
        """Get all events for a specific task."""
        return [e for e in self._event_log if e.task_id == task_id]

    def clear_history(self) -> None:
        """Clear event log."""
        self._event_log.clear()


# =============================================================================
# Task State Machine (Synchronous Interface)
# =============================================================================


class TaskStateMachine:
    """Synchronous state machine for task lifecycle (for non-async contexts)."""

    def __init__(self, lifecycle_manager: TaskLifecycleManager):
        self._manager = lifecycle_manager

    def transition(self, task_id: str, to_status: TaskStatus, message: str = "") -> bool:
        """Synchronous transition (runs async internally)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._manager.transition(task_id, to_status, message)
        )

    def queue(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.QUEUED, message)

    def start_planning(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.PLANNING, message)

    def mark_ready(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.READY, message)

    def start(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.RUNNING, message)

    def pause(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.PAUSED, message)

    def resume(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.RUNNING, message)

    def block(self, task_id: str, reason: str = "") -> bool:
        return self.transition(task_id, TaskStatus.BLOCKED, f"Blocked: {reason}")

    def unblock(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.RUNNING, message)

    def verify(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.VERIFYING, message)

    def complete(self, task_id: str, message: str = "", result: Any = None) -> bool:
        task = self._manager._tasks.get(task_id)
        if task:
            task.result = result
        return self.transition(task_id, TaskStatus.COMPLETED, message)

    def fail(self, task_id: str, error: str) -> bool:
        return self.transition(task_id, TaskStatus.FAILED, error)

    def cancel(self, task_id: str, reason: str = "") -> bool:
        return self.transition(task_id, TaskStatus.CANCELLED, f"Cancelled: {reason}")

    def timeout(self, task_id: str, message: str = "") -> bool:
        return self.transition(task_id, TaskStatus.TIMEOUT, message)

    def emergency_stop(self, task_id: str, reason: str = "") -> bool:
        return self.transition(task_id, TaskStatus.EMERGENCY_STOPPED, reason)

    def request_approval(self, task_id: str, reason: str = "") -> bool:
        task = self._manager._tasks.get(task_id)
        if task:
            task.approval_state = "pending"
        return self.transition(task_id, TaskStatus.REQUIRES_APPROVAL, reason)

    def approve(self, task_id: str, message: str = "") -> bool:
        task = self._manager._tasks.get(task_id)
        if task:
            task.approval_state = "approved"
        return self.transition(task_id, TaskStatus.RUNNING, f"Approved: {message}")

    def deny(self, task_id: str, reason: str = "") -> bool:
        task = self._manager._tasks.get(task_id)
        if task:
            task.approval_state = "denied"
        return self.transition(task_id, TaskStatus.FAILED, f"Denied: {reason}")


# =============================================================================
# Global Lifecycle Manager
# =============================================================================

_lifecycle_manager: Optional[TaskLifecycleManager] = None


def get_lifecycle_manager() -> TaskLifecycleManager:
    """Get the global lifecycle manager instance."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = TaskLifecycleManager()
    return _lifecycle_manager


# =============================================================================
# Integration Helpers
# =============================================================================


def create_task(
    goal: str,
    description: str = "",
    required_capabilities: Optional[List[str]] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    budget: Optional["TaskBudget"] = None,
    depends_on: Optional[List[str]] = None,
    **kwargs,
) -> TaskSpec:
    """Create a new task with lifecycle management."""
    from agent.orchestration.types import create_task_spec

    task = create_task_spec(
        goal=goal,
        description=description,
        priority=priority,
        budget=budget,
        depends_on=depends_on,
    )
    if required_capabilities:
        task.required_capabilities = required_capabilities

    # Register with lifecycle manager
    lifecycle = get_lifecycle_manager()
    lifecycle.register_task(task)

    return task


# Export key symbols
__all__ = [
    # Enums
    "TaskStatus",
    "TaskPriority",
    "LifecycleEventType",
    # Data classes
    "LifecycleEvent",
    "TaskSpec",
    "TaskBudget",
    # State machine
    "can_transition",
    "is_terminal_status",
    # Lifecycle management
    "TaskLifecycleManager",
    "TaskStateMachine",
    # Manager access
    "get_lifecycle_manager",
    "create_task",
    # Convenience functions
    "can_transition",
    "is_terminal_status",
]