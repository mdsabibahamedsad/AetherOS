from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    @property
    @abstractmethod
    def role(self) -> AgentRole: ...

    @abstractmethod
    async def execute(self, task: Task, context: dict | None = None) -> str: ...


class AgentRegistry:
    _AGENT_MAP: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, role: AgentRole, agent_class: type[BaseAgent]) -> None:
        cls._AGENT_MAP[role.value] = agent_class
        logger.debug("Registered agent %s -> %s", role.value, agent_class.__name__)

    @classmethod
    def get(cls, role: AgentRole) -> type[BaseAgent]:
        agent = cls._AGENT_MAP.get(role.value)
        if agent is None:
            raise KeyError(f"No agent registered for role: {role.value}")
        return agent

    @classmethod
    def list_agents(cls) -> list[str]:
        return list(cls._AGENT_MAP.keys())

    @classmethod
    async def execute(
        cls,
        role: AgentRole,
        task: Task,
        context: dict | None = None,
    ) -> str:
        agent_cls = cls.get(role)
        agent = agent_cls()
        logger.info("Executing task '%s' with agent %s", task.name, role.value)
        return await agent.execute(task, context)
