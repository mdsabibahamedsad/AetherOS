"""Agent Handoff Protocols for AetherOS Orchestration Layer.

Implements Phases 25-27 of Master Prompt 11: controlled agent-to-agent handoffs
with context packaging and isolation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from agent.orchestration.agent_interface import AgentInterface, SupportsHandoff
from agent.orchestration.agent_registry import AgentRegistry
from agent.orchestration.types import (
    TaskSpec,
    TaskResult,
    AgentIdentity,
    HandoffContext,
    AgentRole,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Handoff Types
# =============================================================================


class HandoffType(Enum):
    """Types of agent handoffs."""

    SEQUENTIAL = "sequential"      # A -> B (A finishes, B continues)
    PARALLEL = "parallel"          # A -> B, C (A fans out to multiple)
    CONDITIONAL = "conditional"    # A -> B if condition else C
    ESCALATION = "escalation"      # A -> B (B has higher capability)
    SPECIALIZATION = "specialization"  # A -> B (B is specialist for subtask)
    REVIEW = "review"              # A -> B (B reviews A's work)
    FALLBACK = "fallback"          # A -> B (A failed, B retries)


class HandoffStatus(Enum):
    """Status of a handoff operation."""

    PENDING = "pending"
    PACKAGING = "packaging"
    TRANSFERRING = "transferring"
    RECEIVING = "receiving"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HandoffRequest:
    """Request to hand off work from one agent to another."""

    handoff_id: str = field(default_factory=lambda: f"handoff-{uuid.uuid4().hex[:12]}")
    source_agent_id: str = ""
    target_agent_id: str = ""
    target_role: Optional[AgentRole] = None
    task_id: str = ""
    handoff_type: HandoffType = HandoffType.SEQUENTIAL
    reason: str = ""
    context: HandoffContext = None
    required_capabilities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: HandoffStatus = HandoffStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffResult:
    """Result of a handoff operation."""

    handoff_id: str
    success: bool
    target_agent_id: str = ""
    new_task_id: str = ""
    error: str = ""
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Context Packaging
# =============================================================================


class ContextPackager:
    """Packages context for agent handoffs following minimum required context principle."""

    # Maximum sizes to prevent context bloat
    MAX_CONTEXT_TOKENS = 8000
    MAX_ARTIFACTS = 20
    MAX_MEMORY_ENTRIES = 10

    @classmethod
    def package_for_handoff(
        cls,
        source_agent: AgentInterface,
        task: TaskSpec,
        target_capabilities: List[str],
        handoff_type: HandoffType = HandoffType.SEQUENTIAL,
    ) -> HandoffContext:
        """Package minimum required context for handoff.

        Principles:
        - Include only what the target agent needs
        - Avoid dumping entire conversation history
        - Focus on: goal, evidence, artifacts, constraints, permissions
        """
        context = HandoffContext(
            source_agent_id=source_agent.identity.agent_id,
            target_agent_id="",  # Filled in by caller
            task_id=task.task_id,
            goal=task.goal,
            summary=cls._create_summary(task),
            relevant_artifacts=cls._select_relevant_artifacts(task, target_capabilities),
            relevant_memory=cls._select_relevant_memory(task, target_capabilities),
            constraints=task.constraints,
            permissions=cls._get_permissions_for_capabilities(target_capabilities),
        )

        return context

    @classmethod
    def _create_summary(cls, task: TaskSpec) -> str:
        """Create a concise summary of the task."""
        parts = [f"Goal: {task.goal}"]

        if task.description:
            parts.append(f"Description: {task.description[:500]}")

        if task.result:
            result_str = str(task.result)
            parts.append(f"Current Result: {result_str[:1000]}")

        if task.metadata.get("steps_completed"):
            parts.append(f"Steps Completed: {task.metadata['steps_completed']}")

        if task.metadata.get("key_findings"):
            parts.append(f"Key Findings: {task.metadata['key_findings'][:500]}")

        return "\n\n".join(parts)

    @classmethod
    def _select_relevant_artifacts(cls, task: TaskSpec, target_capabilities: List[str]) -> List[str]:
        """Select artifacts relevant to target agent's capabilities."""
        # In a full implementation, this would analyze artifact types
        # For now, return all artifacts up to limit
        return task.artifacts[:cls.MAX_ARTIFACTS]

    @classmethod
    def _select_relevant_memory(cls, task: TaskSpec, target_capabilities: List[str]) -> List[str]:
        """Select memory entries relevant to target agent's capabilities."""
        # Would query memory system with capability-based filters
        memory_refs = task.metadata.get("memory_refs", [])
        return memory_refs[:cls.MAX_MEMORY_ENTRIES]

    @classmethod
    def _get_permissions_for_capabilities(cls, capabilities: List[str]) -> List[str]:
        """Get permissions required for given capabilities."""
        # Map capabilities to permissions
        cap_to_perm = {
            "file_write": "filesystem.write",
            "file_delete": "filesystem.delete",
            "terminal": "terminal.execute",
            "web_search": "network.web_search",
            "browser": "browser.navigate",
            "code_execution": "code.execute",
            "deployment": "deployment.manage",
            "email": "communication.email",
        }

        perms = set()
        for cap in capabilities:
            if cap in cap_to_perm:
                perms.add(cap_to_perm[cap])

        return list(perms)


