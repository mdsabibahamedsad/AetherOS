"""Execution Planner.

Goal -> Choose tools -> Validate permissions -> Build execution plan -> Run -> Verify -> Rollback if required.

The planner takes a high-level goal and decomposes it into a sequence of
tool calls with dependency tracking, permission pre-validation, and rollback support.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from tool_runtime.interface import ToolResult, ToolStatus
from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager
from tool_runtime.permission import get_permission_system, RiskLevel
from tool_runtime.safety import get_safety_engine

logger = logging.getLogger(__name__)


class PlanStatus(enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str
    tool_name: str
    params: Dict[str, Any]
    description: str
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: Optional[float] = None
    rollback_tool: Optional[str] = None
    rollback_params: Optional[Dict[str, Any]] = None
    result: Optional[ToolResult] = None
    status: PlanStatus = PlanStatus.PENDING
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


@dataclass
class ExecutionPlan:
    """Complete execution plan with rollback support."""
    id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class ExecutionPlanner:
    """Decomposes goals into executable tool plans with rollback support.

    Features:
    - Goal decomposition
    - Tool selection and ordering
    - Permission pre-validation
    - Dependency resolution
    - Execution with verification
    - Rollback on failure
    """

    def __init__(self):
        self._manager: Optional[ToolRuntimeManager] = None
        self._permission = get_permission_system()
        self._safety = get_safety_engine()
        self._plans: Dict[str, ExecutionPlan] = {}
        self._lock = threading.RLock()
        self._plan_handlers: Dict[str, Callable] = {}

    @property
    def manager(self) -> ToolRuntimeManager:
        if self._manager is None:
            self._manager = get_runtime_manager()
        return self._manager

    def register_plan_handler(self, goal_pattern: str, handler: Callable) -> None:
        """Register a handler for specific goal patterns."""
        with self._lock:
            self._plan_handlers[goal_pattern] = handler

    def create_plan(
        self,
        goal: str,
        steps: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Create an execution plan from a goal.

        If steps are provided, use them directly.
        Otherwise, decompose the goal using registered handlers or default logic.
        """
        plan_id = str(uuid.uuid4())
        plan = ExecutionPlan(
            id=plan_id,
            goal=goal,
            context=context or {},
        )

        if steps:
            for i, step_data in enumerate(steps):
                step = PlanStep(
                    id=step_data.get("id", f"step_{i}"),
                    tool_name=step_data["tool_name"],
                    params=step_data.get("params", {}),
                    description=step_data.get("description", ""),
                    depends_on=step_data.get("depends_on", []),
                    timeout_seconds=step_data.get("timeout_seconds"),
                    rollback_tool=step_data.get("rollback_tool"),
                    rollback_params=step_data.get("rollback_params"),
                )
                plan.steps.append(step)
        else:
            plan.steps = self._decompose_goal(goal, context or {})

        plan.status = PlanStatus.PENDING
        with self._lock:
            self._plans[plan_id] = plan
        return plan

    def _decompose_goal(self, goal: str, context: Dict[str, Any]) -> List[PlanStep]:
        """Default goal decomposition - single step to execute as-is."""
        with self._lock:
            for pattern, handler in self._plan_handlers.items():
                if pattern in goal.lower():
                    try:
                        steps = handler(goal, context)
                        if steps:
                            return steps
                    except Exception as e:
                        logger.error("Plan handler error for '%s': %s", pattern, e)

        return [
            PlanStep(
                id="step_0",
                tool_name="terminal",
                params={"command": goal},
                description=f"Execute: {goal}",
            )
        ]

    def validate_plan(self, plan: ExecutionPlan) -> List[str]:
        """Validate all steps in a plan before execution."""
        errors = []
        step_map = {s.id: s for s in plan.steps}

        for step in plan.steps:
            runtime = self.manager.get_runtime(step.tool_name)
            if not runtime:
                errors.append(f"Step '{step.id}': Unknown tool '{step.tool_name}'")
                continue

            validation_errors = runtime.validate(step.params)
            if validation_errors:
                for ve in validation_errors:
                    errors.append(f"Step '{step.id}': {ve}")

            for dep_id in step.depends_on:
                if dep_id not in step_map:
                    errors.append(f"Step '{step.id}': Unknown dependency '{dep_id}'")

        if not errors:
            plan.status = PlanStatus.VALIDATED
        return errors

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Execute all steps in the plan with dependency resolution."""
        plan.status = PlanStatus.RUNNING
        plan.started_at = time.time()
        step_map = {s.id: s for s in plan.steps}

        completed: Dict[str, ToolResult] = {}
        errors: List[str] = []

        validation_errors = self.validate_plan(plan)
        if validation_errors:
            plan.status = PlanStatus.FAILED
            plan.error = f"Validation errors: {'; '.join(validation_errors)}"
            return plan

        ready_steps = [s for s in plan.steps if not s.depends_on]
        blocked_steps = [s for s in plan.steps if s.depends_on]

        max_iterations = len(plan.steps) * 2
        iteration = 0

        while (ready_steps or blocked_steps) and iteration < max_iterations:
            iteration += 1

            for step in ready_steps[:]:
                ready_steps.remove(step)
                step.status = PlanStatus.RUNNING
                step.start_time = time.time()

                try:
                    result = self.manager.execute(
                        tool_name=step.tool_name,
                        params=step.params,
                        context=plan.context,
                        timeout_seconds=step.timeout_seconds,
                    )
                    step.result = result
                    step.end_time = time.time()
                    completed[step.id] = result

                    if result.success:
                        step.status = PlanStatus.COMPLETED
                        plan.context[f"step:{step.id}.output"] = result.output
                    else:
                        step.status = PlanStatus.FAILED
                        step.error = result.error
                        errors.append(f"Step '{step.id}' ({step.description}): {result.error}")
                        plan.error = f"Step '{step.id}' failed: {result.error}"
                        plan.status = PlanStatus.FAILED
                        self._rollback_plan(plan)
                        return plan

                except Exception as e:
                    step.status = PlanStatus.FAILED
                    step.error = str(e)
                    errors.append(f"Step '{step.id}' error: {e}")
                    plan.error = f"Step '{step.id}' error: {e}"
                    plan.status = PlanStatus.FAILED
                    self._rollback_plan(plan)
                    return plan

            new_ready = []
            for step in blocked_steps[:]:
                deps_met = all(dep in completed and completed[dep].success for dep in step.depends_on)
                if deps_met:
                    blocked_steps.remove(step)
                    new_ready.append(step)

            ready_steps.extend(new_ready)

        if not errors:
            plan.status = PlanStatus.COMPLETED
        plan.completed_at = time.time()

        logger.info(
            "Plan %s completed: status=%s, steps=%d, errors=%d",
            plan.id, plan.status.value, len(plan.steps), len(errors),
        )
        return plan

    def _rollback_plan(self, plan: ExecutionPlan) -> None:
        """Rollback completed steps if a step fails."""
        plan.status = PlanStatus.ROLLING_BACK
        completed_steps = [s for s in plan.steps if s.status == PlanStatus.COMPLETED and s.rollback_tool]

        if not completed_steps:
            plan.status = PlanStatus.ROLLED_BACK
            return

        logger.info("Rolling back plan %s (%d steps)", plan.id, len(completed_steps))

        for step in reversed(completed_steps):
            try:
                self.manager.execute(
                    tool_name=step.rollback_tool,
                    params=step.rollback_params or {},
                    context=plan.context,
                )
                logger.info("Rolled back step %s (%s)", step.id, step.description)
            except Exception as e:
                logger.error("Rollback failed for step %s: %s", step.id, e)

        plan.status = PlanStatus.ROLLED_BACK

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": p.id,
                    "goal": p.goal[:100],
                    "status": p.status.value,
                    "steps": len(p.steps),
                    "created_at": p.created_at,
                    "error": p.error,
                }
                for p in self._plans.values()
            ]

    def cancel_plan(self, plan_id: str) -> bool:
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan or plan.status in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED):
                return False
            plan.status = PlanStatus.CANCELLED
            for step in plan.steps:
                if step.status == PlanStatus.RUNNING:
                    self.manager.cancel_execution(step.id)
            return True

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for p in self._plans.values() if p.status == PlanStatus.RUNNING)
            completed = sum(1 for p in self._plans.values() if p.status == PlanStatus.COMPLETED)
            failed = sum(1 for p in self._plans.values() if p.status in (PlanStatus.FAILED, PlanStatus.ROLLED_BACK))
            return {
                "total_plans": len(self._plans),
                "active": active,
                "completed": completed,
                "failed": failed,
            }


# Global singleton
_planner_instance: Optional[ExecutionPlanner] = None


def get_execution_planner() -> ExecutionPlanner:
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = ExecutionPlanner()
    return _planner_instance
