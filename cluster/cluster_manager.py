"""
Cluster Manager — coordinates cluster startup, node lifecycle, health monitoring,
and graceful degradation.

The ClusterManager is the top-level orchestrator for the distributed execution layer.
It manages node registration, removal, health monitoring, and cluster lifecycle events.
All operations degrade gracefully when nodes fail or become unreachable.
"""

from __future__ import annotations

import enum
import logging
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus

from cluster.node_registry import NodeRegistry, NodeInfo, NodeStatus
from cluster.node_discovery import NodeDiscovery, DiscoveryResult
from cluster.node_health import NodeHealthMonitor, HealthStatus
from cluster.topology import ClusterTopology, TopologyNode, TopologyType
from cluster.cluster_metrics import ClusterMetricsCollector

logger = logging.getLogger(__name__)


class ClusterState(enum.Enum):
    """States of the cluster manager lifecycle."""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"


class ClusterRole(enum.Enum):
    """Roles a node can assume in the cluster."""
    LEADER = "leader"
    FOLLOWER = "follower"
    WORKER = "worker"
    OBSERVER = "observer"
    STANDALONE = "standalone"


class ClusterEvent(enum.Enum):
    """Events emitted by the cluster manager."""
    CLUSTER_STARTED = "cluster.started"
    CLUSTER_STOPPED = "cluster.stopped"
    CLUSTER_DEGRADED = "cluster.degraded"
    CLUSTER_FAILED = "cluster.failed"
    NODE_JOINED = "cluster.node_joined"
    NODE_LEFT = "cluster.node_left"
    NODE_FAILED = "cluster.node_failed"
    LEADER_ELECTED = "cluster.leader_elected"
    LEADER_LOST = "cluster.leader_lost"
    TOPOLOGY_CHANGED = "cluster.topology_changed"


@dataclass
class ClusterConfig:
    """Configuration for the cluster manager.

    Attributes:
        cluster_name: Human-readable cluster name
        node_id: Unique identifier for this node (auto-generated if empty)
        role: Role of this node in the cluster
        heartbeat_interval_seconds: How often to send heartbeats
        heartbeat_timeout_seconds: How long without heartbeat before node is suspect
        election_timeout_seconds: Leader election timeout
        enable_discovery: Enable automatic node discovery
        enable_health_monitoring: Enable health checks
        enable_metrics: Enable metrics collection
        max_nodes: Maximum number of nodes in the cluster (0 = unlimited)
        require_auth: Require authentication for node enrollment
        auth_token: Shared auth token (empty = no auth)
        data_dir: Directory for cluster state persistence
        graceful_shutdown_timeout: Max time for graceful shutdown
    """
    cluster_name: str = "aetheros-cluster"
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: ClusterRole = ClusterRole.STANDALONE
    heartbeat_interval_seconds: float = 5.0
    heartbeat_timeout_seconds: float = 15.0
    election_timeout_seconds: float = 30.0
    enable_discovery: bool = True
    enable_health_monitoring: bool = True
    enable_metrics: bool = True
    max_nodes: int = 0
    require_auth: bool = True
    auth_token: str = ""
    data_dir: Optional[str] = None
    graceful_shutdown_timeout: float = 10.0


