"""Task Queue System for AetherOS Orchestration Layer.

Implements Phase 87 of Master Prompt 11: durable task queue with
priority scheduling, fair scheduling, and background execution support.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from agent.orchestration.types import (
    TaskSpec,
    TaskStatus,
    TaskPriority,
    TaskBudget,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Queue Types
# =============================================================================


class QueueType(Enum):
    """Types of task queues."""

    FIFO = "fifo"              # First in, first out
    PRIORITY = "priority"      # Priority-based
    DEADLINE = "deadline"      # Earliest deadline first
    FAIR = "fair"              # Fair scheduling across users/projects


@dataclass
class QueueEntry:
    """Entry in the task queue."""

    task: TaskSpec
    enqueued_at: float = field(default_factory=time.time)
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[float] = None
    queue_type: QueueType = QueueType.PRIORITY
    retries: int = 0
    max_retries: int = 3
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "QueueEntry") -> bool:
        """Compare for priority queue ordering."""
        # Higher priority first
        if self.priority != other.priority:
            return self.priority.value > other.priority.value

        # Earlier deadline first
        if self.deadline and other.deadline:
            return self.deadline < other.deadline

        # Earlier enqueue first (FIFO tiebreaker)
        return self.enqueued_at < other.enqueued_at


@dataclass
class QueueStats:
    """Queue statistics."""

    total_enqueued: int = 0
    total_dequeued: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    current_size: int = 0
    avg_wait_time: float = 0.0
    avg_execution_time: float = 0.0
    by_priority: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_user: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_project: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


# =============================================================================
# Task Queue
# =============================================================================


class TaskQueue:
    """Priority-based task queue with fair scheduling support."""

    def __init__(
        self,
        queue_type: QueueType = QueueType.PRIORITY,
        max_size: int = 10000,
        fair_scheduling: bool = True,
    ):
        self._queue_type = queue_type
        self._max_size = max_size
        self._fair_scheduling = fair_scheduling

        # Main queue (heap for priority)
        self._queue: List[QueueEntry] = []

        # Per-user/project queues for fair scheduling
        self._user_queues: Dict[str, List[QueueEntry]] = defaultdict(list)
        self._project_queues: Dict[str, List[QueueEntry]] = defaultdict(list)

        # Tracking
        self._entry_map: Dict[str, QueueEntry] = {}  # task_id -> entry
        self._stats = QueueStats()
        self._lock = asyncio.Lock()
        self._waiters: List[asyncio.Future] = []

    async def enqueue(
        self,
        task: TaskSpec,
        priority: TaskPriority = None,
        deadline: float = None,
        tags: Set[str] = None,
        max_retries: int = 3,
    ) -> bool:
        """Add a task to the queue."""
        async with self._lock:
            if len(self._queue) >= self._max_size:
                logger.warning(f"Queue full, rejecting task {task.task_id}")
                return False

            if task.task_id in self._entry_map:
                logger.warning(f"Task {task.task_id} already in queue")
                return False

            entry = QueueEntry(
                task=task,
                priority=priority or task.priority,
                deadline=deadline or task.deadline,
                queue_type=self._queue_type,
                max_retries=max_retries,
                tags=tags or set(),
            )

            # Add to main queue
            heapq.heappush(self._queue, entry)
            self._entry_map[task.task_id] = entry

            # Add to fair scheduling queues
            if self._fair_scheduling:
                if task.user_id:
                    heapq.heappush(self._user_queues[task.user_id], entry)
                if task.project_id:
                    heapq.heappush(self._project_queues[task.project_id], entry)

            # Update stats
            self._stats.total_enqueued += 1
            self._stats.current_size += 1
            self._stats.by_priority[entry.priority.name] += 1
            if task.user_id:
                self._stats.by_user[task.user_id] += 1
            if task.project_id:
                self._stats.by_project[task.project_id] += 1

            # Notify waiters
            self._notify_waiters()

            logger.debug(f"Enqueued task {task.task_id} with priority {entry.priority.name}")
            return True

    async def dequeue(self, timeout: float = None) -> Optional[QueueEntry]:
        """Get the next task from the queue."""
        async with self._lock:
            while not self._queue:
                if timeout is not None:
                    # Wait with timeout
                    future = asyncio.get_event_loop().create_future()
                    self._waiters.append(future)

                    try:
                        await asyncio.wait_for(future, timeout=timeout)
                    except asyncio.TimeoutError:
                        return None
                    finally:
                        if future in self._waiters:
                            self._waiters.remove(future)
                else:
                    return None

            return self._dequeue_internal()

    def _dequeue_internal(self) -> Optional[QueueEntry]:
        """Internal dequeue without lock (must hold lock)."""
        if not self._queue:
            return None

        if self._fair_scheduling:
            return self._fair_dequeue()
        else:
            return self._priority_dequeue()

    def _priority_dequeue(self) -> QueueEntry:
        """Standard priority dequeue."""
        entry = heapq.heappop(self._queue)
        self._remove_from_fair_queues(entry)
        self._entry_map.pop(entry.task.task_id, None)
        self._stats.total_dequeued += 1
        self._stats.current_size -= 1
        return entry

    def _fair_dequeue(self) -> QueueEntry:
        """Fair scheduling dequeue - round-robin across users/projects."""
        # Get all users/projects with pending tasks
        users_with_tasks = [u for u, q in self._user_queues.items() if q]
        projects_with_tasks = [p for p, q in self._project_queues.items() if q]

        # Simple round-robin: alternate between users
        # In production, would track last served user
        if users_with_tasks:
            # Pick user with fewest completed tasks (simplified)
            user = min(users_with_tasks, key=lambda u: self._stats.by_user.get(u, 0))
            if self._user_queues[user]:
                entry = heapq.heappop(self._user_queues[user])
                self._remove_from_main_queue(entry)
                return entry

        if projects_with_tasks:
            project = min(projects_with_tasks, key=lambda p: self._stats.by_project.get(p, 0))
            if self._project_queues[project]:
                entry = heapq.heappop(self._project_queues[project])
                self._remove_from_main_queue(entry)
                return entry

        # Fallback to priority
        return self._priority_dequeue()

    def _remove_from_main_queue(self, entry: QueueEntry) -> None:
        """Remove entry from main queue (O(n) but rare)."""
        try:
            self._queue.remove(entry)
            heapq.heapify(self._queue)
        except ValueError:
            pass
        self._entry_map.pop(entry.task.task_id, None)
        self._stats.total_dequeued += 1
        self._stats.current_size -= 1

    def _remove_from_fair_queues(self, entry: QueueEntry) -> None:
        """Remove entry from fair scheduling queues."""
        if entry.task.user_id and entry.task.user_id in self._user_queues:
            try:
                self._user_queues[entry.task.user_id].remove(entry)
                heapq.heapify(self._user_queues[entry.task.user_id])
            except ValueError:
                pass

        if entry.task.project_id and entry.task.project_id in self._project_queues:
            try:
                self._project_queues[entry.task.project_id].remove(entry)
                heapq.heapify(self._project_queues[entry.task.project_id])
            except ValueError:
                pass

    def _notify_waiters(self) -> None:
        """Notify waiting dequeuers."""
        for future in self._waiters[:]:
            if not future.done():
                future.set_result(None)
        self._waiters.clear()

    async def requeue(self, task_id: str, new_priority: TaskPriority = None) -> bool:
        """Requeue a task (e.g., after retry)."""
        async with self._lock:
            entry = self._entry_map.get(task_id)
            if not entry:
                return False

            entry.retries += 1
            if entry.retries > entry.max_retries:
                logger.warning(f"Task {task_id} exceeded max retries")
                return False

            if new_priority:
                entry.priority = new_priority

            # Re-insert
            heapq.heappush(self._queue, entry)
            if self._fair_scheduling:
                if entry.task.user_id:
                    heapq.heappush(self._user_queues[entry.task.user_id], entry)
                if entry.task.project_id:
                    heapq.heappush(self._project_queues[entry.task.project_id], entry)

            self._notify_waiters()
            return True

    async def cancel(self, task_id: str) -> bool:
        """Cancel a queued task."""
        async with self._lock:
            entry = self._entry_map.pop(task_id, None)
            if not entry:
                return False

            self._remove_from_fair_queues(entry)

            # Remove from main queue
            try:
                self._queue.remove(entry)
                heapq.heapify(self._queue)
            except ValueError:
                pass

            self._stats.current_size -= 1
            self._stats.total_cancelled += 1
            return True

    async def pause(self, task_id: str) -> bool:
        """Pause a queued task (move to paused state)."""
        # In this implementation, cancelling and re-adding with PAUSED priority
        return await self.cancel(task_id)

    async def get_position(self, task_id: str) -> Optional[int]:
        """Get queue position of a task (1-indexed)."""
        async with self._lock:
            entry = self._entry_map.get(task_id)
            if not entry:
                return None

            # Count tasks with higher priority
            position = 1
            for e in self._queue:
                if e.task_id == task_id:
                    break
                if e < entry:  # Higher priority
                    position += 1
            return position

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats

    def get_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    async def clear(self) -> int:
        """Clear all tasks from queue."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            self._user_queues.clear()
            self._project_queues.clear()
            self._entry_map.clear()
            self._stats.current_size = 0
            return count


