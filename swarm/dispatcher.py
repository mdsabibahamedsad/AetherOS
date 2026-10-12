"""
Task Dispatcher — assigns and executes tasks on agents.

The dispatcher takes ready tasks from the swarm planner, assigns them
to agent types via the task allocator, and manages the execution lifecycle
(running, monitoring, collecting results).

It integrates with the existing delegate_task mechanism for actual agent
spawning, but provides a higher-level orchestration layer on top.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus
from swarm.planner import SwarmPlan, AgentTask, AgentTaskStatus
from swarm.task_allocator import TaskAllocator, Assignment
from swarm.worker import AgentWorker
from swarm.registry import SwarmAgentRegistry

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Dispatches tasks to appropriate agent types and manages execution.

    Usage:
        dispatcher = TaskDispatcher(allocator, worker, event_bus)
        results = dispatcher.dispatch_tasks(plan)
        # results contains completed AgentTask objects
    """

    def __init__(
        self,
        allocator: TaskAllocator,
        worker: AgentWorker,
        event_bus: Optional[EventBus] = None,
    ):
        self._allocator = allocator
        self._worker = worker
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._running_tasks: Dict[str, AgentTask] = {}
        self._completed_tasks: List[AgentTask] = []

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch_tasks(
        self,
        plan: SwarmPlan,
        progress_callback: Optional[Callable] = None,
        max_parallel: int = 3,
    ) -> List[AgentTask]:
        """Dispatch all ready tasks from a plan.

        Processes tasks in dependency order, running parallel tasks
        concurrently within the max_parallel limit.

        Returns the list of completed tasks with their results.
        """
        logger.info(
            "Dispatcher: dispatching %d tasks from plan %s",
            len(plan.tasks), plan.id,
        )

        completed: List[AgentTask] = []
        pending_tasks = list(plan.tasks)
        running: Dict[str, AgentTask] = {}

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}

            while pending_tasks or running:
                # Find and start ready tasks
                ready = self._get_ready_tasks(pending_tasks, completed)

                for task in ready:
                    pending_tasks.remove(task)

                    # Find best agent
                    assignment = self._allocator.find_best_agent(task, plan.id)
                    if assignment is None:
                        task.status = AgentTaskStatus.FAILED
                        task.error = "No suitable agent type found"
                        completed.append(task)
                        if progress_callback:
                            progress_callback(task, "failed", task.error)
                        continue

                    task.assigned_to = assignment.agent_type
                    task.status = AgentTaskStatus.RUNNING

                    # Submit for execution
                    future = executor.submit(
                        self._execute_task, task, plan, assignment,
                    )
                    futures[future] = task
                    running[task.id] = task

                    if progress_callback:
                        progress_callback(task, "running")

                # Wait for at least one task to complete
                if not futures:
                    break

                done, _ = wait(futures.keys(), timeout=1.0, return_when=FIRST_COMPLETED)

                for future in done:
                    task = futures.pop(future)
                    running.pop(task.id, None)
                    try:
                        result = future.result()
                        completed.append(result)
                        if progress_callback:
                            cb_status = (
                                "completed" if result.status == AgentTaskStatus.COMPLETED
                                else "failed"
                            )
                            progress_callback(
                                result, cb_status,
                                result.error if result.status == AgentTaskStatus.FAILED else None,
                            )
                    except Exception as exc:
                        task.status = AgentTaskStatus.FAILED
                        task.error = str(exc)
                        completed.append(task)
                        self._allocator.release_assignment(task.assigned_to or "")
                        if progress_callback:
                            progress_callback(task, "failed", str(exc))

        with self._lock:
            self._completed_tasks.extend(completed)

        if self._event_bus:
            self._event_bus.emit_async("swarm.dispatch_completed", {
                "plan_id": plan.id,
                "total": len(completed),
                "completed": sum(1 for t in completed if t.status == AgentTaskStatus.COMPLETED),
                "failed": sum(1 for t in completed if t.status == AgentTaskStatus.FAILED),
            })

        return completed

    def dispatch_single(self, task: AgentTask,
                        plan_id: str = "") -> Optional[AgentTask]:
        """Dispatch a single task and wait for it to complete.

        Returns the completed task with result, or None on failure.
        """
        assignment = self._allocator.find_best_agent(task, plan_id)
        if assignment is None:
            task.status = AgentTaskStatus.FAILED
            task.error = "No suitable agent type found"
            return task

        # Create plan placeholder for execute_task
        plan = SwarmPlan(id=plan_id, goal=task.goal, tasks=[task])

        task.assigned_to = assignment.agent_type
        task.status = AgentTaskStatus.RUNNING

        try:
            result = self._execute_task(task, plan, assignment)
            return result
        except Exception as exc:
            task.status = AgentTaskStatus.FAILED
            task.error = str(exc)
            return task

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_task(self, task: AgentTask, plan: SwarmPlan,
                      assignment: Assignment) -> AgentTask:
        """Execute a single task using the assigned agent type.

        Uses the AgentWorker to spawn the agent and collect results.
        Handles retries and error recovery.
        """
        attempts = 0
        max_attempts = task.max_retries + 1

        while attempts < max_attempts:
            attempts += 1
            try:
                result = self._worker.run_agent(
                    goal=task.goal,
                    agent_type=assignment.agent_type,
                    context=task.context,
                    task_id=task.id,
                    timeout=task.timeout_seconds,
                    plan_context=plan.context,
                )

                if result.status == "completed":
                    task.status = AgentTaskStatus.COMPLETED
                    task.result = result.output
                    self._allocator.release_assignment(assignment.agent_type)
                    return task
                elif result.status == "error":
                    if attempts < max_attempts:
                        logger.warning(
                            "Dispatcher: task %s attempt %d/%d failed, retrying: %s",
                            task.id, attempts, max_attempts, result.error,
                        )
                        continue
                    task.status = AgentTaskStatus.FAILED
                    task.error = result.error or "Task failed after all retries"
                    self._allocator.release_assignment(assignment.agent_type)
                    return task
                else:
                    task.status = AgentTaskStatus.FAILED
                    task.error = f"Unexpected result status: {result.status}"
                    self._allocator.release_assignment(assignment.agent_type)
                    return task

            except Exception as exc:
                if attempts < max_attempts:
                    logger.warning(
                        "Dispatcher: task %s attempt %d/%d raised: %s",
                        task.id, attempts, max_attempts, exc,
                    )
                    continue
                task.status = AgentTaskStatus.FAILED
                task.error = str(exc)
                self._allocator.release_assignment(assignment.agent_type)
                return task

        return task  # Should not reach here

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ready_tasks(pending: List[AgentTask],
                         completed: List[AgentTask]) -> List[AgentTask]:
        """Get pending tasks whose dependencies are all satisfied."""
        completed_ids = {
            t.id for t in completed
            if t.status == AgentTaskStatus.COMPLETED
        }

        ready = []
        for task in pending:
            if task.status != AgentTaskStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in task.dependencies):
                ready.append(task)

        ready.sort(key=lambda t: (t.priority, t.id))
        return ready

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            task = self._running_tasks.get(task_id)
            if task is None:
                return False
            task.status = AgentTaskStatus.CANCELLED
        return True

    def get_running_tasks(self) -> List[AgentTask]:
        """Get currently running tasks."""
        with self._lock:
            return list(self._running_tasks.values())

    def get_stats(self) -> Dict[str, Any]:
        """Return dispatcher statistics."""
        with self._lock:
            total = len(self._completed_tasks) + len(self._running_tasks)
            return {
                "total_dispatched": total,
                "running": len(self._running_tasks),
                "completed": len(self._completed_tasks),
            }
