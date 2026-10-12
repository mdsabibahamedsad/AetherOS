"""
Coordinator — orchestrates multi-agent workflows.

The coordinator is the central workflow engine for the swarm. It takes a
swarm plan, coordinates the execution of tasks across different agent types,
manages the workflow state, and handles failure recovery.

It delegates to the dispatcher, scheduler, and worker for actual execution,
focusing on the high-level workflow coordination.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus
from swarm.planner import (
    SwarmPlanner, SwarmPlan, AgentTask, AgentTaskStatus,
)
from swarm.dispatcher import TaskDispatcher
from swarm.scheduler import SwarmScheduler
from swarm.worker import AgentWorker
from swarm.task_allocator import TaskAllocator
from swarm.registry import SwarmAgentRegistry
from swarm.result_merger import ResultMerger

logger = logging.getLogger(__name__)


class WorkflowState(enum.Enum):
    """States for a coordinated workflow."""
    PENDING = "pending"
    PLANNING = "planning"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Coordinator:
    """Coordinates multi-agent workflows from planning to completion.

    Orchestrates the full lifecycle of a swarm goal:
      1. Plan decomposition (via SwarmPlanner)
      2. Task assignment (via TaskAllocator)
      3. Parallel execution (via Dispatcher / Scheduler)
      4. Failure recovery
      5. Result merging (via ResultMerger)

    Usage:
        coordinator = Coordinator(planner, dispatcher, merger, event_bus)
        result = coordinator.run_goal("Build a web app")
        # Returns merged result from all agents
    """

    def __init__(
        self,
        planner: SwarmPlanner,
        dispatcher: TaskDispatcher,
        merger: ResultMerger,
        event_bus: Optional[EventBus] = None,
    ):
        self._planner = planner
        self._dispatcher = dispatcher
        self._merger = merger
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._workflows: Dict[str, "WorkflowState"] = {}
        self._workflow_goals: Dict[str, str] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}

    # ------------------------------------------------------------------
    # Workflow lifecycle
    # ------------------------------------------------------------------

    def run_goal(self, goal: str,
                 context: Dict[str, Any] = None,
                 workflow_id: str = None,
                 progress_callback: Optional[Callable] = None,
                 max_parallel: int = 3) -> Dict[str, Any]:
        """Run a complete multi-agent workflow from goal to result.

        Steps:
          1. Decompose the goal into a plan with tasks
          2. Approve the plan
          3. Dispatch and execute tasks (parallel when possible)
          4. Merge results into a final answer

        Args:
            goal: The user's goal/objective
            context: Optional context for the plan
            workflow_id: Optional unique ID
            progress_callback: Optional callback for progress events
            max_parallel: Max parallel tasks

        Returns:
            Dict with merged result and workflow metadata
        """
        wf_id = workflow_id or uuid.uuid4().hex[:12]

        with self._lock:
            self._workflows[wf_id] = WorkflowState.PLANNING
            self._workflow_goals[wf_id] = goal

        if self._event_bus:
            self._event_bus.emit_async("swarm.workflow_started", {
                "workflow_id": wf_id,
                "goal": goal[:200],
            })

        logger.info("Coordinator: starting workflow %s for: %s", wf_id, goal[:80])

        # Step 1: Plan
        plan = self._planner.decompose_goal(goal, context=context or {})
        self._planner.approve_plan(plan.id)

        with self._lock:
            self._workflows[wf_id] = WorkflowState.APPROVED

        logger.info("Coordinator: plan %s has %d tasks", plan.id, len(plan.tasks))

        if progress_callback:
            progress_callback("plan_ready", {
                "workflow_id": wf_id,
                "plan_id": plan.id,
                "task_count": len(plan.tasks),
                "goal": goal,
            })

        # Step 2: Execute
        with self._lock:
            self._workflows[wf_id] = WorkflowState.IN_PROGRESS

        completed_tasks = self._dispatcher.dispatch_tasks(
            plan=plan,
            progress_callback=(
                lambda task, status, error=None: self._on_task_progress(
                    wf_id, task, status, error,
                )
            ),
            max_parallel=max_parallel,
        )

        # Step 3: Merge results
        merged = self._merger.merge(completed_tasks, goal, plan.context)

        # Step 4: Determine final status
        has_failures = any(
            t.status == AgentTaskStatus.FAILED for t in completed_tasks
        )
        all_completed = all(
            t.status == AgentTaskStatus.COMPLETED for t in completed_tasks
        )

        if all_completed:
            with self._lock:
                self._workflows[wf_id] = WorkflowState.COMPLETED
        elif has_failures:
            with self._lock:
                self._workflows[wf_id] = WorkflowState.FAILED
        else:
            with self._lock:
                self._workflows[wf_id] = WorkflowState.COMPLETED

        if self._event_bus:
            self._event_bus.emit_async("swarm.workflow_completed", {
                "workflow_id": wf_id,
                "plan_id": plan.id,
                "status": self._workflows.get(wf_id, WorkflowState.FAILED).value,
                "task_count": len(completed_tasks),
            })

        logger.info(
            "Coordinator: workflow %s %s (%d tasks)",
            wf_id,
            "completed" if not has_failures else "completed with failures",
            len(completed_tasks),
        )

        return {
            "workflow_id": wf_id,
            "plan_id": plan.id,
            "goal": goal,
            "status": self._workflows.get(wf_id, WorkflowState.FAILED).value,
            "merged_result": merged,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status.value,
                    "assigned_to": t.assigned_to,
                    "result": t.result,
                    "error": t.error,
                }
                for t in completed_tasks
            ],
            "stats": {
                "total": len(completed_tasks),
                "completed": sum(1 for t in completed_tasks if t.status == AgentTaskStatus.COMPLETED),
                "failed": sum(1 for t in completed_tasks if t.status == AgentTaskStatus.FAILED),
            },
        }

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        with self._lock:
            state = self._workflows.get(workflow_id)
            if state is None or state in (WorkflowState.COMPLETED,
                                         WorkflowState.FAILED,
                                         WorkflowState.CANCELLED):
                return False
            self._workflows[workflow_id] = WorkflowState.CANCELLED

        if self._event_bus:
            self._event_bus.emit_async("swarm.workflow_cancelled", {
                "workflow_id": workflow_id,
            })

        logger.info("Coordinator: cancelled workflow %s", workflow_id)
        return True

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def _on_task_progress(self, workflow_id: str,
                          task: AgentTask, status: str,
                          error: Optional[str] = None) -> None:
        """Handle task progress updates."""
        if self._event_bus:
            self._event_bus.emit_async("swarm.task_progress", {
                "workflow_id": workflow_id,
                "task_id": task.id,
                "description": task.description[:100],
                "status": status,
                "assigned_to": task.assigned_to,
                "error": error,
            })

        # Notify registered callbacks
        with self._lock:
            callbacks = list(self._progress_callbacks.get(workflow_id, []))

        for cb in callbacks:
            try:
                cb(task, status, error)
            except Exception as exc:
                logger.debug("Coordinator: progress callback failed: %s", exc)

    def subscribe_progress(self, workflow_id: str,
                           callback: Callable) -> Callable:
        """Subscribe to progress events for a workflow.

        Returns an unsubscribe function.
        """
        with self._lock:
            self._progress_callbacks.setdefault(workflow_id, []).append(callback)

        def unsubscribe():
            with self._lock:
                cbs = self._progress_callbacks.get(workflow_id, [])
                if callback in cbs:
                    cbs.remove(callback)

        return unsubscribe

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get the current state of a workflow."""
        with self._lock:
            return self._workflows.get(workflow_id)

    def get_workflow_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a workflow's state."""
        with self._lock:
            state = self._workflows.get(workflow_id)
            if state is None:
                return None
            return {
                "workflow_id": workflow_id,
                "goal": self._workflow_goals.get(workflow_id, ""),
                "state": state.value,
            }

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows."""
        with self._lock:
            active = []
            for wf_id, state in self._workflows.items():
                if state in (WorkflowState.PENDING, WorkflowState.PLANNING,
                           WorkflowState.APPROVED, WorkflowState.IN_PROGRESS):
                    active.append({
                        "workflow_id": wf_id,
                        "goal": self._workflow_goals.get(wf_id, ""),
                        "state": state.value,
                    })
            return active

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        with self._lock:
            total = len(self._workflows)
            by_state: Dict[str, int] = {}
            for state in self._workflows.values():
                by_state[state.value] = by_state.get(state.value, 0) + 1
            return {
                "total_workflows": total,
                "by_state": by_state,
            }
