# AetherOS Distributed Execution Layer

## Cluster Architecture

The AetherOS Distributed Execution Layer enables multiple trusted AetherOS nodes to cooperate on workloads while preserving reliability, security, and observability. The entire layer is **optional** — a standard single-machine installation continues to work unchanged.

```
┌──────────────────────────────────────────────────────────────────┐
│                      Cluster Manager                              │
│                                                                   │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Node     │  │ Discovery │  │ Topology │  │ Health Monitor │ │
│  │ Registry │  │           │  │          │  │                │ │
│  └────┬─────┘  └────┬──────┘  └────┬─────┘  └───────┬────────┘ │
│       │              │              │                 │          │
│  ┌────▼──────────────▼──────────────▼─────────────────▼────────┐ │
│  │                   Scheduler & Load Balancer                   │ │
│  └────┬──────────────────────────────┬─────────────────────────┘ │
│       │                              │                           │
│  ┌────▼──────────────┐    ┌─────────▼───────────────┐          │
│  │  Distributed      │    │  Transport / RPC        │          │
│  │  Executor         │    │  (HTTP, mTLS, custom)   │          │
│  └────┬──────────────┘    └─────────┬───────────────┘          │
│       │                            │                            │
│  ┌────▼──────────────┐    ┌─────────▼───────────────┐          │
│  │  State Sync       │    │  Artifact Sync          │          │
│  │  Task/Workflow    │    │  Files, Reports,        │          │
│  │  Checkpoints      │    │  Patches, Logs          │          │
│  └────┬──────────────┘    └─────────────────────────┘          │
│       │                                                         │
│  ┌────▼──────────────────────────────────────────────────────┐  │
│  │  Capability Registry │ Metrics │ Distributed Events       │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│           AetherOS Core (Kernel, Swarm, Cron, Tools)            │
│           Existing single-node operation UNCHANGED              │
└──────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Optional:** Importing the cluster module never breaks single-node operation.
2. **Backward Compatible:** All existing APIs, tools, and workflows continue working.
3. **Capability-Aware:** Tasks are routed to nodes that have the right tools, plugins, and resources.
4. **Secure:** Mutual authentication, encrypted transport, explicit node enrollment.
5. **Observable:** Structured metrics and events for cluster health monitoring.

## Node Lifecycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────────┐
│ DISCOVER │ ──▶ │ JOINING  │ ──▶ │ HEALTHY │ ──▶ │  OFFLINE     │
│          │     │ (Pending │     │         │     │  (Removed)   │
│          │     │ Approval)│     │         │     │              │
└──────────┘     └──────────┘     └──────────┘     └──────────────┘
                                       │
                                       ▼
                                  ┌──────────┐
                                  │ DEGRADED │
                                  │ (Suspect)│
                                  └──────────┘
                                       │
                                       ▼
                                  ┌──────────┐
                                  │FAILED    │
                                  │(Timeout) │
                                  └──────────┘
```

### Phase 1: Discovery
- Nodes discover each other through pluggable discovery providers.
- Built-in providers: Manual configuration, local network broadcast.
- Custom providers can be implemented via the `DiscoveryProvider` ABC.

### Phase 2: Enrollment
- Discovered nodes require explicit approval (unless auth is disabled).
- Mutual authentication via shared auth tokens.
- Node capabilities are advertised during enrollment.

### Phase 3: Active Operation
- Nodes send periodic heartbeats.
- Health monitor tracks heartbeat intervals and detects failures.
- Scheduler routes tasks based on capabilities, load, and latency.

### Phase 4: Departure
- Graceful shutdown: node deregisters itself, completes active tasks.
- Node failure: detected via heartbeat timeout, tasks are migrated.
- Node removal: manual removal via `remove_node()` API.

## Scheduling Model

```
┌──────────────┐
│   Task       │
│ Requirements │
│  - Tools     │
│  - Resources │
│  - Priority  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│          DistributedScheduler        │
│                                      │
│  1. Find candidate nodes             │
│  2. Filter by requirements           │
│  3. Score by capability match        │
│  4. Apply load balancer strategy     │
│  5. Return SchedulingDecision        │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│          Execution Target            │
│                                      │
│  LOCAL   ── Execute on this node     │
│  REMOTE  ── Execute on remote node   │
│  PARALLEL ── Execute on N nodes      │
│  FALLBACK ── Run locally as fallback │
└──────────────────────────────────────┘
```

### Scheduling Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `LOCAL_ONLY` | Execute on the current node | Development, testing |
| `REMOTE_ONLY` | Always execute on remote nodes | Offloading compute |
| `BALANCED` | Consider load, resources, capabilities | General purpose |
| `LOWEST_LATENCY` | Prefer network-nearest nodes | Latency-sensitive tasks |
| `MOST_RESOURCES` | Prefer nodes with most free resources | Resource-intensive tasks |
| `CAPABILITY_MATCH` | Prefer nodes with best capability fit | Specialized tooling |

