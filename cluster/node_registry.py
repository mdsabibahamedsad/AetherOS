"""
Node Registry — tracks node identity, capabilities, resources, health status,
and available tools/plugins for distributed task scheduling.

Each node in the cluster advertises its capabilities through the registry.
The scheduler uses this information to route tasks to appropriate nodes.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus
from cluster.topology import TopologyType

logger = logging.getLogger(__name__)


class NodeStatus(enum.Enum):
    """Health status of a registered node."""
    UNKNOWN = "unknown"
    JOINING = "joining"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    REMOVED = "removed"


@dataclass
class NodeCapabilities:
    """Advertised capabilities and resources of a node.

    Attributes:
        hostname: Node hostname
        platform: Operating system platform
        python_version: Python runtime version
        cpu_count: Number of CPU cores
        memory_mb: Total system memory in MB
        gpu_count: Number of GPUs available
        gpu_memory_mb: Total GPU memory in MB
        supported_tools: List of tool names this node can execute
        supported_plugins: List of plugin names installed on this node
        supported_models: List of model names available on this node
        software_version: AetherOS version running on this node
        custom: Custom capability key-value pairs
    """
    hostname: str = ""
    platform: str = ""
    python_version: str = ""
    cpu_count: int = 0
    memory_mb: int = 0
    gpu_count: int = 0
    gpu_memory_mb: int = 0
    supported_tools: List[str] = field(default_factory=list)
    supported_plugins: List[str] = field(default_factory=list)
    supported_models: List[str] = field(default_factory=list)
    software_version: str = ""
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeInfo:
    """Complete information about a registered node.

    Attributes:
        node_id: Unique node identifier
        capabilities: Node capabilities and resources
        role: Cluster role of this node
        status: Current health status
        registered_at: When the node was registered
        last_seen_at: Last heartbeat timestamp
        metadata: Additional metadata (labels, tags, etc.)
    """
    node_id: str = ""
    capabilities: Optional[NodeCapabilities] = None
    role: Optional[Any] = None  # ClusterRole (avoid circular import)
    status: NodeStatus = NodeStatus.UNKNOWN
    registered_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NodeRegistry:
    """Runtime registry of all nodes in the cluster.

    Tracks node identity, capabilities, resources, and health status.
    Used by the scheduler to determine where tasks can execute.

    Thread-safe. Integrates with the kernel event bus for observability.

    Usage:
        registry = NodeRegistry(event_bus)

        # Register a node
        registry.register_node("node-1", capabilities=NodeCapabilities(...))

        # Find nodes matching requirements
        nodes = registry.find_nodes(required_tools=["terminal"])
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        # node_id -> NodeInfo
        self._nodes: Dict[str, NodeInfo] = {}
        # tool_name -> set of node_ids that support it
        self._tool_index: Dict[str, Set[str]] = {}
        # plugin_name -> set of node_ids that have it
        self._plugin_index: Dict[str, Set[str]] = {}
        # capability -> set of node_ids matching
        self._capability_index: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_node(
        self,
        node_id: str,
        capabilities: Optional[NodeCapabilities] = None,
        role: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NodeInfo:
        """Register a node in the cluster.

        If the node already exists, updates its information.

        Args:
            node_id: Unique node identifier
            capabilities: Node capabilities (auto-detected if None)
            role: Cluster role
            metadata: Additional metadata

        Returns:
            The registered NodeInfo
        """
        now = time.time()

        with self._lock:
            existing = self._nodes.get(node_id)
            if existing:
                # Update existing
                existing.last_seen_at = now
                if capabilities:
                    existing.capabilities = capabilities
                if role:
                    existing.role = role
                if metadata:
                    existing.metadata.update(metadata)
                if existing.status in (NodeStatus.UNKNOWN, NodeStatus.OFFLINE):
                    existing.status = NodeStatus.JOINING
                node_info = existing
            else:
                # Create new
                node_info = NodeInfo(
                    node_id=node_id,
                    capabilities=capabilities or NodeCapabilities(),
                    role=role,
                    status=NodeStatus.JOINING,
                    registered_at=now,
                    last_seen_at=now,
                    metadata=metadata or {},
                )
                self._nodes[node_id] = node_info

            # Update indexes
            self._reindex(node_id, node_info)

        logger.info(
            "NodeRegistry: registered '%s' (hostname=%s, status=%s)",
            node_id[:8],
            node_info.capabilities.hostname if node_info.capabilities else "?",
            node_info.status.value,
        )

        if self._event_bus:
            self._event_bus.emit_async("cluster.node_registered", {
                "node_id": node_id,
                "hostname": node_info.capabilities.hostname
                if node_info.capabilities else "?",
            })

        return node_info

    def _reindex(self, node_id: str, node_info: NodeInfo) -> None:
        """Rebuild capability/tool/plugin indexes for a node."""
        # Clear old indexes for this node
        for idx in (self._tool_index, self._plugin_index, self._capability_index):
            for key in list(idx.keys()):
                idx[key].discard(node_id)

        if not node_info.capabilities:
            return

        caps = node_info.capabilities

        for tool in caps.supported_tools:
            self._tool_index.setdefault(tool, set()).add(node_id)

        for plugin in caps.supported_plugins:
            self._plugin_index.setdefault(plugin, set()).add(node_id)

        # Index custom capabilities
        for cap_key in caps.custom:
            self._capability_index.setdefault(cap_key, set()).add(node_id)

    def deregister_node(self, node_id: str) -> bool:
        """Remove a node from the registry.

        Returns True if the node existed and was removed.
        """
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if node is None:
                return False

            # Clean up indexes
            for idx in (self._tool_index, self._plugin_index, self._capability_index):
                for key in list(idx.keys()):
                    idx[key].discard(node_id)
                    if not idx[key]:
                        del idx[key]

        logger.info("NodeRegistry: deregistered '%s'", node_id[:8])

        if self._event_bus:
            self._event_bus.emit_async("cluster.node_deregistered", {
                "node_id": node_id,
            })

        return True

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    def mark_healthy(self, node_id: str) -> bool:
        """Mark a node as healthy."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = NodeStatus.HEALTHY
            node.last_seen_at = time.time()
        return True

    def mark_unhealthy(self, node_id: str) -> bool:
        """Mark a node as unhealthy (degraded or failed)."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = NodeStatus.UNHEALTHY
        return True

    def mark_degraded(self, node_id: str) -> bool:
        """Mark a node as degraded (still responding but performance issues)."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = NodeStatus.DEGRADED
        return True

    def mark_offline(self, node_id: str) -> bool:
        """Mark a node as offline."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = NodeStatus.OFFLINE
            node.last_seen_at = time.time()
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """Get a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> Dict[str, NodeInfo]:
        """Get all registered nodes (snapshot)."""
        with self._lock:
            return dict(self._nodes)

    def list_healthy_nodes(self) -> List[NodeInfo]:
        """Get all healthy nodes."""
        with self._lock:
            return [
                n for n in self._nodes.values()
                if n.status == NodeStatus.HEALTHY
            ]

    def find_nodes_with_tool(self, tool_name: str) -> List[NodeInfo]:
        """Find nodes that support a specific tool."""
        with self._lock:
            node_ids = self._tool_index.get(tool_name, set())
            return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_nodes_with_plugin(self, plugin_name: str) -> List[NodeInfo]:
        """Find nodes that have a specific plugin installed."""
        with self._lock:
            node_ids = self._plugin_index.get(plugin_name, set())
            return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_nodes_with_capability(self, capability: str) -> List[NodeInfo]:
        """Find nodes matching a custom capability."""
        with self._lock:
            node_ids = self._capability_index.get(capability, set())
            return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_nodes(
        self,
        required_tools: Optional[List[str]] = None,
        required_plugins: Optional[List[str]] = None,
        min_cpu: int = 0,
        min_memory_mb: int = 0,
        require_gpu: bool = False,
        healthy_only: bool = True,
    ) -> List[NodeInfo]:
        """Find nodes matching all specified requirements.

        Args:
            required_tools: Tools the node must support
            required_plugins: Plugins the node must have
            min_cpu: Minimum CPU core count
            min_memory_mb: Minimum memory in MB
            require_gpu: Node must have at least one GPU
            healthy_only: Only return healthy nodes

        Returns:
            List of matching NodeInfo objects
        """
        with self._lock:
            candidates = list(self._nodes.values())

        if healthy_only:
            candidates = [n for n in candidates if n.status == NodeStatus.HEALTHY]

        if required_tools:
            tool_set = set(required_tools)
            candidates = [
                n for n in candidates
                if n.capabilities and tool_set.issubset(set(n.capabilities.supported_tools))
            ]

        if required_plugins:
            plugin_set = set(required_plugins)
            candidates = [
                n for n in candidates
                if n.capabilities and plugin_set.issubset(set(n.capabilities.supported_plugins))
            ]

        if min_cpu > 0:
            candidates = [
                n for n in candidates
                if n.capabilities and n.capabilities.cpu_count >= min_cpu
            ]

        if min_memory_mb > 0:
            candidates = [
                n for n in candidates
                if n.capabilities and n.capabilities.memory_mb >= min_memory_mb
            ]

        if require_gpu:
            candidates = [
                n for n in candidates
                if n.capabilities and n.capabilities.gpu_count > 0
            ]

        return candidates

    def node_has_tool(self, node_id: str, tool_name: str) -> bool:
        """Check if a specific node supports a tool."""
        with self._lock:
            node_ids = self._tool_index.get(tool_name, set())
            return node_id in node_ids

    # ------------------------------------------------------------------
    # Status & snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the registry."""
        with self._lock:
            nodes = dict(self._nodes)

        healthy = sum(1 for n in nodes.values() if n.status == NodeStatus.HEALTHY)
        unhealthy = sum(1 for n in nodes.values() if n.status == NodeStatus.UNHEALTHY)
        offline = sum(1 for n in nodes.values() if n.status == NodeStatus.OFFLINE)

        return {
            "total_nodes": len(nodes),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "offline": offline,
            "tools_count": len(self._tool_index),
            "plugins_count": len(self._plugin_index),
            "capabilities_count": len(self._capability_index),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "hostname": n.capabilities.hostname if n.capabilities else "?",
                    "status": n.status.value,
                    "role": n.role.value if n.role else "standalone",
                    "cpu_count": n.capabilities.cpu_count if n.capabilities else 0,
                    "memory_mb": n.capabilities.memory_mb if n.capabilities else 0,
                    "gpu_count": n.capabilities.gpu_count if n.capabilities else 0,
                    "registered_at": n.registered_at,
                    "last_seen_at": n.last_seen_at,
                    "tool_count": len(n.capabilities.supported_tools)
                    if n.capabilities else 0,
                }
                for n in nodes.values()
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            return {
                "total_nodes": len(self._nodes),
                "total_tools": len(self._tool_index),
                "total_plugins": len(self._plugin_index),
                "total_capabilities": len(self._capability_index),
                "healthy_nodes": sum(
                    1 for n in self._nodes.values()
                    if n.status == NodeStatus.HEALTHY
                ),
            }
