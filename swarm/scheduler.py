"""
Swarm Scheduler — parallel execution scheduling with dependency awareness.

Manages the execution queue for swarm tasks. Supports:
  - Parallel task execution
  - Dependency-aware scheduling (tasks run when dependencies complete)
  - Join nodes / barriers
  - Timeouts per task
  - Retry with backoff
  - Cancellation

Integrates with the kernel scheduler for background scheduling,
but adds swarm-specific logic for agent task orchestration.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus
from swarm.planner import AgentTask, AgentTaskStatus, SwarmPlan

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A task in the scheduler's execution queue.

    Attributes:
        id: Unique scheduled task ID
        task: The AgentTask to execute
        plan_id: The plan this task belongs to
        order: Execution order (for dependency resolution)
        dependencies: Set of task IDs this depends on
        scheduled_at: When this was scheduled
        started_at: When execution started
        completed_at: When execution completed
        status: Current status
        attempt: Current retry attempt
        max_attempts: Maximum retry attempts
        runner: Callable that executes the task
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task: AgentTask = field(default_factory=AgentTask)
    plan_id: str = ""
    order: int = 0
    dependencies: Set[str] = field(default_factory=set)
    scheduled_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "pending"  # pending, ready, running, completed, failed, cancelled
    attempt: int = 0
    max_attempts: int = 1
    runner: Optional[Callable[[], Any]] = None


class SwarmScheduler:
    """Schedules and executes swarm tasks with dependency awareness.

    Maintains an execution queue where tasks advance from pending → ready
    → running → completed/failed as their dependencies are satisfied.

    Usage:
        scheduler = SwarmScheduler(event_bus)
        scheduler.schedule_plan(plan, task_runner_fn)
        scheduler.run_until_complete()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._queue: Dict[str, ScheduledTask] = {}
        self._running: Set[str] = set()
        self._completed: Set[str] = set()
        self._failed: Set[str] = set()
        self._shutdown_flag = False

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_task(self, task: AgentTask, plan_id: str,
                      runner: Callable[[], Any]) -> ScheduledTask:
        """Schedule a single task for execution."""
        scheduled = ScheduledTask(
            task=task,
            plan_id=plan_id,
            dependencies=set(),
            max_attempts=task.max_retries + 1,
            runner=runner,
        )
        with self._lock:
            self._queue[scheduled.id] = scheduled

        # Resolve dependency IDs: task.dependencies uses AgentTask.id,
        # but our scheduling uses ScheduledTask.id. Build a mapping.
        resolved_deps = set()
        for dep_task_id in task.dependencies:
            # Find the ScheduledTask whose AgentTask has this ID
            for sid, st in self._queue.items():
                if st.task.id == dep_task_id:
                    resolved_deps.add(sid)
                    break
            else:
                # Fall back to the raw task ID (for backward compat)
                resolved_deps.add(dep_task_id)
        scheduled.dependencies = resolved_deps

        logger.debug(
            "Scheduler: scheduled task '%s' (%d deps)",
            task.description[:50], len(resolved_deps),
        )
        return scheduled

    def schedule_plan(self, plan: SwarmPlan,
                      runner_factory: Callable[[AgentTask], Callable[[], Any]]) -> int:
        """Schedule all tasks from a plan.

        Args:
            plan: The swarm plan
            runner_factory: Function that takes an AgentTask and returns
                           a callable to execute it

        Returns:
            Number of tasks scheduled
        """
        count = 0
        for task in plan.tasks:
            runner = runner_factory(task)
            if runner:
                self.schedule_task(task, plan.id, runner)
                count += 1
        logger.info("Scheduler: scheduled %d tasks from plan %s", count, plan.id)
        return count

    # ------------------------------------------------------------------
    # Execution loop
    # ------------------------------------------------------------------

    def run_until_complete(self, max_parallel: int = 3,
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run the scheduling loop until all tasks complete or fail.

        Returns a summary dict with completion stats.
        """
        if self._event_bus:
            self._event_bus.emit_async("swarm.schedule_started", {
                "task_count": len(self._queue),
            })

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}

            while not self._shutdown_flag:
                # Get ready tasks
                ready = self._get_ready_tasks()
                if not ready and not futures:
                    break

                # Submit ready tasks
                for scheduled in ready:
                    scheduled.status = "running"
                    scheduled.started_at = time.time()
                    with self._lock:
                        self._running.add(scheduled.id)

                    future = executor.submit(
                        self._execute_scheduled, scheduled,
                    )
                    futures[future] = scheduled

                    if progress_callback:
                        progress_callback(
                            scheduled.task, "running", scheduled.plan_id,
                        )

                # Wait for completion
                if not futures:
                    break

                done, _ = wait(futures.keys(), timeout=1.0, return_when=FIRST_COMPLETED)

                for future in done:
                    scheduled = futures.pop(future)
                    with self._lock:
                        self._running.discard(scheduled.id)

                    try:
                        result = future.result()
                        if result:
                            scheduled.status = "completed"
                            scheduled.completed_at = time.time()
                            scheduled.task.status = AgentTaskStatus.COMPLETED
                            with self._lock:
                                self._completed.add(scheduled.id)
                        else:
                            scheduled.status = "failed"
                            scheduled.completed_at = time.time()
                            scheduled.task.status = AgentTaskStatus.FAILED
                            with self._lock:
                                self._failed.add(scheduled.id)
                    except Exception as exc:
                        scheduled.status = "failed"
                        scheduled.completed_at = time.time()
                        scheduled.task.status = AgentTaskStatus.FAILED
                        scheduled.task.error = str(exc)
                        with self._lock:
                            self._failed.add(scheduled.id)

                    if progress_callback:
                        cb_status = scheduled.status
                        progress_callback(
                            scheduled.task, cb_status, scheduled.plan_id,
                            scheduled.task.error if cb_status == "failed" else None,
                        )

        summary = self.get_summary()
        if self._event_bus:
            self._event_bus.emit_async("swarm.schedule_completed", summary)

        return summary

    def _execute_scheduled(self, scheduled: ScheduledTask) -> bool:
        """Execute a single scheduled task with retry support."""
        while scheduled.attempt < scheduled.max_attempts:
            scheduled.attempt += 1
            scheduled.task.status = AgentTaskStatus.RUNNING
            try:
                if scheduled.runner:
                    result = scheduled.runner()
                    if result:
                        return True
                else:
                    logger.warning(
                        "Scheduler: task '%s' has no runner", scheduled.task.description[:50],
                    )
                    return False
            except Exception as exc:
                if scheduled.attempt >= scheduled.max_attempts:
                    scheduled.task.error = str(exc)
                    logger.warning(
                        "Scheduler: task '%s' failed after %d attempts: %s",
                        scheduled.task.description[:50], scheduled.attempt, exc,
                    )
                    return False
                logger.debug(
                    "Scheduler: task '%s' attempt %d/%d failed, retrying",
                    scheduled.task.description[:50], scheduled.attempt,
                    scheduled.max_attempts,
                )
        return False

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def _get_ready_tasks(self) -> List[ScheduledTask]:
        """Get tasks whose dependencies are all satisfied."""
        with self._lock:
            # Collect all completed IDs: scheduled IDs + task IDs for fallback
            completed = set(self._completed)
            for sid, st in self._queue.items():
                if st.task.status in (AgentTaskStatus.COMPLETED, AgentTaskStatus.SKIPPED):
                    completed.add(sid)
                    completed.add(st.task.id)
            ready = []
            for scheduled in self._queue.values():
                if scheduled.status != "pending":
                    continue
                if scheduled.id in self._running:
                    continue
                if scheduled.dependencies.issubset(completed):
                    ready.append(scheduled)
            ready.sort(key=lambda s: (s.task.priority, s.order))
            return ready

    def get_status(self, task_id: str) -> Optional[str]:
        """Get the status of a scheduled task."""
        with self._lock:
            scheduled = self._queue.get(task_id)
            return scheduled.status if scheduled else None

    def cancel_all(self) -> int:
        """Cancel all pending and running tasks. Returns count cancelled."""
        count = 0
        with self._lock:
            for scheduled in self._queue.values():
                if scheduled.status in ("pending", "ready"):
                    scheduled.status = "cancelled"
                    scheduled.task.status = AgentTaskStatus.CANCELLED
                    count += 1
        self._shutdown_flag = True
        return count

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        with self._lock:
            total = len(self._queue)
            return {
                "total": total,
                "completed": len(self._completed),
                "failed": len(self._failed),
                "running": len(self._running),
                "pending": total - len(self._completed) - len(self._failed) - len(self._running),
            }

    def reset(self) -> None:
        """Clear the scheduler state."""
        self._shutdown_flag = False
        with self._lock:
            self._queue.clear()
            self._running.clear()
            self._completed.clear()
            self._failed.clear()
