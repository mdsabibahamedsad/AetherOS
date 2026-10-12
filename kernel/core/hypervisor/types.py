"""
AetherOS Agent Hypervisor 1.0 — Capsule canonical types.

Single source of truth for the capsule data model. The capsule is the
controlled execution environment for an agent: identity, authority,
capabilities, filesystem, network, memory, resources, lifecycle,
telemetry, policy, and provenance.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from kernel.core.types import (
    AgentLifecycleState,
    AuthorityGrant,
    CapabilityRiskLevel,
    DataClassification,
    Intent,
    ResourceBudget,
    _now,
    new_id,
)


# =============================================================================
# Enums
# =============================================================================


class CapsuleLifecycleState(str, enum.Enum):
    """Canonical capsule lifecycle states (§4)."""
    REQUESTED = "requested"
    ADMISSION_CHECK = "admission_check"
    PROVISIONING = "provisioning"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    SUSPENDED = "suspended"
    CHECKPOINTING = "checkpointing"
    MIGRATING = "migrating"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    DESTROYED = "destroyed"
    # Failure states
    FAILED = "failed"
    QUARANTINED = "quarantined"
    TERMINATED = "terminated"


class IsolationLevel(str, enum.Enum):
    """Isolation strength abstraction (§7)."""
    LEVEL_0_PROCESS = "level_0_process_isolation"
    LEVEL_1_SANDBOXED_PROCESS = "level_1_sandboxed_process"
    LEVEL_2_CONTAINER = "level_2_container_isolation"
    LEVEL_3_VM = "level_3_vm_isolation"
    LEVEL_4_DEDICATED_HOST = "level_4_dedicated_host"


class IsolationStatus(str, enum.Enum):
    """Capability-detection outcome for an isolation primitive (§9)."""
    SUPPORTED = "supported"
    UNAVAILABLE = "unavailable"
    REQUIRES_CONFIGURATION = "requires_configuration"


class CapsuleProfileName(str, enum.Enum):
    """Standard capsule profiles (§6). Profiles are defaults, never bypasses."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEVELOPER = "developer"
    RESEARCH = "research"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    AUTOMATION = "automation"
    SWARM = "swarm"
    UNTRUSTED = "untrusted"
    HIGH_SECURITY = "high_security"
    PHYSICAL = "physical"
    AMBIENT = "ambient"
    LOCAL_ONLY = "local_only"
    OFFLINE = "offline"


class MountType(str, enum.Enum):
    """Filesystem mount types (§18)."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    TEMPORARY = "temporary"
    COPY_ON_WRITE = "copy_on_write"
    SECRET_MOUNT = "secret_mount"
    ARTIFACT_MOUNT = "artifact_mount"
    SHARED_MOUNT = "shared_mount"


class NetworkMode(str, enum.Enum):
    """Capsule network policy modes (§20)."""
    NO_NETWORK = "no_network"
    LOCAL_ONLY = "local_only"
    ALLOWLIST = "allowlist"
    PRIVATE_NETWORK = "private_network"
    FULL_NETWORK = "full_network"


class TerminationMode(str, enum.Enum):
    """Capsule termination modes (§92)."""
    GRACEFUL = "graceful"
    IMMEDIATE = "immediate"
    FORCED = "forced"
    EMERGENCY = "emergency"


class ReplayMode(str, enum.Enum):
    """Agent replay modes (§53). Default is OBSERVE_ONLY."""
    OBSERVE_ONLY = "observe_only"
    SIMULATION = "simulation"
    DRY_RUN = "dry_run"
    FULL_EXECUTION = "full_execution"


class CapsuleHealth(str, enum.Enum):
    """Capsule health states (§119)."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    UNRESPONSIVE = "unresponsive"
    RESOURCE_STARVED = "resource_starved"
    FAILED = "failed"


class AutonomyLevel(str, enum.Enum):
    """Earned autonomy bands (§59). Bounded by policy, risk, history, trust."""
    AUTONOMY_0 = "autonomy_0"
    AUTONOMY_1 = "autonomy_1"
    AUTONOMY_2 = "autonomy_2"
    AUTONOMY_3 = "autonomy_3"
    AUTONOMY_4 = "autonomy_4"
    AUTONOMY_5 = "autonomy_5"


