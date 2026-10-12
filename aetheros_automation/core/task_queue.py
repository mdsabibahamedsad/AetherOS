from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from aetheros_automation.models.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class QueueEntry:
    task: Task
    priority: int = 0
    scheduled_at: float = 0.0
    attempts: int = 0
    enqueued_at: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task.id,
            "name": self.task.name,
            "status": self.task.status.value if self.task.status else "unknown",
            "priority": self.priority,
            "attempts": self.attempts,
            "scheduled_at": self.scheduled_at,
            "enqueued_at": self.enqueued_at,
        }


class TaskQueue:
    """A durable task queue with priority, retry, scheduled, failed, and
    completed buckets.

    Complements ``TaskScheduler``: the scheduler runs tasks immediately;
    this queue keeps every task in an explicit lifecycle bucket and drives
    retries with backoff.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        base_dir: str | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._entries: dict[str, QueueEntry] = {}
        self._failed: dict[str, QueueEntry] = {}
        self._completed: dict[str, QueueEntry] = {}
        self._scheduled: dict[str, QueueEntry] = {}
        self._running: dict[str, QueueEntry] = {}
        self._handler: Callable[[Task], Any] | None = None
        self._base_dir = base_dir or os.path.expanduser("~/.aetheros/automation/queue")

    # ── submission ──────────────────────────────────────────────

    def enqueue(self, task: Task, priority: int = 0, delay: float = 0.0) -> str:
        entry = QueueEntry(
            task=task,
            priority=priority,
            scheduled_at=time.time() + max(0.0, delay),
            enqueued_at=time.time(),
        )
        if delay > 0:
            entry.task.status = TaskStatus.PENDING
            self._scheduled[task.id] = entry
        else:
            entry.task.status = TaskStatus.QUEUED
            self._entries[task.id] = entry
        logger.info("Queued task %s (priority=%s, delay=%s)", task.id, priority, delay)
        return task.id

    def retry(self, task_id: str, delay: float = 0.0) -> bool:
        entry = self._failed.get(task_id) or self._entries.get(task_id)
        if entry is None:
            return False
        self._failed.pop(task_id, None)
        self._entries.pop(task_id, None)
        self.enqueue(entry.task, priority=entry.priority, delay=delay)
        return True

    # ── worker ──────────────────────────────────────────────────

    def set_handler(self, handler: Callable[[Task], Any]) -> None:
        self._handler = handler

    async def run_once(self) -> bool:
        """Pop the highest-priority ready task and execute it (or reschedule).
        Returns True if any task was processed."""
        entry = self._next_ready()
        if entry is None:
            return False
        await self._execute(entry)
        return True

    async def run(self, poll_interval: float = 0.25) -> None:
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(poll_interval)

    # ── introspection ───────────────────────────────────────────

    def size(self) -> int:
        return len(self._entries)

    def get_task(self, task_id: str) -> QueueEntry | None:
        return (
            self._entries.get(task_id)
            or self._running.get(task_id)
            or self._scheduled.get(task_id)
            or self._failed.get(task_id)
            or self._completed.get(task_id)
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "queued": len(self._entries),
            "scheduled": len(self._scheduled),
            "running": len(self._running),
            "failed": len(self._failed),
            "completed": len(self._completed),
            "total": (
                len(self._entries)
                + len(self._scheduled)
                + len(self._running)
                + len(self._failed)
                + len(self._completed)
            ),
        }

    def list_failed(self) -> list[dict[str, Any]]:
        return [e.as_dict() for e in self._failed.values()]

    def list_completed(self, limit: int = 100) -> list[dict[str, Any]]:
        entries = list(self._completed.values())
        entries.sort(key=lambda e: e.enqueued_at, reverse=True)
        return [e.as_dict() for e in entries[:limit]]

    # ── internals ───────────────────────────────────────────────

    def _next_ready(self) -> QueueEntry | None:
        now = time.time()
        for task_id in list(self._scheduled):
            entry = self._scheduled[task_id]
            if entry.scheduled_at <= now:
                self._scheduled.pop(task_id)
                entry.task.status = TaskStatus.QUEUED
                self._entries[task_id] = entry
        if not self._entries:
            return None
        return max(self._entries.values(), key=lambda e: (e.priority, -e.enqueued_at))

    async def _execute(self, entry: QueueEntry) -> None:
        task = entry.task
        self._entries.pop(task.id, None)
        self._running[task.id] = entry
        task.status = TaskStatus.RUNNING
        handler = self._handler
        if handler is None:
            task.status = TaskStatus.FAILED
            self._running.pop(task.id, None)
            self._failed[task.id] = entry
            return
        try:
            result = handler(task)
            if asyncio.iscoroutine(result):
                result = await result
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self._running.pop(task.id, None)
            self._completed[task.id] = entry
        except Exception as exc:
            entry.attempts += 1
            task.error = str(exc)
            if entry.attempts > self.max_retries:
                task.status = TaskStatus.FAILED
                self._running.pop(task.id, None)
                self._failed[task.id] = entry
                logger.warning("Task %s permanently failed: %s", task.id, exc)
            else:
                delay = self.retry_base_delay * (2 ** (entry.attempts - 1))
                task.status = TaskStatus.PENDING
                entry.scheduled_at = time.time() + delay
                self._running.pop(task.id, None)
                self._scheduled[task.id] = entry
                logger.info("Task %s failed, retrying in %.1fs (%d/%d)",
                            task.id, delay, entry.attempts, self.max_retries)
