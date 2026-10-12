"""
Implementation Plan Generator — creates structured implementation plans.

Converts architecture designs and decomposed tasks into ordered,
dependency-aware implementation plans with phases and milestones.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class TaskType(enum.Enum):
    """Types of tasks in an implementation plan."""
    SETUP = "setup"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    MIGRATION = "migration"
    REFACTORING = "refactoring"
    RESEARCH = "research"
    INTEGRATION = "integration"


class PlanStatus(enum.Enum):
    """Status of an implementation plan."""
    DRAFT = "draft"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EngineeringTask:
    """A task within an implementation plan.

    Attributes:
        id: Unique task ID
        type: Type of task
        title: Task title
        description: Detailed description
        phase: Phase this task belongs to
        priority: Priority (0-100, lower = higher)
        status: Task status
        dependencies: Task IDs this task depends on
        estimated_hours: Estimated person-hours
        assigned_to: Who is assigned
        acceptance_criteria: Completion criteria
        files: Files to create or modify
        result: Result of execution
        error: Error message if failed
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: TaskType = TaskType.IMPLEMENTATION
    title: str = ""
    description: str = ""
    phase: str = ""
    priority: int = 50
    status: str = "pending"
    dependencies: List[str] = field(default_factory=list)
    estimated_hours: float = 1.0
    assigned_to: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanPhase:
    """A phase within an implementation plan.

    Attributes:
        name: Phase name
        description: Phase description
        order: Execution order
        tasks: Task IDs in this phase
        status: Phase status
    """
    name: str = ""
    description: str = ""
    order: int = 0
    tasks: List[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class ImplementationPlan:
    """A complete implementation plan.

    Attributes:
        id: Unique plan ID
        title: Plan title
        architecture_id: Related architecture design ID
        spec_id: Related specification ID
        goal: Original engineering goal
        phases: Implementation phases
        tasks: All tasks in the plan
        status: Plan status
        total_estimated_hours: Total estimated effort
        created_at: When the plan was created
        updated_at: When the plan was last updated
        completed_at: When the plan was completed
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    architecture_id: str = ""
    spec_id: str = ""
    goal: str = ""
    phases: List[PlanPhase] = field(default_factory=list)
    tasks: List[EngineeringTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    total_estimated_hours: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EngineeringPlanner:
    """Creates structured implementation plans from architecture and tasks.

    Converts architecture designs and decomposed tasks into ordered,
    phased implementation plans with dependency tracking.

    Usage:
        planner = EngineeringPlanner(event_bus)
        plan = planner.create_plan(architecture, tasks)
        plan = planner.approve(plan.id)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._plans: Dict[str, ImplementationPlan] = {}

    def create_plan(self, architecture, decomposed_tasks: List = None,
                    title: str = "",
                    context: Dict[str, Any] = None) -> ImplementationPlan:
        """Create an implementation plan from architecture and tasks.

        Args:
            architecture: ArchitectureDesign object
            decomposed_tasks: List of DecomposedTask objects (optional)
            title: Plan title
            context: Additional context

        Returns:
            ImplementationPlan with phases and ordered tasks
        """
        arch_title = getattr(architecture, 'title', 'Untitled')
        arch_id = getattr(architecture, 'id', '')

        plan = ImplementationPlan(
            title=title or f"Implementation Plan: {arch_title}",
            architecture_id=arch_id,
            spec_id=getattr(architecture, 'spec_id', ''),
            goal=getattr(architecture, 'goal', ''),
        )

        if decomposed_tasks:
            self._organize_tasks(plan, decomposed_tasks)
        else:
            self._generate_phases(plan, architecture)

        # Calculate total hours
        plan.total_estimated_hours = sum(
            t.estimated_hours for t in plan.tasks
        )

        # Sort tasks by priority within each phase
        self._resolve_dependency_order(plan)

        self._plans[plan.id] = plan

        logger.info(
            "EngineeringPlanner: created plan %s: %d phases, %d tasks, %.1f hours",
            plan.id[:8], len(plan.phases), len(plan.tasks),
            plan.total_estimated_hours,
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.plan_created", {
                "plan_id": plan.id,
                "title": plan.title,
                "phase_count": len(plan.phases),
                "task_count": len(plan.tasks),
                "estimated_hours": plan.total_estimated_hours,
            })

        return plan

    def _organize_tasks(self, plan: ImplementationPlan,
                        decomposed_tasks: List) -> None:
        """Organize decomposed tasks into phases."""
        # Define phases
        phases_order = [
            ("Setup", "Project setup and configuration", ["setup"]),
            ("Core Implementation", "Core module implementation", ["implementation"]),
            ("Integration", "Integration of modules", ["integration"]),
            ("Testing", "Test writing and execution", ["testing"]),
            ("Review", "Code review and refinement", ["review"]),
            ("Documentation", "Documentation generation", ["documentation"]),
            ("Deployment", "Build, package, and deploy", ["deployment"]),
        ]

        for i, (name, desc, keywords) in enumerate(phases_order):
            phase = PlanPhase(
                name=name,
                description=desc,
                order=i,
            )

            for task in decomposed_tasks:
                task_type_lower = getattr(task, 'type', '').lower()
                task_title = getattr(task, 'title', '').lower()

                if any(kw in task_type_lower or kw in task_title for kw in keywords):
                    eng_task = EngineeringTask(
                        title=getattr(task, 'title', ''),
                        description=getattr(task, 'description', ''),
                        phase=name,
                        estimated_hours=getattr(task, 'estimation', None),
                        dependencies=getattr(task, 'dependencies', []),
                        files=getattr(task, 'files_to_modify', []),
                    )
                    if hasattr(task, 'estimation') and task.estimation:
                        eng_task.estimated_hours = task.estimation.estimated_hours
                    if hasattr(task, 'acceptance_criteria'):
                        eng_task.acceptance_criteria = task.acceptance_criteria

                    plan.tasks.append(eng_task)
                    phase.tasks.append(eng_task.id)

            plan.phases.append(phase)

        # Add any remaining tasks to a general phase
        assigned_ids = set()
        for phase in plan.phases:
            assigned_ids.update(phase.tasks)

        unassigned = [
            t for t in decomposed_tasks
            if t.id not in assigned_ids
        ]
        if unassigned:
            general_phase = next(
                (p for p in plan.phases if p.name == "Implementation"),
                None,
            )
            if general_phase:
                for task in unassigned:
                    eng_task = EngineeringTask(
                        title=getattr(task, 'title', ''),
                        description=getattr(task, 'description', ''),
                        phase="Implementation",
                        estimated_hours=getattr(task, 'estimation', None),
                        files=getattr(task, 'files_to_modify', []),
                    )
                    plan.tasks.append(eng_task)
                    general_phase.tasks.append(eng_task.id)

    def _generate_phases(self, plan: ImplementationPlan, architecture) -> None:
        """Generate default phases from architecture modules."""
        phase = PlanPhase(
            name="Implementation",
            description="Implementation of all modules",
            order=0,
        )

        # Create tasks from modules
        if hasattr(architecture, 'modules'):
            for module in architecture.modules:
                module_name = getattr(module, 'name', 'Unnamed')
                task = EngineeringTask(
                    type=TaskType.IMPLEMENTATION,
                    title=f"Implement {module_name}",
                    description=getattr(module, 'description', ''),
                    phase="Implementation",
                    priority=50,
                    estimated_hours=2.0,
                )
                plan.tasks.append(task)
                phase.tasks.append(task.id)
        else:
            task = EngineeringTask(
                type=TaskType.IMPLEMENTATION,
                title="Implement architecture",
                phase="Implementation",
                estimated_hours=4.0,
            )
            plan.tasks.append(task)
            phase.tasks.append(task.id)

        plan.phases.append(phase)

    def _resolve_dependency_order(self, plan: ImplementationPlan) -> None:
        """Resolve task ordering based on dependencies."""
        # Simple topological sort within each phase
        task_map = {t.id: t for t in plan.tasks}

        for task in plan.tasks:
            task.dependencies = [
                dep for dep in task.dependencies if dep in task_map
            ]

    # ------------------------------------------------------------------
    # Plan management
    # ------------------------------------------------------------------

    def approve(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Approve a plan for execution.

        Args:
            plan_id: Plan ID

        Returns:
            Updated plan, or None if not found
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        plan.status = PlanStatus.APPROVED
        plan.updated_at = time.time()

        logger.info("EngineeringPlanner: plan %s approved", plan_id[:8])

        if self._event_bus:
            self._event_bus.emit_async("engineering.plan_approved", {
                "plan_id": plan_id,
                "tasks": len(plan.tasks),
                "hours": plan.total_estimated_hours,
            })

        return plan

    def start(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Start executing a plan."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        plan.status = PlanStatus.IN_PROGRESS
        plan.updated_at = time.time()
        logger.info("EngineeringPlanner: plan %s started", plan_id[:8])

        if self._event_bus:
            self._event_bus.emit_async("engineering.plan_started", {
                "plan_id": plan_id,
            })

        return plan

    def complete(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Mark a plan as completed."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        plan.status = PlanStatus.COMPLETED
        plan.completed_at = time.time()
        plan.updated_at = time.time()

        logger.info("EngineeringPlanner: plan %s completed", plan_id[:8])

        if self._event_bus:
            self._event_bus.emit_async("engineering.plan_completed", {
                "plan_id": plan_id,
            })

        return plan

    def update_task_status(self, plan_id: str, task_id: str,
                           status: str, result: Any = None,
                           error: str = None) -> bool:
        """Update the status of a task within a plan.

        Args:
            plan_id: Plan ID
            task_id: Task ID
            status: New status
            result: Optional result data
            error: Optional error message

        Returns:
            True if successful
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return False

        for task in plan.tasks:
            if task.id == task_id:
                task.status = status
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
                plan.updated_at = time.time()
                self._check_plan_completion(plan)
                return True
        return False

    def _check_plan_completion(self, plan: ImplementationPlan) -> None:
        """Check if all tasks are complete and auto-update plan status."""
        all_terminal = all(
            t.status in ("completed", "failed", "cancelled", "skipped")
            for t in plan.tasks
        )
        if all_terminal and plan.status == PlanStatus.IN_PROGRESS:
            has_failures = any(t.status == "failed" for t in plan.tasks)
            if has_failures:
                plan.status = PlanStatus.FAILED
            else:
                plan.status = PlanStatus.COMPLETED
            plan.completed_at = time.time()
            plan.updated_at = time.time()

    def get_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self, status: Optional[PlanStatus] = None) -> List[ImplementationPlan]:
        """List all plans, optionally filtered by status."""
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans

    def get_ready_tasks(self, plan_id: str) -> List[EngineeringTask]:
        """Get tasks in a plan that are ready to execute.

        Args:
            plan_id: Plan ID

        Returns:
            Tasks whose dependencies are satisfied
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return []

        completed_ids = {
            t.id for t in plan.tasks if t.status == "completed"
        }

        ready = [
            t for t in plan.tasks
            if t.status == "pending"
            and all(dep in completed_ids for dep in t.dependencies)
        ]

        ready.sort(key=lambda t: t.priority)
        return ready

    def get_progress(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get progress summary for a plan."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        total = len(plan.tasks)
        completed = sum(1 for t in plan.tasks if t.status == "completed")
        failed = sum(1 for t in plan.tasks if t.status == "failed")
        in_progress = sum(1 for t in plan.tasks if t.status == "in_progress")
        pending = sum(1 for t in plan.tasks if t.status == "pending")

        hours_completed = sum(
            t.estimated_hours for t in plan.tasks if t.status == "completed"
        )

        return {
            "plan_id": plan.id,
            "title": plan.title,
            "status": plan.status.value,
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "progress_pct": (completed / total * 100) if total > 0 else 0,
            "hours_estimated": plan.total_estimated_hours,
            "hours_completed_estimated": hours_completed,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get planner statistics."""
        return {
            "total_plans": len(self._plans),
            "by_status": {
                status.value: sum(
                    1 for p in self._plans.values() if p.status == status
                )
                for status in PlanStatus
            },
            "total_tasks": sum(len(p.tasks) for p in self._plans.values()),
            "total_hours": sum(p.total_estimated_hours for p in self._plans.values()),
        }