## Security Model

### Authentication
- **Token-based:** Shared auth token verified during discovery and enrollment.
- **Mutual authentication:** Both sides verify identity before exchanging data.
- **Pluggable:** Custom auth providers can be implemented.

### Authorization
- **Node trust model:** Only explicitly approved nodes can join the cluster.
- **Capability gating:** Nodes can only execute tasks their capabilities support.
- **Policy constraints:** Custom policies can restrict which tasks a node can accept.

### Communication Security
- **Encrypted transport:** TLS/SSL support for inter-node communication.
- **mTLS support:** Mutual TLS for certificate-based authentication.
- **Message integrity:** All messages are validated before processing.

### Node Enrollment
```
1. Discovery → Node found with valid auth token
2. Pending  → Admin must explicitly approve (optional)
3. Joined   → Node registered and begins heartbeating
4. Removed  → Node deregistered, connections closed
```

## Synchronization Strategy

### State Synchronization
- **Minimal data:** Only task state, workflow state, checkpoints, and progress are synchronized.
- **Conflict resolution:** Last-write-wins by default; merge and first-write-wins also supported.
- **Batched propagation:** State changes are batched before transmission to reduce network overhead.

### Artifact Synchronization
- **Smart transfers:** Checksum-based change detection avoids unnecessary transfer.
- **Size thresholds:** Files below/above configurable size limits can be skipped.
- **Manifest support:** Large directories can be synced via manifest (file list only).

## Extension Guide

### Adding a Discovery Provider

```python
from cluster.node_discovery import DiscoveryProvider, DiscoveryResult

class MyDiscoveryProvider(DiscoveryProvider):
    def discover(self) -> list[DiscoveryResult]:
        # Custom discovery logic
        return [DiscoveryResult(
            node_id="node-1",
            hostname="10.0.0.1",
            port=9876,
            auth_token="my-token",
        )]

# Register with NodeDiscovery
discovery.add_provider(MyDiscoveryProvider())
```

### Adding a Transport Provider

```python
from cluster.transport import TransportProvider, Message

class MyTransport(TransportProvider):
    def send(self, message: Message) -> Optional[Message]:
        # Custom transport logic
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def is_connected(self, node_id: str) -> bool:
        return True
```

### Adding a Custom Routing Strategy

```python
from cluster.load_balancer import LoadBalancingStrategy

# New strategies can be added to LoadBalancingStrategy enum
# and implemented in the LoadBalancer class
```

### Plugin Integration

Plugins can contribute:
- Transport providers
- Discovery providers
- Routing strategies
- Metrics exporters
- Cluster schedulers

No kernel changes are required for plugin integration. Create a plugin that imports from `cluster` and registers its components.

## Operational Considerations

### Monitoring

The `ClusterMetricsCollector` provides:
- Cluster health (node count, status distribution)
- Task distribution (which nodes are executing what)
- Execution latency (p50/p75/p90/p99)
- Queue depths
- Failure rates
- Resource utilization

```python
# Access cluster metrics
metrics = cluster_manager.metrics
summary = metrics.summary()
print(f"Error rate: {summary['error_rate_pct']}%")
print(f"Operations: {summary['total_operations']}")
```

### Failure Handling

| Failure Mode | Behavior |
|-------------|----------|
| Node failure | Heartbeat timeout → task migration to healthy nodes |
| Network partition | Degraded mode with healthy majority |
| Partial completion | Automatic retry with exponential backoff |
| Task timeout | Task cancelled, configurable timeout per task |
| Graceful shutdown | Active tasks completed before node leaves |

### Developer APIs

```python
# Node management
register_node(node_id, capabilities, role)
remove_node(node_id)
list_nodes()

# Task management
submit_distributed_task(task)
query_cluster()
stream_cluster_events()

# State management
synchronize_state(state_type, key, data)
create_checkpoint(workflow_id, data)

# Health
cluster_health()
cluster_status()
```

### Configuration

```python
config = ClusterConfig(
    cluster_name="my-cluster",
    role=ClusterRole.LEADER,
    heartbeat_interval_seconds=5.0,
    heartbeat_timeout_seconds=15.0,
    enable_discovery=True,
    require_auth=True,
    auth_token="your-secret-token",
)
```

### Testing

Tests are in `tests/cluster/` and cover:
- Single-node lifecycle
- Multi-node coordination
- Node discovery and enrollment
- Task routing and scheduling
- Load balancing strategies
- State synchronization
- Artifact synchronization
- Failure recovery
- Security checks
