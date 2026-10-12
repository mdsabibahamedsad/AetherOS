from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import (
    AgentRole,
    Task,
    TaskStatus,
    TaskStep,
    Workflow,
)

logger = logging.getLogger(__name__)

_PLANS_DIR = os.path.expanduser("~/.aetheros/automation/plans")

_AGENT_MAP: dict[str, AgentRole] = {
    "code": AgentRole.DEVELOPER,
    "develop": AgentRole.DEVELOPER,
    "program": AgentRole.DEVELOPER,
    "write": AgentRole.WRITER,
    "document": AgentRole.WRITER,
    "research": AgentRole.RESEARCH,
    "investigate": AgentRole.RESEARCH,
    "analyse": AgentRole.RESEARCH,
    "analyze": AgentRole.RESEARCH,
    "browse": AgentRole.BROWSER,
    "navigate": AgentRole.BROWSER,
    "test": AgentRole.QA,
    "verify": AgentRole.QA,
    "validate": AgentRole.QA,
    "deploy": AgentRole.DEPLOYMENT,
    "release": AgentRole.DEPLOYMENT,
    "security": AgentRole.SECURITY,
    "audit": AgentRole.SECURITY,
    "plan": AgentRole.PLANNER,
    "coordinate": AgentRole.COORDINATOR,
    "remember": AgentRole.MEMORY,
    "store": AgentRole.MEMORY,
}