# =============================================================================
# Background Task Queue
# =============================================================================


class BackgroundTaskQueue(TaskQueue):
    """Queue for background tasks with lower priority."""

    def __init__(self, max_size: int = 1000):
        super().__init__(QueueType.PRIORITY, max_size, fair_scheduling=True)
        self._background_workers: int = 0
        self._max_background_workers: int = 2

    def set_background_workers(self, count: int) -> None:
        """Set max background workers."""
        self._max_background_workers = max(0, count)

    async def enqueue_background(
        self,
        task: TaskSpec,
        tags: Set[str] = None,
    ) -> bool:
        """Enqueue a background task (low priority)."""
        task.priority = TaskPriority.BACKGROUND
        return await self.enqueue(task, priority=TaskPriority.BACKGROUND, tags=tags or {"background"})

    def can_run_background(self) -> bool:
        """Check if background worker slot available."""
        return self._background_workers < self._max_background_workers

    def acquire_background_slot(self) -> bool:
        """Acquire a background worker slot."""
        if self.can_run_background():
            self._background_workers += 1
            return True
        return False

    def release_background_slot(self) -> None:
        """Release a background worker slot."""
        self._background_workers = max(0, self._background_workers - 1)


# =============================================================================
# Scheduled Task Queue (for cron-like tasks)
# =============================================================================