class CircuitState(str, enum.Enum):
    """Circuit breaker states (§61)."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class MemoryScopeKind(str, enum.Enum):
    """Capsule memory scopes (§42)."""
    EPHEMERAL = "ephemeral"
    TASK = "task"
    PROJECT = "project"
    PERSISTENT = "persistent"


# Valid lifecycle transitions (every transition emits a Kernel event).
CAPSULE_TRANSITIONS: Dict[CapsuleLifecycleState, frozenset] = {
    CapsuleLifecycleState.REQUESTED: frozenset({
        CapsuleLifecycleState.ADMISSION_CHECK, CapsuleLifecycleState.FAILED,
    }),
    CapsuleLifecycleState.ADMISSION_CHECK: frozenset({
        CapsuleLifecycleState.PROVISIONING, CapsuleLifecycleState.FAILED,
    }),
    CapsuleLifecycleState.PROVISIONING: frozenset({
        CapsuleLifecycleState.INITIALIZING, CapsuleLifecycleState.FAILED,
    }),
    CapsuleLifecycleState.INITIALIZING: frozenset({
        CapsuleLifecycleState.READY, CapsuleLifecycleState.FAILED,
    }),
    CapsuleLifecycleState.READY: frozenset({
        CapsuleLifecycleState.RUNNING, CapsuleLifecycleState.SUSPENDED,
        CapsuleLifecycleState.CHECKPOINTING, CapsuleLifecycleState.MIGRATING,
        CapsuleLifecycleState.QUARANTINED, CapsuleLifecycleState.COMPLETED,
        CapsuleLifecycleState.TERMINATED,
    }),
    CapsuleLifecycleState.RUNNING: frozenset({
        CapsuleLifecycleState.SUSPENDED, CapsuleLifecycleState.CHECKPOINTING,
        CapsuleLifecycleState.MIGRATING, CapsuleLifecycleState.RECOVERING,
        CapsuleLifecycleState.QUARANTINED, CapsuleLifecycleState.COMPLETED,
        CapsuleLifecycleState.FAILED, CapsuleLifecycleState.TERMINATED,
    }),
    CapsuleLifecycleState.SUSPENDED: frozenset({
        CapsuleLifecycleState.RUNNING, CapsuleLifecycleState.CHECKPOINTING,
        CapsuleLifecycleState.MIGRATING, CapsuleLifecycleState.QUARANTINED,
        CapsuleLifecycleState.TERMINATED, CapsuleLifecycleState.READY,
    }),
    CapsuleLifecycleState.CHECKPOINTING: frozenset({
        CapsuleLifecycleState.READY, CapsuleLifecycleState.RUNNING,
        CapsuleLifecycleState.SUSPENDED, CapsuleLifecycleState.FAILED,
    }),
    CapsuleLifecycleState.MIGRATING: frozenset({
        CapsuleLifecycleState.READY, CapsuleLifecycleState.RUNNING,
        CapsuleLifecycleState.SUSPENDED, CapsuleLifecycleState.FAILED,
        CapsuleLifecycleState.RECOVERING,
    }),
    CapsuleLifecycleState.RECOVERING: frozenset({
        CapsuleLifecycleState.READY, CapsuleLifecycleState.RUNNING,
        CapsuleLifecycleState.FAILED, CapsuleLifecycleState.QUARANTINED,
    }),
    CapsuleLifecycleState.QUARANTINED: frozenset({
        CapsuleLifecycleState.RECOVERING, CapsuleLifecycleState.TERMINATED,
        CapsuleLifecycleState.DESTROYED,
    }),
    CapsuleLifecycleState.COMPLETED: frozenset({
        CapsuleLifecycleState.DESTROYED, CapsuleLifecycleState.TERMINATED,
    }),
    CapsuleLifecycleState.FAILED: frozenset({
        CapsuleLifecycleState.RECOVERING, CapsuleLifecycleState.QUARANTINED,
        CapsuleLifecycleState.TERMINATED, CapsuleLifecycleState.DESTROYED,
    }),
    CapsuleLifecycleState.TERMINATED: frozenset({
        CapsuleLifecycleState.DESTROYED,
    }),
    CapsuleLifecycleState.DESTROYED: frozenset(),
}


# =============================================================================
# Core capsule objects
# =============================================================================


@dataclass
class CapsuleMount:
    """A single filesystem mount inside a capsule (§17-§18)."""
    name: str  # workspace | scratch | artifacts | cache | tmp | memory | readonly | ...
    mount_type: MountType = MountType.READ_WRITE
    host_path: str = ""  # empty => capsule-private directory under capsule root
    capsule_path: str = ""  # logical path, defaults to /<name>
    read_only: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "mount_type": self.mount_type.value,
            "host_path": self.host_path,
            "capsule_path": self.capsule_path or f"/{self.name}",
            "read_only": self.read_only,
        }


@dataclass
class NetworkPolicy:
    """Explicit capsule network policy (§20)."""
    mode: NetworkMode = NetworkMode.NO_NETWORK
    allowlist: List[str] = field(default_factory=list)
    denylist: List[str] = field(default_factory=list)
    require_tls: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode.value,
            "allowlist": list(self.allowlist),
            "denylist": list(self.denylist),
            "require_tls": self.require_tls,
        }


@dataclass
class CapabilityManifest:
    """Signed/logically-authenticated capability manifest (§15)."""
    capsule_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    policy_version: str = "1.0"
    issued_at: float = field(default_factory=_now)
    issuer: str = "aetheros-kernel"
    manifest_hash: str = ""

    def compute_hash(self) -> str:
        payload = json.dumps(
            {"capsule_id": self.capsule_id,
             "capabilities": sorted(self.capabilities),
             "policy_version": self.policy_version,
             "issued_at": self.issued_at,
             "issuer": self.issuer},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal(self) -> "CapabilityManifest":
        self.manifest_hash = self.compute_hash()
        return self

    def verify(self) -> bool:
        return bool(self.manifest_hash) and self.manifest_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, object]:
        return {
            "capsule_id": self.capsule_id,
            "capabilities": list(self.capabilities),
            "policy_version": self.policy_version,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "manifest_hash": self.manifest_hash,
        }


@dataclass
class BlastRadius:
    """Measurable blast radius of a capsule (§57)."""
    filesystem_scope: List[str] = field(default_factory=list)
    network_scope: List[str] = field(default_factory=list)
    credential_scope: List[str] = field(default_factory=list)
    device_scope: List[str] = field(default_factory=list)
    agent_scope: List[str] = field(default_factory=list)
    memory_scope: List[str] = field(default_factory=list)
    financial_scope: List[str] = field(default_factory=list)
    communication_scope: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "filesystem_scope": self.filesystem_scope,
            "network_scope": self.network_scope,
            "credential_scope": self.credential_scope,
            "device_scope": self.device_scope,
            "agent_scope": self.agent_scope,
            "memory_scope": self.memory_scope,
            "financial_scope": self.financial_scope,
            "communication_scope": self.communication_scope,
        }


@dataclass
class RiskAssessment:
    """Deterministic risk assessment (§58). Never LLM-judged."""
    score: int = 0  # 0-100
    band: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    factors: List[str] = field(default_factory=list)
    weights: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "score": self.score,
            "band": self.band,
            "factors": list(self.factors),
            "weights": dict(self.weights),
        }


@dataclass
class AgentCapsuleContract:
    """Capsule contract (§86)."""
    objective: str = ""
    authority: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    resources: Optional[ResourceBudget] = None
    security_profile: str = "standard"
    privacy_class: DataClassification = DataClassification.INTERNAL
    network: Optional[NetworkPolicy] = None
    mounts: List[CapsuleMount] = field(default_factory=list)
    termination: TerminationMode = TerminationMode.GRACEFUL
    verification: str = "observe"

    def to_dict(self) -> Dict[str, object]:
        return {
            "objective": self.objective,
            "authority": list(self.authority),
            "capabilities": list(self.capabilities),
            "resources": self.resources.to_dict() if self.resources else None,
            "security_profile": self.security_profile,
            "privacy_class": self.privacy_class.value,
            "network": self.network.to_dict() if self.network else None,
            "mounts": [m.to_dict() for m in self.mounts],
            "termination": self.termination.value,
            "verification": self.verification,
        }


@dataclass
class AgentCapsule:
    """The controlled execution environment for an agent (§3)."""
    capsule_id: str = field(default_factory=lambda: new_id("capsule"))
    agent_id: str = ""
    task_id: str = ""
    intent_id: str = ""
    parent_capsule_id: Optional[str] = None
    identity_key_id: str = ""
    trust_level: int = 1
    security_profile: str = "standard"
    capsule_profile: str = CapsuleProfileName.STANDARD.value
    authority: Optional[AuthorityGrant] = None
    capabilities: List[str] = field(default_factory=list)
    manifest: Optional[CapabilityManifest] = None
    resource_limits: ResourceBudget = field(default_factory=ResourceBudget)
    mounts: List[CapsuleMount] = field(default_factory=list)
    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    memory_policy: MemoryScopeKind = MemoryScopeKind.TASK
    model_policy: Dict[str, object] = field(default_factory=dict)
    tool_policy: Dict[str, object] = field(default_factory=dict)
    device_policy: Dict[str, object] = field(default_factory=dict)
    secret_policy: Dict[str, object] = field(default_factory=dict)
    process_policy: Dict[str, object] = field(default_factory=dict)
    environment_policy: Dict[str, str] = field(default_factory=dict)
    isolation_level: IsolationLevel = IsolationLevel.LEVEL_0_PROCESS
    isolation_provider: str = "native_process"
    lifecycle_state: CapsuleLifecycleState = CapsuleLifecycleState.REQUESTED
    checkpoint_id: Optional[str] = None
    provenance: Dict[str, object] = field(default_factory=dict)
    risk: Optional[RiskAssessment] = None
    blast_radius: Optional[BlastRadius] = None
    autonomy: AutonomyLevel = AutonomyLevel.AUTONOMY_1
    node_id: str = "local"
    policy_version: str = "1.0"
    policy_hash: str = ""
    contract: Optional[AgentCapsuleContract] = None
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    error: Optional[str] = None

    def transition(self, new_state: CapsuleLifecycleState) -> None:
        allowed = CAPSULE_TRANSITIONS.get(self.lifecycle_state, frozenset())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid capsule transition: {self.lifecycle_state.value} -> {new_state.value}")
        self.lifecycle_state = new_state
        self.updated_at = _now()

    def is_expired(self) -> bool:
        return bool(self.expires_at) and _now() > self.expires_at

    def to_dict(self) -> Dict[str, object]:
        return {
            "capsule_id": self.capsule_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "intent_id": self.intent_id,
            "parent_capsule_id": self.parent_capsule_id,
            "identity_key_id": self.identity_key_id,
            "trust_level": self.trust_level,
            "security_profile": self.security_profile,
            "capsule_profile": self.capsule_profile,
            "authority": self.authority.to_dict() if self.authority else None,
            "capabilities": list(self.capabilities),
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "resource_limits": self.resource_limits.to_dict(),
            "mounts": [m.to_dict() for m in self.mounts],
            "network": self.network.to_dict(),
            "memory_policy": self.memory_policy.value,
            "model_policy": dict(self.model_policy),
            "tool_policy": dict(self.tool_policy),
            "device_policy": dict(self.device_policy),
            "secret_policy": dict(self.secret_policy),
            "process_policy": dict(self.process_policy),
            "environment_policy": dict(self.environment_policy),
            "isolation_level": self.isolation_level.value,
            "isolation_provider": self.isolation_provider,
            "lifecycle_state": self.lifecycle_state.value,
            "checkpoint_id": self.checkpoint_id,
            "provenance": dict(self.provenance),
            "risk": self.risk.to_dict() if self.risk else None,
            "blast_radius": self.blast_radius.to_dict() if self.blast_radius else None,
            "autonomy": self.autonomy.value,
            "node_id": self.node_id,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "contract": self.contract.to_dict() if self.contract else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "error": self.error,
        }


SNAPSHOT_VERSION = "AETHEROS_CAPSULE_SNAPSHOT_V1"


@dataclass
class CapsuleSnapshot:
    """Versioned capsule snapshot (§50)."""
    version: str = SNAPSHOT_VERSION
    capsule_id: str = ""
    agent_id: str = ""
    intent: Optional[Intent] = None
    state: CapsuleLifecycleState = CapsuleLifecycleState.SUSPENDED
    authority: Optional[AuthorityGrant] = None
    capabilities: List[str] = field(default_factory=list)
    manifest_hash: str = ""
    policy_version: str = "1.0"
    policy_hash: str = ""
    resource_limits: Optional[ResourceBudget] = None
    filesystem_meta: Dict[str, object] = field(default_factory=dict)
    network_state: Dict[str, object] = field(default_factory=dict)
    memory_refs: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    tool_state: Dict[str, object] = field(default_factory=dict)
    event_offset: int = 0
    runtime_version: str = "1.0"
    integrity_hash: str = ""
    created_at: float = field(default_factory=_now)

    def compute_integrity(self) -> str:
        payload = json.dumps({
            "version": self.version,
            "capsule_id": self.capsule_id,
            "agent_id": self.agent_id,
            "capabilities": sorted(self.capabilities),
            "manifest_hash": self.manifest_hash,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "filesystem_meta": self.filesystem_meta,
            "memory_refs": sorted(self.memory_refs),
            "artifacts": sorted(self.artifacts),
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal(self) -> "CapsuleSnapshot":
        self.integrity_hash = self.compute_integrity()
        return self

    def verify(self) -> bool:
        if self.version != SNAPSHOT_VERSION:
            return False
        return bool(self.integrity_hash) and self.integrity_hash == self.compute_integrity()

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "capsule_id": self.capsule_id,
            "agent_id": self.agent_id,
            "intent": self.intent.to_dict() if self.intent else None,
            "state": self.state.value,
            "authority": self.authority.to_dict() if self.authority else None,
            "capabilities": list(self.capabilities),
            "manifest_hash": self.manifest_hash,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "resource_limits": self.resource_limits.to_dict() if self.resource_limits else None,
            "filesystem_meta": dict(self.filesystem_meta),
            "network_state": dict(self.network_state),
            "memory_refs": list(self.memory_refs),
            "artifacts": list(self.artifacts),
            "tool_state": dict(self.tool_state),
            "event_offset": self.event_offset,
            "runtime_version": self.runtime_version,
            "integrity_hash": self.integrity_hash,
            "created_at": self.created_at,
        }


@dataclass
class CapsuleReceipt:
    """Cryptographically-chained action receipt (§95)."""
    action_id: str = field(default_factory=lambda: new_id("act"))
    capsule_id: str = ""
    agent_id: str = ""
    intent_id: str = ""
    capability: str = ""
    authority_grant_id: str = ""
    policy_version: str = "1.0"
    input_hash: str = ""
    result_hash: str = ""
    outcome: str = "ok"
    timestamp: float = field(default_factory=_now)
    verification: str = "observe"
    previous_hash: str = ""
    receipt_hash: str = ""

    @staticmethod
    def hash_payload(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal(self, previous_hash: str = "") -> "CapsuleReceipt":
        self.previous_hash = previous_hash
        body = json.dumps({
            "action_id": self.action_id, "capsule_id": self.capsule_id,
            "agent_id": self.agent_id, "intent_id": self.intent_id,
            "capability": self.capability, "authority_grant_id": self.authority_grant_id,
            "policy_version": self.policy_version, "input_hash": self.input_hash,
            "result_hash": self.result_hash, "outcome": self.outcome,
            "timestamp": self.timestamp, "previous_hash": self.previous_hash,
        }, sort_keys=True, default=str)
        self.receipt_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return self

    def to_dict(self) -> Dict[str, object]:
        return {
            "action_id": self.action_id, "capsule_id": self.capsule_id,
            "agent_id": self.agent_id, "intent_id": self.intent_id,
            "capability": self.capability, "authority_grant_id": self.authority_grant_id,
            "policy_version": self.policy_version, "input_hash": self.input_hash,
            "result_hash": self.result_hash, "outcome": self.outcome,
            "timestamp": self.timestamp, "verification": self.verification,
            "previous_hash": self.previous_hash, "receipt_hash": self.receipt_hash,
        }


@dataclass
class ForensicSnapshot:
    """Pre-destruction forensic capture for quarantined capsules (§93)."""
    forensic_id: str = field(default_factory=lambda: new_id("forensic"))
    capsule_id: str = ""
    configuration: Dict[str, object] = field(default_factory=dict)
    policy_version: str = "1.0"
    event_trace: List[Dict[str, object]] = field(default_factory=list)
    process_tree: Dict[str, object] = field(default_factory=dict)
    network_metadata: Dict[str, object] = field(default_factory=dict)
    filesystem_metadata: Dict[str, object] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    security_events: List[Dict[str, object]] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, object]:
        return {
            "forensic_id": self.forensic_id, "capsule_id": self.capsule_id,
            "configuration": dict(self.configuration),
            "policy_version": self.policy_version,
            "event_trace": list(self.event_trace),
            "process_tree": dict(self.process_tree),
            "network_metadata": dict(self.network_metadata),
            "filesystem_metadata": dict(self.filesystem_metadata),
            "artifacts": list(self.artifacts),
            "security_events": list(self.security_events),
            "created_at": self.created_at,
        }


@dataclass
class PlacementDecision:
    """Capsule placement decision (§104)."""
    target: str = "local"  # local | remote_lan | private_server | cloud
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {"target": self.target, "reasons": list(self.reasons),
                "warnings": list(self.warnings)}
