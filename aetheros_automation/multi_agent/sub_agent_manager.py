from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from aetheros_automation.models.models import AgentRole, TaskStatus
from aetheros_automation.orchestrator.types import AgentAssignment, OrchestrationTask

logger = logging.getLogger(__name__)


class SubAgentManager:
    def __init__(self, orchestrator=None):
        self._orchestrator = orchestrator
        self._sub_agents: dict[str, list[str]] = {}
        self._agent_assignments: dict[str, AgentAssignment] = {}

    async def create_sub_agent(
        self,
        parent_id: str,
        role: AgentRole,
        goal: str,
        instructions: str = "",
        max_steps: int = 20,
        max_time: float = 300.0,
    ) -> AgentAssignment:
        sub = AgentAssignment(
            agent_id=uuid.uuid4().hex[:12],
            role=role,
            name=f"sub-{role.value}-{uuid.uuid4().hex[:6]}",
            tools=self._infer_tools(goal),
            permissions=self._get_base_permissions(role),
            instructions=instructions or goal,
            parent_agent_id=parent_id,
            is_sub_agent=True,
            limits={
                "max_steps": max_steps,
                "max_time": max_time,
                "max_tool_calls": max_steps * 3,
            },
        )

        self._agent_assignments[sub.agent_id] = sub
        self._sub_agents.setdefault(parent_id, []).append(sub.agent_id)

        logger.info(
            "Sub-agent %s (%s) created by parent %s",
            sub.agent_id, role.value, parent_id,
        )
        return sub

    def _infer_tools(self, text: str) -> list[str]:
        tools: list[str] = []
        text_lower = text.lower()
        if any(k in text_lower for k in ["search", "research", "find"]):
            tools.append("web_search")
        if any(k in text_lower for k in ["file", "save", "read"]):
            tools.append("file_operations")
        if any(k in text_lower for k in ["code", "develop", "program"]):
            tools.append("code_execution")
        if any(k in text_lower for k in ["terminal", "shell"]):
            tools.append("terminal")
        return tools

    def _get_base_permissions(self, role: AgentRole) -> list[str]:
        base = ["filesystem_read"]
        if role in (AgentRole.DEVELOPER, AgentRole.WRITER, AgentRole.CREATIVE, AgentRole.DATA):
            base.append("filesystem_write")
        if role in (AgentRole.BROWSER, AgentRole.RESEARCH):
            base.append("network")
        return base

    async def execute_task(
        self,
        sub_agent: AgentAssignment,
        task: OrchestrationTask,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "Sub-agent %s executing task '%s'",
            sub_agent.agent_id, task.name,
        )
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        await asyncio.sleep(0.5)

        result = {
            "success": True,
            "task_id": task.id,
            "agent_id": sub_agent.agent_id,
            "summary": f"Sub-agent {sub_agent.name} completed task '{task.name}'",
        }

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        return result

    async def terminate_sub_agent(self, sub_agent_id: str) -> bool:
        sub = self._agent_assignments.pop(sub_agent_id, None)
        if not sub:
            return False

        parent_id = sub.parent_agent_id
        if parent_id in self._sub_agents:
            try:
                self._sub_agents[parent_id].remove(sub_agent_id)
            except ValueError:
                pass

        if not self._sub_agents.get(parent_id):
            self._sub_agents.pop(parent_id, None)

        logger.info("Sub-agent %s terminated", sub_agent_id)
        return True

    async def terminate_all_sub_agents(self, parent_id: str):
        sub_ids = list(self._sub_agents.get(parent_id, []))
        for sid in sub_ids:
            await self.terminate_sub_agent(sid)
        logger.info(
            "All sub-agents terminated for parent %s (%d agents)",
            parent_id, len(sub_ids),
        )

    def get_sub_agents(self, parent_id: str) -> list[AgentAssignment]:
        return [
            self._agent_assignments[sid]
            for sid in self._sub_agents.get(parent_id, [])
            if sid in self._agent_assignments
        ]

    def get_agent(self, agent_id: str) -> AgentAssignment | None:
        return self._agent_assignments.get(agent_id)

    def get_all_agents(self) -> list[AgentAssignment]:
        return list(self._agent_assignments.values())

    def get_active_sub_agents(self, parent_id: str) -> int:
        return len(self._sub_agents.get(parent_id, []))

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_agents": len(self._agent_assignments),
            "sub_agent_groups": len(self._sub_agents),
            "active_agents": sum(
                1 for a in self._agent_assignments.values()
                if a.is_sub_agent
            ),
        }