class ClusterManager:
    """Orchestrates the distributed cluster lifecycle.

    Manages node registration, health monitoring, leader election,
    and graceful degradation. Integrates with the AetherOS Kernel
    event bus for observability.

    Usage:
        config = ClusterConfig(
            cluster_name="my-cluster",
            role=ClusterRole.LEADER,
            enable_discovery=True,
        )
        manager = ClusterManager(event_bus, config)
        manager.start()

        # ... cluster is operational ...

        manager.stop()
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[ClusterConfig] = None,
    ):
        self.config = config or ClusterConfig()
        self._event_bus = event_bus
        self._state = ClusterState.STOPPED
        self._lock = threading.RLock()
        self._start_time: Optional[float] = None
        self._shutdown_flag = False

        # Subsystems (created in start())
        self.node_registry: Optional[NodeRegistry] = None
        self.node_discovery: Optional[NodeDiscovery] = None
        self.health_monitor: Optional[NodeHealthMonitor] = None
        self.topology: Optional[ClusterTopology] = None
        self.metrics: Optional[ClusterMetricsCollector] = None

        # Leader election state
        self._leader_id: Optional[str] = None
        self._last_heartbeat: Dict[str, float] = {}
        self._election_in_progress = False

        # Registered callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "node_joined": [],
            "node_left": [],
            "node_failed": [],
            "leader_changed": [],
            "state_changed": [],
        }

        # Graceful shutdown
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> ClusterState:
        with self._lock:
            return self._state

    @property
    def is_leader(self) -> bool:
        return self.config.node_id == self._leader_id

    @property
    def leader_id(self) -> Optional[str]:
        return self._leader_id

    @property
    def node_count(self) -> int:
        if self.node_registry is None:
            return 1  # Just this node
        return len(self.node_registry.list_nodes())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the cluster manager and all subsystems."""
        with self._lock:
            if self._state in (ClusterState.RUNNING, ClusterState.DEGRADED):
                logger.warning("ClusterManager: already running")
                return
            self._state = ClusterState.INITIALIZING

        logger.info(
            "ClusterManager: starting cluster '%s' (node=%s, role=%s)",
            self.config.cluster_name, self.config.node_id[:8], self.config.role.value,
        )
        self._start_time = time.time()

        # Initialize subsystems
        self._init_subsystems()

        # Register self
        self._register_self()

        with self._lock:
            self._state = ClusterState.RUNNING
            self._leader_id = (
                self.config.node_id if self.config.role == ClusterRole.LEADER else None
            )

        # Start background threads
        self._start_background_tasks()

        self._emit_event(ClusterEvent.CLUSTER_STARTED, {
            "cluster_name": self.config.cluster_name,
            "node_id": self.config.node_id,
            "role": self.config.role.value,
        })

        logger.info(
            "ClusterManager: started (role=%s, leader=%s)",
            self.config.role.value, self._leader_id[:8] if self._leader_id else "none",
        )

    def _init_subsystems(self) -> None:
        """Create and initialize all cluster subsystems."""
        self.node_registry = NodeRegistry(self._event_bus)

        if self.config.enable_health_monitoring:
            self.health_monitor = NodeHealthMonitor(
                event_bus=self._event_bus,
                heartbeat_timeout=self.config.heartbeat_timeout_seconds,
                check_interval=self.config.heartbeat_interval_seconds,
            )

        self.topology = ClusterTopology(self._event_bus)

        if self.config.enable_metrics:
            self.metrics = ClusterMetricsCollector(self._event_bus)

        if self.config.enable_discovery:
            self.node_discovery = NodeDiscovery(
                self.node_registry,
                self._event_bus,
                require_auth=self.config.require_auth,
                auth_token=self.config.auth_token,
            )

    def _register_self(self) -> None:
        """Register this node in the registry."""
        if self.node_registry is None:
            return

        import platform as _platform
        from cluster.node_registry import NodeCapabilities

        capabilities = NodeCapabilities(
            hostname=_platform.node(),
            platform=sys.platform,
            python_version=_platform.python_version(),
            cpu_count=os.cpu_count() or 0,
            memory_mb=self._get_memory_mb(),
            supported_tools=[],
            supported_plugins=[],
        )

        self.node_registry.register_node(
            self.config.node_id,
            capabilities=capabilities,
            role=self.config.role,
            metadata={
                "cluster_name": self.config.cluster_name,
                "start_time": time.time(),
            },
        )
        self.node_registry.mark_healthy(self.config.node_id)

    def _get_memory_mb(self) -> int:
        """Get total system memory in MB."""
        try:
            import psutil
            return int(psutil.virtual_memory().total / (1024 * 1024))
        except ImportError:
            return 0

    def _start_background_tasks(self) -> None:
        """Start background monitoring threads."""
        if self.config.role == ClusterRole.LEADER:
            self._start_leader_tasks()

        if self.config.enable_health_monitoring and self.health_monitor:
            self.health_monitor.start(
                on_failure=self._on_node_failure,
            )

    def _start_leader_tasks(self) -> None:
        """Start leader-specific background tasks."""
        threading.Thread(
            target=self._leader_loop,
            daemon=True,
            name="cluster-leader",
        ).start()

    def _leader_loop(self) -> None:
        """Leader's main loop — manages cluster state."""
        while not self._shutdown_flag:
            try:
                self._check_node_health()
            except Exception as exc:
                logger.error("ClusterManager: leader loop error: %s", exc)
            time.sleep(self.config.heartbeat_interval_seconds)

    def _check_node_health(self) -> None:
        """Check all nodes for heartbeat timeouts."""
        if self.node_registry is None:
            return

        now = time.time()
        for node_id, node_info in self.node_registry.list_nodes().items():
            if node_id == self.config.node_id:
                continue

            last_seen = self._last_heartbeat.get(node_id, 0)
            if now - last_seen > self.config.heartbeat_timeout_seconds:
                logger.warning(
                    "ClusterManager: node %s heartbeat timeout (%.1fs ago)",
                    node_id[:8], now - last_seen,
                )
                self._on_node_failure(node_id)

    def _on_node_failure(self, node_id: str) -> None:
        """Handle a node failure event."""
        if self.node_registry is None:
            return

        node = self.node_registry.get_node(node_id)
        if node is None:
            return

        self.node_registry.mark_unhealthy(node_id)
        self._last_heartbeat.pop(node_id, None)

        self._emit_event(ClusterEvent.NODE_FAILED, {
            "node_id": node_id,
            "hostname": node.capabilities.hostname if node.capabilities else "unknown",
        })

        # Check if we should enter degraded mode
        if self.state == ClusterState.RUNNING:
            healthy_count = self._count_healthy_nodes()
            total = len(self.node_registry.list_nodes())
            if healthy_count < total // 2 + 1 and total > 1:
                with self._lock:
                    self._state = ClusterState.DEGRADED
                self._emit_event(ClusterEvent.CLUSTER_DEGRADED, {
                    "healthy": healthy_count,
                    "total": total,
                })

        # Notify callbacks
        self._notify_callbacks("node_failed", node_id)

    def _count_healthy_nodes(self) -> int:
        """Count healthy nodes in the registry."""
        if self.node_registry is None:
            return 0
        return sum(
            1 for n in self.node_registry.list_nodes().values()
            if n.status == NodeStatus.HEALTHY
        )

    def stop(self) -> None:
        """Gracefully stop the cluster manager."""
        with self._lock:
            if self._state == ClusterState.STOPPED:
                return
            self._state = ClusterState.STOPPING

        logger.info("ClusterManager: stopping...")
        self._shutdown_flag = True

        # Stop subsystems
        if self.health_monitor:
            self.health_monitor.stop()

        if self.node_discovery:
            self.node_discovery.stop()

        if self.node_registry:
            self.node_registry.mark_offline(self.config.node_id)

        self._stop_event.set()

        with self._lock:
            self._state = ClusterState.STOPPED

        self._emit_event(ClusterEvent.CLUSTER_STOPPED, {
            "node_id": self.config.node_id,
            "uptime_seconds": time.time() - (self._start_time or time.time()),
        })

        uptime = time.time() - (self._start_time or time.time())
        logger.info("ClusterManager: stopped (uptime: %.1fs)", uptime)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def send_heartbeat(self, node_id: str) -> None:
        """Record a heartbeat from a node."""
        self._last_heartbeat[node_id] = time.time()

        if self.node_registry:
            node = self.node_registry.get_node(node_id)
            if node and node.status != NodeStatus.HEALTHY:
                self.node_registry.mark_healthy(node_id)

    def receive_heartbeat(self, node_id: str) -> Dict[str, Any]:
        """Handle an incoming heartbeat. Returns this node's status."""
        self.send_heartbeat(node_id)
        return {
            "node_id": self.config.node_id,
            "state": self.state.value,
            "is_leader": self.is_leader,
            "leader_id": self._leader_id,
            "timestamp": time.time(),
            "node_count": self.node_count,
        }

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def node_joined(self, node_id: str, node_info: NodeInfo) -> None:
        """Handle a node joining the cluster."""
        if self.node_registry is None:
            return

        self.node_registry.register_node(
            node_id,
            capabilities=node_info.capabilities,
            role=node_info.role,
            metadata=node_info.metadata,
        )
        self._last_heartbeat[node_id] = time.time()

        self._emit_event(ClusterEvent.NODE_JOINED, {
            "node_id": node_id,
            "role": node_info.role.value if node_info.role else "unknown",
        })

        self._notify_callbacks("node_joined", node_id)

        # Update topology
        if self.topology:
            self.topology.add_node(
                TopologyNode(
                    node_id=node_id,
                    hostname=node_info.capabilities.hostname
                    if node_info.capabilities else node_id,
                    role=node_info.role.value if node_info.role else "worker",
                )
            )

    def node_left(self, node_id: str) -> None:
        """Handle a node leaving the cluster."""
        if self.node_registry is None:
            return

        self.node_registry.mark_offline(node_id)
        self._last_heartbeat.pop(node_id, None)

        self._emit_event(ClusterEvent.NODE_LEFT, {
            "node_id": node_id,
        })

        self._notify_callbacks("node_left", node_id)

        if self.topology:
            self.topology.remove_node(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the cluster entirely.

        Returns True if the node was found and removed.
        """
        if self.node_registry is None:
            return False

        result = self.node_registry.deregister_node(node_id)
        if result:
            self._last_heartbeat.pop(node_id, None)
            self._emit_event(ClusterEvent.NODE_LEFT, {
                "node_id": node_id,
                "reason": "removed",
            })
        return result

    # ------------------------------------------------------------------
    # Leader election (simplified — single leader with heartbeat)
    # ------------------------------------------------------------------

    def elect_leader(self, candidate_id: str) -> bool:
        """Elect a new leader. Returns True if the election succeeded.

        Simplified leader election: the candidate with the lowest node ID
        wins ties, or the first to request becomes leader.
        """
        with self._lock:
            if self._election_in_progress:
                return False
            self._election_in_progress = True

        try:
            if self.node_registry is None:
                return False

            # Verify candidate exists and is healthy
            candidate = self.node_registry.get_node(candidate_id)
            if candidate is None or candidate.status != NodeStatus.HEALTHY:
                return False

            old_leader = self._leader_id
            self._leader_id = candidate_id

            self._emit_event(ClusterEvent.LEADER_ELECTED, {
                "leader_id": candidate_id,
                "old_leader": old_leader,
            })

            self._notify_callbacks("leader_changed", candidate_id)

            logger.info(
                "ClusterManager: leader elected: %s (was: %s)",
                candidate_id[:8], old_leader[:8] if old_leader else "none",
            )
            return True
        finally:
            with self._lock:
                self._election_in_progress = False

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_node_joined(self, callback: Callable[[str], None]) -> Callable:
        """Register a callback for node join events.

        Returns an unsubscribe function.
        """
        with self._lock:
            self._callbacks["node_joined"].append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._callbacks["node_joined"]:
                    self._callbacks["node_joined"].remove(callback)

        return unsubscribe

    def on_node_left(self, callback: Callable[[str], None]) -> Callable:
        """Register a callback for node leave events."""
        with self._lock:
            self._callbacks["node_left"].append(callback)
        return lambda: self._callbacks["node_left"].remove(callback) if callback in self._callbacks["node_left"] else None

    def on_node_failed(self, callback: Callable[[str], None]) -> Callable:
        """Register a callback for node failure events."""
        with self._lock:
            self._callbacks["node_failed"].append(callback)
        return lambda: self._callbacks["node_failed"].remove(callback) if callback in self._callbacks["node_failed"] else None

    def on_leader_changed(self, callback: Callable[[str], None]) -> Callable:
        """Register a callback for leader change events."""
        with self._lock:
            self._callbacks["leader_changed"].append(callback)
        return lambda: self._callbacks["leader_changed"].remove(callback) if callback in self._callbacks["leader_changed"] else None

    def _notify_callbacks(self, event: str, data: Any) -> None:
        """Notify all callbacks for an event type."""
        with self._lock:
            callbacks = list(self._callbacks.get(event, []))
        for cb in callbacks:
            try:
                cb(data)
            except Exception as exc:
                logger.debug("ClusterManager: callback %s failed: %s", event, exc)

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def _emit_event(self, event: ClusterEvent, data: Dict[str, Any]) -> None:
        """Emit a cluster event through the event bus."""
        if self._event_bus:
            self._event_bus.emit_async(
                event.value,
                {"cluster": self.config.cluster_name, **data},
                source="cluster_manager",
            )

    # ------------------------------------------------------------------
    # Status & health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Get cluster health status."""
        with self._lock:
            registry_status = {}
            if self.node_registry:
                registry_status = self.node_registry.snapshot()

            return {
                "cluster_name": self.config.cluster_name,
                "node_id": self.config.node_id,
                "state": self._state.value,
                "role": self.config.role.value,
                "is_leader": self.is_leader,
                "leader_id": self._leader_id,
                "node_count": self.node_count,
                "uptime_seconds": time.time() - (self._start_time or time.time()),
                "registry": registry_status,
                "health_monitor": self.health_monitor.get_stats()
                if self.health_monitor else {},
                "topology": self.topology.snapshot() if self.topology else {},
            }

    def status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status."""
        base = self.health()
        if self.metrics:
            base["metrics"] = self.metrics.summary()
        return base



