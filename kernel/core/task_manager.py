"""
Task Manager — manages task lifecycle and execution tracking.

Tracks tasks, subtasks, dependencies, and execution state.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from kernel.core.types import (
    AgentLifecycleState,
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    REQUIRES_APPROVAL = "requires_approval"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 50
    HIGH = 75
    CRITICAL = 100
    BACKGROUND = -50


@dataclass
class Task:
    """Task specification."""
    task_id: str = field(default_factory=lambda: new_id("task"))
    parent_task_id: str = ""
    root_task_id: str = ""
    agent_id: str = ""
    intent_id: str = ""
    goal: str = ""
    description: str = ""
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    blocks: List[str] = field(default_factory=list)  # Task IDs
    result: Any = None
    error: str = ""
    artifacts: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    started_at: float = 0
    completed_at: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecution:
    """Task execution state."""
    task: Task
    assigned_agent_id: str = ""
    attempts: int = 0
    max_attempts: int = 3
    last_error: str = ""


class TaskManager:
    """
    Manages task lifecycle and execution tracking.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._tasks: Dict[str, Task] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._task_index: Dict[str, List[str]] = {}  # agent_id -> task_ids

    def create_task(
        self,
        agent_id: str,
        intent_id: str,
        goal: str,
        description: str = "",
        parent_task_id: str = "",
        required_capabilities: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        depends_on: List[str] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            agent_id=agent_id,
            intent_id=intent_id,
            goal=goal,
            description=description,
            parent_task_id=parent_task_id,
            root_task_id=parent_task_id or new_id("task"),
            required_capabilities=required_capabilities or [],
            priority=priority,
            depends_on=depends_on or [],
        )

        with self._lock:
            self._tasks[task.task_id] = task
            self._task_index.setdefault(agent_id, []).append(task.task_id)

        if self.event_bus:
            self.event_bus.emit("task.created", {
                "task_id": task.task_id,
                "agent_id": agent_id,
                "intent_id": intent_id,
                "goal": goal,
            })

        logger.debug("TaskManager: created task %s for agent %s", task.task_id, agent_id)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus, error: str = "") -> bool:
        """Update task status."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            old_status = task.status
            task.status = status
            task.updated_at = _now()
            task.error = error

            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = _now()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.completed_at = _now()

        if self.event_bus:
            self.event_bus.emit("task.status_changed", {
                "task_id": task_id,
                "old_status": old_status.value,
                "new_status": status.value,
                "error": error,
            })

        return True

    def set_task_result(self, task_id: str, result: Any) -> bool:
        """Set task result."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.result = result
            task.updated_at = _now()
        return True

    def add_task_artifact(self, task_id: str, artifact_id: str) -> bool:
        """Add artifact to task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if artifact_id not in task.artifacts:
                task.artifacts.append(artifact_id)
                task.updated_at = _now()
        return True

    def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """Get all tasks for an agent."""
        with self._lock:
            task_ids = self._task_index.get(agent_id, [])
            return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_ready_tasks(self, agent_id: str) -> List[Task]:
        """Get tasks ready to execute (dependencies met)."""
        tasks = self.get_agent_tasks(agent_id)
        ready = []
        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue
            # Check dependencies
            deps_met = all(
                self._tasks.get(dep_id, Task()).status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
            )
            if deps_met:
                ready.append(task)
        return ready

    def get_task_tree(self, root_task_id: str) -> Dict[str, Any]:
        """Get task tree for visualization."""
        def build_tree(task_id: str) -> Dict[str, Any]:
            task = self._tasks.get(task_id)
            if not task:
                return {}
            return {
                "task_id": task.task_id,
                "goal": task.goal,
                "status": task.status.value,
                "children": [build_tree(c) for c in task.blocks],
            }
        return build_tree(root_task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics."""
        with self._lock:
            total = len(self._tasks)
            by_status: Dict[str, int] = {}
            by_agent: Dict[str, int] = {}
            for task in self._tasks.values():
                by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
                by_agent[task.agent_id] = by_agent.get(task.agent_id, 0) + 1

        return {
            "total_tasks": total,
            "by_status": by_status,
            "by_agent": by_agent,
        }

    def shutdown(self) -> None:
        """Shutdown the task manager."""
        logger.info("TaskManager: shutting down")
        with self._lock:
            self._tasks.clear()
            self._executions.clear()
            self._task_index.clear()