# =============================================================================
# Handoff Manager
# =============================================================================


class HandoffManager:
    """Manages agent-to-agent handoffs with validation and tracking."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        context_packager: Optional[ContextPackager] = None,
    ):
        self._registry = agent_registry
        self._packager = context_packager or ContextPackager()
        self._active_handoffs: Dict[str, HandoffRequest] = {}
        self._handoff_history: List[HandoffResult] = []
        self._max_history = 1000
        self._callbacks: Dict[str, List[Callable[[HandoffResult], None]]] = {}

    async def initiate_handoff(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        target_agent_id: str = "",
        target_role: Optional[AgentRole] = None,
        handoff_type: HandoffType = HandoffType.SEQUENTIAL,
        reason: str = "",
        required_capabilities: Optional[List[str]] = None,
    ) -> HandoffResult:
        """Initiate a handoff from source agent to target agent."""
        start_time = time.time()

        # Find target agent if not specified
        if not target_agent_id and target_role:
            target_reg = self._registry.find_best_for_capability(
                required_capabilities[0] if required_capabilities else "task_execution",
                target_role,
            )
            if target_reg:
                target_agent_id = target_reg.identity.agent_id

        if not target_agent_id:
            return HandoffResult(
                handoff_id="",
                success=False,
                error="No target agent found",
                duration=time.time() - start_time,
            )

        # Create handoff request
        handoff = HandoffRequest(
            source_agent_id=source_agent.identity.agent_id,
            target_agent_id=target_agent_id,
            target_role=target_role,
            task_id=task.task_id,
            handoff_type=handoff_type,
            reason=reason,
            required_capabilities=required_capabilities or task.required_capabilities,
        )

        # Package context
        handoff.status = HandoffStatus.PACKAGING
        context = self._packager.package_for_handoff(
            source_agent, task, handoff.required_capabilities, handoff_type
        )
        context.target_agent_id = target_agent_id
        handoff.context = context

        # Store active handoff
        self._active_handoffs[handoff.handoff_id] = handoff

        # Execute handoff
        handoff.status = HandoffStatus.TRANSFERRING
        result = await self._execute_handoff(handoff)
        result.duration = time.time() - start_time

        # Record history
        self._handoff_history.append(result)
        if len(self._handoff_history) > self._max_history:
            self._handoff_history = self._handoff_history[-self._max_history:]

        # Clean up
        self._active_handoffs.pop(handoff.handoff_id, None)

        # Notify callbacks
        self._notify_callbacks(result)

        return result

    async def _execute_handoff(self, handoff: HandoffRequest) -> HandoffResult:
        """Execute the handoff by transferring context to target agent."""
        try:
            handoff.status = HandoffStatus.TRANSFERRING

            # Get target agent instance
            target_agent = self._registry.get_instance(handoff.target_agent_id)
            if not target_agent:
                # Try to create instance
                reg = self._registry.get_registration(handoff.target_agent_id)
                if reg:
                    target_agent = await self._registry.create_instance(reg.registration_id)
                else:
                    return HandoffResult(
                        handoff_id=handoff.handoff_id,
                        success=False,
                        error=f"Target agent not found: {handoff.target_agent_id}",
                    )

            # Verify target supports handoff
            if not isinstance(target_agent.instance, SupportsHandoff):
                return HandoffResult(
                    handoff_id=handoff.handoff_id,
                    success=False,
                    error=f"Target agent does not support handoff: {handoff.target_agent_id}",
                )

            handoff.status = HandoffStatus.RECEIVING

            # Create new task for target agent (or continue existing)
            new_task = self._create_handoff_task(handoff)

            # Transfer context to target
            handoff.status = HandoffStatus.INTEGRATING
            await target_agent.instance.receive_handoff(
                handoff.context.to_dict() if hasattr(handoff.context, "to_dict") else handoff.context.__dict__,
                new_task,
            )

            return HandoffResult(
                handoff_id=handoff.handoff_id,
                success=True,
                target_agent_id=handoff.target_agent_id,
                new_task_id=new_task.task_id,
                metadata={
                    "handoff_type": handoff.handoff_type.value,
                    "context_size": len(str(handoff.context)),
                },
            )

        except Exception as e:
            logger.error(f"Handoff failed: {e}")
            return HandoffResult(
                handoff_id=handoff.handoff_id,
                success=False,
                error=str(e),
            )

    def _create_handoff_task(self, handoff: HandoffRequest) -> TaskSpec:
        """Create a task specification for the target agent."""
        from agent.orchestration.types import create_task_spec

        new_task = create_task_spec(
            goal=handoff.context.goal,
            description=f"Handoff from {handoff.source_agent_id}: {handoff.reason}",
            priority=handoff.metadata.get("priority", 0),
        )
        new_task.parent_task_id = handoff.task_id
        new_task.root_task_id = handoff.metadata.get("root_task_id", handoff.task_id)
        new_task.required_capabilities = handoff.required_capabilities
        new_task.context = {
            "handoff": handoff.context.__dict__,
            "source_agent": handoff.source_agent_id,
        }
        new_task.metadata["handoff_id"] = handoff.handoff_id
        new_task.metadata["handoff_type"] = handoff.handoff_type.value

        return new_task

    def register_callback(self, event: str, callback: Callable[[HandoffResult], None]) -> None:
        """Register callback for handoff events."""
        self._callbacks.setdefault(event, []).append(callback)

    def _notify_callbacks(self, result: HandoffResult) -> None:
        """Notify registered callbacks."""
        for cb in self._callbacks.get("handoff_completed", []):
            try:
                cb(result)
            except Exception as e:
                logger.warning(f"Handoff callback failed: {e}")

    def get_handoff_status(self, handoff_id: str) -> Optional[HandoffStatus]:
        """Get status of an active handoff."""
        handoff = self._active_handoffs.get(handoff_id)
        return handoff.status if handoff else None

    def get_handoff_history(self, limit: int = 10) -> List[HandoffResult]:
        """Get recent handoff history."""
        return self._handoff_history[-limit:]


# =============================================================================
# Specialized Handoff Patterns
# =============================================================================


class SequentialHandoff:
    """Sequential handoff: A completes, B continues."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        target_role: AgentRole,
        reason: str = "Sequential handoff",
    ) -> HandoffResult:
        return await self.manager.initiate_handoff(
            source_agent=source_agent,
            task=task,
            target_role=target_role,
            handoff_type=HandoffType.SEQUENTIAL,
            reason=reason,
            required_capabilities=task.required_capabilities,
        )


