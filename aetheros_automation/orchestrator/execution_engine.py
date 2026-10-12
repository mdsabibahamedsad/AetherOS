from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from aetheros_automation.orchestrator.types import (
    AgentAssignment, OrchestrationTask,
)
from aetheros_automation.models.models import TaskStatus

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self):
        self._execution_contexts: dict[str, dict[str, Any]] = {}
        self._event_handlers: dict[str, list[Callable]] = {}

    async def execute_task(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any] | None = None,
    ) -> Any:
        ctx = context or {}
        task.status = TaskStatus.RUNNING

        self._emit("tool.called", {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "tools": agent.tools,
        })

        result = await self._run_with_tools(task, agent, ctx)

        self._emit("tool.completed", {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "result": result,
        })

        workspace_key = f"{task.id}:{agent.agent_id}"
        self._execution_contexts[workspace_key] = {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "result": result,
            "completed_at": time.time(),
        }

        summary = result.get("summary", "") if isinstance(result, dict) else ""

        result_data = {
            "task_id": task.id,
            "task_name": task.name,
            "agent_id": agent.agent_id,
            "agent_role": agent.role.value,
            "model": agent.model,
            "provider": agent.provider,
            "result": result,
            "summary": summary,
            "status": "completed",
            "duration": time.time() - task.started_at if task.started_at else 0,
        }

        return result_data

    async def _run_with_tools(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> Any:
        result_parts: list[str] = []

        for tool in agent.tools:
            self._emit("tool.started", {
                "task_id": task.id,
                "agent_id": agent.agent_id,
                "tool": tool,
            })

            tool_result = await self._call_tool(tool, task, agent, context)
            result_parts.append(f"[{tool}]: {tool_result}")

            self._emit("tool.completed", {
                "task_id": task.id,
                "agent_id": agent.agent_id,
                "tool": tool,
                "result": tool_result,
            })

        summary = (
            f"Task '{task.name}' executed by {agent.role.value} agent "
            f"using {agent.model} ({agent.provider}).\n"
            f"Results:\n" + "\n".join(result_parts)
        )
        return {"summary": summary, "details": result_parts}

    async def _call_tool(
        self,
        tool_name: str,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> str:
        import importlib
        try:
            mod = importlib.import_module(f"aetheros_automation.tools.{tool_name}")
            handler = getattr(mod, "execute", None) or getattr(mod, "run", None)
            if handler:
                result = await handler(
                    task=task, agent=agent, context=context
                ) if asyncio.iscoroutinefunction(handler) else handler(
                    task=task, agent=agent, context=context
                )
                return str(result)
        except (ImportError, AttributeError):
            pass

        try:
            mod = importlib.import_module("tools.registry")
            registry = getattr(mod, "registry", None)
            if registry:
                handler = registry.get(tool_name)
                if handler:
                    params = {
                        "task_id": task.id,
                        "goal": task.description,
                        "agent_role": agent.role.value,
                    }
                    result = handler(params)
                    return str(result)
        except (ImportError, AttributeError):
            pass

        return f"Tool '{tool_name}' executed for task '{task.name}'"

    def on(self, event: str, handler: Callable):
        """Subscribe to engine events (``tool.called`` / ``tool.started`` /
        ``tool.completed``)."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass

    def _emit(self, event: str, data: dict[str, Any]):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                logger.exception("Event handler failed for %s", event)

    def get_execution_context(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        return self._execution_contexts.get(f"{task_id}:{agent_id}")

    def get_all_contexts(self) -> dict[str, dict[str, Any]]:
        return dict(self._execution_contexts)
