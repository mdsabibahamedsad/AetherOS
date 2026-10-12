from __future__ import annotations

import logging
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    AgentLimits, OrchestrationTask, Plan, AgentInstance,
)

logger = logging.getLogger(__name__)


class LimitsManager:
    def __init__(self):
        self._default_limits = AgentLimits()

    def set_default_limits(self, limits: AgentLimits):
        self._default_limits = limits

    def get_limits(self, task: OrchestrationTask) -> AgentLimits:
        if task.limits:
            return task.limits
        return self._default_limits

    def check_task_limits(self, task: OrchestrationTask) -> list[str]:
        violations: list[str] = []
        limits = self.get_limits(task)
        if limits.max_steps > 0 and task.retry_count > limits.max_steps:
            violations.append(f"Max steps exceeded ({task.retry_count} > {limits.max_steps})")
        if task.estimated_cost > 0 and limits.max_cost > 0 and task.estimated_cost > limits.max_cost:
            violations.append(f"Max cost exceeded (${task.estimated_cost:.2f} > ${limits.max_cost:.2f})")
        return violations

    def check_plan_limits(self, plan: Plan) -> list[str]:
        violations: list[str] = []
        total_steps = sum(
            len(t.subtasks) + 1 for t in plan.tasks
        )
        if total_steps > self._default_limits.max_steps:
            violations.append(f"Plan too large ({total_steps} steps > {self._default_limits.max_steps})")
        return violations

    def check_agent_limits(self, instance: AgentInstance) -> list[str]:
        violations: list[str] = []
        definition = instance.definition
        if definition:
            if definition.max_sub_agents <= 0:
                pass
            if definition.max_steps <= 0:
                pass
        return violations

    def get_default_limits(self) -> AgentLimits:
        return AgentLimits(
            max_steps=self._default_limits.max_steps,
            max_time=self._default_limits.max_time,
            max_cost=self._default_limits.max_cost,
            max_tokens=self._default_limits.max_tokens,
            max_sub_agents=self._default_limits.max_sub_agents,
            max_parallel_tasks=self._default_limits.max_parallel_tasks,
            max_tool_calls=self._default_limits.max_tool_calls,
        )

    def get_stats(self) -> dict:
        return {
            "default_max_steps": self._default_limits.max_steps,
            "default_max_time": self._default_limits.max_time,
            "default_max_cost": self._default_limits.max_cost,
            "default_max_tokens": self._default_limits.max_tokens,
            "default_max_sub_agents": self._default_limits.max_sub_agents,
            "default_max_parallel": self._default_limits.max_parallel_tasks,
            "default_max_tool_calls": self._default_limits.max_tool_calls,
        }