class ParallelHandoff:
    """Parallel handoff: A fans out to multiple agents."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        target_roles: List[AgentRole],
        reason: str = "Parallel fan-out",
    ) -> List[HandoffResult]:
        """Fan out to multiple agents in parallel."""
        results = []

        for role in target_roles:
            result = await self.manager.initiate_handoff(
                source_agent=source_agent,
                task=task,
                target_role=role,
                handoff_type=HandoffType.PARALLEL,
                reason=f"{reason} to {role.value}",
                required_capabilities=task.required_capabilities,
            )
            results.append(result)

        return results


class ConditionalHandoff:
    """Conditional handoff: A -> B if condition else C."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        condition: Callable[[TaskResult], bool],
        if_true_role: AgentRole,
        if_false_role: AgentRole,
        reason: str = "Conditional handoff",
    ) -> HandoffResult:
        # Evaluate condition on current task result
        task_result = task.result
        target_role = if_true_role if condition(task_result) else if_false_role

        return await self.manager.initiate_handoff(
            source_agent=source_agent,
            task=task,
            target_role=target_role,
            handoff_type=HandoffType.CONDITIONAL,
            reason=f"{reason} (condition={'true' if condition(task_result) else 'false'})",
            required_capabilities=task.required_capabilities,
        )


class EscalationHandoff:
    """Escalation handoff: A fails/struggles -> B (more capable) takes over."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        target_role: AgentRole,
        reason: str = "Escalation: agent needs more capability",
    ) -> HandoffResult:
        return await self.manager.initiate_handoff(
            source_agent=source_agent,
            task=task,
            target_role=target_role,
            handoff_type=HandoffType.ESCALATION,
            reason=reason,
            required_capabilities=task.required_capabilities,
        )


class ReviewHandoff:
    """Review handoff: A produces work -> B reviews/validates."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        reviewer_role: AgentRole = AgentRole.REVIEW,
        reason: str = "Independent review required",
    ) -> HandoffResult:
        return await self.manager.initiate_handoff(
            source_agent=source_agent,
            task=task,
            target_role=reviewer_role,
            handoff_type=HandoffType.REVIEW,
            reason=reason,
            required_capabilities=["verification", "review"],
        )


