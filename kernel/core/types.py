"""
AetherOS Agent Kernel 1.0 — Core Canonical Types

Single source of truth for all kernel data structures.
These types form the Intent ABI and Capability ABI contracts.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from pathlib import Path


def _now() -> float:
    return time.time()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Enums — Kernel-level constants
# =============================================================================


class AgentLifecycleState(str, enum.Enum):
    """Canonical agent process lifecycle states."""
    CREATED = "created"
    ADMITTED = "admitted"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    PAUSED = "paused"
    CHECKPOINTING = "checkpointing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


class AgentPriority(str, enum.Enum):
    """Scheduling priority classes."""
    INTERACTIVE = "interactive"
    REAL_TIME = "real_time"
    HIGH_PRIORITY = "high_priority"
    NORMAL = "normal"
    BACKGROUND = "background"
    BATCH = "batch"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"
    AUTOMATION = "automation"
    PHYSICAL = "physical"


class ResourceType(str, enum.Enum):
    """Schedulable resource types."""
    CPU = "cpu"
    GPU = "gpu"
    NPU = "npu"
    RAM = "ram"
    VRAM = "vram"
    DISK = "disk"
    NETWORK_BANDWIDTH = "network_bandwidth"
    LLM_TOKENS = "llm_tokens"
    MODEL_CONCURRENCY = "model_concurrency"
    TOOL_CONCURRENCY = "tool_concurrency"
    BROWSER_SESSIONS = "browser_sessions"
    COMPUTER_SESSIONS = "computer_sessions"
    DEVICE_SESSIONS = "device_sessions"
    RESEARCH_REQUESTS = "research_requests"
    AGENT_SLOTS = "agent_slots"
    AUTOMATION_SLOTS = "automation_slots"
    BATTERY = "battery"
    THERMAL_BUDGET = "thermal_budget"


class CapabilityRiskLevel(str, enum.Enum):
    """Risk classification for capabilities."""
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
    FINANCIAL = "financial"
    COMMUNICATION = "communication"
    PRIVACY_SENSITIVE = "privacy_sensitive"
    PHYSICAL = "physical"
    SECURITY_CRITICAL = "security_critical"


class DataClassification(str, enum.Enum):
    """Information flow control classifications."""
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    HIGHLY_SENSITIVE = "highly_sensitive"


class ProvenanceType(str, enum.Enum):
    """Provenance tracking for all state."""
    USER_PROVIDED = "user_provided"
    MODEL_GENERATED = "model_generated"
    TOOL_RETURNED = "tool_returned"
    WEB_DERIVED = "web_derived"
    MEMORY_DERIVED = "memory_derived"
    SENSOR_DERIVED = "sensor_derived"
    DEVICE_DERIVED = "device_derived"
    AGENT_DERIVED = "agent_derived"
    HUMAN_APPROVED = "human_approved"
    SYSTEM_DERIVED = "system_derived"
    INFERRED = "inferred"
    SIMULATED = "simulated"
    PREDICTED = "predicted"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class RecoveryAction(str, enum.Enum):
    """Recovery classification for operations."""
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    UNKNOWN = "unknown"
    UNSAFE = "unsafe"
    PARTIAL_SUCCESS = "partial_success"
    STATE_DIVERGENCE = "state_divergence"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


class SchedulingClass(str, enum.Enum):
    """Real-time scheduling classes."""
    HARD_REAL_TIME = "hard_real_time"
    SOFT_REAL_TIME = "soft_real_time"
    INTERACTIVE = "interactive"
    DELAY_TOLERANT = "delay_tolerant"
    BATCH = "batch"


class ApprovalStatus(str, enum.Enum):
    """Human approval states."""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"
    DELEGATED = "delegated"
    REMEMBERED = "remembered"


class ApprovalResponse(str, enum.Enum):
    """Possible responses to approval requests."""
    APPROVE_ONCE = "approve_once"
    APPROVE_SESSION = "approve_session"
    ALWAYS_ALLOW = "always_allow"
    DENY = "deny"
    DENY_SESSION = "deny_session"


# =============================================================================
# Core Kernel Objects
# =============================================================================


@dataclass
class ResourceBudget:
    """Resource allocation for an agent/task."""
    cpu_cores: float = 1.0
    gpu_memory_mb: int = 0
    ram_mb: int = 1024
    disk_mb: int = 1024
    network_mbps: float = 100.0
    llm_tokens_per_minute: int = 100000
    model_concurrency: int = 1
    tool_concurrency: int = 5
    browser_sessions: int = 1
    computer_sessions: int = 1
    device_sessions: int = 0
    research_requests_per_minute: int = 10
    agent_slots: int = 1
    automation_slots: int = 0
    battery_percent: float = 100.0
    thermal_budget_celsius: float = 80.0

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def zero(cls) -> "ResourceBudget":
        """A budget with every dimension at zero (initial usage, deltas)."""
        return cls(cpu_cores=0.0, gpu_memory_mb=0, ram_mb=0, disk_mb=0,
                   network_mbps=0.0, llm_tokens_per_minute=0,
                   model_concurrency=0, tool_concurrency=0,
                   browser_sessions=0, computer_sessions=0,
                   device_sessions=0, research_requests_per_minute=0,
                   agent_slots=0, automation_slots=0, battery_percent=0.0,
                   thermal_budget_celsius=0.0)


@dataclass
class ResourceAllocation:
    """Current resource allocation snapshot."""
    agent_id: str
    allocated: ResourceBudget
    used: ResourceBudget
    reserved: ResourceBudget
    timestamp: float = field(default_factory=_now)


@dataclass
class CapabilityDescriptor:
    """Machine-readable capability metadata (Capability ABI)."""
    capability_id: str
    version: str
    provider: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)  # JSON Schema
    outputs: Dict[str, Any] = field(default_factory=dict)  # JSON Schema
    side_effects: List[CapabilityRiskLevel] = field(default_factory=list)
    required_authority: List[str] = field(default_factory=list)
    required_resources: ResourceBudget = field(default_factory=ResourceBudget)
    required_credentials: List[str] = field(default_factory=list)
    network_access: bool = False
    filesystem_access: bool = False
    device_access: bool = False
    data_classification: DataClassification = DataClassification.INTERNAL
    reversibility: bool = False
    idempotency: bool = False
    latency_class: str = "normal"  # fast, normal, slow
    cost_class: str = "free"  # free, low, medium, high
    sandbox_support: bool = True
    verification_strategy: str = "observe"  # observe, verify, attest
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "version": self.version,
            "provider": self.provider,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "side_effects": [s.value for s in self.side_effects],
            "required_authority": self.required_authority,
            "required_resources": self.required_resources.to_dict(),
            "required_credentials": self.required_credentials,
            "network_access": self.network_access,
            "filesystem_access": self.filesystem_access,
            "device_access": self.device_access,
            "data_classification": self.data_classification.value,
            "reversibility": self.reversibility,
            "idempotency": self.idempotency,
            "latency_class": self.latency_class,
            "cost_class": self.cost_class,
            "sandbox_support": self.sandbox_support,
            "verification_strategy": self.verification_strategy,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Intent:
    """Structured Intent object (Intent ABI) — survives planning, delegation, handoffs, recovery."""
    intent_id: str = field(default_factory=lambda: new_id("intent"))
    actor: str = ""  # human, agent, automation, system
    objective: str = ""
    constraints: List[str] = field(default_factory=list)
    requested_capabilities: List[str] = field(default_factory=list)
    requested_resources: ResourceBudget = field(default_factory=ResourceBudget)
    authority_scope: List[str] = field(default_factory=list)
    data_scope: List[str] = field(default_factory=list)
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY
    deadline: Optional[float] = None
    budget: ResourceBudget = field(default_factory=ResourceBudget)
    privacy_class: DataClassification = DataClassification.INTERNAL
    autonomy_level: float = 0.5  # 0.0 = fully supervised, 1.0 = fully autonomous
    approval_requirement: str = "none"  # none, notify, require_approval, require_step_up
    provenance: ProvenanceType = ProvenanceType.USER_PROVIDED
    parent_intent_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: new_id("corr"))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "actor": self.actor,
            "objective": self.objective,
            "constraints": self.constraints,
            "requested_capabilities": self.requested_capabilities,
            "requested_resources": self.requested_resources.to_dict(),
            "authority_scope": self.authority_scope,
            "data_scope": self.data_scope,
            "risk_level": self.risk_level.value,
            "deadline": self.deadline,
            "budget": self.budget.to_dict(),
            "privacy_class": self.privacy_class.value,
            "autonomy_level": self.autonomy_level,
            "approval_requirement": self.approval_requirement,
            "provenance": self.provenance.value,
            "parent_intent_id": self.parent_intent_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class IntentEnvelope:
    """Versioned Intent ABI envelope (Master 59 §5).

    Raw natural language must never directly trigger privileged actions:
    it is normalized into an Intent, wrapped here with provenance and a
    content signature, and only the envelope travels the pipeline.
    """
    version: str = "1.0"
    intent: Optional["Intent"] = None
    provenance: ProvenanceType = ProvenanceType.USER_PROVIDED
    signature: str = ""
    timestamp: float = field(default_factory=_now)

    def seal(self) -> "IntentEnvelope":
        import hashlib
        import json
        payload = json.dumps({
            "version": self.version,
            "intent": self.intent.to_dict() if self.intent else None,
            "provenance": self.provenance.value,
            "timestamp": self.timestamp,
        }, sort_keys=True, default=str)
        self.signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self

    def verify(self) -> bool:
        if self.version != "1.0":
            return False
        if not self.signature or self.intent is None:
            return False
        check = IntentEnvelope(
            version=self.version, intent=self.intent,
            provenance=self.provenance, timestamp=self.timestamp)
        check.seal()
        return check.signature == self.signature

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "intent": self.intent.to_dict() if self.intent else None,
            "provenance": self.provenance.value,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class AuthorityGrant:
    """Explicit authority grant from kernel to agent."""
    grant_id: str = field(default_factory=lambda: new_id("grant"))
    agent_id: str = ""
    intent_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    resources: ResourceBudget = field(default_factory=ResourceBudget)
    data_scopes: List[str] = field(default_factory=list)
    network_scopes: List[str] = field(default_factory=list)
    filesystem_scopes: List[str] = field(default_factory=list)
    device_scopes: List[str] = field(default_factory=list)
    credentials: List[str] = field(default_factory=list)
    parent_grant_id: Optional[str] = None  # For delegation chain
    expires_at: Optional[float] = None
    revocable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def is_valid(self) -> bool:
        if self.expires_at and _now() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "agent_id": self.agent_id,
            "intent_id": self.intent_id,
            "capabilities": self.capabilities,
            "resources": self.resources.to_dict(),
            "data_scopes": self.data_scopes,
            "network_scopes": self.network_scopes,
            "filesystem_scopes": self.filesystem_scopes,
            "device_scopes": self.device_scopes,
            "credentials": self.credentials,
            "parent_grant_id": self.parent_grant_id,
            "expires_at": self.expires_at,
            "revocable": self.revocable,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class AgentIdentity:
    """Cryptographic agent identity."""
    agent_id: str = field(default_factory=lambda: new_id("agent"))
    identity_type: str = "agent"  # agent, human, service, device, delegated
    public_key: str = ""
    key_id: str = ""
    issuer: str = "aetheros-kernel"
    subject: str = ""
    display_name: str = ""
    version: int = 1
    trust_level: int = 0  # 0=unknown, 1=unverified, 2=verified, 3=trusted, 4=high, 5=system
    organization: str = "default"
    tenant: str = "default"
    capabilities: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    status: str = "active"  # active, suspended, revoked, expired, quarantined
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_usable(self) -> bool:
        if self.status not in ("active", "created"):
            return False
        if self.expires_at and _now() > self.expires_at:
            return False
        return True


@dataclass
class AgentProcess:
    """First-class agent process — the central kernel abstraction."""
    agent_id: str = field(default_factory=lambda: new_id("agent"))
    process_id: str = field(default_factory=lambda: new_id("proc"))
    parent_agent_id: Optional[str] = None
    tenant_id: str = "default"
    identity: Optional[AgentIdentity] = None
    intent: Optional[Intent] = None
    authority: Optional[AuthorityGrant] = None
    capabilities: List[str] = field(default_factory=list)
    state: AgentLifecycleState = AgentLifecycleState.CREATED
    priority: AgentPriority = AgentPriority.NORMAL
    resource_budget: ResourceBudget = field(default_factory=ResourceBudget)
    resource_allocation: Optional[ResourceAllocation] = None
    context_budget: int = 32000  # tokens
    memory_scope: str = ""  # namespace for memory isolation
    model_policy: Dict[str, Any] = field(default_factory=dict)
    tool_policy: Dict[str, Any] = field(default_factory=dict)
    network_policy: Dict[str, Any] = field(default_factory=dict)
    filesystem_policy: Dict[str, Any] = field(default_factory=dict)
    device_policy: Dict[str, Any] = field(default_factory=dict)
    security_profile: str = "standard"
    lifecycle_state: AgentLifecycleState = AgentLifecycleState.CREATED
    checkpoint_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None

    # Internal runtime state (not serialized)
    _event_bus: Any = field(default=None, repr=False)
    _kernel: Any = field(default=None, repr=False)

    def transition(self, new_state: AgentLifecycleState) -> None:
        """Transition lifecycle state with validation."""
        valid_transitions = {
            AgentLifecycleState.CREATED: {AgentLifecycleState.ADMITTED, AgentLifecycleState.FAILED},
            AgentLifecycleState.ADMITTED: {AgentLifecycleState.INITIALIZING, AgentLifecycleState.READY, AgentLifecycleState.CANCELLED},
            AgentLifecycleState.INITIALIZING: {AgentLifecycleState.READY, AgentLifecycleState.FAILED, AgentLifecycleState.CANCELLED},
            AgentLifecycleState.READY: {AgentLifecycleState.RUNNING, AgentLifecycleState.PAUSED, AgentLifecycleState.CANCELLED, AgentLifecycleState.CHECKPOINTING},
            AgentLifecycleState.RUNNING: {
                AgentLifecycleState.WAITING, AgentLifecycleState.BLOCKED,
                AgentLifecycleState.PAUSED, AgentLifecycleState.CHECKPOINTING,
                AgentLifecycleState.COMPLETED, AgentLifecycleState.FAILED,
                AgentLifecycleState.CANCELLED
            },
            AgentLifecycleState.WAITING: {AgentLifecycleState.RUNNING, AgentLifecycleState.READY, AgentLifecycleState.BLOCKED, AgentLifecycleState.CANCELLED, AgentLifecycleState.TERMINATED},
            AgentLifecycleState.BLOCKED: {AgentLifecycleState.RUNNING, AgentLifecycleState.READY, AgentLifecycleState.FAILED, AgentLifecycleState.CANCELLED},
            AgentLifecycleState.PAUSED: {AgentLifecycleState.READY, AgentLifecycleState.RUNNING, AgentLifecycleState.CANCELLED, AgentLifecycleState.CHECKPOINTING},
            AgentLifecycleState.CHECKPOINTING: {AgentLifecycleState.READY, AgentLifecycleState.RECOVERING, AgentLifecycleState.FAILED},
            AgentLifecycleState.RECOVERING: {AgentLifecycleState.READY, AgentLifecycleState.FAILED},
            AgentLifecycleState.COMPLETED: {AgentLifecycleState.TERMINATED},
            AgentLifecycleState.FAILED: {AgentLifecycleState.RECOVERING, AgentLifecycleState.TERMINATED},
            AgentLifecycleState.CANCELLED: {AgentLifecycleState.TERMINATED},
            AgentLifecycleState.TERMINATED: set(),
        }
        if new_state not in valid_transitions.get(self.state, set()):
            raise ValueError(f"Invalid transition: {self.state} -> {new_state}")

        old_state = self.state
        self.state = new_state
        self.updated_at = _now()

        # Emit lifecycle event
        if self._event_bus:
            self._event_bus.emit("agent.lifecycle.transition", {
                "agent_id": self.agent_id,
                "process_id": self.process_id,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "timestamp": self.updated_at,
            })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "process_id": self.process_id,
            "parent_agent_id": self.parent_agent_id,
            "tenant_id": self.tenant_id,
            "identity": self.identity.__dict__ if self.identity else None,
            "intent": self.intent.to_dict() if self.intent else None,
            "authority": self.authority.to_dict() if self.authority else None,
            "capabilities": self.capabilities,
            "state": self.state.value,
            "priority": self.priority.value,
            "resource_budget": self.resource_budget.to_dict(),
            "resource_allocation": self.resource_allocation.__dict__ if self.resource_allocation else None,
            "context_budget": self.context_budget,
            "memory_scope": self.memory_scope,
            "model_policy": self.model_policy,
            "tool_policy": self.tool_policy,
            "network_policy": self.network_policy,
            "filesystem_policy": self.filesystem_policy,
            "device_policy": self.device_policy,
            "security_profile": self.security_profile,
            "lifecycle_state": self.lifecycle_state.value,
            "checkpoint_id": self.checkpoint_id,
            "provenance": self.provenance,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class CapabilityInvocation:
    """A capability syscall invocation."""
    invocation_id: str = field(default_factory=lambda: new_id("inv"))
    agent_id: str = ""
    capability_id: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    authority_grant_id: str = ""
    intent_id: str = ""
    trace_id: str = field(default_factory=lambda: new_id("trace"))
    span_id: str = field(default_factory=lambda: new_id("span"))
    parent_span_id: Optional[str] = None
    status: str = "pending"  # pending, authorized, executing, completed, failed, denied
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    provenance: ProvenanceType = ProvenanceType.AGENT_DERIVED
    verification: Dict[str, Any] = field(default_factory=dict)
    side_effects_observed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "agent_id": self.agent_id,
            "capability_id": self.capability_id,
            "inputs": self.inputs,
            "authority_grant_id": self.authority_grant_id,
            "intent_id": self.intent_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "provenance": self.provenance.value,
            "verification": self.verification,
            "side_effects_observed": self.side_effects_observed,
        }


@dataclass
class Checkpoint:
    """Checkpoint for agent recovery and migration."""
    checkpoint_id: str = field(default_factory=lambda: new_id("cp"))
    agent_id: str = ""
    process_id: str = ""
    intent_id: str = ""
    intent: Optional[Intent] = None
    state: AgentLifecycleState = AgentLifecycleState.READY
    context: Dict[str, Any] = field(default_factory=dict)
    memory_refs: List[str] = field(default_factory=list)
    authority: Optional[AuthorityGrant] = None
    capabilities: List[str] = field(default_factory=list)
    resource_allocation: Optional[ResourceAllocation] = None
    model_state: Dict[str, Any] = field(default_factory=dict)
    tool_state: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    event_offset: int = 0
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "agent_id": self.agent_id,
            "process_id": self.process_id,
            "intent_id": self.intent_id,
            "intent": self.intent.to_dict() if self.intent else None,
            "state": self.state.value,
            "context": self.context,
            "memory_refs": self.memory_refs,
            "authority": self.authority.to_dict() if self.authority else None,
            "capabilities": self.capabilities,
            "resource_allocation": self.resource_allocation.__dict__ if self.resource_allocation else None,
            "model_state": self.model_state,
            "tool_state": self.tool_state,
            "artifacts": self.artifacts,
            "subtasks": self.subtasks,
            "event_offset": self.event_offset,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class KernelEvent:
    """Kernel event with full provenance and tracing."""
    event_id: str = field(default_factory=lambda: new_id("evt"))
    topic: str = ""
    source: str = ""
    agent_id: str = ""
    process_id: str = ""
    task_id: str = ""
    intent_id: str = ""
    trace_id: str = field(default_factory=lambda: new_id("trace"))
    span_id: str = field(default_factory=lambda: new_id("span"))
    parent_span_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED
    timestamp: float = field(default_factory=_now)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "source": self.source,
            "agent_id": self.agent_id,
            "process_id": self.process_id,
            "task_id": self.task_id,
            "intent_id": self.intent_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "data": self.data,
            "provenance": self.provenance.value,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
        }


# =============================================================================
# Kernel Configuration
# =============================================================================


@dataclass
class KernelConfig:
    """Kernel configuration."""
    # Core
    enable_scheduler: bool = True
    enable_telemetry: bool = True
    enable_state_persistence: bool = True
    enable_event_bus: bool = True
    auto_discover_components: bool = True

    # Multi-agent
    enable_multi_agent: bool = True
    enable_supervisor: bool = True
    enable_approvals: bool = True
    enable_reflection: bool = True
    enable_artifact_storage: bool = True
    enable_inter_agent_bus: bool = True

    # Security
    enable_capability_authorization: bool = True
    enable_information_flow_control: bool = True
    enable_prompt_injection_defense: bool = True
    emergency_stop_enabled: bool = True

    # Resources
    default_agent_budget: ResourceBudget = field(default_factory=ResourceBudget)
    max_concurrent_agents: int = 50
    max_agent_depth: int = 5  # delegation depth
    default_context_budget: int = 32000

    # Checkpointing
    checkpoint_interval_seconds: float = 60.0
    checkpoint_on_state_change: bool = True
    max_checkpoints_per_agent: int = 10

    # Recovery
    max_recovery_attempts: int = 3
    recovery_timeout_seconds: float = 300.0

    # Observability
    trace_sampling_rate: float = 1.0
    metrics_interval_seconds: float = 10.0
    health_check_interval_seconds: float = 30.0

    # State persistence
    state_dir: Optional[str] = None
    artifact_dir: Optional[str] = None
    checkpoint_dir: Optional[str] = None

    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "kernel.scheduler.v2": True,
        "kernel.capabilities.v2": True,
        "kernel.authority.v2": True,
        "kernel.agent_migration": False,
        "kernel.distributed_compute": False,
        "kernel.physical_execution": False,
    })


# =============================================================================
# Kernel Service Interfaces (Protocols)
# =============================================================================

# These are documented as interfaces for type checking
# Actual implementations are in separate modules

class ICapabilityProvider:
    """Interface for capability providers."""
    def get_descriptor(self) -> CapabilityDescriptor: ...
    def invoke(self, invocation: CapabilityInvocation) -> Any: ...
    def verify(self, invocation: CapabilityInvocation, result: Any) -> bool: ...


class IMemoryProvider:
    """Interface for memory providers."""
    def read(self, scope: str, key: str) -> Any: ...
    def write(self, scope: str, key: str, value: Any) -> None: ...
    def search(self, scope: str, query: str, limit: int = 10) -> List[Any]: ...
    def delete(self, scope: str, key: str) -> bool: ...


class IModelProvider:
    """Interface for model providers."""
    def get_capabilities(self) -> Dict[str, Any]: ...
    def complete(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Any: ...
    def estimate_cost(self, messages: List[Dict], tools: List[Dict]) -> float: ...


class IResourceManager:
    """Interface for resource management."""
    def allocate(self, agent_id: str, budget: ResourceBudget) -> ResourceAllocation: ...
    def release(self, agent_id: str) -> None: ...
    def get_usage(self, agent_id: str) -> ResourceAllocation: ...
    def get_available(self) -> ResourceBudget: ...


class IScheduler:
    """Interface for agent scheduling."""
    def admit(self, process: AgentProcess) -> bool: ...
    def schedule(self, process: AgentProcess) -> bool: ...
    def preempt(self, agent_id: str) -> bool: ...
    def yield_cpu(self, agent_id: str) -> bool: ...


class IEventBus:
    """Interface for event bus."""
    def publish(self, event: KernelEvent) -> int: ...
    def subscribe(self, topic: str, callback: Callable[[KernelEvent], None]) -> Any: ...
    def unsubscribe(self, subscription: Any) -> None: ...


class IPolicyEngine:
    """Interface for policy evaluation."""
    def evaluate(self, intent: Intent, authority: AuthorityGrant) -> Dict[str, Any]: ...
    def check_capability(self, agent_id: str, capability_id: str) -> bool: ...
    def check_data_flow(self, source: DataClassification, dest: DataClassification) -> bool: ...


__all__ = [
    # Enums
    "AgentLifecycleState",
    "AgentPriority",
    "ResourceType",
    "CapabilityRiskLevel",
    "DataClassification",
    "ProvenanceType",
    "RecoveryAction",
    "SchedulingClass",
    "ApprovalStatus",
    # Core types
    "ResourceBudget",
    "ResourceAllocation",
    "CapabilityDescriptor",
    "Intent",
    "IntentEnvelope",
    "AuthorityGrant",
    "AgentIdentity",
    "AgentProcess",
    "CapabilityInvocation",
    "Checkpoint",
    "KernelEvent",
    "KernelConfig",
    # Interfaces
    "ICapabilityProvider",
    "IMemoryProvider",
    "IModelProvider",
    "IResourceManager",
    "IScheduler",
    "IEventBus",
    "IPolicyEngine",
    # Utilities
    "_now",
    "new_id",
]