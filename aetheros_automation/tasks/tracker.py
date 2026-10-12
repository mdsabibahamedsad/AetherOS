from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import LogEntry, Task, TaskStatus

logger = logging.getLogger(__name__)

_TASKS_DIR = os.path.expanduser("~/.aetheros/automation/tasks")


class TaskTracker:
    """In-memory task store with JSON persistence.

    All mutation methods are async (backed by ``asyncio`` executor calls for
    file I/O) so they integrate cleanly with the rest of the automation
    engine's event loop.
    """

    def __init__(self) -> None:
        os.makedirs(_TASKS_DIR, exist_ok=True)
        self._store: dict[str, Task] = {}

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    async def create_task(self, task_data: dict[str, Any]) -> Task:
        """Create a new ``Task`` from *task_data* and persist it.

        If ``task_data`` lacks an ``id`` a new one is generated automatically.
        """
        now = time.time()
        task = Task(
            id=task_data.get("id", uuid.uuid4().hex[:12]),
            name=task_data.get("name", ""),
            description=task_data.get("description", ""),
            status=TaskStatus(task_data["status"])
            if "status" in task_data
            else TaskStatus.PENDING,
            agent=task_data.get("agent"),
            dependencies=task_data.get("dependencies", []),
            created_at=task_data.get("created_at", now),
            estimated_duration=task_data.get("estimated_duration", 0.0),
            progress=task_data.get("progress", 0.0),
            metadata=task_data.get("metadata", {}),
            parent_task_id=task_data.get("parent_task_id", ""),
            subtasks=task_data.get("subtasks", []),
            max_retries=task_data.get("max_retries", 3),
            requires_approval=task_data.get("requires_approval", False),
        )

        self._store[task.id] = task
        await self._persist(task)
        logger.info("Created task %s (%s)", task.id, task.name)
        return task

    async def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Change a task's status and record timing when terminal."""
        task = self._store.get(task_id)
        if task is None:
            logger.warning("update_status: unknown task %s", task_id)
            return

        task.status = status
        now = time.time()

        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = now
        if status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            task.completed_at = now
            if task.started_at:
                task.actual_duration = task.completed_at - task.started_at

        await self._persist(task)
        logger.info("Task %s status -> %s", task_id, status.value)

    async def update_progress(self, task_id: str, progress: float) -> None:
        """Set *progress* (0–100) for the given task."""
        task = self._store.get(task_id)
        if task is None:
            return
        task.progress = max(0.0, min(100.0, progress))
        await self._persist(task)

    async def add_log(
        self, task_id: str, level: str = "info", message: str = "",
    ) -> None:
        """Append a ``LogEntry`` to the task's log list."""
        task = self._store.get(task_id)
        if task is None:
            return
        entry = LogEntry(timestamp=time.time(), level=level, message=message)
        task.logs.append(entry)
        await self._persist(task)

    async def attach_result(self, task_id: str, result: str) -> None:
        """Attach a textual result to the task."""
        task = self._store.get(task_id)
        if task is None:
            return
        task.result = result
        await self._persist(task)

    async def attach_error(self, task_id: str, error: str) -> None:
        """Attach an error message and mark the task as failed."""
        task = self._store.get(task_id)
        if task is None:
            return
        task.error = error
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        await self._persist(task)

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Task | None:
        """Return the task or ``None`` if not found."""
        return self._store.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """Return all tasks, optionally filtered by *status*."""
        if status is None:
            return list(self._store.values())
        return [t for t in self._store.values() if t.status == status]

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a task that is not yet in a terminal state."""
        await self.update_status(task_id, TaskStatus.CANCELLED)

    async def pause_task(self, task_id: str) -> None:
        """Pause a running task."""
        task = self._store.get(task_id)
        if task is None or task.status != TaskStatus.RUNNING:
            return
        await self.update_status(task_id, TaskStatus.PAUSED)

    async def resume_task(self, task_id: str) -> None:
        """Resume a paused task."""
        task = self._store.get(task_id)
        if task is None or task.status != TaskStatus.PAUSED:
            return
        await self.update_status(task_id, TaskStatus.RUNNING)

    # ------------------------------------------------------------------
    # derived collections
    # ------------------------------------------------------------------

    def active_tasks(self) -> list[Task]:
        """Return all tasks that are currently running or paused."""
        return [
            t
            for t in self._store.values()
            if t.status in (TaskStatus.RUNNING, TaskStatus.PAUSED)
        ]

    def completed_tasks(self) -> list[Task]:
        """Return all successfully completed tasks."""
        return [t for t in self._store.values() if t.status == TaskStatus.COMPLETED]

    def failed_tasks(self) -> list[Task]:
        """Return all tasks that failed or were cancelled."""
        return [
            t
            for t in self._store.values()
            if t.status in (TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]

    # ------------------------------------------------------------------
    # statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Aggregate summary of all tracked tasks."""
        all_tasks = list(self._store.values())
        total = len(all_tasks)
        completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]
        running = [t for t in all_tasks if t.status == TaskStatus.RUNNING]

        durations = [t.actual_duration for t in completed if t.actual_duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total": total,
            "completed": len(completed),
            "failed": len(failed),
            "running": len(running),
            "paused": sum(1 for t in all_tasks if t.status == TaskStatus.PAUSED),
            "pending": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            "cancelled": sum(1 for t in all_tasks if t.status == TaskStatus.CANCELLED),
            "avg_duration": avg_duration,
            "total_progress": (
                sum(t.progress for t in all_tasks) / total if total else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Load every persisted task into the in-memory store."""
        if not os.path.isdir(_TASKS_DIR):
            return
        for name in os.listdir(_TASKS_DIR):
            if name.endswith(".json"):
                path = os.path.join(_TASKS_DIR, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    task = _task_from_dict(data)
                    self._store[task.id] = task
                except Exception:
                    logger.exception("Failed to load task %s", path)

    async def _persist(self, task: Task) -> None:
        """Write a single task to disk as JSON."""
        path = os.path.join(_TASKS_DIR, f"{task.id}.json")
        data = _task_to_dict(task)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, data)


# ------------------------------------------------------------------
# serialisation helpers
# ------------------------------------------------------------------


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "status": task.status.value,
        "agent": task.agent.value if task.agent else None,
        "dependencies": list(task.dependencies),
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "assigned_to": task.assigned_to,
        "result": task.result,
        "error": task.error,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "requires_approval": task.requires_approval,
        "approval_granted": task.approval_granted,
        "parent_task_id": task.parent_task_id,
        "subtasks": list(task.subtasks),
        "metadata": dict(task.metadata),
        "estimated_duration": task.estimated_duration,
        "actual_duration": task.actual_duration,
        "progress": task.progress,
        "logs": [
            {
                "timestamp": e.timestamp,
                "level": e.level,
                "message": e.message,
                "source": e.source,
            }
            for e in task.logs
        ],
    }


def _task_from_dict(data: dict[str, Any]) -> Task:
    return Task(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        status=TaskStatus(data["status"]) if "status" in data else TaskStatus.PENDING,
        agent=data.get("agent"),
        dependencies=data.get("dependencies", []),
        created_at=data.get("created_at", 0.0),
        started_at=data.get("started_at", 0.0),
        completed_at=data.get("completed_at", 0.0),
        assigned_to=data.get("assigned_to", ""),
        result=data.get("result", ""),
        error=data.get("error", ""),
        retry_count=data.get("retry_count", 0),
        max_retries=data.get("max_retries", 3),
        requires_approval=data.get("requires_approval", False),
        approval_granted=data.get("approval_granted", False),
        parent_task_id=data.get("parent_task_id", ""),
        subtasks=data.get("subtasks", []),
        metadata=data.get("metadata", {}),
        estimated_duration=data.get("estimated_duration", 0.0),
        actual_duration=data.get("actual_duration", 0.0),
        progress=data.get("progress", 0.0),
        logs=[
            LogEntry(
                timestamp=e["timestamp"],
                level=e.get("level", "info"),
                message=e.get("message", ""),
                source=e.get("source", ""),
            )
            for e in data.get("logs", [])
        ],
    )


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