class FallbackHandoff:
    """Fallback handoff: A failed -> B retries with different approach."""

    def __init__(self, manager: HandoffManager):
        self.manager = manager

    async def execute(
        self,
        source_agent: AgentInterface,
        task: TaskSpec,
        fallback_role: AgentRole,
        failure_reason: str,
    ) -> HandoffResult:
        return await self.manager.initiate_handoff(
            source_agent=source_agent,
            task=task,
            target_role=fallback_role,
            handoff_type=HandoffType.FALLBACK,
            reason=f"Fallback after failure: {failure_reason}",
            required_capabilities=task.required_capabilities,
        )


# =============================================================================
# Context Isolation
# =============================================================================


class ContextIsolator:
    """Ensures context isolation between agents and tasks."""

    @staticmethod
    def isolate_task_context(task: TaskSpec, allowed_keys: Set[str] = None) -> Dict[str, Any]:
        """Extract only allowed context keys for a task."""
        if allowed_keys is None:
            # Default allowed keys for task execution
            allowed_keys = {
                "goal", "description", "constraints", "success_criteria",
                "required_capabilities", "artifacts", "metadata",
            }

        isolated = {}
        for key in allowed_keys:
            if hasattr(task, key):
                isolated[key] = getattr(task, key)

        # Include relevant context sub-keys
        if task.context:
            isolated["context"] = {
                k: v for k, v in task.context.items()
                if not k.startswith("_")  # Exclude private keys
            }

        return isolated

    @staticmethod
    def sanitize_for_agent(context: Dict[str, Any], agent: AgentInterface) -> Dict[str, Any]:
        """Sanitize context for a specific agent's permissions."""
        # In a full implementation, this would check agent permissions
        # and remove unauthorized data
        return context

    @staticmethod
    def prevent_leakage(source_task: TaskSpec, target_task: TaskSpec) -> bool:
        """Check if handoff would leak unauthorized information."""
        # Check for cross-user, cross-project leakage
        if source_task.user_id and target_task.user_id:
            if source_task.user_id != target_task.user_id:
                logger.warning(f"Cross-user handoff attempted: {source_task.user_id} -> {target_task.user_id}")
                return False

        if source_task.project_id and target_task.project_id:
            if source_task.project_id != target_task.project_id:
                logger.warning(f"Cross-project handoff attempted: {source_task.project_id} -> {target_task.project_id}")
                return False

        return True


# =============================================================================
# Factory
# =============================================================================


def create_handoff_manager(agent_registry: AgentRegistry) -> HandoffManager:
    """Create a handoff manager with all specialized patterns."""
    manager = HandoffManager(agent_registry)
    manager.sequential = SequentialHandoff(manager)
    manager.parallel = ParallelHandoff(manager)
    manager.conditional = ConditionalHandoff(manager)
    manager.escalation = EscalationHandoff(manager)
    manager.review = ReviewHandoff(manager)
    manager.fallback = FallbackHandoff(manager)
    return manager


__all__ = [
    "HandoffType",
    "HandoffStatus",
    "HandoffRequest",
    "HandoffResult",
    "ContextPackager",
    "HandoffManager",
    "SequentialHandoff",
    "ParallelHandoff",
    "ConditionalHandoff",
    "EscalationHandoff",
    "ReviewHandoff",
    "FallbackHandoff",
    "ContextIsolator",
    "create_handoff_manager",
]