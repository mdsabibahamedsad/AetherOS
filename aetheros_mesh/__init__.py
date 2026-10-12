"""AetherOS Global Agent Mesh (Master 49).

Transforms AetherOS from an intelligent agent economy into a
GLOBAL AGENT MESH capable of safely coordinating many heterogeneous
agents, capabilities, resources, models, tools, organizations, and
verification systems as one coherent distributed intelligence layer.

The mesh integrates:
- A2A federation (aetheros_network)
- Agent marketplace (aetheros_agent_market)
- Capability economy (aetheros_agent_economy)
- Multi-agent orchestration (aetheros_automation, aetheros_swarm)
- Autonomous workflows (aetheros_autonomy)

Core components:
- MeshNode: Identity, capability, trust, location, availability, resource, protocol, organization, policy, performance, economic state
- MeshEdge: Relationships (delegation, trust, capability, dependency, verification, collaboration, organization, resource, economic, communication)
- GlobalAgentMesh: Mesh controller
- MeshDiscovery: Dynamic topology discovery
- MeshTrust: Multidimensional trust
- MeshRouter: Topology-aware routing
- TeamFormationEngine: Dynamic team formation
- CollectiveIntelligenceEngine: Multi-agent reasoning
- MeshBlackboard: Shared state with locking
- MeshOptimizationEngine: Self-optimization
- MeshGovernanceEngine: Policy enforcement
- MeshIncidentEngine: Security incident response
"""

from __future__ import annotations

__version__ = "0.1.0"

from .models import (
    MeshNode,
    MeshNodeState,
    MeshEdge,
    EdgeType,
    CollectiveResult,
    MeshTask,
    MeshTeam,
)

from .discovery import MeshDiscovery
from .trust import MeshTrust, TrustDimension
from .router import MeshRouter, TopologyType
from .team import TeamFormationEngine
from .collective import CollectiveIntelligenceEngine, CollectiveMode
from .blackboard import MeshBlackboard
from .optimization import MeshOptimizationEngine
from .governance import MeshGovernanceEngine
from .incident import MeshIncidentEngine
from .mesh import GlobalAgentMesh

__all__ = [
    "MeshNode",
    "MeshNodeState",
    "MeshEdge",
    "EdgeType",
    "CollectiveResult",
    "MeshTask",
    "MeshTeam",
    "MeshDiscovery",
    "MeshTrust",
    "TrustDimension",
    "MeshRouter",
    "TopologyType",
    "TeamFormationEngine",
    "CollectiveIntelligenceEngine",
    "CollectiveMode",
    "MeshBlackboard",
    "MeshOptimizationEngine",
    "MeshGovernanceEngine",
    "MeshIncidentEngine",
    "GlobalAgentMesh",
]