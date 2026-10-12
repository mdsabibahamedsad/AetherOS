"""Automation Agent Adapter for AetherOS Orchestration Layer.

Wraps automation BaseAgent and role-specific agents to the universal AgentInterface.
"""

from __future__ import annotations

import asyncio
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
    SupportsVerification,
    SupportsCheckpointing,
)
from agent.orchestration.types import TaskResult, TaskSpec, HandoffContext

logger = logging.getLogger(__name__)


class AutomationAgentAdapter(AgentAdapter):
    """Adapter for automation BaseAgent and role-specific agents."""

    # Role to capability mapping
    ROLE_CAPABILITIES = {
        AgentRole.COORDINATOR: ["planning", "coordination", "delegation"],
        AgentRole.PLANNER: ["planning", "task_decomposition", "scheduling"],
        AgentRole.DEVELOPER: ["coding", "code_generation", "refactoring", "debugging"],
        AgentRole.CODING: ["coding", "implementation", "code_review"],
        AgentRole.BROWSER: ["browser_navigation", "web_scraping", "web_search"],
        AgentRole.RESEARCH: ["research", "information_gathering", "synthesis", "citation"],
        AgentRole.WRITER: ["writing", "content_creation", "editing", "formatting"],
        AgentRole.QA: ["testing", "validation", "quality_assurance"],
        AgentRole.DEPLOYMENT: ["deployment", "ci_cd", "infrastructure"],
        AgentRole.SECURITY: ["security_auditing", "vulnerability_scanning", "compliance"],
        AgentRole.MEMORY: ["memory_management", "knowledge_retrieval", "storage"],
        AgentRole.CREATIVE: ["design", "generation", "creative_writing"],
        AgentRole.DATA: ["data_analysis", "visualization", "statistics"],
        AgentRole.COMMUNICATION: ["email", "messaging", "notifications"],
        AgentRole.REVIEW: ["code_review", "proofreading", "quality_review"],
        AgentRole.FILE: ["file_operations", "filesystem", "document_processing"],
        AgentRole.VISION: ["vision", "image_understanding", "ocr"],
        AgentRole.AUDIO: ["transcription", "text_to_speech", "audio_processing"],
        AgentRole.VIDEO: ["video_understanding", "video_processing"],
        AgentRole.COMPUTER: ["computer_use", "screen_understanding", "automation"],
    }

    def __init__(self, wrapped_agent: Any = None, role: AgentRole = AgentRole.COORDINATOR):
        if wrapped_agent:
            super().__init__(wrapped_agent)
            self._identity.role = role
            self._identity.name = f"Automation{role.value.title()}Agent"
        else:
            # Create identity for standalone adapter
            self._identity = AgentIdentity(
                role=role,
                name=f"Automation{role.value.title()}Agent",
            )
            self._state = AgentLifecycleState.CREATED
            self._config: Dict[str, Any] = {}
            self._active_tasks: Dict[str, Dict[str, Any]] = {}
            self._wrapped = None
            self._role = role

    @property
    def capabilities(self) -> AgentCapabilities:
        caps = AgentCapabilities()
        role_caps = self.ROLE_CAPABILITIES.get(self._identity.role, [])
        for cap in role_caps:
            caps.add(cap)
        # All automation agents support basic execution
        caps.add("task_execution")
        caps.add("async_execution")
        
        # Set schemas for automation agents
        caps.set_schemas(
            input_schema={"type": "object", "properties": {"task": {"type": "object"}, "context": {"type": "object"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}, "artifacts": {"type": "array"}}}
        )
        
        # Add role-specific permissions
        role_permissions = {
            AgentRole.DEVELOPER: ["code_execution", "file_system", "git"],
            AgentRole.CODING: ["code_execution", "file_system", "git"],
            AgentRole.BROWSER: ["network_access", "web_browsing"],
            AgentRole.RESEARCH: ["network_access", "web_search"],
            AgentRole.WRITER: ["file_system"],
            AgentRole.QA: ["code_execution", "file_system"],
            AgentRole.DEPLOYMENT: ["deployment", "ci_cd", "file_system"],
            AgentRole.SECURITY: ["security_audit", "file_system"],
            AgentRole.FILE: ["file_system"],
        }
        for perm in role_permissions.get(self._identity.role, ["task_execution"]):
            caps.add_permission(perm)
        return caps

    @property
    def metadata(self) -> AgentMetadata:
        role_perms = {
            AgentRole.DEVELOPER: ["code_execution", "file_system", "git"],
            AgentRole.CODING: ["code_execution", "file_system", "git"],
            AgentRole.BROWSER: ["network_access", "web_browsing"],
            AgentRole.RESEARCH: ["network_access", "web_search"],
            AgentRole.WRITER: ["file_system"],
            AgentRole.QA: ["code_execution", "file_system"],
            AgentRole.DEPLOYMENT: ["deployment", "ci_cd", "file_system"],
            AgentRole.SECURITY: ["security_audit", "file_system"],
            AgentRole.FILE: ["file_system"],
        }
        return AgentMetadata(
            description=f"Automation {self._identity.role.value} agent",
            author="AetherOS",
            tags=["automation", self._identity.role.value],
            supported_platforms=["linux", "macos", "windows"],
            permissions=role_perms.get(self._identity.role, ["task_execution"]),
        )

    @classmethod
    async def create(cls, config: Dict[str, Any], role: AgentRole = AgentRole.COORDINATOR) -> "AutomationAgentAdapter":
        """Factory method to create and initialize an AutomationAgentAdapter."""
        # Import here to avoid circular imports
        from aetheros_automation.agents.registry import AgentRegistry, AgentRole as AutoAgentRole

        # Map orchestration role to automation role
        role_map = {
            AgentRole.COORDINATOR: AutoAgentRole.COORDINATOR,
            AgentRole.PLANNER: AutoAgentRole.PLANNER,
            AgentRole.DEVELOPER: AutoAgentRole.DEVELOPER,
            AgentRole.CODING: AutoAgentRole.CODING,
            AgentRole.BROWSER: AutoAgentRole.BROWSER,
            AgentRole.RESEARCH: AutoAgentRole.RESEARCH,
            AgentRole.WRITER: AutoAgentRole.WRITER,
            AgentRole.QA: AutoAgentRole.QA,
            AgentRole.DEPLOYMENT: AutoAgentRole.DEPLOYMENT,
            AgentRole.SECURITY: AutoAgentRole.SECURITY,
            AgentRole.MEMORY: AutoAgentRole.MEMORY,
            AgentRole.CREATIVE: AutoAgentRole.CREATIVE,
            AgentRole.DATA: AutoAgentRole.DATA,
            AgentRole.COMMUNICATION: AutoAgentRole.COMMUNICATION,
            AgentRole.REVIEW: AutoAgentRole.REVIEW,
            AgentRole.FILE: AutoAgentRole.FILE,
        }

        auto_role = role_map.get(role, AutoAgentRole.COORDINATOR)
        agent_cls = AgentRegistry.get(auto_role)
        wrapped = agent_cls()

        adapter = cls(wrapped, role)
        await adapter.initialize(config)
        return adapter

    async def _do_initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the automation agent."""
        self._config = config
        if self._wrapped and hasattr(self._wrapped, "initialize"):
            await self._wrapped.initialize(config)
        logger.info(f"Automation agent adapter initialized for role {self._identity.role.value}")

    async def _do_execute_task(self, task: TaskSpec) -> Any:
        """Execute a task using the automation agent."""
        if not self._wrapped:
            raise RuntimeError("Automation agent not initialized")

        # Build task dict for automation agent
        auto_task = {
            "id": task.task_id,
            "goal": task.goal,
            "description": task.description,
            "context": task.context,
            "constraints": task.constraints,
            "success_criteria": task.success_criteria,
        }

        try:
            # Automation agents use async execute method
            if hasattr(self._wrapped, "execute"):
                result = await self._wrapped.execute(auto_task, task.context or {})
            else:
                # Fallback for sync agents
                result = self._wrapped.execute(auto_task, task.context or {})
            return result
        except Exception as e:
            logger.error(f"Automation agent execution failed: {e}")
            raise

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel a running task."""
        if task_id in self._active_tasks and self._wrapped:
            if hasattr(self._wrapped, "cancel"):
                await self._wrapped.cancel(task_id, reason)
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
            "summary": f"Task: {task.goal}",
            "relevant_artifacts": task.artifacts,
            "constraints": task.constraints,
            "permissions": [],  # Would be filled from security context
        }

    async def receive_handoff(self, context: Dict[str, Any], task: Any) -> None:
        """Receive handoff context and integrate with current state."""
        # Store handoff context for use in execution
        self._config["handoff_context"] = context

    async def _graceful_shutdown(self) -> None:
        """Graceful shutdown of automation agent."""
        if self._wrapped and hasattr(self._wrapped, "shutdown"):
            await self._wrapped.shutdown()
        self._wrapped = None


class AutomationRoleAdapter(AutomationAgentAdapter):
    """Specialized adapter for automation role-specific agents."""

    @classmethod
    async def create(cls, config: Dict[str, Any], role: AgentRole = AgentRole.COORDINATOR) -> "AutomationRoleAdapter":
        """Factory method to create role-specific automation agent."""
        return await super().create(config, role)


def adapt_automation_agent(agent: Any) -> AutomationAgentAdapter:
    """Adapt an existing automation BaseAgent instance."""
    return AutomationAgentAdapter(agent)


def adapt_automation_role_agent(agent: Any, role: AgentRole) -> AutomationRoleAdapter:
    """Adapt an existing automation role-specific agent."""
    return AutomationRoleAdapter(agent, role)


__all__ = ["AutomationAgentAdapter", "AutomationRoleAdapter", "adapt_automation_agent", "adapt_automation_role_agent"]