"""Core mesh data models (Master 49 sections 2-3, 16, 31)."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class MeshNodeState(str, enum.Enum):
    """Node lifecycle states (section 5)."""
    DISCOVERED = "discovered"
    VERIFYING = "verifying"
    TRUSTED = "trusted"
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    REMOVED = "removed"


class EdgeType(str, enum.Enum):
    """Mesh edge relationship types (section 3)."""
    DELEGATION = "delegation"
    TRUST = "trust"
    CAPABILITY = "capability"
    DEPENDENCY = "dependency"
    VERIFICATION = "verification"
    COLLABORATION = "collaboration"
    ORGANIZATION = "organization"
    RESOURCE = "resource"
    ECONOMIC = "economic"
    COMMUNICATION = "communication"


class TrustDimension(str, enum.Enum):
    """Trust assessment dimensions (section 7)."""
    IDENTITY = "identity"
    SECURITY = "security"
    EXECUTION = "execution"
    ECONOMIC = "economic"
    EVIDENCE = "evidence"
    ORGANIZATION = "organization"
    NETWORK = "network"
    BEHAVIOR = "behavior"


class TopologyType(str, enum.Enum):
    """Execution topologies (section 9)."""
    SINGLE_AGENT = "single_agent"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DAG = "dag"
    PIPELINE = "pipeline"
    HIERARCHICAL = "hierarchical"
    SWARM = "swarm"
    DEBATE = "debate"
    MAP_REDUCE = "map_reduce"
    SPECIALIST_VERIFIER = "specialist_verifier"
    LOCAL_REMOTE_HYBRID = "local_remote_hybrid"


class CollectiveMode(str, enum.Enum):
    """Collective intelligence combination modes (section 10)."""
    INDEPENDENT = "independent"
    ENSEMBLE = "ensemble"
    DEBATE = "debate"
    CRITIQUE = "critique"
    CONSENSUS = "consensus"
    SPECIALIST_PANEL = "specialist_panel"
    RED_TEAM = "red_team"
    VERIFICATION_PANEL = "verification_panel"
    SYNTHESIS = "synthesis"


@dataclass
class MeshNode:
    """Mesh node representing an agent in the global mesh (section 2)."""
    
    node_id: str = field(default_factory=lambda: f"node-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
    organization_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    endpoint: str = ""
    location: str = ""
    trust: Dict[TrustDimension, float] = field(default_factory=dict)
    security_state: Dict[str, Any] = field(default_factory=dict)
    availability: Dict[str, Any] = field(default_factory=dict)
    resource_state: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, float] = field(default_factory=dict)
    economic_policy: Dict[str, Any] = field(default_factory=dict)
    data_policy: Dict[str, Any] = field(default_factory=dict)
    state: MeshNodeState = MeshNodeState.DISCOVERED
    last_seen: float = field(default_factory=time.time)
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal tracking
    _created_at: float = field(default_factory=time.time, init=False)
    _updated_at: float = field(default_factory=time.time, init=False)
    
    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        if not self.trust:
            self.trust = {dim: 0.0 for dim in TrustDimension}
    
    def update_state(self, new_state: MeshNodeState) -> bool:
        """Update node state with validation."""
        valid_transitions = {
            MeshNodeState.DISCOVERED: {MeshNodeState.VERIFYING, MeshNodeState.REMOVED},
            MeshNodeState.VERIFYING: {MeshNodeState.TRUSTED, MeshNodeState.SUSPENDED, MeshNodeState.REMOVED},
            MeshNodeState.TRUSTED: {MeshNodeState.AVAILABLE, MeshNodeState.SUSPENDED, MeshNodeState.REVOKED},
            MeshNodeState.AVAILABLE: {MeshNodeState.BUSY, MeshNodeState.DEGRADED, MeshNodeState.UNAVAILABLE, MeshNodeState.SUSPENDED, MeshNodeState.REVOKED},
            MeshNodeState.BUSY: {MeshNodeState.AVAILABLE, MeshNodeState.DEGRADED, MeshNodeState.UNAVAILABLE, MeshNodeState.SUSPENDED},
            MeshNodeState.DEGRADED: {MeshNodeState.AVAILABLE, MeshNodeState.UNAVAILABLE, MeshNodeState.SUSPENDED, MeshNodeState.REVOKED},
            MeshNodeState.UNAVAILABLE: {MeshNodeState.AVAILABLE, MeshNodeState.SUSPENDED, MeshNodeState.REVOKED, MeshNodeState.REMOVED},
            MeshNodeState.SUSPENDED: {MeshNodeState.TRUSTED, MeshNodeState.REVOKED, MeshNodeState.REMOVED},
            MeshNodeState.REVOKED: {MeshNodeState.REMOVED},
            MeshNodeState.REMOVED: set(),
        }
        if new_state in valid_transitions.get(self.state, set()):
            self.state = new_state
            self._updated_at = time.time()
            return True
        return False
    
    def update_trust(self, dimension: TrustDimension, value: float) -> None:
        """Update trust score for a dimension."""
        self.trust[dimension] = max(0.0, min(1.0, value))
        self._updated_at = time.time()
    
    def get_overall_trust(self) -> float:
        """Compute overall trust as weighted average."""
        if not self.trust:
            return 0.0
        weights = {
            TrustDimension.IDENTITY: 0.15,
            TrustDimension.SECURITY: 0.20,
            TrustDimension.EXECUTION: 0.15,
            TrustDimension.ECONOMIC: 0.10,
            TrustDimension.EVIDENCE: 0.15,
            TrustDimension.ORGANIZATION: 0.10,
            TrustDimension.NETWORK: 0.05,
            TrustDimension.BEHAVIOR: 0.10,
        }
        total = sum(self.trust.get(d, 0.0) * w for d, w in weights.items())
        weight_sum = sum(w for d, w in weights.items() if d in self.trust)
        return total / weight_sum if weight_sum > 0 else 0.0
    
    def is_available_for_task(self, required_caps: List[str] = None) -> bool:
        """Check if node can accept a task."""
        if self.state not in (MeshNodeState.AVAILABLE, MeshNodeState.BUSY):
            return False
        if required_caps:
            missing = set(required_caps) - set(self.capabilities)
            if missing:
                return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        d["trust"] = {k.value: v for k, v in self.trust.items()}
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshNode":
        trust_data = data.pop("trust", {})
        state_val = data.pop("state", "discovered")
        node = cls(**{k: v for k, v in data.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})
        node.state = MeshNodeState(state_val)
        node.trust = {TrustDimension(k): v for k, v in trust_data.items()}
        return node


@dataclass
class MeshEdge:
    """Mesh edge representing a relationship between nodes (section 3)."""
    
    edge_id: str = field(default_factory=lambda: f"edge-{uuid.uuid4().hex[:12]}")
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: EdgeType = EdgeType.COMMUNICATION
    provenance: Dict[str, Any] = field(default_factory=dict)  # source, evidence, timestamp
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    active: bool = True
    
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edge_type"] = self.edge_type.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshEdge":
        edge_type_val = data.pop("edge_type", "communication")
        edge = cls(**{k: v for k, v in data.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})
        edge.edge_type = EdgeType(edge_type_val)
        return edge


@dataclass
class CollectiveResult:
    """Result from collective intelligence execution (section 16)."""
    
    result_id: str = field(default_factory=lambda: f"coll-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    participants: List[str] = field(default_factory=list)
    independent_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agreements: List[Dict[str, Any]] = field(default_factory=list)
    disagreements: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    decision: str = ""
    rationale: str = ""
    uncertainty: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeshTask:
    """Task in the mesh execution context (section 31)."""
    
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    goal: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    preferred_topology: Optional[TopologyType] = None
    policy: Dict[str, Any] = field(default_factory=dict)
    privacy_level: str = "internal"  # public|internal|sensitive|highly_sensitive
    trust_requirements: Dict[TrustDimension, float] = field(default_factory=dict)
    latency_sla_ms: Optional[float] = None
    cost_budget: Optional[float] = None
    max_agents: int = 10
    verification_required: bool = False
    verification_quorum: int = 1
    parent_task_id: str = ""
    subtasks: List[str] = field(default_factory=list)
    assigned_nodes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    status: str = "pending"
    result: Optional[CollectiveResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["preferred_topology"] = self.preferred_topology.value if self.preferred_topology else None
        d["trust_requirements"] = {k.value: v for k, v in self.trust_requirements.items()}
        if self.result:
            d["result"] = self.result.to_dict()
        return d


@dataclass
class MeshTeam:
    """Dynamic team formed for a task (section 39)."""
    
    team_id: str = field(default_factory=lambda: f"team-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    members: List[str] = field(default_factory=list)  # node_ids
    roles: Dict[str, str] = field(default_factory=dict)  # node_id -> role
    topology: TopologyType = TopologyType.SEQUENTIAL
    coordinator_id: str = ""
    formed_at: float = field(default_factory=time.time)
    dissolved_at: float = 0.0
    active: bool = True
    budget_allocated: float = 0.0
    budget_used: float = 0.0
    performance: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["topology"] = self.topology.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshTeam":
        topo_val = data.pop("topology", "sequential")
        team = cls(**{k: v for k, v in data.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})
        team.topology = TopologyType(topo_val)
        return team


@dataclass
class MeshConfig:
    """Global mesh configuration."""
    
    mesh_id: str = field(default_factory=lambda: f"mesh-{uuid.uuid4().hex[:12]}")
    organization_id: str = "default"
    discovery_sources: List[str] = field(default_factory=lambda: [
        "local", "lan", "manual", "a2a", "org_registry", "marketplace", "trusted_registry", "direct_card"
    ])
    trust_thresholds: Dict[TrustDimension, float] = field(default_factory=lambda: {
        TrustDimension.IDENTITY: 0.7,
        TrustDimension.SECURITY: 0.8,
        TrustDimension.EXECUTION: 0.6,
        TrustDimension.ECONOMIC: 0.5,
        TrustDimension.EVIDENCE: 0.6,
        TrustDimension.ORGANIZATION: 0.7,
        TrustDimension.NETWORK: 0.5,
        TrustDimension.BEHAVIOR: 0.6,
    })
    max_parallel_agents: int = 10
    default_topology: TopologyType = TopologyType.SEQUENTIAL
    enable_self_optimization: bool = True
    optimization_interval_s: float = 300.0
    incident_response_enabled: bool = True
    governance_enabled: bool = True
    data_retention_days: int = 30
    heartbeat_interval_s: float = 30.0
    node_timeout_s: float = 120.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["trust_thresholds"] = {k.value: v for k, v in self.trust_thresholds.items()}
        d["default_topology"] = self.default_topology.value
        return d


def create_mesh_node_from_agent_card(
    agent_card: Dict[str, Any],
    organization_id: str = "",
    endpoint: str = "",
    location: str = ""
) -> MeshNode:
    """Create a MeshNode from an A2A Agent Card."""
    from aetheros_network.agent_card import parse_agent_card
    from aetheros_network.identity import AgentIdentity
    
    card = parse_agent_card(agent_card)
    
    capabilities = [skill.id for skill in card.skills]
    protocols = [f"A2A/{card.protocol_version}"]
    
    node = MeshNode(
        agent_id=f"a2a-{card.name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        identity={
            "name": card.name,
            "description": card.description,
            "version": card.version,
            "provider": card.provider,
        },
        organization_id=organization_id,
        capabilities=capabilities,
        protocols=protocols,
        endpoint=endpoint or card.url,
        location=location,
    )
    return node