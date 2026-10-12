from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task, TaskStatus

from aetheros_automation.agents.registry import AgentRegistry

logger = logging.getLogger(__name__)

_SUBTASK_ROUTING: dict[str, AgentRole] = {
    "plan": AgentRole.PLANNER,
    "code": AgentRole.DEVELOPER,
    "develop": AgentRole.DEVELOPER,
    "fix": AgentRole.DEVELOPER,
    "browse": AgentRole.BROWSER,
    "scrape": AgentRole.BROWSER,
    "research": AgentRole.RESEARCH,
    "search": AgentRole.RESEARCH,
    "write": AgentRole.WRITER,
    "document": AgentRole.WRITER,
    "test": AgentRole.QA,
    "qa": AgentRole.QA,
    "deploy": AgentRole.DEPLOYMENT,
    "release": AgentRole.DEPLOYMENT,
    "security": AgentRole.SECURITY,
    "audit": AgentRole.SECURITY,
    "remember": AgentRole.MEMORY,
    "memory": AgentRole.MEMORY,
}


def _infer_role_from_description(description: str) -> AgentRole:
    lower = description.lower()
    for keyword, role in _SUBTASK_ROUTING.items():
        if keyword in lower:
            return role
    return AgentRole.DEVELOPER


class CoordinatorAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.COORDINATOR

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("Coordinator processing task: %s", task.name)

        if task.steps:
            return await self._execute_with_steps(task, ctx)

        return await self._delegate(task, ctx)

    async def _execute_with_steps(self, task: Task, context: dict) -> str:
        results: list[str] = []
        for step in task.steps:
            step.status = TaskStatus.RUNNING
            step.started_at = time.time()

            sub_task = Task(
                id=str(uuid.uuid4()),
                name=step.name,
                description=step.action,
                agent=_infer_role_from_description(step.action),
                parent_task_id=task.id,
                metadata=dict(step.params or {}),
            )

            try:
                result = await self._delegate(sub_task, context)
                step.result = result
                step.status = TaskStatus.COMPLETED
                results.append(result)
            except Exception as e:
                step.status = TaskStatus.FAILED
                step.error = str(e)
                logger.error("Step '%s' failed: %s", step.name, e)
                raise

            step.completed_at = time.time()

        return "\n".join(results)

    async def _delegate(self, task: Task, context: dict) -> str:
        target_role = task.agent
        if target_role == AgentRole.COORDINATOR:
            target_role = _infer_role_from_description(task.description)

        logger.info(
            "Delegating task '%s' to %s", task.name, target_role.value
        )

        agent_cls = AgentRegistry.get(target_role)
        agent = agent_cls()
        ctx = {
            "parent_task_id": task.id,
            "assigned_to": target_role.value,
            **context,
        }
        return await agent.execute(task, ctx)

    async def execute_plan(
        self,
        plan: list[dict],
        global_context: dict | None = None,
    ) -> list[dict]:
        ctx = global_context or {}
        results: list[dict] = []

        for step in plan:
            desc = step.get("description", "")
            role = AgentRole(step.get("agent", _infer_role_from_description(desc).value))
            sub_task = Task(
                id=str(uuid.uuid4()),
                name=step.get("name", desc[:50]),
                description=desc,
                agent=role,
                dependencies=step.get("dependencies", []),
                estimated_duration=step.get("estimated_duration", 0),
            )

            try:
                result = await self._delegate(sub_task, ctx)
                results.append({"step": step, "status": "completed", "result": result})
            except Exception as e:
                results.append({"step": step, "status": "failed", "error": str(e)})
                raise

        return results


AgentRegistry.register(AgentRole.COORDINATOR, CoordinatorAgent)
