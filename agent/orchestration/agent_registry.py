"""Unified Agent Registry for AetherOS Orchestration Layer.

Implements Phase 2 of Master Prompt 11: a central registry for all
agents in the system supporting discovery, capability queries,
health checks, and lifecycle management.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import time
import uuid
import weakref
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type

from agent.orchestration.agent_interface import (
    AgentAdapter,
    AgentCapabilities,
    AgentHealth,
    AgentHealthStatus,
    AgentIdentity,
    AgentInterface,
    AgentLifecycleState,
    AgentMetadata,
    AgentRole,
    AgentCapabilities,
)
from agent.orchestration.types import (
    AgentIdentity,
    AgentMetadata,
    AgentRole,
    AgentCapabilities,
    AgentHealth,
    AgentHealthStatus,
)
from agent.orchestration.types import AgentIdentity as TypesAgentIdentity

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Registration
# =============================================================================


@dataclass
class AgentRegistration:
    """Registration record for an agent in the registry."""

    identity: "AgentIdentity"
    agent_type: str  # "core", "automation", "automation_role", "delegate", "custom"
    factory: Callable[..., "AgentInterface"]  # Factory function to create instance
    default_config: Dict[str, Any] = field(default_factory=dict)
    capabilities: "AgentCapabilities" = field(default_factory=lambda: AgentCapabilities())
    metadata: "AgentMetadata" = field(default_factory=lambda: AgentMetadata())
    tags: Set[str] = field(default_factory=set)
    enabled: bool = True
    priority: int = 0  # Higher = preferred for capability routing
    registered_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    registration_id: str = field(default_factory=lambda: f"reg-{uuid.uuid4().hex[:12]}")


@dataclass
class AgentInstance:
    """Runtime instance of a registered agent."""

    registration: "AgentRegistration"
    instance: "AgentInterface"
    created_at: float = field(default_factory=time.time)
    last_health_check: float = 0
    health_status: "AgentHealthStatus" = None
    active_task_count: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    last_error: str = ""
    weak_ref: Any = None  # Weak reference for GC


# =============================================================================
# Agent Registry
# =============================================================================


class AgentRegistry:
    """Central registry for all agents in AetherOS.

    Supports:
    - Registration of agent types with factories
    - Discovery by role, capability, tag
    - Instance lifecycle management
    - Health monitoring
    - Capability-based routing
    """

    def __init__(self):
        self._registrations: Dict[str, AgentRegistration] = {}
        self._instances: Dict[str, AgentInstance] = {}
        self._role_index: Dict[str, Set[str]] = {}  # role -> registration_ids
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> registration_ids
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> registration_ids
        self._lock = asyncio.Lock()
        self._health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

        # Built-in role priorities (higher = preferred)
        self._role_priorities = {
            "planner": 100,
            "coordinator": 90,
            "research": 80,
            "developer": 80,
            "coding": 80,
            "browser": 70,
            "research": 70,
            "writer": 60,
            "qa": 60,
            "deployment": 50,
            "security": 50,
            "memory": 40,
            "creative": 40,
            "data": 40,
            "communication": 30,
            "review": 30,
            "file": 30,
            "vision": 20,
            "audio": 20,
            "video": 20,
            "computer": 20,
        }

    async def start(self):
        """Start the registry background tasks."""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self):
        """Stop the registry background tasks."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    # ── Registration ──────────────────────────────────────────────────

    async def register(
        self,
        agent_type: str,
        factory: Callable[..., "AgentInterface"],
        role: "AgentRole" = None,
        capabilities: Optional["AgentCapabilities"] = None,
        metadata: Optional["AgentMetadata"] = None,
        default_config: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        priority: int = 0,
        identity: Optional["AgentIdentity"] = None,
    ) -> str:
        """Register a new agent type.

        Args:
            agent_type: Unique type identifier (e.g., "core", "automation:research")
            factory: Async factory function returning AgentInterface
            role: Agent role (defaults to COORDINATOR)
            capabilities: Capabilities this agent provides
            metadata: Metadata about the agent
            default_config: Default configuration
            tags: Tags for discovery
            priority: Routing priority (higher = preferred)
            identity: Explicit identity (generated if not provided)

        Returns:
            Registration ID
        """
        if role is None:
            role = AgentRole.COORDINATOR

        identity = identity or TypesAgentIdentity(role=role)
        reg_id = f"{agent_type}-{identity.agent_id}"

        registration = AgentRegistration(
            identity=identity,
            agent_type=agent_type,
            factory=factory,
            default_config=default_config or {},
            capabilities=capabilities or AgentCapabilities(),
            metadata=metadata or AgentMetadata(),
            tags=tags or set(),
            enabled=True,
            priority=priority or self._role_priorities.get(role.value if role else "coordinator", 0),
            registration_id=reg_id,
        )

        async with self._lock:
            self._registrations[reg_id] = registration
            self._update_indexes(reg_id, registration)
            logger.info(f"Registered agent: {reg_id} (role={role.value if role else 'custom'})")

        return reg_id

    async def unregister(self, registration_id: str) -> bool:
        """Unregister an agent type."""
        async with self._lock:
            if registration_id not in self._registrations:
                return False

            reg = self._registrations.pop(registration_id)
            self._remove_from_indexes(registration_id, reg)
            logger.info(f"Unregistered agent: {registration_id}")
            return True

    def _update_indexes(self, reg_id: str, reg: AgentRegistration) -> None:
        # Role index
        self._role_index.setdefault(reg.identity.role.value, set()).add(reg_id)

        # Capability index
        for cap in reg.capabilities.capabilities:
            self._capability_index.setdefault(cap, set()).add(reg_id)

        # Tag index
        for tag in reg.tags:
            self._tag_index.setdefault(tag, set()).add(reg_id)

    def _remove_from_indexes(self, reg_id: str, reg: AgentRegistration) -> None:
        # Role index
        if reg.identity.role.value in self._role_index:
            self._role_index[reg.identity.role.value].discard(reg_id)

        # Capability index
        for cap in reg.capabilities.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap].discard(reg_id)

        # Tag index
        for tag in reg.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(reg_id)

    # ── Discovery ─────────────────────────────────────────────────────

    def get_registration(self, registration_id: str) -> Optional[AgentRegistration]:
        """Get registration by ID."""
        return self._registrations.get(registration_id)

    def list_registrations(
        self,
        role: Optional["AgentRole"] = None,
        capability: Optional[str] = None,
        tag: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[AgentRegistration]:
        """List registrations with optional filters."""
        results = list(self._registrations.values())

        if enabled_only:
            results = [r for r in results if r.enabled]

        if role:
            results = [r for r in results if r.identity.role == role]

        if capability:
            results = [r for r in results if r.capabilities.has(capability)]

        if tag:
            results = [r for r in results if tag in r.tags]

        # Sort by priority (descending)
        results.sort(key=lambda r: r.priority, reverse=True)
        return results

    def find_by_capability(self, capability: str) -> List[AgentRegistration]:
        """Find all registrations supporting a capability."""
        reg_ids = self._capability_index.get(capability, set())
        return [self._registrations[reg_id] for reg_id in reg_ids if reg_id in self._registrations]

    def find_by_role(self, role: "AgentRole") -> List[AgentRegistration]:
        """Find all registrations for a role."""
        reg_ids = self._role_index.get(role.value, set())
        return [self._registrations[rid] for rid in reg_ids if rid in self._registrations]

    def find_best_for_capability(
        self,
        capability: str,
        role: Optional["AgentRole"] = None,
    ) -> Optional[AgentRegistration]:
        """Find the best agent for a capability (highest priority)."""
        candidates = self.find_by_capability(capability)
        if role:
            candidates = [c for c in candidates if c.identity.role == role]

        if not candidates:
            return None

        # Sort by priority and return highest
        return max(candidates, key=lambda r: r.priority)

    def query(
        self,
        capabilities: Optional[List[str]] = None,
        role: Optional["AgentRole"] = None,
        tags: Optional[Set[str]] = None,
        min_priority: int = 0,
    ) -> List[AgentRegistration]:
        """Query registrations with complex filters."""
        results = list(self._registrations.values())

        if capabilities:
            for cap in capabilities:
                results = [r for r in results if r.capabilities.has(cap)]

        if role:
            results = [r for r in results if r.identity.role == role]

        if tags:
            results = [r for r in results if tags.issubset(r.tags)]

        results = [r for r in results if r.priority >= min_priority and r.enabled]

        results.sort(key=lambda r: r.priority, reverse=True)
        return results

    # ── Instance Management ───────────────────────────────────────────

    async def create_instance(
        self,
        registration_id: str,
        config: Optional[Dict[str, Any]] = None,
        instance_id: Optional[str] = None,
    ) -> "AgentInterface":
        """Create an agent instance from a registration."""
        registration = self.get_registration(registration_id)
        if not registration:
            raise ValueError(f"Registration not found: {registration_id}")

        if not registration.enabled:
            raise RuntimeError(f"Agent type is disabled: {registration_id}")

        merged_config = {**registration.default_config, **(config or {})}

        instance = await registration.factory(**merged_config)

        if instance_id:
            instance.identity.instance_id = instance_id

        await instance.initialize({})

        # Track instance
        async with self._lock:
            inst = AgentInstance(
                registration=registration,
                instance=instance,
                weak_ref=weakref.ref(instance),
            )
            self._instances[instance.identity.agent_id] = inst

        return instance

    def get_instance(self, instance_id: str) -> Optional["AgentInstance"]:
        """Get a running instance by ID."""
        return self._instances.get(instance_id)

    def list_instances(self, include_stopped: bool = False) -> List["AgentInstance"]:
        """List all running instances."""
        instances = list(self._instances.values())
        if not include_stopped:
            instances = [i for i in instances if i.instance.state != "terminated"]
        return instances

    async def destroy_instance(self, instance_id: str, graceful: bool = True) -> bool:
        """Destroy an agent instance."""
        inst = self._instances.get(instance_id)
        if not inst:
            return False

        await inst.instance.shutdown(graceful)

        async with self._lock:
            self._instances.pop(instance_id, None)

        return True

    # ── Capability-Based Routing ──────────────────────────────────────

    async def route_task(
        self,
        task_spec: "TaskSpec",
        strategy: str = "best_match",
    ) -> Optional["AgentInterface"]:
        """Route a task to the best available agent.

        Args:
            task_spec: Task specification with requirements
            strategy: Routing strategy ("best_match", "least_loaded", "round_robin")

        Returns:
            Agent instance or None if no suitable agent found
        """
        # Find candidates based on required capabilities
        candidates = []

        for cap in task_spec.required_capabilities:
            candidates.extend(self.find_by_capability(cap))

        if task_spec.preferred_agent_role:
            role_candidates = self.find_by_role(task_spec.preferred_agent_role)
            candidates = [c for c in candidates if c in role_candidates] or role_candidates

        # Filter by model preference
        if task_spec.preferred_model:
            candidates = [c for c in candidates if task_spec.preferred_model in c.metadata.model_requirements or not c.metadata.model_requirements]

        if not candidates:
            return None

        # Select based on strategy
        if strategy == "least_loaded":
            # Find agent with fewest active tasks
            best = min(
                candidates,
                key=lambda r: self._get_instance_load(r.identity.agent_id) if self._get_instance_load(r.identity.agent_id) >= 0 else float("inf"),
            )
        elif strategy == "round_robin":
            # Simple round-robin (track last used)
            pass  # Implement if needed
        else:  # best_match
            best = max(candidates, key=lambda r: r.priority)

        # Create or reuse instance
        return await self.create_instance(best.registration_id)

    def _get_instance_load(self, agent_id: str) -> int:
        inst = self._instances.get(agent_id)
        if not inst:
            return 0
        return inst.active_task_count

    # ── Health Monitoring ────────────────────────────────────────────

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self._running:
            try:
                await self._check_all_instances()
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

            await asyncio.sleep(self._health_check_interval)

    async def _check_all_instances(self):
        """Check health of all running instances."""
        for inst in list(self._instances.values()):
            if inst.instance.state in (AgentLifecycleState.TERMINATED, AgentLifecycleState.UNHEALTHY):
                continue

            try:
                health = await asyncio.wait_for(inst.instance.health_check(), timeout=10.0)
                inst.health_status = health.status
                inst.last_health_check = time.time()

                if health.status == AgentHealthStatus.UNHEALTHY:
                    logger.warning(f"Agent {inst.identity.agent_id} unhealthy: {health.details}")
                    await self._handle_unhealthy_agent(inst)
            except asyncio.TimeoutError:
                logger.warning(f"Health check timeout for {inst.identity.agent_id}")
                inst.health_status = AgentHealthStatus.UNHEALTHY
            except Exception as e:
                logger.error(f"Health check failed for {inst.identity.agent_id}: {e}")
                inst.health_status = AgentHealthStatus.UNHEALTHY

    async def _handle_unhealthy_agent(self, inst: "AgentInstance"):
        """Handle an unhealthy agent (could trigger failover, alert, etc.)."""
        # Mark as degraded
        inst.health_status = AgentHealthStatus.DEGRADED

        # Could implement automatic failover here
        logger.info(f"Agent {inst.identity.agent_id} marked as degraded")

    def get_health_status(self, instance_id: str) -> Optional["AgentHealthStatus"]:
        """Get health status for an instance."""
        inst = self._instances.get(instance_id)
        if not inst:
            return None
        return inst.health_status

    async def force_health_check(self, instance_id: str) -> Optional["AgentHealth"]:
        """Force an immediate health check."""
        inst = self._instances.get(instance_id)
        if not inst:
            return None

        try:
            health = await asyncio.wait_for(inst.instance.health_check(), timeout=10.0)
            inst.health_status = health.status
            inst.last_health_check = time.time()
            return health
        except Exception as e:
            logger.error(f"Forced health check failed for {instance_id}: {e}")
            return None

    # ── Status & Inspection ──────────────────────────────────────────

    def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status."""
        return {
            "registrations": len(self._registrations),
            "instances": len(self._instances),
            "roles": list(self._role_index.keys()),
            "capabilities": list(self._capability_index.keys()),
            "tags": list(self._tag_index.keys()),
        }

    def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for an instance."""
        inst = self._instances.get(instance_id)
        if not inst:
            return None

        return {
            "instance_id": instance_id,
            "agent_id": inst.identity.agent_id,
            "role": inst.identity.role.value,
            "state": inst.instance.state.value,
            "health": inst.health_status.value if inst.health_status else "unknown",
            "active_tasks": inst.active_task_count,
            "completed": inst.total_tasks_completed,
            "failed": inst.total_tasks_failed,
            "last_error": inst.last_error,
            "created_at": inst.created_at,
            "last_health_check": inst.last_health_check,
        }

    def get_capability_coverage(self) -> Dict[str, int]:
        """Get count of agents per capability."""
        return {cap: len(regs) for cap, regs in self._capability_index.items()}

    def get_role_distribution(self) -> Dict[str, int]:
        """Get count of instances per role."""
        dist = {}
        for inst in self._instances.values():
            role = inst.identity.role.value
            dist[role] = dist.get(role, 0) + 1
        return dist

    # ── Configuration ────────────────────────────────────────────────

    def enable_registration(self, registration_id: str) -> bool:
        """Enable a registration."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return False
        reg.enabled = True
        reg.updated_at = time.time()
        return True

    def disable_registration(self, registration_id: str) -> bool:
        """Disable a registration (prevents new instances)."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return False
        reg.enabled = False
        reg.updated_at = time.time()
        return True

    def update_registration_priority(self, registration_id: str, priority: int) -> bool:
        """Update routing priority for a registration."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return False
        reg.priority = priority
        reg.updated_at = time.time()
        return True


# =============================================================================
# Global Registry Instance
# =============================================================================

_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


async def initialize_agent_registry() -> AgentRegistry:
    """Initialize and start the global agent registry."""
    registry = get_agent_registry()
    await registry.start()
    return registry


async def shutdown_agent_registry():
    """Shutdown the global agent registry."""
    global _global_registry
    if _global_registry:
        await _global_registry.stop()
        _global_registry = None