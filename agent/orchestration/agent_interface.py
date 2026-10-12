"""Universal Agent Interface for AetherOS Orchestration Layer.

Implements Phase 1 of Master Prompt 11: a common interface that all
compatible agents must expose. Existing agent implementations are
wrapped via adapters — no existing APIs are broken.

Design principles:
- Minimal required surface; capabilities are opt-in via mixins
- No breaking changes to existing agent classes
- Capability discovery via standard introspection
- Health checks are non-destructive
- Versioning for forward compatibility
"""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from agent.orchestration.types import (
    AgentCapabilities,
    AgentHealth,
    AgentHealthStatus,
    AgentMetadata,
    AgentVersion,
    AgentRole,
    TaskResult,
    TaskSpec,
)


class AgentLifecycleState(Enum):
    """Lifecycle states for agent instances."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    PAUSED = "paused"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


@dataclass
class AgentIdentity:
    """Immutable identity for an agent instance."""

    agent_id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:12]}")
    role: AgentRole = AgentRole.COORDINATOR
    name: str = ""
    version: str = "1.0.0"
    instance_id: str = field(default_factory=lambda: f"inst-{uuid.uuid4().hex[:8]}")


@runtime_checkable
class AgentInterface(Protocol):
    """Universal interface that all AetherOS agents must implement.

    This is the minimal required surface. Agents declare additional
    capabilities via the `capabilities` property and mixin classes.
    """

    # ── Identity ─────────────────────────────────────────────────────
    @property
    def identity(self) -> AgentIdentity: ...

    @property
    def capabilities(self) -> AgentCapabilities: ...

    @property
    def metadata(self) -> AgentMetadata: ...

    # ── Lifecycle ────────────────────────────────────────────────────
    @property
    def state(self) -> AgentLifecycleState: ...

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration.

        Called once after construction. Safe to call multiple times
        (idempotent). May raise if initialization fails.
        """
        ...

    async def shutdown(self, graceful: bool = True) -> None:
        """Shut down the agent.

        Args:
            graceful: If True, wait for in-flight work to complete.
        """
        ...

    async def health_check(self) -> AgentHealth:
        """Perform a non-destructive health check.

        Must not modify agent state or trigger side effects.
        Returns immediately with cached/lightweight status.
        """
        ...

    # ── Task Execution ───────────────────────────────────────────────
    async def execute_task(self, task: TaskSpec) -> TaskResult:
        """Execute a task and return the result.

        This is the primary entry point for task execution.
        The task spec contains all context needed for execution.
        """
        ...

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Request cancellation of a running task.

        Returns True if cancellation was initiated.
        """
        ...

    # ── Capability Query ─────────────────────────────────────────────
    def supports_capability(self, capability: str) -> bool:
        """Check if agent supports a specific capability by name."""
        return capability in self.capabilities.capabilities

    def get_capability_detail(self, capability: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a capability if supported."""
        return self.capabilities.details.get(capability)

    # ── State Inspection ─────────────────────────────────────────────
    def get_active_tasks(self) -> List[str]:
        """Return list of currently active task IDs."""
        ...

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific task."""
        ...

    # ── Configuration ────────────────────────────────────────────────
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update agent configuration at runtime.

        Only affects future task executions.
        """
        ...

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration (sanitized, no secrets)."""
        ...


# ── Capability Mixins ────────────────────────────────────────────────

class SupportsPlanning:
    """Agent can decompose goals into subtasks and create plans."""

    async def create_plan(self, goal: str, context: Dict[str, Any]) -> Any: ...

    async def replan(self, plan_id: str, reason: str, context: Dict[str, Any]) -> Any: ...


class SupportsHandoff:
    """Agent can hand off work to another agent with context packaging."""

    async def package_context(self, task_id: str, target_agent: str) -> Dict[str, Any]:
        """Package minimal required context for handoff to target agent."""
        ...

    async def receive_handoff(self, context: Dict[str, Any], task: Any) -> None:
        """Receive handoff context and integrate with current state."""
        ...


class SupportsVerification:
    """Agent can independently verify results produced by itself or others."""

    async def verify_result(self, result: Any, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a result against criteria. Returns verification report."""
        ...


class SupportsCheckpointing:
    """Agent can create and restore checkpoints for long-running work."""

    async def create_checkpoint(self, task_id: str) -> Dict[str, Any]:
        """Create a checkpoint of current state. Returns checkpoint data."""
        ...

    async def restore_checkpoint(self, checkpoint_data: Dict[str, Any]) -> bool:
        """Restore from checkpoint. Returns True if successful."""
        ...


class SupportsStreaming:
    """Agent can stream incremental results during execution."""

    async def execute_task_streaming(self, task: TaskSpec) -> Any:
        """Execute task and yield incremental results via async generator."""
        ...


class SupportsParallelism:
    """Agent can execute multiple sub-tasks in parallel."""

    async def execute_parallel(self, tasks: List[TaskSpec]) -> List[TaskResult]:
        """Execute multiple independent tasks in parallel."""
        ...


class SupportsModelSelection:
    """Agent can select appropriate model for a task."""

    def select_model(self, task: TaskSpec, available_models: List[str]) -> str: ...


class SupportsSkillSelection:
    """Agent can select and load skills for a task."""

    async def select_skills(self, task: TaskSpec) -> List[str]: ...


class SupportsToolSelection:
    """Agent can select tools for a task."""

    def select_tools(self, task: TaskSpec, available_tools: List[str]) -> List[str]: ...


