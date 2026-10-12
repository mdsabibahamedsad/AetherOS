"""
Migration Engine — manages code migration between versions or architectures.

Handles:
  - Migration planning
  - Step-by-step migration execution
  - Rollback support
  - Data migration
  - API compatibility tracking
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class MigrationStatus(enum.Enum):
    """Status of a migration step or plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class MigrationStep:
    """A single step in a migration plan.

    Attributes:
        id: Unique step ID
        name: Step name
        description: What this step does
        status: Step status
        order: Execution order
        can_rollback: Whether this step supports rollback
        error: Error message if failed
        result: Step result
        started_at: When this step started
        completed_at: When this step completed
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    status: MigrationStatus = MigrationStatus.PENDING
    order: int = 0
    can_rollback: bool = True
    error: Optional[str] = None
    result: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class MigrationPlan:
    """A complete migration plan.

    Attributes:
        id: Unique plan ID
        title: Migration title
        description: Description of the migration
        from_version: Source version/state
        to_version: Target version/state
        steps: List of migration steps
        status: Overall plan status
        created_at: When the plan was created
        started_at: When execution started
        completed_at: When execution completed
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    from_version: str = ""
    to_version: str = ""
    steps: List[MigrationStep] = field(default_factory=list)
    status: MigrationStatus = MigrationStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    notes: str = ""


class MigrationEngine:
    """Manages code and data migration between versions.

    Creates migration plans with ordered steps, executes them
    with rollback support, and tracks migration history.

    Usage:
        engine = MigrationEngine(event_bus)
        plan = engine.create_plan(
            title="Migrate to new API",
            from_version="1.0.0",
            to_version="2.0.0",
        )
        plan.steps.append(MigrationStep(
            name="Update imports",
            description="Update import paths for new module structure",
        ))
        result = engine.execute(plan)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._plans: Dict[str, MigrationPlan] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def create_plan(self, title: str,
                    description: str = "",
                    from_version: str = "",
                    to_version: str = "") -> MigrationPlan:
        """Create a new migration plan.

        Args:
            title: Migration title
            description: Description of the migration
            from_version: Source version/state
            to_version: Target version/state

        Returns:
            An empty MigrationPlan ready for steps
        """
        plan = MigrationPlan(
            title=title,
            description=description,
            from_version=from_version,
            to_version=to_version,
        )

        self._plans[plan.id] = plan

        logger.info(
            "MigrationEngine: created plan %s: %s",
            plan.id[:8], title,
        )

        return plan

    def add_step(self, plan_id: str, name: str,
                 description: str = "",
                 can_rollback: bool = True,
                 order: Optional[int] = None) -> Optional[MigrationStep]:
        """Add a step to a migration plan.

        Args:
            plan_id: Plan ID
            name: Step name
            description: Step description
            can_rollback: Whether this step can be rolled back
            order: Step order (auto-assigned if not specified)

        Returns:
            The created MigrationStep, or None if plan not found
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        step = MigrationStep(
            name=name,
            description=description,
            can_rollback=can_rollback,
            order=order if order is not None else len(plan.steps),
        )

        plan.steps.append(step)
        plan.steps.sort(key=lambda s: s.order)

        return step

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, plan: MigrationPlan,
                step_executor: Optional[Callable[[MigrationStep], bool]] = None
                ) -> MigrationPlan:
        """Execute a migration plan.

        Args:
            plan: The plan to execute
            step_executor: Optional callback to execute each step.
                          If not provided, steps are marked as completed
                          without executing.

        Returns:
            The plan with updated step statuses
        """
        plan.status = MigrationStatus.IN_PROGRESS
        plan.started_at = time.time()

        logger.info("MigrationEngine: executing plan '%s' (%d steps)",
                    plan.title, len(plan.steps))

        if self._event_bus:
            self._event_bus.emit_async("engineering.migration_started", {
                "plan_id": plan.id,
                "title": plan.title,
                "steps": len(plan.steps),
            })

        for step in plan.steps:
            if step.status != MigrationStatus.PENDING:
                continue

            step.status = MigrationStatus.IN_PROGRESS
            step.started_at = time.time()

            try:
                if step_executor:
                    success = step_executor(step)
                else:
                    # Default: mark step as completed
                    success = True

                if success:
                    step.status = MigrationStatus.COMPLETED
                    step.completed_at = time.time()
                    logger.debug("MigrationEngine: step '%s' completed", step.name)
                else:
                    step.status = MigrationStatus.FAILED
                    step.error = step.error or "Step execution returned False"
                    logger.error("MigrationEngine: step '%s' failed: %s",
                                step.name, step.error)

                    # Rollback on failure
                    self._rollback(plan, stop_at_step=step)
                    plan.status = MigrationStatus.FAILED
                    plan.completed_at = time.time()
                    return plan

            except Exception as exc:
                step.status = MigrationStatus.FAILED
                step.error = str(exc)
                logger.error("MigrationEngine: step '%s' failed: %s", step.name, exc)

                self._rollback(plan, stop_at_step=step)
                plan.status = MigrationStatus.FAILED
                plan.completed_at = time.time()
                return plan

        plan.status = MigrationStatus.COMPLETED
        plan.completed_at = time.time()

        logger.info("MigrationEngine: plan '%s' completed successfully", plan.title)

        if self._event_bus:
            self._event_bus.emit_async("engineering.migration_completed", {
                "plan_id": plan.id,
                "title": plan.title,
                "steps_completed": sum(
                    1 for s in plan.steps if s.status == MigrationStatus.COMPLETED
                ),
            })

        # Record execution
        self._execution_history.append({
            "plan_id": plan.id,
            "title": plan.title,
            "status": plan.status.value,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
        })

        return plan

    def _rollback(self, plan: MigrationPlan,
                  stop_at_step: MigrationStep = None) -> None:
        """Rollback completed steps in reverse order.

        Args:
            plan: The plan to rollback
            stop_at_step: Stop at this step (do not rollback it or earlier steps)
        """
        completed_steps = [
            s for s in plan.steps
            if s.status == MigrationStatus.COMPLETED
            and (stop_at_step is None or s.order < stop_at_step.order)
        ]

        # Rollback in reverse order
        for step in reversed(completed_steps):
            if step.can_rollback:
                step.status = MigrationStatus.ROLLED_BACK
                logger.info("MigrationEngine: rolled back step '%s'", step.name)
            else:
                logger.warning(
                    "MigrationEngine: step '%s' cannot be rolled back",
                    step.name,
                )

    # ------------------------------------------------------------------
    # Plan management
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> Optional[MigrationPlan]:
        """Get a migration plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self, status: Optional[MigrationStatus] = None) -> List[MigrationPlan]:
        """List migration plans, optionally filtered by status."""
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get migration execution history."""
        return list(reversed(self._execution_history))

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_plans": len(self._plans),
            "by_status": {
                status.value: sum(1 for p in self._plans.values() if p.status == status)
                for status in MigrationStatus
            },
            "total_steps": sum(len(p.steps) for p in self._plans.values()),
            "total_executions": len(self._execution_history),
        }