class TaskPlanner:
    """Decomposes goals into structured, executable workflows.

    Produces a ``Workflow`` whose tasks have estimated durations, assigned
    agent roles, subtask trees, and optional retry fallback paths.  Plans are
    persisted to ``~/.aetheros/automation/plans/`` as JSON.
    """

    def __init__(self) -> None:
        os.makedirs(_PLANS_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def plan(self, goal: str, context: dict | None = None) -> Workflow:
        """Break *goal* into a sequence of tasks and return a ``Workflow``.

        *context* may contain hints such as *domain*, *constraints*,
        *priority* or *previous_attempt* that influence decomposition.
        """
        ctx = context or {}
        now = time.time()

        tasks = await self._decompose_goal(goal, ctx)

        workflow = Workflow(
            id=uuid.uuid4().hex[:12],
            name=f"Plan: {goal[:60]}",
            description=goal,
            tasks=tasks,
            status=TaskStatus.PENDING,
            created_at=now,
        )

        await self._persist(workflow)
        logger.info("Planned workflow %s (%d tasks)", workflow.id, len(tasks))
        return workflow

    async def estimate_duration(self, task: Task) -> float:
        """Return an estimated duration in seconds for *task*.

        Uses a combination of step count, action type, and historical
        averages when available.
        """
        base = max(task.estimated_duration, 10.0)
        step_count = max(len(task.steps), 1)

        action_weight = 1.0
        if task.agent == AgentRole.DEVELOPER:
            action_weight = 2.0
        elif task.agent == AgentRole.RESEARCH:
            action_weight = 1.5
        elif task.agent == AgentRole.BROWSER:
            action_weight = 0.8

        duration = base * step_count * action_weight
        task.estimated_duration = duration
        return duration

    async def assign_agents(self, tasks: list[Task]) -> None:
        """Assign an ``AgentRole`` to each task based on its name / description."""
        for task in tasks:
            text = f"{task.name} {task.description}".lower()
            assigned = AgentRole.COORDINATOR

            for keyword, role in _AGENT_MAP.items():
                if keyword in text:
                    assigned = role
                    break

            task.agent = assigned
            logger.debug("Assigned %s to task %s", assigned.value, task.id)

    async def create_subtasks(self, parent_task: Task, count: int = 3) -> list[Task]:
        """Generate *count* child tasks for *parent_task*.

        Subtasks inherit the parent's agent role and are linked via
        ``parent_task_id`` / ``subtasks``.
        """
        subtasks: list[Task] = []
        now = time.time()

        for i in range(count):
            child = Task(
                id=uuid.uuid4().hex[:12],
                name=f"{parent_task.name} — substep {i + 1}",
                description=f"Subtask {i + 1} of {parent_task.name}",
                status=TaskStatus.PENDING,
                agent=parent_task.agent,
                parent_task_id=parent_task.id,
                created_at=now,
                dependencies=[parent_task.id] if i > 0 else [],
                estimated_duration=parent_task.estimated_duration / count,
            )
            parent_task.subtasks.append(child.id)
            subtasks.append(child)

        logger.debug(
            "Created %d subtasks for task %s", count, parent_task.id,
        )
        return subtasks

    async def add_retry_paths(
        self, workflow: Workflow, retry_limit: int = 3,
    ) -> None:
        """Augment every task in *workflow* with retry metadata.

        Each task receives a ``max_retries`` cap and a fallback step that
        records the retry attempt in its log.
        """
        for task in workflow.tasks:
            task.max_retries = retry_limit
            fallback = TaskStep(
                id=uuid.uuid4().hex[:12],
                name=f"retry-fallback-{task.id}",
                action="retry_fallback",
                params={"max_retries": retry_limit},
                status=TaskStatus.PENDING,
            )
            task.steps.append(fallback)

        logger.debug(
            "Retry paths added (limit=%d) for workflow %s",
            retry_limit, workflow.id,
        )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    async def _decompose_goal(
        self, goal: str, context: dict[str, Any],
    ) -> list[Task]:
        """Break *goal* into concrete tasks.

        In a production build this would call an LLM; here we apply a
        heuristic decomposition based on action verbs found in the goal.
        """
        now = time.time()
        sentences = [s.strip() for s in goal.replace("?", ".").split(".") if s.strip()]
        tasks: list[Task] = []
        seen: set[str] = set()

        for sentence in sentences[:8]:
            slug = sentence.lower().strip()
            if not slug or slug in seen:
                continue
            seen.add(slug)

            task = Task(
                id=uuid.uuid4().hex[:12],
                name=sentence[:80],
                description=sentence,
                status=TaskStatus.PENDING,
                steps=_default_steps(sentence),
                dependencies=[],
                created_at=now,
                estimated_duration=60.0,
            )

            await self.estimate_duration(task)
            tasks.append(task)

        await self.assign_agents(tasks)

        # wire sequential dependencies
        for i in range(1, len(tasks)):
            prev = tasks[i - 1]
            tasks[i].dependencies.append(prev.id)

        return tasks

    async def _persist(self, workflow: Workflow) -> None:
        """Write the workflow plan to disk as JSON."""
        path = os.path.join(_PLANS_DIR, f"{workflow.id}.json")
        data = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "created_at": workflow.created_at,
            "status": workflow.status.value,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "status": t.status.value,
                    "agent": t.agent.value if t.agent else None,
                    "dependencies": t.dependencies,
                    "estimated_duration": t.estimated_duration,
                    "created_at": t.created_at,
                }
                for t in workflow.tasks
            ],
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, data)

    def list_plans(self) -> list[dict[str, Any]]:
        """Return metadata for every stored plan."""
        plans: list[dict[str, Any]] = []
        if not os.path.isdir(_PLANS_DIR):
            return plans
        for name in sorted(os.listdir(_PLANS_DIR), reverse=True):
            if name.endswith(".json"):
                path = os.path.join(_PLANS_DIR, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    plans.append({
                        "id": data.get("id"),
                        "name": data.get("name", ""),
                        "created_at": data.get("created_at", 0),
                        "status": data.get("status", "unknown"),
                        "task_count": len(data.get("tasks", [])),
                    })
                except Exception:
                    logger.warning("Failed to read plan %s", path)
        return plans

    def load_plan(self, plan_id: str) -> Workflow | None:
        """Rehydrate a previously persisted plan."""
        path = os.path.join(_PLANS_DIR, f"{plan_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            logger.exception("Failed to load plan %s", plan_id)
            return None

        tasks = [
            Task(
                id=t["id"],
                name=t["name"],
                description=t.get("description", ""),
                status=TaskStatus(t["status"]) if t.get("status") else TaskStatus.PENDING,
                agent=AgentRole(t["agent"]) if t.get("agent") else AgentRole.COORDINATOR,
                dependencies=t.get("dependencies", []),
                estimated_duration=t.get("estimated_duration", 0.0),
                created_at=t.get("created_at", 0.0),
            )
            for t in data.get("tasks", [])
        ]

        return Workflow(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            tasks=tasks,
            status=TaskStatus(data["status"]) if data.get("status") else TaskStatus.PENDING,
            created_at=data.get("created_at", 0.0),
        )


# ------------------------------------------------------------------
# module-level helpers
# ------------------------------------------------------------------

def _default_steps(sentence: str) -> list[TaskStep]:
    """Generate placeholder steps for a sentence-based task."""
    return [
        TaskStep(
            id=uuid.uuid4().hex[:12],
            name="analyse",
            action="analyse",
            params={"input": sentence},
            status=TaskStatus.PENDING,
        ),
        TaskStep(
            id=uuid.uuid4().hex[:12],
            name="execute",
            action="execute",
            params={"input": sentence},
            status=TaskStatus.PENDING,
        ),
        TaskStep(
            id=uuid.uuid4().hex[:12],
            name="verify",
            action="verify",
            params={"input": sentence},
            status=TaskStatus.PENDING,
        ),
    ]


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
