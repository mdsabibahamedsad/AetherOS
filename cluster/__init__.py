"""
AetherOS Distributed Execution Layer.

Provides multi-node coordination, capability-aware scheduling, secure node
enrollment, and distributed observability. The entire layer is OPTIONAL —
a standard single-machine installation works unchanged.

Architecture
-----------
The cluster layer sits alongside the Swarm and Kernel layers:

    User Request
         │
         ▼
    ┌─────────────────────────────────────────────────────┐
    │              Cluster Manager                         │
    │                                                      │
    │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐ │
    │  │NodeReg.  │  │Discovery  │  │Topology          │ │
    │  └────┬─────┘  └────┬──────┘  └───────┬──────────┘ │
    │       │              │                 │             │
    │  ┌────▼─────┐  ┌────▼──────┐  ┌───────▼──────────┐ │
    │  │Scheduler │  │Balancer   │  │Executor          │ │
    │  └────┬─────┘  └────┬──────┘  └───────┬──────────┘ │
    │       │              │                 │             │
    │  ┌────▼─────┐  ┌────▼──────┐  ┌───────▼──────────┐ │
    │  │Transport │  │State Sync │  │Artifact Sync     │ │
    │  └──────────┘  └───────────┘  └──────────────────┘ │
    └─────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────────┐
    │     Swarm Layer  │  Kernel Layer  │  Cron Layer     │
    └─────────────────────────────────────────────────────┘

Key design decisions:
  - Every cluster component is optional; imports must not break
    single-node operation.
  - Transport is replaceable (TCP, mTLS, Unix sockets, custom).
  - All inter-node communication is authenticated and encrypted.
  - Nodes self-register capabilities; the scheduler routes accordingly.
"""

from cluster.cluster_manager import (
    ClusterManager,
    ClusterConfig,
    ClusterState,
    ClusterRole,
    ClusterEvent,
)
from cluster.node_registry import (
    NodeRegistry,
    NodeInfo,
    NodeStatus,
    NodeCapabilities,
)
from cluster.node_discovery import (
    NodeDiscovery,
    DiscoveryProvider,
    ManualDiscoveryProvider,
    NetworkDiscoveryProvider,
    DiscoveryResult,
)
from cluster.node_health import (
    NodeHealthMonitor,
    HealthCheckResult,
    HealthStatus,
)
from cluster.scheduler import (
    DistributedScheduler,
    SchedulingDecision,
    SchedulingStrategy,
    ExecutionTarget,
)
from cluster.load_balancer import (
    LoadBalancer,
    LoadBalancingStrategy,
    BalancerDecision,
)
from cluster.executor import (
    DistributedExecutor,
    DistributedTask,
    TaskStatus,
    ExecutionResult,
)
from cluster.transport import (
    TransportProvider,
    Message,
    MessageType,
    RequestResponseTransport,
)
from cluster.rpc import (
    RPCClient,
    RPCServer,
    RPCRequest,
    RPCResponse,
    RPCHandler,
)
from cluster.task_replication import (
    TaskReplicator,
    ReplicationStrategy,
    ReplicaState,
)
from cluster.artifact_sync import (
    ArtifactSynchronizer,
    Artifact,
    SyncDirection,
    SyncStrategy,
)
from cluster.state_sync import (
    StateSynchronizer,
    StateSnapshot,
    SyncOp,
    ConflictStrategy,
)
from cluster.distributed_events import (
    DistributedEventBus,
    ClusterEvent as DistClusterEvent,
    EventScope,
)
from cluster.capability_registry import (
    ClusterCapabilityRegistry,
    NodeCapability,
    CapabilityCategory,
)
from cluster.topology import (
    ClusterTopology,
    TopologyNode,
    TopologyLink,
    TopologyType,
)
from cluster.cluster_metrics import (
    ClusterMetricsCollector,
    MetricPoint,
    MetricCategory,
)

__all__ = [
    # Cluster Manager
    "ClusterManager", "ClusterConfig", "ClusterState", "ClusterRole", "ClusterEvent",
    # Node Registry
    "NodeRegistry", "NodeInfo", "NodeStatus", "NodeCapabilities",
    # Node Discovery
    "NodeDiscovery", "DiscoveryProvider", "ManualDiscoveryProvider",
    "NetworkDiscoveryProvider", "DiscoveryResult",
    # Node Health
    "NodeHealthMonitor", "HealthCheckResult", "HealthStatus",
    # Distributed Scheduler
    "DistributedScheduler", "SchedulingDecision", "SchedulingStrategy", "ExecutionTarget",
    # Load Balancer
    "LoadBalancer", "LoadBalancingStrategy", "BalancerDecision",
    # Distributed Executor
    "DistributedExecutor", "DistributedTask", "TaskStatus", "ExecutionResult",
    # Transport
    "TransportProvider", "Message", "MessageType", "RequestResponseTransport",
    # RPC
    "RPCClient", "RPCServer", "RPCRequest", "RPCResponse", "RPCHandler",
    # Task Replication
    "TaskReplicator", "ReplicationStrategy", "ReplicaState",
    # Artifact Sync
    "ArtifactSynchronizer", "Artifact", "SyncDirection", "SyncStrategy",
    # State Sync
    "StateSynchronizer", "StateSnapshot", "SyncOp", "ConflictStrategy",
    # Distributed Events
    "DistributedEventBus", "DistClusterEvent", "EventScope",
    # Capability Registry
    "ClusterCapabilityRegistry", "NodeCapability", "CapabilityCategory",
    # Topology
    "ClusterTopology", "TopologyNode", "TopologyLink", "TopologyType",
    # Metrics
    "ClusterMetricsCollector", "MetricPoint", "MetricCategory",
]
