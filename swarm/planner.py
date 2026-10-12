"""
Swarm Planner — decomposes high-level goals into multi-agent execution plans.

The swarm planner extends the kernel planner with multi-agent awareness.
Given a goal, it produces a SwarmPlan containing AgentTasks that can be
assigned to different agent types based on required capabilities.

Supports parallel tasks, dependency chains, priority levels,
and capability-based task requirements.
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

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class AgentTaskStatus(enum.Enum):
    """Status of a single agent task within a swarm plan."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class AgentTask:
    """A single task for an agent within a swarm plan.

    Attributes:
        id: Unique task ID
        description: Human-readable description
        goal: The goal/objective for the agent
        required_capabilities: Set of capabilities the agent must have
        preferred_agent_type: Preferred agent type (e.g. "coding-agent")
        dependencies: Task IDs that must complete first
        priority: Task priority (lower = higher priority)
        max_retries: Maximum retry attempts on failure
        timeout_seconds: Max execution time per attempt
        status: Current task status
        assigned_to: Agent type or ID this is assigned to
        context: Additional context for the agent
        result: Execution result
        error: Error message if failed
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    goal: str = ""
    required_capabilities: Set[str] = field(default_factory=set)
    preferred_agent_type: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    priority: int = 50
    max_retries: int = 0
    timeout_seconds: float = 600.0
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    assigned_to: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmPlan:
    """A multi-agent execution plan produced by the swarm planner.

    Attributes:
        id: Unique plan ID
        goal: The original user goal
        tasks: List of AgentTasks
        status: Current plan status
        context: Shared context for the plan
        created_at: Creation timestamp
        completed_at: Completion timestamp
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    tasks: List[AgentTask] = field(default_factory=list)
    status: str = "pending"  # pending, approved, in_progress, completed, failed, cancelled
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmPlanner:
    """Multi-agent planning engine for the swarm.

    Decomposes high-level user goals into structured plans with tasks
    that can be assigned to different agent types based on capability
    requirements.

    Usage:
        planner = SwarmPlanner(event_bus)
        plan = planner.decompose_goal("Build a web app with user auth")
        # plan.tasks contains tasks like:
        #   - "Design database schema" (requires: analysis)
        #   - "Implement user authentication" (requires: coding)
        #   - "Write frontend login page" (requires: coding)
        #   - "Test authentication flow" (requires: testing)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._plans: Dict[str, SwarmPlan] = {}
        # Registered decomposition strategies
        self._strategies: List[Callable[[str], Optional[List[AgentTask]]]] = []
        # Load default strategy
        self._strategies.append(self._default_strategy)

    # ------------------------------------------------------------------
    # Plan creation
    # ------------------------------------------------------------------

    def decompose_goal(self, goal: str,
                       context: Dict[str, Any] = None,
                       metadata: Dict[str, Any] = None) -> SwarmPlan:
        """Decompose a high-level goal into a multi-agent execution plan.

        Runs registered decomposition strategies to generate tasks.
        """
        plan = SwarmPlan(
            goal=goal,
            context=context or {},
            metadata=metadata or {},
        )

        # Run strategies to generate tasks
        all_tasks: List[AgentTask] = []
        for strategy in self._strategies:
            try:
                tasks = strategy(goal, context or {})
                if tasks:
                    all_tasks.extend(tasks)
            except Exception as exc:
                logger.warning("SwarmPlanner: strategy failed: %s", exc)

        if all_tasks:
            plan.tasks = self._deduplicate_tasks(all_tasks)

        with self._lock:
            self._plans[plan.id] = plan

        logger.info(
            "SwarmPlanner: created plan %s with %d tasks for: %s",
            plan.id, len(plan.tasks), goal[:80],
        )

        if self._event_bus:
            self._event_bus.emit_async("swarm.plan_created", {
                "plan_id": plan.id,
                "goal": goal[:200],
                "task_count": len(plan.tasks),
            })

        return plan

    def get_plan(self, plan_id: str) -> Optional[SwarmPlan]:
        """Get a plan by ID."""
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self, status: Optional[str] = None) -> List[SwarmPlan]:
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
        plan.status = "approved"
        logger.info("SwarmPlanner: plan %s approved", plan_id)
        return True

    def start_plan(self, plan_id: str) -> bool:
        """Mark a plan as in progress."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = "in_progress"
        if self._event_bus:
            self._event_bus.emit_async("swarm.plan_started", {
                "plan_id": plan_id,
                "goal": plan.goal[:200],
            })
        return True

    def complete_plan(self, plan_id: str, result: Any = None) -> bool:
        """Mark a plan as completed."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = "completed"
        plan.completed_at = time.time()
        plan.metadata["result"] = result
        logger.info("SwarmPlanner: plan %s completed", plan_id)
        return True

    def fail_plan(self, plan_id: str, error: str) -> bool:
        """Mark a plan as failed."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = "failed"
        plan.completed_at = time.time()
        plan.metadata["error"] = error
        logger.error("SwarmPlanner: plan %s failed: %s", plan_id, error)
        return True

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a plan and all its tasks."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        plan.status = "cancelled"
        plan.completed_at = time.time()
        for task in plan.tasks:
            if task.status in (AgentTaskStatus.PENDING, AgentTaskStatus.ASSIGNED,
                             AgentTaskStatus.RUNNING):
                task.status = AgentTaskStatus.CANCELLED
        if self._event_bus:
            self._event_bus.emit_async("swarm.plan_cancelled", {"plan_id": plan_id})
        logger.info("SwarmPlanner: plan %s cancelled", plan_id)
        return True

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def add_task(self, plan_id: str, task: AgentTask) -> bool:
        """Add a task to an existing plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        with self._lock:
            plan.tasks.append(task)
        return True

    def get_ready_tasks(self, plan_id: str) -> List[AgentTask]:
        """Get tasks whose dependencies are all satisfied (ready to assign)."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return []

        completed_ids = {
            t.id for t in plan.tasks
            if t.status == AgentTaskStatus.COMPLETED
        }

        ready = []
        for task in plan.tasks:
            if task.status != AgentTaskStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in task.dependencies):
                ready.append(task)

        ready.sort(key=lambda t: (t.priority, t.id))
        return ready

    def update_task_status(self, plan_id: str, task_id: str,
                           status: AgentTaskStatus,
                           result: Any = None,
                           error: str = None) -> bool:
        """Update the status of a single task in a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return False

        for task in plan.tasks:
            if task.id == task_id:
                task.status = status
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error

                if self._event_bus:
                    self._event_bus.emit_async("swarm.task_status_changed", {
                        "plan_id": plan_id,
                        "task_id": task_id,
                        "status": status.value,
                        "description": task.description,
                    })

                self._check_plan_completion(plan_id)
                return True
        return False

    def _check_plan_completion(self, plan_id: str) -> None:
        """Auto-complete or fail a plan when all tasks are done."""
        plan = self.get_plan(plan_id)
        if plan is None or plan.status in ("completed", "failed", "cancelled"):
            return

        all_terminal = True
        has_failure = False
        has_cancelled = False

        for task in plan.tasks:
            if task.status == AgentTaskStatus.FAILED:
                has_failure = True
            elif task.status == AgentTaskStatus.CANCELLED:
                has_cancelled = True
            elif task.status not in (AgentTaskStatus.COMPLETED,
                                   AgentTaskStatus.FAILED,
                                   AgentTaskStatus.CANCELLED,
                                   AgentTaskStatus.SKIPPED):
                all_terminal = False

        if all_terminal:
            if has_failure:
                self.fail_plan(plan_id, "One or more tasks failed")
            elif has_cancelled:
                self.cancel_plan(plan_id)
            else:
                self.complete_plan(plan_id)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def register_strategy(
        self, strategy: Callable[[str, Dict[str, Any]], Optional[List[AgentTask]]]
    ) -> None:
        """Register a decomposition strategy.

        Strategies receive (goal, context) and return a list of AgentTasks
        or None if they cannot handle the goal.
        """
        with self._lock:
            self._strategies.append(strategy)
        logger.debug("SwarmPlanner: registered decomposition strategy")

    def _default_strategy(self, goal: str,
                          context: Dict[str, Any]) -> List[AgentTask]:
        """Default decomposition: analyze, plan, research, implement, review.

        Creates a generic multi-agent workflow for any goal:
          1. Analyze the goal (planning/analysis capability)
          2. Research relevant information (research capability)
          3. Implement the solution (coding capability)
          4. Test the implementation (testing capability)
          5. Review the result (review capability)
        """
        return [
            AgentTask(
                description=f"Analyze goal and create execution plan: {goal[:100]}",
                goal=f"Analyze this goal and create a detailed execution plan: {goal}",
                required_capabilities={"planning", "analysis", "decomposition"},
                preferred_agent_type="planning-agent",
                priority=10,
            ),
            AgentTask(
                description=f"Research relevant information for: {goal[:100]}",
                goal=f"Research and gather relevant information needed for: {goal}",
                required_capabilities={"research", "web_search"},
                preferred_agent_type="research-agent",
                priority=30,
            ),
            AgentTask(
                description=f"Implement solution for: {goal[:100]}",
                goal=f"Implement the solution for: {goal}",
                required_capabilities={"coding"},
                preferred_agent_type="coding-agent",
                priority=40,
            ),
            AgentTask(
                description=f"Test the implementation for: {goal[:100]}",
                goal=f"Test the implementation thoroughly: {goal}",
                required_capabilities={"testing", "validation"},
                preferred_agent_type="testing-agent",
                priority=50,
            ),
            AgentTask(
                description=f"Review and finalize: {goal[:100]}",
                goal=f"Review all work done and provide a final summary for: {goal}",
                required_capabilities={"review", "quality", "audit"},
                preferred_agent_type="review-agent",
                priority=60,
            ),
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_tasks(tasks: List[AgentTask]) -> List[AgentTask]:
        """Remove duplicate tasks by description."""
        seen: Set[str] = set()
        unique = []
        for task in tasks:
            key = task.description.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(task)
        return unique

    def update_dependencies(self, plan_id: str,
                            task_deps: Dict[str, List[str]]) -> bool:
        """Update dependency relationships between tasks.

        Args:
            plan_id: The plan ID
            task_deps: Mapping of task_id -> list of dependency task IDs
        """
        plan = self.get_plan(plan_id)
        if plan is None:
            return False

        task_ids = {t.id for t in plan.tasks}
        for task_id, deps in task_deps.items():
            if task_id not in task_ids:
                continue
            for task in plan.tasks:
                if task.id == task_id:
                    task.dependencies = [d for d in deps if d in task_ids]
                    break
        return True

    def get_progress(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get progress summary for a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return None

        total = len(plan.tasks)
        completed = sum(1 for t in plan.tasks if t.status == AgentTaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == AgentTaskStatus.FAILED)
        running = sum(1 for t in plan.tasks if t.status == AgentTaskStatus.RUNNING)
        pending = sum(
            1 for t in plan.tasks
            if t.status in (AgentTaskStatus.PENDING, AgentTaskStatus.ASSIGNED)
        )

        return {
            "plan_id": plan.id,
            "goal": plan.goal[:100],
            "status": plan.status,
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "progress_pct": (completed / total * 100) if total > 0 else 0,
        }

    def cleanup(self) -> int:
        """Remove all plans. Returns count removed."""
        with self._lock:
            count = len(self._plans)
            self._plans.clear()
        return count
