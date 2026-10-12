"""
Task Planning Engine for AetherOS Intelligence Engine.

Implements:
    - Task Planning with dependency resolution
    - Hierarchical Planning (goal → subgoals → tasks)
    - Goal Decomposition
    - Long-term Task Execution with status tracking
    - Plan persistence and history
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    parent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    result: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "parent_id": self.parent_id,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "result": self.result[:200] if self.result else "",
            "error": self.error[:200] if self.error else "",
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Plan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    description: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    tasks: Dict[str, Task] = field(default_factory=dict)
    root_task_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "description": self.description[:200],
            "status": self.status.value,
            "priority": self.priority.value,
            "task_count": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "in_progress_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
            "confidence": self.confidence,
        }


class PlanningEngine:
    """Hierarchical task planning engine.

    Breaks down goals into hierarchical plans, manages task dependencies,
    tracks execution status, and persists plans across sessions.
    """

    def __init__(self) -> None:
        self._plans: Dict[str, Plan] = {}
        self._active_plan_id: Optional[str] = None
        self._store_path = get_aetheros_home() / "intelligence" / "plans"
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._load_plans()

    # ------------------------------------------------------------------
    # Plan CRUD
    # ------------------------------------------------------------------

    def create_plan(self, goal: str, description: str = "",
                    context: Dict[str, Any] = None,
                    priority: str = "medium") -> Dict[str, Any]:
        """Create a new plan and decompose it into tasks."""
        plan = Plan(
            goal=goal,
            description=description,
            priority=Priority(priority),
            context=context or {},
        )
        self._decompose_goal(plan)
        self._plans[plan.id] = plan
        self._active_plan_id = plan.id
        self._save_plan(plan)
        logger.info("Created plan %s: %s", plan.id, goal[:60])
        return plan.to_dict()

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        result = plan.to_dict()
        result["tasks"] = [t.to_dict() for t in sorted(
            plan.tasks.values(), key=lambda t: t.created_at
        )]
        result["goal"] = plan.goal
        result["description"] = plan.description
        return result

    def list_plans(self, include_completed: bool = False,
                   limit: int = 10) -> List[Dict[str, Any]]:
        plans = sorted(self._plans.values(), key=lambda p: p.updated_at, reverse=True)
        if not include_completed:
            plans = [p for p in plans if p.status not in (
                PlanStatus.COMPLETED, PlanStatus.CANCELLED, PlanStatus.FAILED
            )]
        return [p.to_dict() for p in plans[:limit]]

    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        for key, value in updates.items():
            if hasattr(plan, key) and key not in ("id", "created_at", "tasks"):
                setattr(plan, key, value)
        plan.updated_at = time.time()
        self._save_plan(plan)
        return plan.to_dict()

    def delete_plan(self, plan_id: str) -> bool:
        plan = self._plans.pop(plan_id, None)
        if plan:
            self._delete_plan_file(plan_id)
            if self._active_plan_id == plan_id:
                self._active_plan_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def get_next_tasks(self, plan_id: str, agent: str = "",
                       limit: int = 5) -> List[Dict[str, Any]]:
        """Get the next ready-to-execute tasks for a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []

        ready = []
        for task in plan.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if agent and task.assigned_agent and task.assigned_agent != agent:
                continue
            deps_met = all(
                plan.tasks.get(dep_id, Task()).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_met:
                ready.append(task)

        ready.sort(key=lambda t: (
            list(Priority).index(t.priority),
            t.estimated_hours,
        ))
        return [t.to_dict() for t in ready[:limit]]

    def update_task(self, plan_id: str, task_id: str,
                    updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        task = plan.tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if key == "status":
                task.status = TaskStatus(value)
                if task.status == TaskStatus.IN_PROGRESS:
                    task.started_at = time.time()
                    plan.started_at = plan.started_at or time.time()
                    if plan.status == PlanStatus.DRAFT:
                        plan.status = PlanStatus.IN_PROGRESS
                elif task.status == TaskStatus.COMPLETED:
                    task.completed_at = time.time()
                elif task.status == TaskStatus.FAILED:
                    task.completed_at = time.time()
            elif hasattr(task, key):
                setattr(task, key, value)

        plan.updated_at = time.time()
        self._update_plan_status(plan)
        self._save_plan(plan)
        return task.to_dict()

    def add_task(self, plan_id: str, title: str,
                 description: str = "",
                 parent_id: str = None,
                 dependencies: List[str] = None,
                 priority: str = "medium",
                 assigned_agent: str = "") -> Optional[Dict[str, Any]]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        task = Task(
            title=title,
            description=description,
            parent_id=parent_id,
            dependencies=dependencies or [],
            priority=Priority(priority),
            assigned_agent=assigned_agent,
        )
        plan.tasks[task.id] = task
        if not parent_id:
            plan.root_task_ids.append(task.id)
        plan.updated_at = time.time()
        self._save_plan(plan)
        return task.to_dict()

    # ------------------------------------------------------------------
    # Goal decomposition
    # ------------------------------------------------------------------

    def _decompose_goal(self, plan: Plan) -> None:
        """Decompose a goal into hierarchical tasks."""
        plan.status = PlanStatus.ACTIVE
        goal = plan.goal

        decomposition_keywords = {
            "analyze": ["Research requirements", "Identify constraints",
                        "Document assumptions", "Review existing solutions"],
            "build": ["Design architecture", "Set up environment",
                      "Implement core", "Add integration tests",
                      "Create documentation"],
            "deploy": ["Prepare infrastructure", "Configure CI/CD",
                       "Run staging tests", "Deploy to production",
                       "Monitor rollout"],
            "migrate": ["Audit current state", "Plan migration strategy",
                        "Create backup", "Execute migration",
                        "Verify integrity"],
            "refactor": ["Identify code sections", "Write test coverage",
                         "Refactor incrementally", "Verify behavior unchanged",
                         "Update documentation"],
            "research": ["Define research questions", "Gather sources",
                         "Analyze findings", "Synthesize conclusions",
                         "Document results"],
            "optimize": ["Profile current performance", "Identify bottlenecks",
                         "Implement optimizations", "Measure improvements",
                         "Document changes"],
            "learn": ["Define learning objectives", "Find resources",
                      "Practice hands-on", "Build reference project",
                      "Document key takeaways"],
            "write": ["Outline content", "Draft sections",
                      "Review and edit", "Format and publish",
                      "Gather feedback"],
            "test": ["Review requirements", "Design test cases",
                     "Set up test environment", "Execute test suite",
                     "Report results"],
            "secure": ["Audit security posture", "Identify vulnerabilities",
                       "Implement fixes", "Verify remediation",
                       "Update security docs"],
            "automate": ["Identify repetitive steps", "Design automation",
                         "Implement pipeline", "Test automation",
                         "Document workflow"],
            "integrate": ["Map integration points", "Design API contracts",
                          "Implement connectors", "Test end-to-end",
                          "Monitor integration"],
            "design": ["Gather requirements", "Explore alternatives",
                       "Create prototype", "Review design",
                       "Finalize specifications"],
            "fix": ["Reproduce issue", "Identify root cause",
                    "Implement fix", "Add regression test",
                    "Verify in staging"],
        }

        goal_lower = goal.lower()
        matched = False
        for keyword, steps in decomposition_keywords.items():
            if keyword in goal_lower:
                matched = True
                for step_text in steps:
                    task = Task(
                        title=step_text,
                        priority=Priority.HIGH if "core" in step_text.lower() or "implement" in step_text.lower()
                                    else Priority.MEDIUM,
                    )
                    plan.tasks[task.id] = task
                    plan.root_task_ids.append(task.id)
                break

        if not matched:
            generic_steps = [
                "Understand the goal and requirements",
                "Plan the approach",
                "Execute the plan",
                "Verify the results",
                "Review and refine",
            ]
            for step_text in generic_steps:
                task = Task(title=step_text)
                plan.tasks[task.id] = task
                plan.root_task_ids.append(task.id)

        self._resolve_dependencies(plan)

    def _resolve_dependencies(self, plan: Plan) -> None:
        """Set up dependency chain between tasks."""
        task_ids = plan.root_task_ids[:]
        for i in range(len(task_ids)):
            if i > 0:
                task = plan.tasks.get(task_ids[i])
                if task:
                    task.dependencies.append(task_ids[i - 1])

    def _update_plan_status(self, plan: Plan) -> None:
        """Update plan status based on task statuses."""
        if not plan.tasks:
            return

        all_completed = all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
            for t in plan.tasks.values()
        )
        any_failed = any(
            t.status == TaskStatus.FAILED for t in plan.tasks.values()
        )
        any_in_progress = any(
            t.status == TaskStatus.IN_PROGRESS for t in plan.tasks.values()
        )

        if all_completed:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = time.time()
        elif any_failed:
            plan.status = PlanStatus.FAILED
            plan.completed_at = time.time()
        elif any_in_progress:
            plan.status = PlanStatus.IN_PROGRESS
            plan.started_at = plan.started_at or time.time()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_next(self, plan_id: str, agent: str = "",
                     auto_complete: bool = False) -> Dict[str, Any]:
        """Execute the next ready task in a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": f"Plan {plan_id} not found"}

        if plan.status in (PlanStatus.COMPLETED, PlanStatus.CANCELLED, PlanStatus.FAILED):
            return {"error": f"Plan is already {plan.status.value}"}

        next_tasks = self.get_next_tasks(plan_id, agent, limit=1)
        if not next_tasks:
            remaining = [
                t.to_dict() for t in plan.tasks.values()
                if t.status == TaskStatus.PENDING
            ]
            if not remaining:
                plan.status = PlanStatus.COMPLETED
                plan.completed_at = time.time()
                self._save_plan(plan)
                return {"message": "All tasks completed", "plan_completed": True}
            return {
                "message": "No ready tasks (dependencies not met)",
                "blocked_tasks": [t.to_dict() for t in plan.tasks.values()
                                  if t.status == TaskStatus.PENDING][:5],
            }

        task_data = next_tasks[0]
        task_id = task_data["id"]
        self.update_task(plan_id, task_id, {"status": "in_progress"})

        if auto_complete:
            self.update_task(plan_id, task_id, {
                "status": "completed",
                "result": "Completed automatically",
            })

        return {
            "task": task_data,
            "plan_id": plan_id,
            "remaining": sum(1 for t in plan.tasks.values()
                            if t.status == TaskStatus.PENDING),
        }

    def get_plan_status(self, plan_id: str = None) -> Dict[str, Any]:
        """Get execution status of a plan or the active plan."""
        plan_id = plan_id or self._active_plan_id
        if not plan_id:
            return {"error": "No active plan"}
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": f"Plan {plan_id} not found"}

        total = len(plan.tasks)
        completed = sum(1 for t in plan.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks.values() if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in plan.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in plan.tasks.values() if t.status == TaskStatus.PENDING)
        blocked = sum(1 for t in plan.tasks.values() if t.status == TaskStatus.BLOCKED)

        progress = (completed / total * 100) if total > 0 else 0

        return {
            "plan_id": plan_id,
            "goal": plan.goal,
            "status": plan.status.value,
            "progress": round(progress, 1),
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "blocked": blocked,
            "elapsed": round(time.time() - (plan.started_at or plan.created_at), 1),
            "confidence": plan.confidence,
        }

    def refine_plan(self, plan_id: str, feedback: str) -> Optional[Dict[str, Any]]:
        """Refine a plan based on feedback."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.metadata["feedback"] = plan.metadata.get("feedback", []) + [feedback]
        plan.updated_at = time.time()
        self._save_plan(plan)
        return plan.to_dict()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_plan(self, plan: Plan) -> None:
        path = self._store_path / f"{plan.id}.json"
        data = {
            "id": plan.id,
            "goal": plan.goal,
            "description": plan.description,
            "status": plan.status.value,
            "priority": plan.priority.value,
            "tasks": {tid: task.to_dict() for tid, task in plan.tasks.items()},
            "root_task_ids": plan.root_task_ids,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "context": plan.context,
            "tags": plan.tags,
            "confidence": plan.confidence,
            "metadata": plan.metadata,
        }
        path.write_text(json.dumps(data, indent=2, default=str))

    def _load_plans(self) -> None:
        if not self._store_path.exists():
            return
        for path in self._store_path.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                tasks = {}
                for tid, tdata in data.get("tasks", {}).items():
                    task = Task(
                        id=tdata.get("id", tid),
                        title=tdata.get("title", ""),
                        description=tdata.get("description", ""),
                        status=TaskStatus(tdata.get("status", "pending")),
                        priority=Priority(tdata.get("priority", "medium")),
                        parent_id=tdata.get("parent_id"),
                        dependencies=tdata.get("dependencies", []),
                        assigned_agent=tdata.get("assigned_agent", ""),
                        estimated_hours=tdata.get("estimated_hours", 0.0),
                        actual_hours=tdata.get("actual_hours", 0.0),
                        result=tdata.get("result", ""),
                        error=tdata.get("error", ""),
                        created_at=tdata.get("created_at", 0.0),
                        started_at=tdata.get("started_at"),
                        completed_at=tdata.get("completed_at"),
                    )
                    tasks[tid] = task

                plan = Plan(
                    id=data["id"],
                    goal=data.get("goal", ""),
                    description=data.get("description", ""),
                    status=PlanStatus(data.get("status", "draft")),
                    priority=Priority(data.get("priority", "medium")),
                    tasks=tasks,
                    root_task_ids=data.get("root_task_ids", []),
                    created_at=data.get("created_at", 0.0),
                    updated_at=data.get("updated_at", 0.0),
                    started_at=data.get("started_at"),
                    completed_at=data.get("completed_at"),
                    context=data.get("context", {}),
                    tags=data.get("tags", []),
                    confidence=data.get("confidence", 0.0),
                    metadata=data.get("metadata", {}),
                )
                self._plans[plan.id] = plan
            except Exception as exc:
                logger.warning("Failed to load plan %s: %s", path.name, exc)

    def _delete_plan_file(self, plan_id: str) -> None:
        path = self._store_path / f"{plan_id}.json"
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._plans)
        active = sum(1 for p in self._plans.values()
                     if p.status in (PlanStatus.ACTIVE, PlanStatus.IN_PROGRESS))
        completed = sum(1 for p in self._plans.values()
                        if p.status == PlanStatus.COMPLETED)
        total_tasks = sum(len(p.tasks) for p in self._plans.values())
        completed_tasks = sum(
            sum(1 for t in p.tasks.values() if t.status == TaskStatus.COMPLETED)
            for p in self._plans.values()
        )

        return {
            "total_plans": total,
            "active_plans": active,
            "completed_plans": completed,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "active_plan_id": self._active_plan_id,
            "store_path": str(self._store_path),
        }
