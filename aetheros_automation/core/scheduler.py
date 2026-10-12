"""Task scheduler with priority queue, concurrency control, and timeout support."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from aetheros_automation.models.models import (
    ExecutionMode, Task, TaskStatus, TaskStep as Step, Workflow
)

logger = logging.getLogger(__name__)


class PriorityTask:
    """Wrapper for a task with priority sorting."""

    def __init__(self, task: Task, engine: Any):
        self.task = task
        self.engine = engine
        self.priority = -task.priority  # negate so higher priority sorts first

    def __lt__(self, other: "PriorityTask") -> bool:
        return self.priority < other.priority

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriorityTask):
            return NotImplemented
        return self.task.id == other.task.id

    def __hash__(self) -> int:
        return hash(self.task.id)


class TaskScheduler:
    """Async scheduler that dispatches tasks through the engine."""

    def __init__(
        self,
        engine: Any,
        max_concurrent: int = 5,
        poll_interval: float = 0.5,
        default_timeout: int = 300,
    ):
        self.engine = engine
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.default_timeout = default_timeout

        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running: Set[str] = set()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._active = False
        self._stats: Dict[str, int] = {"enqueued": 0, "dispatched": 0, "completed": 0, "failed": 0, "timeout": 0}

    def enqueue(self, task: Task) -> bool:
        if task.status not in (TaskStatus.PENDING, TaskStatus.QUEUED):
            return False
        task.status = TaskStatus.QUEUED
        self._queue.put_nowait(PriorityTask(task, self.engine))
        self._stats["enqueued"] += 1
        logger.info("Enqueued task %s (priority=%s)", task.id, task.priority)
        return True

    def enqueue_workflow(self, workflow: Workflow):
        tasks = workflow.tasks
        if not tasks:
            for step in getattr(workflow, "steps", []) or []:
                if isinstance(step, dict):
                    tasks.append(self.engine.create_task(
                        name=step.get("name", step.get("goal", step.get("description", "Workflow step"))),
                        description=step.get("description", ""),
                        priority=step.get("priority", 0),
                        timeout=step.get("timeout"),
                    ))
                else:
                    tasks.append(self.engine.create_task(
                        name=getattr(step, "name", "Workflow step"),
                        description=getattr(step, "description", ""),
                        priority=getattr(step, "priority", 0),
                        timeout=getattr(step, "timeout", None),
                    ))
        for task in tasks:
            self.enqueue(task)

    async def start(self):
        if self._active:
            return
        self._active = True
        self._scheduler_task = asyncio.create_task(self._run())
        logger.info("TaskScheduler started (max_concurrent=%s)", self.max_concurrent)

    async def stop(self):
        self._active = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("TaskScheduler stopped.")

    async def _run(self):
        while self._active:
            try:
                if len(self._running) >= self.max_concurrent:
                    await asyncio.sleep(self.poll_interval)
                    continue

                priority_task = await asyncio.wait_for(
                    self._queue.get(), timeout=self.poll_interval * 2
                )
                task = priority_task.task
                self._running.add(task.id)
                self._stats["dispatched"] += 1
                asyncio.create_task(self._execute(priority_task))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Scheduler error: %s", e)

    async def _execute(self, priority_task: PriorityTask):
        task = priority_task.task
        timeout = task.timeout or self.default_timeout
        try:
            await asyncio.wait_for(
                self.engine._execute_task(task),
                timeout=timeout,
            )
            if task.status == TaskStatus.COMPLETED:
                self._stats["completed"] += 1
            else:
                self._stats["failed"] += 1
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            self._stats["timeout"] += 1
            logger.warning("Task %s timed out after %ss", task.id, timeout)
        except Exception as e:
            task.status = TaskStatus.FAILED
            self._stats["failed"] += 1
            logger.exception("Task %s failed: %s", task.id, e)
        finally:
            self._running.discard(task.id)

    def cancel(self, task_id: str) -> bool:
        return self.engine.cancel_task(task_id)

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def get_running_count(self) -> int:
        return len(self._running)

    def get_status(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "queue_size": self._queue.qsize(),
            "running": len(self._running),
            "max_concurrent": self.max_concurrent,
            "stats": self._stats,
        }