class SupportsMemory:
    """Agent has persistent memory integration."""

    async def store_memory(self, key: str, value: Any, metadata: Dict[str, Any]) -> None: ...

    async def retrieve_memory(self, query: str, limit: int = 10) -> List[Any]: ...

    async def search_memory(self, query: str, filters: Dict[str, Any]) -> List[Any]: ...


class SupportsMultimodal:
    """Agent can process multimodal inputs (image, audio, video, document)."""

    async def process_image(self, image_data: bytes, query: str) -> str: ...

    async def process_audio(self, audio_data: bytes, query: str) -> str: ...

    async def process_video(self, video_data: bytes, query: str) -> str: ...

    async def process_document(self, doc_data: bytes, query: str) -> str: ...


# ── Adapter Base ────────────────────────────────────────────────────

class AgentAdapter:
    """Base class for wrapping existing agents to the universal interface.

    Subclasses implement the abstract methods to bridge a specific
    agent implementation to the universal interface.
    """

    def __init__(self, wrapped_agent: Any):
        self._wrapped = wrapped_agent
        self._identity = AgentIdentity(
            role=AgentRole.CUSTOM,
            name=type(wrapped_agent).__name__,
        )
        self._state = AgentLifecycleState.CREATED
        self._config: Dict[str, Any] = {}
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def state(self) -> AgentLifecycleState:
        return self._state

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities()  # Override in subclasses

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata()

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config.update(config)
        self._state = AgentLifecycleState.INITIALIZING
        try:
            await self._do_initialize(config)
            self._state = AgentLifecycleState.READY
        except Exception:
            self._state = AgentLifecycleState.UNHEALTHY
            raise

    async def _do_initialize(self, config: Dict[str, Any]) -> None:
        """Subclass implementation for initialization."""
        pass

    async def shutdown(self, graceful: bool = True) -> None:
        self._state = AgentLifecycleState.SHUTTING_DOWN
        try:
            if graceful:
                await self._graceful_shutdown()
        finally:
            self._state = AgentLifecycleState.TERMINATED

    async def _graceful_shutdown(self) -> None:
        pass

    async def health_check(self) -> "AgentHealth":
        return AgentHealth(
            status=AgentHealthStatus.HEALTHY if self._state == AgentLifecycleState.READY else AgentHealthStatus.UNHEALTHY,
            agent_id=self.identity.agent_id,
            details={},
        )

    async def execute_task(self, task: "TaskSpec") -> "TaskResult":
        self._state = AgentLifecycleState.BUSY
        task_id = task.task_id or str(uuid.uuid4())
        self._active_tasks[task_id] = {"task": task, "started_at": time.time()}
        try:
            result = await self._do_execute_task(task)
            return TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                artifacts=[],
                execution_time=time.time() - self._active_tasks[task_id]["started_at"],
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                result=None,
                error=str(e),
                artifacts=[],
                execution_time=time.time() - self._active_tasks.get(task_id, {}).get("started_at", time.time()),
            )
        finally:
            self._active_tasks.pop(task_id, None)
            self._state = AgentLifecycleState.READY

    async def _do_execute_task(self, task: "TaskSpec") -> Any:
        """Subclass implementation for task execution."""
        raise NotImplementedError

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        if task_id in self._active_tasks:
            # Subclass can implement actual cancellation
            return True
        return False

    def get_active_tasks(self) -> List[str]:
        return list(self._active_tasks.keys())

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._active_tasks.get(task_id)

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config.update(config)

    def get_config(self) -> Dict[str, Any]:
        return {k: v for k, v in self._config.items() if not k.endswith(("_key", "_secret", "_token", "_password"))}


# ── Factory ────────────────────────────────────────────────────────

async def create_agent(
    agent_type: str,
    config: Dict[str, Any],
    role: AgentRole = AgentRole.COORDINATOR,
) -> AgentInterface:
    """Factory function to create agents by type.

    Args:
        agent_type: Type identifier (e.g., "core", "automation", "delegate")
        config: Agent configuration
        role: Agent role

    Returns:
        Agent implementing AgentInterface
    """
    # Import here to avoid circular imports
    if agent_type == "core":
        from agent.orchestration.adapters.core_agent_adapter import CoreAgentAdapter
        return await CoreAgentAdapter.create(config, role)
    elif agent_type == "automation":
        from agent.orchestration.adapters.automation_agent_adapter import AutomationAgentAdapter
        return await AutomationAgentAdapter.create(config, role)
    elif agent_type == "delegate":
        from agent.orchestration.adapters.delegate_adapter import DelegateAgentAdapter
        return await DelegateAgentAdapter.create(config, role)
    elif agent_type == "automation_role":
        from agent.orchestration.adapters.automation_role_adapter import AutomationRoleAdapter
        return await AutomationRoleAdapter.create(config, role)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


# ── Compatibility Helpers ──────────────────────────────────────────

def adapt_core_agent(agent: Any) -> AgentInterface:
    """Adapt a core AIAgent (run_agent.py) to the universal interface."""
    from agent.orchestration.adapters.core_agent_adapter import CoreAgentAdapter
    return CoreAgentAdapter(agent)


def adapt_automation_agent(agent: Any) -> AgentInterface:
    """Adapt an automation BaseAgent to the universal interface."""
    from agent.orchestration.adapters.automation_agent_adapter import AutomationAgentAdapter
    return AutomationAgentAdapter(agent)


def adapt_delegate_agent(agent: Any) -> AgentInterface:
    """Adapt a delegate subagent to the universal interface."""
    from agent.orchestration.adapters.delegate_adapter import DelegateAgentAdapter
    return DelegateAgentAdapter(agent)