class ScheduledTaskQueue:
    """Queue for scheduled/recurring tasks."""

    def __init__(self):
        self._scheduled: List[QueueEntry] = []  # Heap by next_run_time
        self._recurring: Dict[str, Dict[str, Any]] = {}  # task_id -> schedule info
        self._lock = asyncio.Lock()
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def schedule_once(
        self,
        task: TaskSpec,
        run_at: float,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Schedule a one-time task."""
        schedule_id = f"sched-{uuid.uuid4().hex[:12]}"
        entry = QueueEntry(
            task=task,
            priority=priority,
            deadline=run_at,
            metadata={"schedule_id": schedule_id, "run_at": run_at, "recurring": False},
        )

        async with self._lock:
            heapq.heappush(self._scheduled, entry)

        return schedule_id

    async def schedule_recurring(
        self,
        task: TaskSpec,
        interval_seconds: float,
        priority: TaskPriority = TaskPriority.NORMAL,
        start_at: float = None,
    ) -> str:
        """Schedule a recurring task."""
        schedule_id = f"sched-{uuid.uuid4().hex[:12]}"
        first_run = start_at or (time.time() + interval_seconds)

        entry = QueueEntry(
            task=task,
            priority=priority,
            deadline=first_run,
            metadata={
                "schedule_id": schedule_id,
                "run_at": first_run,
                "recurring": True,
                "interval": interval_seconds,
            },
        )

        self._recurring[task.task_id] = {
            "entry": entry,
            "interval": interval_seconds,
            "schedule_id": schedule_id,
        }

        async with self._lock:
            heapq.heappush(self._scheduled, entry)

        return schedule_id

    async def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled task."""
        async with self._lock:
            # Find and remove from scheduled
            for i, entry in enumerate(self._scheduled):
                if entry.metadata.get("schedule_id") == schedule_id:
                    self._scheduled.pop(i)
                    heapq.heapify(self._scheduled)
                    break

            # Remove from recurring
            for task_id, info in list(self._recurring.items()):
                if info["schedule_id"] == schedule_id:
                    del self._recurring[task_id]
                    break

            return True

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = time.time()
            due_entries = []

            async with self._lock:
                while self._scheduled and self._scheduled[0].deadline <= now:
                    due_entries.append(heapq.heappop(self._scheduled))

            for entry in due_entries:
                # Re-enqueue for execution
                entry.task.status = TaskStatus.QUEUED
                # This would be picked up by the main queue processor

                # Reschedule if recurring
                if entry.metadata.get("recurring"):
                    interval = entry.metadata.get("interval", 3600)
                    entry.deadline = time.time() + interval
                    entry.metadata["run_at"] = entry.deadline
                    heapq.heappush(self._scheduled, entry)

            await asyncio.sleep(1)  # Check every second

    def get_upcoming(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming scheduled tasks."""
        upcoming = []
        for entry in sorted(self._scheduled, key=lambda e: e.deadline or 0)[:limit]:
            upcoming.append({
                "schedule_id": entry.metadata.get("schedule_id"),
                "task_id": entry.task.task_id,
                "run_at": entry.deadline,
                "recurring": entry.metadata.get("recurring", False),
                "interval": entry.metadata.get("interval"),
            })
        return upcoming


# =============================================================================
# Queue Manager
# =============================================================================


class QueueManager:
    """Manages multiple task queues."""

    def __init__(self):
        self._queues: Dict[str, TaskQueue] = {}
        self._background_queue = BackgroundTaskQueue()
        self._scheduled_queue = ScheduledTaskQueue()
        self._default_queue_name = "default"

    def get_queue(self, name: str = "default") -> TaskQueue:
        """Get or create a queue."""
        if name not in self._queues:
            self._queues[name] = TaskQueue()
        return self._queues[name]

    def get_background_queue(self) -> BackgroundTaskQueue:
        """Get the background task queue."""
        return self._background_queue

    def get_scheduled_queue(self) -> ScheduledTaskQueue:
        """Get the scheduled task queue."""
        return self._scheduled_queue

    async def start(self):
        """Start all queues."""
        await self._scheduled_queue.start()

    async def stop(self):
        """Stop all queues."""
        await self._scheduled_queue.stop()

    async def enqueue(
        self,
        task: TaskSpec,
        queue_name: str = "default",
        **kwargs,
    ) -> bool:
        """Enqueue a task to a specific queue."""
        queue = self.get_queue(queue_name)
        return await queue.enqueue(task, **kwargs)

    async def dequeue(self, queue_name: str = "default", timeout: float = None) -> Optional[QueueEntry]:
        """Dequeue from a specific queue."""
        queue = self.get_queue(queue_name)
        return await queue.dequeue(timeout)

    def get_all_stats(self) -> Dict[str, QueueStats]:
        """Get stats for all queues."""
        stats = {}
        for name, queue in self._queues.items():
            stats[name] = queue.get_stats()
        stats["background"] = self._background_queue.get_stats()
        return stats


# =============================================================================
# Factory
# =============================================================================


def create_queue_manager() -> QueueManager:
    """Create a queue manager."""
    return QueueManager()


def create_task_queue(queue_type: QueueType = QueueType.PRIORITY) -> TaskQueue:
    """Create a task queue."""
    return TaskQueue(queue_type)


__all__ = [
    "QueueType",
    "QueueEntry",
    "QueueStats",
    "TaskQueue",
    "BackgroundTaskQueue",
    "ScheduledTaskQueue",
    "QueueManager",
    "create_queue_manager",
    "create_task_queue",
]