"""Core Agent Adapter for AetherOS Orchestration Layer.

Wraps the core AIAgent (run_agent.py) to the universal AgentInterface.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agent.orchestration.agent_interface import (
    AgentAdapter,
    AgentCapabilities,
    AgentIdentity,
    AgentInterface,
    AgentLifecycleState,
    AgentMetadata,
    AgentRole,
)
from agent.orchestration.types import TaskResult, TaskSpec

logger = logging.getLogger(__name__)


class CoreAgentAdapter(AgentAdapter):
    """Adapter for the core AIAgent from run_agent.py."""

    def __init__(self, wrapped_agent: Any = None):
        if wrapped_agent:
            super().__init__(wrapped_agent)
        else:
            # Create identity for standalone adapter
            self._identity = AgentIdentity(
                role=AgentRole.COORDINATOR,
                name="CoreAIAgent",
            )
            self._state = AgentLifecycleState.CREATED
            self._config: Dict[str, Any] = {}
            self._active_tasks: Dict[str, Dict[str, Any]] = {}
            self._wrapped = None

    @property
    def capabilities(self) -> AgentCapabilities:
        caps = AgentCapabilities()
        # Core agent supports all major capabilities
        caps.add("chat")
        caps.add("tool_calling")
        caps.add("terminal")
        caps.add("browser")
        caps.add("file_operations")
        caps.add("web_search")
        caps.add("vision")
        caps.add("audio_transcription")
        caps.add("text_to_speech")
        caps.add("memory")
        caps.add("delegation")
        caps.add("coding")
        caps.add("research")
        caps.add("document_processing")
        caps.add("screen_capture")
        caps.add("screen_understanding")
        
        # Set schemas for core agent
        caps.set_schemas(
            input_schema={"type": "object", "properties": {"message": {"type": "string"}, "context": {"type": "object"}}},
            output_schema={"type": "object", "properties": {"response": {"type": "string"}, "artifacts": {"type": "array"}}}
        )
        
        # Core agent permissions
        caps.add_permission("tool_execution")
        caps.add_permission("file_system")
        caps.add_permission("network_access")
        caps.add_permission("process_execution")
        return caps

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            description="Core AetherOS agent with full tool access and conversation loop",
            author="AetherOS",
            tags=["core", "general", "multimodal"],
            supported_platforms=["linux", "macos", "windows"],
            model_requirements=["openai", "anthropic", "gemini", "local"],
            permissions=["tool_execution", "file_system", "network_access", "process_execution"],
        )

    @classmethod
    async def create(cls, config: Dict[str, Any], role: AgentRole = AgentRole.COORDINATOR) -> "CoreAgentAdapter":
        """Factory method to create and initialize a CoreAgentAdapter."""
        # Import here to avoid circular imports
        from run_agent import AIAgent

        # Create the core agent with config
        agent = AIAgent(
            base_url=config.get("base_url"),
            api_key=config.get("api_key"),
            provider=config.get("provider"),
            api_mode=config.get("api_mode"),
            model=config.get("model", ""),
            max_iterations=config.get("max_iterations", 90),
            enabled_toolsets=config.get("enabled_toolsets"),
            disabled_toolsets=config.get("disabled_toolsets"),
            quiet_mode=config.get("quiet_mode", False),
            save_trajectories=config.get("save_trajectories", False),
            platform=config.get("platform", "orchestration"),
            skip_context_files=config.get("skip_context_files", False),
            skip_memory=config.get("skip_memory", False),
        )

        adapter = cls(agent)
        adapter._identity.role = role
        await adapter.initialize(config)
        return adapter

    async def _do_initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the core agent."""
        # Core agent initialization is mostly done in constructor
        # Store config for later use
        self._config = config
        logger.info("Core agent adapter initialized")

    async def _do_execute_task(self, task: TaskSpec) -> Any:
        """Execute a task using the core agent."""
        if not self._wrapped:
            raise RuntimeError("Core agent not initialized")

        # Build user message from task
        user_message = task.goal
        if task.description:
            user_message += f"\n\n{task.description}"

        # Add context if available
        if task.context:
            context_str = "\n".join(f"{k}: {v}" for k, v in task.context.items())
            user_message += f"\n\nContext:\n{context_str}"

        # Add constraints
        if task.constraints:
            constraints_str = "\n".join(f"- {c}" for c in task.constraints)
            user_message += f"\n\nConstraints:\n{constraints_str}"

        # Add success criteria
        if task.success_criteria:
            criteria_str = "\n".join(f"- {c}" for c in task.success_criteria)
            user_message += f"\n\nSuccess Criteria:\n{criteria_str}"

        # Execute via chat method (simpler interface)
        try:
            result = self._wrapped.chat(user_message)
            return result
        except Exception as e:
            logger.error(f"Core agent execution failed: {e}")
            raise

    async def execute_task_streaming(self, task: TaskSpec):
        """Execute task with streaming results."""
        if not self._wrapped:
            raise RuntimeError("Core agent not initialized")

        user_message = task.goal
        if task.description:
            user_message += f"\n\n{task.description}"

        # Core agent supports streaming via callbacks
        # This is a simplified version
        result = await self._do_execute_task(task)
        yield {"type": "result", "content": result}

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel a running task."""
        if task_id in self._active_tasks:
            self._wrapped.interrupt(reason or "Cancelled by orchestrator")
            return True
        return False

    async def create_checkpoint(self, task_id: str) -> Dict[str, Any]:
        """Create a checkpoint of current state."""
        # Core agent has checkpoint support
        if self._wrapped and hasattr(self._wrapped, "create_checkpoint"):
            return await self._wrapped.create_checkpoint(task_id)
        return {}

    async def restore_checkpoint(self, checkpoint_data: Dict[str, Any]) -> bool:
        """Restore from checkpoint."""
        if self._wrapped and hasattr(self._wrapped, "restore_checkpoint"):
            return await self._wrapped.restore_checkpoint(checkpoint_data)
        return False

    async def _graceful_shutdown(self) -> None:
        """Graceful shutdown of core agent."""
        if self._wrapped and hasattr(self._wrapped, "shutdown"):
            await self._wrapped.shutdown()
        self._wrapped = None


def adapt_core_agent(agent: Any) -> CoreAgentAdapter:
    """Adapt an existing core AIAgent instance."""
    return CoreAgentAdapter(agent)


__all__ = ["CoreAgentAdapter", "adapt_core_agent"]