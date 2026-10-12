"""
Planner — converts user goals into structured execution plans.

Given a high-level goal, the planner:
  1. Analyzes the goal and breaks it into steps
  2. Identifies dependencies between steps
  3. Produces a Plan with ordered PlanSteps
  4. Optionally converts the plan to a TaskGraph for execution

Plans support parallel tasks, dependencies, retry policies,
priority levels, and cancellation.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class PlanStatus(enum.Enum):
    """Lifecycle status of a plan."""
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """A single step within a plan.

    Attributes:
        id: Unique step ID
        description: Human-readable description of the step
        action: Action type (e.g. "agent_run", "tool_call", "subplan")
        params: Parameters for the action
        dependencies: List of step IDs that must complete first
        retry_count: Max retries on failure (0 = no retry)
        priority: Priority level (lower = higher priority)
        timeout_seconds: Max execution time per attempt
        status: Current status
        result: Optional result data
        error: Optional error message
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    action: str = "agent_run"  # agent_run, tool_call, subplan, wait, notify
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    priority: int = 50
    timeout_seconds: float = 300.0
    status: PlanStatus = PlanStatus.PENDING
    result: Any = None
    error: Optional[str] = None


@dataclass
class Plan:
    """A complete execution plan for a user goal.

    Attributes:
        id: Unique plan ID
        goal: The original user goal/request
        steps: Ordered list of PlanSteps
        status: Current plan status
        context: Shared context dict for the plan
        created_at: Timestamp of creation
        completed_at: Timestamp of completion
        metadata: Optional metadata dict
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """Planning engine for the AetherOS Kernel.

    Converts high-level user goals into structured execution plans
    with dependency-aware step ordering.

    Usage:
        planner = Planner(event_bus)
        plan = planner.create_plan("Deploy the web app to production")
        planner.approve_plan(plan.id)
        steps = planner.get_ready_steps(plan.id)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._plans: Dict[str, Plan] = {}
        # Registered plan strategies (callable that can produce steps for a goal)
        self._strategies: List[Callable[[str], Optional[List[PlanStep]]]] = []

    # ------------------------------------------------------------------
    # Plan creation
    # ------------------------------------------------------------------

    def create_plan(self, goal: str, steps: List[PlanStep] = None,
                    context: Dict[str, Any] = None,
                    metadata: Dict[str, Any] = None) -> Plan:
        """Create a new plan for a user goal.

        If steps are not provided, runs registered strategies to generate them.
        """
        plan = Plan(
            goal=goal,
            steps=steps or [],
            context=context or {},
            metadata=metadata or {},
        )

        with self._lock:
            self._plans[plan.id] = plan

        logger.info("Planner: created plan %s for goal: %s", plan.id, goal[:80])

        if self._event_bus:
            self._event_bus.emit(EventTopics.TASK_CREATED, {
                "plan_id": plan.id,
                "goal": goal,
                "step_count": len(plan.steps),
            })

        # Auto-generate steps if none provided
        if not plan.steps:
            generated = self._auto_generate_steps(goal)
            if generated:
                plan.steps = generated
                logger.info(
                    "Planner: auto-generated %d steps for plan %s",
                    len(generated), plan.id,
                )

        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self, status: PlanStatus = None) -> List[Plan]:
        """List all plans, optionally filtered by status."""
        with self._lock:
            plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def approve_plan(self, plan_id: str) -> bool:
        """Mark a plan as approved and ready for execution."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = PlanStatus.APPROVED
        logger.info("Planner: plan %s approved", plan_id)
        return True

    def start_plan(self, plan_id: str) -> bool:
        """Mark a plan as in progress."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = PlanStatus.IN_PROGRESS

        if self._event_bus:
            self._event_bus.emit(EventTopics.TASK_STARTED, {
                "plan_id": plan_id, "goal": plan.goal,
            })
        return True

    def complete_plan(self, plan_id: str, result: Any = None) -> bool:
        """Mark a plan as completed."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = PlanStatus.COMPLETED
        plan.completed_at = time.time()
        plan.metadata["result"] = result

        if self._event_bus:
            self._event_bus.emit(EventTopics.TASK_COMPLETED, {
                "plan_id": plan_id, "result": str(result)[:200],
            })
        logger.info("Planner: plan %s completed", plan_id)
        return True

    def fail_plan(self, plan_id: str, error: str) -> bool:
        """Mark a plan as failed with an error message."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = PlanStatus.FAILED
        plan.completed_at = time.time()
        plan.metadata["error"] = error

        if self._event_bus:
            self._event_bus.emit(EventTopics.TASK_FAILED, {
                "plan_id": plan_id, "error": error,
            })
        logger.error("Planner: plan %s failed: %s", plan_id, error)
        return True

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a plan and all its steps."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = PlanStatus.CANCELLED
        plan.completed_at = time.time()

        # Cancel all pending steps
        for step in plan.steps:
            if step.status in (PlanStatus.PENDING, PlanStatus.APPROVED):
                step.status = PlanStatus.CANCELLED

        if self._event_bus:
            self._event_bus.emit(EventTopics.TASK_CANCELLED, {
                "plan_id": plan_id,
            })
        logger.info("Planner: plan %s cancelled", plan_id)
        return True

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    def add_step(self, plan_id: str, step: PlanStep) -> bool:
        """Add a step to an existing plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        with self._lock:
            plan.steps.append(step)
        logger.debug("Planner: added step %s to plan %s", step.id, plan_id)
        return True

    def get_ready_steps(self, plan_id: str) -> List[PlanStep]:
        """Get steps whose dependencies are all satisfied (ready to execute)."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return []

        completed_ids = {
            s.id for s in plan.steps
            if s.status == PlanStatus.COMPLETED
        }

        ready = []
        for step in plan.steps:
            if step.status != PlanStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                ready.append(step)

        # Sort by priority (lower = first)
        ready.sort(key=lambda s: (s.priority, s.id))
        return ready

    def update_step_status(self, plan_id: str, step_id: str,
                           status: PlanStatus, result: Any = None,
                           error: str = None) -> bool:
        """Update the status of a single step."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False

        for step in plan.steps:
            if step.id == step_id:
                step.status = status
                if result is not None:
                    step.result = result
                if error is not None:
                    step.error = error
                logger.debug(
                    "Planner: step %s in plan %s -> %s", step_id, plan_id, status.value,
                )

                # Check if plan is complete
                if status in (PlanStatus.COMPLETED, PlanStatus.FAILED):
                    self._check_plan_completion(plan_id)

                if self._event_bus:
                    self._event_bus.emit_async(EventTopics.TASK_PROGRESS, {
                        "plan_id": plan_id,
                        "step_id": step_id,
                        "status": status.value,
                        "progress": self._progress_summary(plan),
                    })
                return True
        return False

    def _check_plan_completion(self, plan_id: str) -> None:
        """Auto-complete or fail a plan when all steps are done."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return

        all_done = True
        has_failure = False
        has_cancelled = False

        for step in plan.steps:
            if step.status == PlanStatus.FAILED:
                has_failure = True
                all_done = False
            elif step.status == PlanStatus.CANCELLED:
                has_cancelled = True
            elif step.status not in (PlanStatus.COMPLETED, PlanStatus.CANCELLED):
                all_done = False

        if all_done or has_failure:
            if has_failure:
                self.fail_plan(plan_id, "One or more steps failed")
            elif has_cancelled:
                self.cancel_plan(plan_id)
            else:
                self.complete_plan(plan_id)

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------

    def _progress_summary(self, plan: Plan) -> Dict[str, Any]:
        """Return a progress summary for a plan."""
        total = len(plan.steps)
        completed = sum(1 for s in plan.steps if s.status == PlanStatus.COMPLETED)
        failed = sum(1 for s in plan.steps if s.status == PlanStatus.FAILED)
        in_progress = sum(1 for s in plan.steps if s.status == PlanStatus.IN_PROGRESS)
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "progress_pct": (completed / total * 100) if total > 0 else 0,
        }

    def get_progress(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get progress summary for a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return None
        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            **self._progress_summary(plan),
        }

    # ------------------------------------------------------------------
    # Strategy-based step generation
    # ------------------------------------------------------------------

    def register_strategy(self, strategy: Callable[[str], Optional[List[PlanStep]]]) -> None:
        """Register a strategy that can auto-generate steps for goals."""
        with self._lock:
            self._strategies.append(strategy)
        logger.debug("Planner: registered step generation strategy")

    def _auto_generate_steps(self, goal: str) -> List[PlanStep]:
        """Run registered strategies to generate steps for a goal."""
        all_steps = []
        for strategy in self._strategies:
            try:
                steps = strategy(goal)
                if steps:
                    all_steps.extend(steps)
            except Exception as exc:
                logger.warning("Planner: strategy failed: %s", exc)
        return all_steps

    def _default_strategy(self, goal: str) -> List[PlanStep]:
        """Default strategy: create a single-agent-run step for any goal."""
        return [
            PlanStep(
                description=f"Execute goal: {goal[:100]}",
                action="agent_run",
                params={"prompt": goal},
            ),
        ]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self, plan_id: str) -> Optional[str]:
        """Serialize a plan to JSON."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return None
        return json.dumps({
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "action": s.action,
                    "dependencies": s.dependencies,
                    "status": s.status.value,
                }
                for s in plan.steps
            ],
            "created_at": plan.created_at,
            "completed_at": plan.completed_at,
        }, indent=2)

    def cleanup(self) -> int:
        """Remove all plans. Returns count of plans removed."""
        with self._lock:
            count = len(self._plans)
            self._plans.clear()
        return count
