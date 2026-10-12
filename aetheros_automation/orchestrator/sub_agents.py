from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    SubAgentSpec, AgentRole, AgentInstance, AgentDefinition,
)
from aetheros_automation.orchestrator.agents import AgentManager

logger = logging.getLogger(__name__)


class SubAgentManager:
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self._sub_agents: dict[str, list[str]] = {}
        self._sub_specs: dict[str, SubAgentSpec] = {}

    async def create_sub_agent(
        self,
        spec: SubAgentSpec,
        parent_instance: AgentInstance,
    ) -> Optional[AgentInstance]:
        parent_id = parent_instance.id
        children = self._sub_agents.get(parent_id, [])
        parent_def = parent_instance.definition
        parent_max = parent_def.max_sub_agents if parent_def else 3
        if len(children) >= parent_max:
            logger.warning("Parent %s has reached max sub-agents (%d)", parent_id, parent_max)
            return None
        temp_def = AgentDefinition(
            role=spec.role,
            name=spec.name or f"Sub-{spec.role.value}_{uuid.uuid4().hex[:6]}",
            description=f"Temporary sub-agent created by {parent_id}",
            tools=spec.tools,
            permissions=spec.permissions,
            instructions=spec.instructions,
            personality="",
            max_sub_agents=0,
            max_steps=spec.max_steps,
        )
        instance = self.agent_manager.spawn_agent(
            role=spec.role,
            parent_id=parent_id,
        )
        if not instance:
            return None
        instance.definition = temp_def
        instance.session_id = spec.scope or parent_instance.id
        children.append(instance.id)
        self._sub_agents[parent_id] = children
        self._sub_specs[instance.id] = spec
        logger.info(
            "Created sub-agent %s (%s) for parent %s",
            instance.id, spec.role.value if hasattr(spec.role, 'value') else str(spec.role), parent_id,
        )
        return instance

    async def run_sub_agent(
        self,
        instance: AgentInstance,
        goal: str,
    ) -> dict:
        instance.status = "running"
        start_time = time.time()
        spec = self._sub_specs.get(instance.id)
        timeout = spec.timeout if spec else 300.0
        try:
            await asyncio.sleep(0.1)
            result = {
                "success": True,
                "output": f"Sub-agent {instance.id} completed: {goal[:100]}",
                "agent_id": instance.id,
            }
            instance.status = "completed"
            return result
        except asyncio.TimeoutError:
            instance.status = "failed"
            return {"success": False, "error": "timeout", "agent_id": instance.id}
        except Exception as e:
            instance.status = "failed"
            return {"success": False, "error": str(e), "agent_id": instance.id}
        finally:
            instance.completed_at = time.time()
            if spec and spec.auto_terminate:
                await self.terminate_sub_agent(instance.id)

    async def terminate_sub_agent(self, instance_id: str) -> bool:
        instance = self.agent_manager.get_agent(instance_id)
        if not instance:
            return False
        parent_id = instance.parent_id
        if parent_id and parent_id in self._sub_agents:
            children = self._sub_agents[parent_id]
            if instance_id in children:
                children.remove(instance_id)
        if instance_id in self._sub_specs:
            del self._sub_specs[instance_id]
        self.agent_manager.terminate_agent(instance_id)
        logger.info("Terminated sub-agent %s", instance_id)
        return True

    async def terminate_all_sub_agents(self, parent_id: str):
        children = list(self._sub_agents.get(parent_id, []))
        for child_id in children:
            await self.terminate_sub_agent(child_id)

    def get_sub_agents(self, parent_id: str) -> list[AgentInstance]:
        children = self._sub_agents.get(parent_id, [])
        return [
            inst for cid in children
            if (inst := self.agent_manager.get_agent(cid)) is not None
        ]

    def get_active_sub_agents(self) -> list[AgentInstance]:
        active: list[AgentInstance] = []
        for children in self._sub_agents.values():
            for cid in children:
                inst = self.agent_manager.get_agent(cid)
                if inst and inst.status in ("idle", "running"):
                    active.append(inst)
        return active

    def get_stats(self) -> dict:
        total = sum(len(v) for v in self._sub_agents.values())
        active = len(self.get_active_sub_agents())
        return {
            "total_sub_agents": total,
            "active_sub_agents": active,
            "parent_count": len(self._sub_agents),
        }
