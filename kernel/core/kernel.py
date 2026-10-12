"""
AetherOS Agent Kernel 1.0 — Core Kernel

The central orchestration layer for the agent operating system.
Manages agent lifecycle, intent admission, authority, capabilities,
resources, scheduling, context, memory, and observability.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from pathlib import Path

from kernel.core.types import (
    AgentLifecycleState,
    AgentPriority,
    AgentProcess,
    AgentIdentity,
    Intent,
    AuthorityGrant,
    CapabilityDescriptor,
    CapabilityInvocation,
    CapabilityRiskLevel,
    Checkpoint,
    KernelConfig,
    KernelEvent,
    ResourceBudget,
    ResourceAllocation,
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
    ICapabilityProvider,
    IMemoryProvider,
    IModelProvider,
    IResourceManager,
    IScheduler,
    IEventBus,
    IPolicyEngine,
)
from kernel.event_bus import EventBus, EventTopics
from kernel.lifecycle import LifecycleManager, ServiceRegistration, ComponentState

logger = logging.getLogger(__name__)


class AgentKernel:
    """
    AetherOS Agent Kernel 1.0
    
    The foundational runtime layer for agent-native computing.
    
    Responsibilities:
    - Agent process lifecycle management
    - Intent admission and authority grants
    - Capability registration and invocation
    - Resource scheduling and allocation
    - Context and memory coordination
    - Event bus and observability
    - Checkpointing and recovery
    - Policy enforcement and security boundary
    """

    def __init__(self, config: KernelConfig = None):
        self.config = config or KernelConfig()
        self._booted = False
        self._shutdown_flag = False
        self._boot_time: Optional[float] = None
        self._lock = threading.RLock()

        # Core services
        self.event_bus = EventBus() if self.config.enable_event_bus else None
        self.lifecycle = LifecycleManager(self.event_bus) if self.event_bus else None

        # Kernel subsystems (initialized in boot)
        self.agent_manager: Optional["AgentProcessManager"] = None
        self.intent_manager: Optional["IntentManager"] = None
        self.authority_manager: Optional["AuthorityManager"] = None
        self.capability_manager: Optional["CapabilityManager"] = None
        self.capability_invoker: Optional["CapabilityInvoker"] = None
        self.resource_manager: Optional["ResourceManager"] = None
        self.scheduler: Optional["KernelScheduler"] = None
        self.context_manager: Optional["ContextManager"] = None
        self.memory_manager: Optional["MemoryManager"] = None
        self.model_manager: Optional["ModelManager"] = None
        self.tool_manager: Optional["ToolManager"] = None
        self.task_manager: Optional["TaskManager"] = None
        self.checkpoint_manager: Optional["CheckpointManager"] = None
        self.recovery_manager: Optional["RecoveryManager"] = None
        self.policy_engine: Optional["PolicyEngine"] = None
        self.governance_engine: Optional["GovernanceEngine"] = None
        self.security_boundary: Optional["SecurityBoundary"] = None
        self.provenance_engine: Optional["ProvenanceEngine"] = None
        self.audit_engine: Optional["AuditEngine"] = None
        self.observability_engine: Optional["ObservabilityEngine"] = None
        self.cost_manager: Optional["CostManager"] = None
        self.latency_manager: Optional["LatencyManager"] = None
        self.artifact_manager: Optional["ArtifactManager"] = None
        self.network_manager: Optional["NetworkManager"] = None
        self.device_manager: Optional["DeviceManager"] = None
        self.human_oversight_manager: Optional["HumanOversightManager"] = None
        self.hypervisor: Optional["AgentHypervisor"] = None

        # Registries
        self._capability_providers: Dict[str, ICapabilityProvider] = {}
        self._memory_providers: Dict[str, IMemoryProvider] = {}
        self._model_providers: Dict[str, IModelProvider] = {}

        # State
        self._agent_processes: Dict[str, AgentProcess] = {}
        self._intent_index: Dict[str, Intent] = {}
        self._authority_grants: Dict[str, AuthorityGrant] = {}
        self._capability_descriptors: Dict[str, CapabilityDescriptor] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}

        # Background tasks
        self._state_save_timer: Optional[threading.Thread] = None
        self._checkpoint_timer: Optional[threading.Thread] = None
        self._health_check_timer: Optional[threading.Thread] = None

        # Metrics
        self._metrics = {
            "agents_created": 0,
            "agents_started": 0,
            "agents_completed": 0,
            "agents_failed": 0,
            "intents_admitted": 0,
            "intents_denied": 0,
            "capabilities_invoked": 0,
            "capabilities_denied": 0,
            "checkpoints_created": 0,
            "recoveries_attempted": 0,
            "recoveries_succeeded": 0,
            "policy_denials": 0,
            "approvals_requested": 0,
            "approvals_granted": 0,
            "approvals_denied": 0,
        }

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def boot(self) -> None:
        """Boot the kernel and initialize all subsystems."""
        if self._booted:
            logger.warning("Kernel: already booted")
            return

        self._boot_time = time.time()
        logger.info("AetherOS Agent Kernel 1.0 booting...")

        # Register core services
        self._register_core_services()

        # Initialize subsystems
        self._initialize_subsystems()

        # Wire event listeners
        self._wire_event_listeners()

        # Start lifecycle manager
        if self.lifecycle:
            self.lifecycle.start()

        # Start background tasks
        self._start_background_tasks()

        # Install signal handlers
        self._install_signal_handlers()

        self._booted = True
        boot_duration = time.time() - self._boot_time
        logger.info("AetherOS Agent Kernel 1.0 booted in %.2fs", boot_duration)

        if self.event_bus:
            self.event_bus.emit(EventTopics.LIFECYCLE_STARTED, {
                "boot_time": boot_duration,
                "version": "1.0.0",
                "kernel": "AgentKernel",
            })

    def _register_core_services(self) -> None:
        """Register core kernel services with lifecycle manager."""
        if not self.lifecycle:
            return

        services = [
            ServiceRegistration(
                name="event_bus",
                description="Kernel event system",
                health_fn=lambda: self.event_bus is not None,
            ),
            ServiceRegistration(
                name="agent_manager",
                description="Agent process lifecycle manager",
                health_fn=lambda: self.agent_manager is not None,
            ),
            ServiceRegistration(
                name="intent_manager",
                description="Intent admission and tracking",
                health_fn=lambda: self.intent_manager is not None,
            ),
            ServiceRegistration(
                name="authority_manager",
                description="Authority grant management",
                health_fn=lambda: self.authority_manager is not None,
            ),
            ServiceRegistration(
                name="capability_manager",
                description="Capability registration and discovery",
                health_fn=lambda: self.capability_manager is not None,
            ),
            ServiceRegistration(
                name="resource_manager",
                description="Resource allocation and scheduling",
                health_fn=lambda: self.resource_manager is not None,
            ),
            ServiceRegistration(
                name="scheduler",
                description="Agent scheduling",
                health_fn=lambda: self.scheduler is not None and self.scheduler.is_healthy(),
            ),
            ServiceRegistration(
                name="context_manager",
                description="Context allocation and coordination",
                health_fn=lambda: self.context_manager is not None,
            ),
            ServiceRegistration(
                name="memory_manager",
                description="Memory coordination",
                health_fn=lambda: self.memory_manager is not None,
            ),
            ServiceRegistration(
                name="model_manager",
                description="Model routing and selection",
                health_fn=lambda: self.model_manager is not None,
            ),
            ServiceRegistration(
                name="checkpoint_manager",
                description="Checkpoint and recovery",
                health_fn=lambda: self.checkpoint_manager is not None,
            ),
            ServiceRegistration(
                name="policy_engine",
                description="Policy evaluation and enforcement",
                health_fn=lambda: self.policy_engine is not None,
            ),
            ServiceRegistration(
                name="security_boundary",
                description="Security boundary enforcement",
                health_fn=lambda: self.security_boundary is not None,
            ),
            ServiceRegistration(
                name="observability_engine",
                description="Tracing, metrics, and observability",
                health_fn=lambda: self.observability_engine is not None,
            ),
            ServiceRegistration(
                name="hypervisor",
                description="Agent capsule runtime (isolation, enforcement, recovery)",
                health_fn=lambda: self.hypervisor is not None,
            ),
        ]

        for svc in services:
            self.lifecycle.register(svc)

    def _initialize_subsystems(self) -> None:
        """Initialize all kernel subsystems."""
        # Import here to avoid circular dependencies
        from kernel.core.agent_process_manager import AgentProcessManager
        from kernel.core.intent_manager import IntentManager
        from kernel.core.authority_manager import AuthorityManager
        from kernel.core.capability_manager import CapabilityManager
        from kernel.core.capability_invoker import CapabilityInvoker
        from kernel.core.resource_manager import ResourceManager
        from kernel.core.scheduler import KernelScheduler
        from kernel.core.context_manager import ContextManager
        from kernel.core.memory_manager import MemoryManager
        from kernel.core.model_manager import ModelManager
        from kernel.core.tool_manager import ToolManager
        from kernel.core.task_manager import TaskManager
        from kernel.core.checkpoint_manager import CheckpointManager
        from kernel.core.recovery_manager import RecoveryManager
        from kernel.core.policy_engine import PolicyEngine
        from kernel.core.governance_engine import GovernanceEngine
        from kernel.core.security_boundary import SecurityBoundary
        from kernel.core.provenance_engine import ProvenanceEngine
        from kernel.core.audit_engine import AuditEngine
        from kernel.core.observability_engine import ObservabilityEngine
        from kernel.core.cost_manager import CostManager
        from kernel.core.latency_manager import LatencyManager
        from kernel.core.artifact_manager import ArtifactManager
        from kernel.core.network_manager import NetworkManager
        from kernel.core.device_manager import DeviceManager
        from kernel.core.human_oversight_manager import HumanOversightManager
        from kernel.core.hypervisor import AgentHypervisor

        # Initialize in dependency order
        self.resource_manager = ResourceManager(self.config, self.event_bus)
        self.policy_engine = PolicyEngine(self.config, self.event_bus)
        self.security_boundary = SecurityBoundary(self.config, self.event_bus)
        self.authority_manager = AuthorityManager(self.config, self.event_bus, self.policy_engine, self.security_boundary)
        self.authority_manager.set_resource_manager(self.resource_manager)
        self.intent_manager = IntentManager(self.config, self.event_bus, self.authority_manager, self.policy_engine)
        self.capability_manager = CapabilityManager(self.config, self.event_bus)
        self.capability_invoker = CapabilityInvoker(self.config, self.event_bus, self.capability_manager, self.authority_manager, self.policy_engine, self.security_boundary, self.resource_manager)
        self.scheduler = KernelScheduler(self.config, self.event_bus, self.resource_manager)
        self.context_manager = ContextManager(self.config, self.event_bus)
        self.memory_manager = MemoryManager(self.config, self.event_bus)
        self.model_manager = ModelManager(self.config, self.event_bus)
        self.tool_manager = ToolManager(self.config, self.event_bus, self.capability_manager)
        self.task_manager = TaskManager(self.config, self.event_bus)
        self.checkpoint_manager = CheckpointManager(self.config, self.event_bus)
        self.recovery_manager = RecoveryManager(self.config, self.event_bus, self.checkpoint_manager)
        self.governance_engine = GovernanceEngine(self.config, self.event_bus)
        self.provenance_engine = ProvenanceEngine(self.config, self.event_bus)
        self.audit_engine = AuditEngine(self.config, self.event_bus)
        self.observability_engine = ObservabilityEngine(self.config, self.event_bus)
        self.cost_manager = CostManager(self.config, self.event_bus)
        self.latency_manager = LatencyManager(self.config, self.event_bus)
        self.artifact_manager = ArtifactManager(self.config, self.event_bus)
        self.network_manager = NetworkManager(self.config, self.event_bus)
        self.device_manager = DeviceManager(self.config, self.event_bus)
        self.human_oversight_manager = HumanOversightManager(self.config, self.event_bus)
        self.hypervisor = AgentHypervisor(self.config, self.event_bus, self)
        # Capability resolution for the intent pipeline (§5): unknown
        # requested capabilities are stripped at validation time.
        self.intent_manager.bind_capability_manager(self.capability_manager)
        self.agent_manager = AgentProcessManager(self.config, self.event_bus, self)

        # Set kernel reference on agent processes
        for process in self._agent_processes.values():
            process._kernel = self
            if self.event_bus:
                process._event_bus = self.event_bus

    def _wire_event_listeners(self) -> None:
        """Wire cross-subsystem event listeners."""
        if not self.event_bus:
            return

        # Agent lifecycle events
        self.event_bus.subscribe("agent.lifecycle.transition", self._on_agent_transition)
        self.event_bus.subscribe("agent.capability.invoke", self._on_capability_invoke)
        self.event_bus.subscribe("agent.checkpoint.request", self._on_checkpoint_request)
        self.event_bus.subscribe("agent.recovery.request", self._on_recovery_request)

        # Intent events
        self.event_bus.subscribe("intent.created", self._on_intent_created)
        self.event_bus.subscribe("intent.admitted", self._on_intent_admitted)
        self.event_bus.subscribe("intent.denied", self._on_intent_denied)

        # Resource events
        self.event_bus.subscribe("resource.allocated", self._on_resource_allocated)
        self.event_bus.subscribe("resource.released", self._on_resource_released)
        self.event_bus.subscribe("resource.exhausted", self._on_resource_exhausted)

        # Security events
        self.event_bus.subscribe("security.violation", self._on_security_violation)
        self.event_bus.subscribe("policy.denied", self._on_policy_denied)

        # Human oversight
        self.event_bus.subscribe("approval.requested", self._on_approval_requested)
        self.event_bus.subscribe("approval.granted", self._on_approval_granted)
        self.event_bus.subscribe("approval.denied", self._on_approval_denied)

    def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        if self.config.enable_state_persistence:
            self._state_save_timer = threading.Thread(
                target=self._state_save_loop,
                daemon=True,
                name="kernel-state-save",
            )
            self._state_save_timer.start()

        if self.config.checkpoint_interval_seconds > 0:
            self._checkpoint_timer = threading.Thread(
                target=self._checkpoint_loop,
                daemon=True,
                name="kernel-checkpoint",
            )
            self._checkpoint_timer.start()

        self._health_check_timer = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="kernel-health",
        )
        self._health_check_timer.start()

    def _install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        import signal

        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Kernel: received %s, shutting down...", sig_name)
            self.shutdown()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, RuntimeError):
            pass

    def shutdown(self) -> None:
        """Graceful kernel shutdown."""
        if self._shutdown_flag:
            return

        self._shutdown_flag = True
        logger.info("Kernel: shutting down...")

        # Hypervisor first: gracefully destroy live capsules (stops agents,
        # checkpoints, releases resources, revokes capsule secrets).
        if self.hypervisor:
            try:
                self.hypervisor.shutdown()
            except Exception as exc:
                logger.error("Error shutting down hypervisor: %s", exc)

        if self.event_bus:
            self.event_bus.emit(EventTopics.SYSTEM_SHUTDOWN, source="kernel")

        # Stop background timers (daemon threads; short join so shutdown is fast)
        for timer in [self._state_save_timer, self._checkpoint_timer, self._health_check_timer]:
            if timer:
                timer.join(timeout=0.2)

        # Checkpoint all running agents
        for process in self._agent_processes.values():
            if process.state in (AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING):
                try:
                    self.checkpoint_manager.create_checkpoint(process.agent_id)
                except Exception as exc:
                    logger.error("Failed to checkpoint agent %s: %s", process.agent_id, exc)

        # Release all resources
        for agent_id in list(self._agent_processes.keys()):
            self.resource_manager.release(agent_id)

        # Shutdown subsystems
        subsystems = [
            self.hypervisor,
            self.agent_manager, self.task_manager, self.scheduler,
            self.checkpoint_manager, self.recovery_manager,
            self.capability_invoker, self.capability_manager,
            self.authority_manager, self.intent_manager,
            self.context_manager, self.memory_manager, self.model_manager,
            self.tool_manager, self.resource_manager,
            self.policy_engine, self.governance_engine, self.security_boundary,
            self.provenance_engine, self.audit_engine, self.observability_engine,
            self.cost_manager, self.latency_manager, self.artifact_manager,
            self.network_manager, self.device_manager, self.human_oversight_manager,
        ]

        for subsystem in subsystems:
            if subsystem and hasattr(subsystem, 'shutdown'):
                try:
                    subsystem.shutdown()
                except Exception as exc:
                    logger.error("Error shutting down %s: %s", type(subsystem).__name__, exc)

        # Shutdown lifecycle
        if self.lifecycle:
            self.lifecycle.shutdown()

        # Shutdown event bus
        if self.event_bus:
            self.event_bus.shutdown()

        uptime = time.time() - (self._boot_time or time.time())
        logger.info("AetherOS Agent Kernel 1.0 shut down (uptime: %.1fs)", uptime)

    def is_running(self) -> bool:
        return self._booted and not self._shutdown_flag

    # -------------------------------------------------------------------------
    # Agent Process Management
    # -------------------------------------------------------------------------

    def create_agent_process(
        self,
        intent: Intent,
        identity: AgentIdentity = None,
        parent_agent_id: str = None,
        priority: AgentPriority = AgentPriority.NORMAL,
        resource_budget: ResourceBudget = None,
        security_profile: str = "standard",
    ) -> AgentProcess:
        """Create a new agent process from an intent."""
        if not self._booted:
            raise RuntimeError("Kernel not booted")

        # Admit intent (AdmissionResult object)
        admission = self.intent_manager.admit(intent)
        allowed = admission.allowed if hasattr(admission, "allowed") else admission["allowed"]
        reason = admission.reason if hasattr(admission, "reason") else admission["reason"]
        if not allowed:
            raise PermissionError(f"Intent denied: {reason}")

        # Create agent identity if not provided
        if identity is None:
            identity = AgentIdentity(
                agent_id=new_id("agent"),
                identity_type="agent",
                subject=intent.actor,
                display_name=f"Agent for: {intent.objective[:50]}",
                trust_level=2,  # T2_VERIFIED
                tenant=self.config.default_agent_budget.tenant if hasattr(self.config.default_agent_budget, 'tenant') else "default",
            )

        # Reuse authority grant from admission when available, else grant fresh.
        # IntentManager.admit() already creates a grant via AuthorityManager.
        admission_grant = getattr(admission, "authority_grant", None)
        if admission_grant is not None:
            admission_grant.agent_id = identity.agent_id
            authority = admission_grant
            # Ensure grant is indexed under the agent
            with self.authority_manager._lock:
                self.authority_manager._grants[authority.grant_id] = authority
                self.authority_manager._grant_index.setdefault(identity.agent_id, set()).add(authority.grant_id)
        else:
            authority = self.authority_manager.grant_authority(
                agent_id=identity.agent_id,
                intent=intent,
                parent_grant_id=None,
            )

        # Allocate resources (admission only reserves; allocate the real budget)
        budget = resource_budget or self.config.default_agent_budget
        try:
            allocation = self.resource_manager.allocate(identity.agent_id, budget)
        except Exception:
            # Fall back to the constrained grant resources if default budget is exhausted
            allocation = self.resource_manager.allocate(identity.agent_id, authority.resources)
        # Release the admission-time reservation now that the real allocation
        # exists; otherwise every admission leaks a reservation (the reserve()
        # id never matches the agent-keyed pop in allocate()).
        admission_reservation = (getattr(admission, "resource_allocation", None) or {})
        if isinstance(admission_reservation, dict) and admission_reservation.get("reservation_id"):
            try:
                self.resource_manager.release_reservation(
                    admission_reservation["reservation_id"])
            except Exception as exc:
                logger.debug("reservation release failed: %s", exc)

        # Create agent process
        process = AgentProcess(
            agent_id=identity.agent_id,
            process_id=new_id("proc"),
            parent_agent_id=parent_agent_id,
            tenant_id=identity.tenant,
            identity=identity,
            intent=intent,
            authority=authority,
            capabilities=list(authority.capabilities),
            state=AgentLifecycleState.CREATED,
            priority=priority,
            resource_budget=budget,
            resource_allocation=allocation,
            context_budget=self.config.default_context_budget,
            memory_scope=f"agent:{identity.agent_id}",
            security_profile=security_profile,
        )
        process._kernel = self
        process._event_bus = self.event_bus

        # Register process
        with self._lock:
            self._agent_processes[identity.agent_id] = process
            self._intent_index[intent.intent_id] = intent
            self._authority_grants[authority.grant_id] = authority

        self._metrics["agents_created"] += 1

        # Emit creation event
        if self.event_bus:
            self.event_bus.emit("agent.created", {
                "agent_id": identity.agent_id,
                "process_id": process.process_id,
                "intent_id": intent.intent_id,
                "parent_agent_id": parent_agent_id,
            })

        # Admit to scheduler
        if self.scheduler:
            self.scheduler.admit(process)

        return process

    def start_agent(self, agent_id: str) -> bool:
        """Start an admitted agent process."""
        process = self._agent_processes.get(agent_id)
        if not process:
            raise ValueError(f"Agent not found: {agent_id}")

        # Scheduler admission already moved CREATED -> ADMITTED; accept both.
        if process.state == AgentLifecycleState.CREATED:
            process.transition(AgentLifecycleState.ADMITTED)
        elif process.state != AgentLifecycleState.ADMITTED:
            raise ValueError(f"Agent not in CREATED/ADMITTED state: {process.state}")
        # Transition ADMITTED -> INITIALIZING, then the
        # AgentProcessManager drives INITIALIZING -> READY.
        process.transition(AgentLifecycleState.INITIALIZING)

        # Initialize agent runtime (transitions to READY on success)
        success = self.agent_manager.initialize_agent(process)

        if success:
            self._metrics["agents_started"] += 1
            return True
        else:
            try:
                process.transition(AgentLifecycleState.FAILED)
            except ValueError:
                pass
            return False

    def stop_agent(self, agent_id: str, reason: str = "stopped") -> bool:
        """Stop an agent process gracefully."""
        process = self._agent_processes.get(agent_id)
        if not process:
            return False

        # Checkpoint before stopping
        if process.state in (AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING):
            self.checkpoint_manager.create_checkpoint(agent_id)

        process.transition(AgentLifecycleState.CANCELLED)
        process.error = reason
        self.agent_manager.terminate_agent(process)

        # Release resources
        self.resource_manager.release(agent_id)

        return True

    def pause_agent(self, agent_id: str) -> bool:
        """Pause an agent process."""
        process = self._agent_processes.get(agent_id)
        if not process:
            return False

        if process.state == AgentLifecycleState.RUNNING:
            process.transition(AgentLifecycleState.PAUSED)
            self.checkpoint_manager.create_checkpoint(agent_id)
            return True
        return False

    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent process."""
        process = self._agent_processes.get(agent_id)
        if not process:
            return False

        if process.state == AgentLifecycleState.PAUSED:
            process.transition(AgentLifecycleState.READY)
            if self.scheduler:
                self.scheduler.schedule(process)
            return True
        return False

    def get_agent_process(self, agent_id: str) -> Optional[AgentProcess]:
        """Get an agent process by ID."""
        return self._agent_processes.get(agent_id)

    def list_agent_processes(self, state: AgentLifecycleState = None) -> List[AgentProcess]:
        """List all agent processes, optionally filtered by state."""
        with self._lock:
            processes = list(self._agent_processes.values())
        if state:
            processes = [p for p in processes if p.state == state]
        return processes

    # -------------------------------------------------------------------------
    # Intent Management
    # -------------------------------------------------------------------------

    def submit_intent(self, intent: Intent) -> Dict[str, Any]:
        """Submit an intent for admission."""
        return self.intent_manager.admit(intent)

    def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get an intent by ID."""
        return self._intent_index.get(intent_id)

    # -------------------------------------------------------------------------
    # Capability Management
    # -------------------------------------------------------------------------

    def register_capability(self, descriptor: CapabilityDescriptor, provider: ICapabilityProvider) -> None:
        """Register a capability with its provider."""
        self.capability_manager.register(descriptor, provider)
        self._capability_descriptors[descriptor.capability_id] = descriptor
        self._capability_providers[descriptor.capability_id] = provider

    def get_capability_descriptor(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        """Get a capability descriptor."""
        return self._capability_descriptors.get(capability_id)

    def invoke_capability(
        self,
        agent_id: str,
        capability_id: str,
        inputs: Dict[str, Any],
        intent_id: str = "",
    ) -> CapabilityInvocation:
        """Invoke a capability on behalf of an agent."""
        process = self._agent_processes.get(agent_id)
        if not process:
            raise ValueError(f"Agent not found: {agent_id}")

        if not process.authority:
            raise PermissionError("Agent has no authority grant")

        invocation = CapabilityInvocation(
            agent_id=agent_id,
            capability_id=capability_id,
            inputs=inputs,
            authority_grant_id=process.authority.grant_id,
            intent_id=intent_id or (process.intent.intent_id if process.intent else ""),
        )

        return self.capability_invoker.invoke(invocation)

    # -------------------------------------------------------------------------
    # Resource Management
    # -------------------------------------------------------------------------

    def get_resource_allocation(self, agent_id: str) -> Optional[ResourceAllocation]:
        """Get current resource allocation for an agent."""
        return self.resource_manager.get_usage(agent_id)

    def get_available_resources(self) -> ResourceBudget:
        """Get available system resources."""
        return self.resource_manager.get_available()

    # -------------------------------------------------------------------------
    # Checkpoint/Recovery
    # -------------------------------------------------------------------------

    def create_checkpoint(self, agent_id: str) -> Checkpoint:
        """Create a checkpoint for an agent."""
        return self.checkpoint_manager.create_checkpoint(agent_id)

    def restore_checkpoint(self, checkpoint_id: str) -> AgentProcess:
        """Restore an agent from a checkpoint."""
        return self.recovery_manager.restore(checkpoint_id)

    # -------------------------------------------------------------------------
    # Emergency stop / fail-closed control plane (§31-§32)
    # -------------------------------------------------------------------------

    def emergency_stop(self, scope: str = "global", reason: str = "operator request") -> Dict[str, Any]:
        """Activate AETHEROS KERNEL STOP. Independent of any LLM; cannot be
        overridden by agent output. Halts capability invocation fail-closed."""
        self.security_boundary.activate_emergency_stop(scope)
        stopped = 0
        for process in list(self._agent_processes.values()):
            if process.state in (AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING,
                                 AgentLifecycleState.READY, AgentLifecycleState.PAUSED):
                try:
                    process.transition(AgentLifecycleState.PAUSED)
                    stopped += 1
                except ValueError:
                    pass
        if self.event_bus:
            self.event_bus.emit("kernel.emergency_stop", {"scope": scope, "reason": reason,
                                                          "agents_paused": stopped})
        logger.critical("KERNEL STOP activated (scope=%s reason=%s agents_paused=%d)", scope, reason, stopped)
        return {"stopped": True, "scope": scope, "agents_paused": stopped}

    def emergency_resume(self, scope: str = "global") -> Dict[str, Any]:
        """Clear a previous emergency stop. Agents stay PAUSED until resumed."""
        self.security_boundary.deactivate_emergency_stop(scope)
        if self.event_bus:
            self.event_bus.emit("kernel.emergency_stop_cleared", {"scope": scope})
        return {"stopped": False, "scope": scope}

    def is_stopped(self) -> bool:
        """Fail-closed status check."""
        return bool(getattr(self.security_boundary, "_emergency_stop_active", False))

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_agent_transition(self, event: KernelEvent) -> None:
        """Handle agent lifecycle transitions."""
        agent_id = event.data.get("agent_id")
        to_state = event.data.get("to_state")

        if to_state == AgentLifecycleState.COMPLETED.value:
            self._metrics["agents_completed"] += 1
            self.resource_manager.release(agent_id)
        elif to_state == AgentLifecycleState.FAILED.value:
            self._metrics["agents_failed"] += 1
            self.resource_manager.release(agent_id)

    def _on_capability_invoke(self, event: KernelEvent) -> None:
        """Handle capability invocation."""
        self._metrics["capabilities_invoked"] += 1
        if event.data.get("denied"):
            self._metrics["capabilities_denied"] += 1

    def _on_checkpoint_request(self, event: KernelEvent) -> None:
        """Handle checkpoint request."""
        agent_id = event.data.get("agent_id")
        self.checkpoint_manager.create_checkpoint(agent_id)

    def _on_recovery_request(self, event: KernelEvent) -> None:
        """Handle recovery request."""
        checkpoint_id = event.data.get("checkpoint_id")
        self.recovery_manager.restore(checkpoint_id)

    def _on_intent_created(self, event: KernelEvent) -> None:
        """Handle intent creation."""
        self._metrics["intents_admitted"] += 1

    def _on_intent_admitted(self, event: KernelEvent) -> None:
        """Handle intent admission."""
        pass

    def _on_intent_denied(self, event: KernelEvent) -> None:
        """Handle intent denial."""
        self._metrics["intents_denied"] += 1

    def _on_resource_allocated(self, event: KernelEvent) -> None:
        """Handle resource allocation."""
        pass

    def _on_resource_released(self, event: KernelEvent) -> None:
        """Handle resource release."""
        pass

    def _on_resource_exhausted(self, event: KernelEvent) -> None:
        """Handle resource exhaustion."""
        agent_id = event.data.get("agent_id")
        if agent_id and self.scheduler:
            self.scheduler.preempt(agent_id)

    def _on_security_violation(self, event: KernelEvent) -> None:
        """Handle security violation."""
        logger.critical("SECURITY VIOLATION: %s", event.data)
        agent_id = event.data.get("agent_id")
        if agent_id:
            self.stop_agent(agent_id, reason="security_violation")

    def _on_policy_denied(self, event: KernelEvent) -> None:
        """Handle policy denial."""
        self._metrics["policy_denials"] += 1

    def _on_approval_requested(self, event: KernelEvent) -> None:
        """Handle approval request."""
        self._metrics["approvals_requested"] += 1

    def _on_approval_granted(self, event: KernelEvent) -> None:
        """Handle approval grant."""
        self._metrics["approvals_granted"] += 1

    def _on_approval_denied(self, event: KernelEvent) -> None:
        """Handle approval denial."""
        self._metrics["approvals_denied"] += 1

    # -------------------------------------------------------------------------
    # Background Loops
    # -------------------------------------------------------------------------

    def _state_save_loop(self) -> None:
        """Periodic state persistence."""
        while not self._shutdown_flag:
            time.sleep(30)
            try:
                self._persist_state()
            except Exception as exc:
                logger.error("State save failed: %s", exc)

    def _checkpoint_loop(self) -> None:
        """Periodic checkpointing."""
        while not self._shutdown_flag:
            time.sleep(self.config.checkpoint_interval_seconds)
            try:
                for process in self._agent_processes.values():
                    if process.state in (AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING):
                        self.checkpoint_manager.create_checkpoint(process.agent_id)
            except Exception as exc:
                logger.error("Checkpoint loop failed: %s", exc)

    def _health_check_loop(self) -> None:
        """Periodic health checks."""
        while not self._shutdown_flag:
            time.sleep(self.config.health_check_interval_seconds)
            try:
                self._run_health_checks()
            except Exception as exc:
                logger.error("Health check failed: %s", exc)

    def _persist_state(self) -> None:
        """Persist kernel state."""
        # Implemented by state manager
        pass

    def _run_health_checks(self) -> None:
        """Run health checks on all subsystems."""
        if self.lifecycle:
            health = self.lifecycle.health_summary()
            if health["failed"] > 0:
                logger.warning("Kernel health check: %d components failed", health["failed"])

    # -------------------------------------------------------------------------
    # Status and Metrics
    # -------------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Get kernel health status."""
        return {
            "booted": self._booted,
            "running": self.is_running(),
            "uptime_seconds": time.time() - (self._boot_time or time.time()),
            "services": self.lifecycle.health_summary() if self.lifecycle else {},
            "agents": {
                "total": len(self._agent_processes),
                "running": len([p for p in self._agent_processes.values() if p.state == AgentLifecycleState.RUNNING]),
                "paused": len([p for p in self._agent_processes.values() if p.state == AgentLifecycleState.PAUSED]),
                "failed": len([p for p in self._agent_processes.values() if p.state == AgentLifecycleState.FAILED]),
            },
            "capabilities": len(self._capability_descriptors),
            "intents": len(self._intent_index),
            "checkpoints": len(self._checkpoints),
        }

    def status(self) -> Dict[str, Any]:
        """Get detailed kernel status."""
        return {
            "kernel": {
                "booted": self._booted,
                "running": self.is_running(),
                "uptime_seconds": time.time() - (self._boot_time or time.time()),
                "version": "1.0.0",
            },
            "health": self.health(),
            "metrics": self._metrics,
            "subsystems": {
                "agent_manager": self.agent_manager.get_stats() if self.agent_manager else {},
                "intent_manager": self.intent_manager.get_stats() if self.intent_manager else {},
                "authority_manager": self.authority_manager.get_stats() if self.authority_manager else {},
                "capability_manager": self.capability_manager.get_stats() if self.capability_manager else {},
                "resource_manager": self.resource_manager.get_stats() if self.resource_manager else {},
                "scheduler": self.scheduler.get_stats() if self.scheduler else {},
                "context_manager": self.context_manager.get_stats() if self.context_manager else {},
                "memory_manager": self.memory_manager.get_stats() if self.memory_manager else {},
                "model_manager": self.model_manager.get_stats() if self.model_manager else {},
                "tool_manager": self.tool_manager.get_stats() if self.tool_manager else {},
                "task_manager": self.task_manager.get_stats() if self.task_manager else {},
                "checkpoint_manager": self.checkpoint_manager.get_stats() if self.checkpoint_manager else {},
                "recovery_manager": self.recovery_manager.get_stats() if self.recovery_manager else {},
                "policy_engine": self.policy_engine.get_stats() if self.policy_engine else {},
                "governance_engine": self.governance_engine.get_stats() if self.governance_engine else {},
                "security_boundary": self.security_boundary.get_stats() if self.security_boundary else {},
                "provenance_engine": self.provenance_engine.get_stats() if self.provenance_engine else {},
                "audit_engine": self.audit_engine.get_stats() if self.audit_engine else {},
                "observability_engine": self.observability_engine.get_stats() if self.observability_engine else {},
                "cost_manager": self.cost_manager.get_stats() if self.cost_manager else {},
                "latency_manager": self.latency_manager.get_stats() if self.latency_manager else {},
                "artifact_manager": self.artifact_manager.get_stats() if self.artifact_manager else {},
                "network_manager": self.network_manager.get_stats() if self.network_manager else {},
                "device_manager": self.device_manager.get_stats() if self.device_manager else {},
                "human_oversight_manager": self.human_oversight_manager.get_stats() if self.human_oversight_manager else {},
                "hypervisor": self.hypervisor.get_stats() if self.hypervisor else {},
            },
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get kernel metrics."""
        return dict(self._metrics)


# Global kernel instance (singleton pattern for process)
_kernel_instance: Optional[AgentKernel] = None


def get_kernel() -> AgentKernel:
    """Get the global kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = AgentKernel()
    return _kernel_instance


def set_kernel(kernel: AgentKernel) -> None:
    """Set the global kernel instance (for testing)."""
    global _kernel_instance
    _kernel_instance = kernel


def create_kernel(config: KernelConfig = None) -> AgentKernel:
    """Create and boot a new kernel instance."""
    kernel = AgentKernel(config)
    kernel.boot()
    return kernel