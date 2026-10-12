"""Delegate Agent Adapter for AetherOS Orchestration Layer.

Wraps delegate subagents (from tools/delegate_tool.py) to the universal AgentInterface.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from agent.orchestration.agent_interface import (
    AgentAdapter,
    AgentCapabilities,
    AgentIdentity,
    AgentInterface,
    AgentLifecycleState,
    AgentMetadata,
    AgentRole,
    SupportsHandoff,
    SupportsCheckpointing,
)
from agent.orchestration.types import TaskResult, TaskSpec, HandoffContext

logger = logging.getLogger(__name__)


class DelegateAgentAdapter(AgentAdapter):
    """Adapter for delegate subagents spawned via delegate_task tool."""

    def __init__(self, wrapped_agent: Any = None, parent_agent_id: str = "", role: str = "leaf"):
        if wrapped_agent:
            super().__init__(wrapped_agent)
        else:
            self._identity = AgentIdentity(
                role=AgentRole.COORDINATOR,  # Will be adjusted based on role
                name=f"DelegateAgent({role})",
            )
            self._state = AgentLifecycleState.CREATED
            self._config: Dict[str, Any] = {}
            self._active_tasks: Dict[str, Dict[str, Any]] = {}
            self._wrapped = None

        self._parent_agent_id = parent_agent_id
        self._delegate_role = role  # "leaf" or "orchestrator"
        self._toolsets: List[str] = []
        self._max_iterations: int = 90
        self._model: Optional[str] = None

    @property
    def capabilities(self) -> AgentCapabilities:
        caps = AgentCapabilities()
        caps.add("task_execution")
        caps.add("tool_calling")
        caps.add("delegation" if self._delegate_role == "orchestrator" else "leaf_execution")

        # Add capabilities based on toolsets
        for toolset in self._toolsets:
            caps.add(f"toolset:{toolset}")

        # Set schemas for delegate agents
        caps.set_schemas(
            input_schema={"type": "object", "properties": {"goal": {"type": "string"}, "context": {"type": "object"}, "toolsets": {"type": "array"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}, "artifacts": {"type": "array"}}}
        )

        # Delegate agent permissions
        caps.add_permission("task_execution")
        caps.add_permission("tool_calling")
        if self._delegate_role == "orchestrator":
            caps.add_permission("delegation")
        return caps

    @property
    def metadata(self) -> AgentMetadata:
        perms = ["task_execution", "tool_calling"]
        if self._delegate_role == "orchestrator":
            perms.append("delegation")
        return AgentMetadata(
            description=f"Delegate subagent ({self._delegate_role})",
            author="AetherOS",
            tags=["delegate", "subagent", self._delegate_role],
            supported_platforms=["linux", "macos", "windows"],
            permissions=perms,
        )

    @classmethod
    async def create(cls, config: Dict[str, Any], role: AgentRole = AgentRole.COORDINATOR) -> "DelegateAgentAdapter":
        """Factory method to create a DelegateAgentAdapter."""
        # Delegate agents are typically created via delegate_task tool
        # This factory creates a template that will be configured at runtime
        adapter = cls(
            parent_agent_id=config.get("parent_agent_id", ""),
            role=config.get("delegate_role", "leaf"),
        )
        adapter._identity.role = role
        adapter._toolsets = config.get("toolsets", [])
        adapter._max_iterations = config.get("max_iterations", 90)
        adapter._model = config.get("model")

        await adapter.initialize(config)
        return adapter

    def configure_for_task(self, task: TaskSpec) -> None:
        """Configure the delegate agent for a specific task."""
        self._toolsets = task.preferred_tools or self._toolsets
        self._model = task.preferred_model or self._model
        self._config.update({
            "task_id": task.task_id,
            "parent_task_id": task.parent_task_id,
            "root_task_id": task.root_task_id,
            "toolsets": self._toolsets,
            "model": self._model,
            "max_iterations": task.budget.max_iterations,
        })

    async def _do_initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the delegate agent configuration."""
        self._config = config
        self._parent_agent_id = config.get("parent_agent_id", "")
        self._delegate_role = config.get("delegate_role", "leaf")
        self._toolsets = config.get("toolsets", [])
        self._model = config.get("model")
        self._max_iterations = config.get("max_iterations", 90)
        logger.info(f"Delegate agent adapter initialized ({self._delegate_role})")

    async def _do_execute_task(self, task: TaskSpec) -> Any:
        """Execute a task using the delegate agent."""
        # Delegate agents are typically spawned via the delegate_task tool
        # This adapter wraps an already-spawned agent or coordinates spawning
        if self._wrapped and hasattr(self._wrapped, "execute_task"):
            # Wrapped is an AIAgent instance
            self.configure_for_task(task)
            return await self._wrapped.execute_task(task)

        # If no wrapped agent, we can't execute directly
        # This would be called via delegate_task tool
        raise RuntimeError("Delegate agent requires wrapped AIAgent instance")

    async def execute_task_streaming(self, task: TaskSpec):
        """Execute task with streaming results."""
        if self._wrapped and hasattr(self._wrapped, "execute_task_streaming"):
            self.configure_for_task(task)
            async for chunk in self._wrapped.execute_task_streaming(task):
                yield chunk
        else:
            result = await self._do_execute_task(task)
            yield {"type": "result", "content": result}

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel a running task."""
        if task_id in self._active_tasks and self._wrapped:
            if hasattr(self._wrapped, "interrupt"):
                self._wrapped.interrupt(reason or "Cancelled by orchestrator")
                return True
        return False

    async def create_checkpoint(self, task_id: str) -> Dict[str, Any]:
        """Create a checkpoint of current state."""
        if self._wrapped and hasattr(self._wrapped, "create_checkpoint"):
            return await self._wrapped.create_checkpoint(task_id)
        return {}

    async def restore_checkpoint(self, checkpoint_data: Dict[str, Any]) -> bool:
        """Restore from checkpoint."""
        if self._wrapped and hasattr(self._wrapped, "restore_checkpoint"):
            return await self._wrapped.restore_checkpoint(checkpoint_data)
        return False

    # Handoff support
    async def package_context(self, task_id: str, target_agent: str) -> Dict[str, Any]:
        """Package minimal required context for handoff."""
        if task_id not in self._active_tasks:
            return {}

        task_data = self._active_tasks[task_id]
        task = task_data.get("task")
        if not task:
            return {}

        return {
            "source_agent_id": self.identity.agent_id,
            "target_agent_id": target_agent,
            "task_id": task_id,
            "goal": task.goal,
            "summary": f"Delegated task: {task.goal}",
            "relevant_artifacts": task.artifacts,
            "constraints": task.constraints,
            "permissions": [],
            "delegate_role": self._delegate_role,
            "parent_agent_id": self._parent_agent_id,
        }

    async def receive_handoff(self, context: Dict[str, Any], task: Any) -> None:
        """Receive handoff context and integrate with current state."""
        # Delegate agents receive context from parent
        self._config["handoff_context"] = context
        if "parent_agent_id" in context:
            self._parent_agent_id = context["parent_agent_id"]

    async def _graceful_shutdown(self) -> None:
        """Graceful shutdown of delegate agent."""
        if self._wrapped and hasattr(self._wrapped, "shutdown"):
            await self._wrapped.shutdown()
        self._wrapped = None


def adapt_delegate_agent(agent: Any, parent_agent_id: str = "", delegate_role: str = "leaf") -> DelegateAgentAdapter:
    """Adapt an existing delegate subagent (AIAgent instance)."""
    return DelegateAgentAdapter(agent, parent_agent_id, delegate_role)


__all__ = ["DelegateAgentAdapter", "adapt_delegate_agent"]