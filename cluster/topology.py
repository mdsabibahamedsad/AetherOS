"""
Cluster Topology — tracks the network topology of the cluster.

Maintains information about:
  - Node locations and network addresses
  - Inter-node links and their latency
  - Network topology type (mesh, star, tree, ring)
  - Connection health
  - Network partitions
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class TopologyType(enum.Enum):
    """Types of cluster network topology."""
    STANDALONE = "standalone"         # Single node
    MESH = "mesh"                     # All nodes connected to all others
    STAR = "star"                     # Central hub with leaf nodes
    TREE = "tree"                     # Hierarchical parent-child
    RING = "ring"                     # Each node connected to two neighbors
    HYBRID = "hybrid"                 # Mixed topology


@dataclass
class TopologyNode:
    """A node in the cluster topology.

    Attributes:
        node_id: Unique node identifier
        hostname: Node hostname or IP address
        port: Cluster communication port
        role: Node role in the cluster
        is_active: Whether the node is currently active
        last_seen: Last time the node was reachable
        metadata: Additional topology metadata
    """
    node_id: str = ""
    hostname: str = ""
    port: int = 0
    role: str = "worker"
    is_active: bool = True
    last_seen: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyLink:
    """A network link between two nodes.

    Attributes:
        source: Source node ID
        target: Target node ID
        latency_ms: Estimated round-trip latency
        bandwidth_mbps: Estimated bandwidth
        is_active: Whether the link is operational
        last_checked: When the link was last verified
        metadata: Additional link metadata
    """
    source: str = ""
    target: str = ""
    latency_ms: float = 0.0
    bandwidth_mbps: float = 0.0
    is_active: bool = True
    last_checked: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClusterTopology:
    """Tracks cluster network topology.

    Maintains the current view of which nodes are connected and how.
    Used by the scheduler and load balancer for latency-aware routing.

    Usage:
        topology = ClusterTopology(event_bus)

        # Add a node
        topology.add_node(TopologyNode(node_id="node-1", hostname="10.0.0.1"))

        # Record a link between nodes
        topology.add_link(TopologyLink(source="node-1", target="node-2", latency_ms=5.0))

        # Get the nearest nodes
        nearest = topology.get_nearest_nodes("node-1", limit=3)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()

        # node_id -> TopologyNode
        self._nodes: Dict[str, TopologyNode] = {}
        # (source, target) -> TopologyLink
        self._links: Dict[tuple, TopologyLink] = {}
        # Topology type
        self._topology_type = TopologyType.STANDALONE

        # Self node
        self._self_node_id: str = ""

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def set_self(self, node_id: str) -> None:
        """Set this node's ID in the topology."""
        self._self_node_id = node_id

    def add_node(self, node: TopologyNode) -> None:
        """Add a node to the topology."""
        with self._lock:
            self._nodes[node.node_id] = node
            self._update_topology_type()

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the topology."""
        with self._lock:
            result = self._nodes.pop(node_id, None) is not None
            # Remove all links involving this node
            self._links = {
                k: v for k, v in self._links.items()
                if k[0] != node_id and k[1] != node_id
            }
            if result:
                self._update_topology_type()
            return result

    def get_node(self, node_id: str) -> Optional[TopologyNode]:
        """Get a topology node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> List[TopologyNode]:
        """List all nodes in the topology."""
        with self._lock:
            return list(self._nodes.values())

    def node_count(self) -> int:
        """Get the number of nodes in the topology."""
        with self._lock:
            return len(self._nodes)

    def update_node_status(self, node_id: str, is_active: bool) -> None:
        """Update whether a node is active."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.is_active = is_active
                node.last_seen = time.time() if is_active else node.last_seen

    # ------------------------------------------------------------------
    # Link management
    # ------------------------------------------------------------------

    def add_link(self, link: TopologyLink) -> None:
        """Record a network link between two nodes."""
        with self._lock:
            key = self._link_key(link.source, link.target)
            self._links[key] = link
            self._update_topology_type()

    def remove_link(self, source: str, target: str) -> bool:
        """Remove a link between two nodes."""
        with self._lock:
            return self._links.pop(self._link_key(source, target), None) is not None

    def get_link(self, source: str, target: str) -> Optional[TopologyLink]:
        """Get the link between two nodes."""
        with self._lock:
            return self._links.get(self._link_key(source, target))

    def update_link_latency(self, source: str, target: str,
                            latency_ms: float) -> None:
        """Update the estimated latency of a link."""
        with self._lock:
            key = self._link_key(source, target)
            link = self._links.get(key)
            if link:
                link.latency_ms = latency_ms
                link.last_checked = time.time()

    def update_link_bandwidth(self, source: str, target: str,
                              bandwidth_mbps: float) -> None:
        """Update the estimated bandwidth of a link."""
        with self._lock:
            key = self._link_key(source, target)
            link = self._links.get(key)
            if link:
                link.bandwidth_mbps = bandwidth_mbps
                link.last_checked = time.time()

    def get_nearest_nodes(self, node_id: str, limit: int = 5) -> List[TopologyNode]:
        """Get the nearest nodes by latency."""
        with self._lock:
            distances = []
            for other_id in self._nodes:
                if other_id == node_id:
                    continue
                link = self._links.get(self._link_key(node_id, other_id))
                latency = link.latency_ms if link else float("inf")
                distances.append((latency, other_id))

            distances.sort(key=lambda x: x[0])
            nearest_ids = [nid for _, nid in distances[:limit]]
            return [self._nodes[nid] for nid in nearest_ids if nid in self._nodes]

    def get_links_for_node(self, node_id: str) -> List[TopologyLink]:
        """Get all links connected to a node."""
        with self._lock:
            return [
                v for k, v in self._links.items()
                if k[0] == node_id or k[1] == node_id
            ]

    @staticmethod
    def _link_key(a: str, b: str) -> tuple:
        """Create a canonical, order-independent link key."""
        return (a, b) if a < b else (b, a)

    # ------------------------------------------------------------------
    # Topology type
    # ------------------------------------------------------------------

    def get_topology_type(self) -> TopologyType:
        """Get the current topology type."""
        with self._lock:
            return self._topology_type

    def _update_topology_type(self) -> None:
        """Re-evaluate the topology type based on current state."""
        node_count = len(self._nodes)
        link_count = len(self._links)

        if node_count <= 1:
            self._topology_type = TopologyType.STANDALONE
        elif link_count >= node_count * (node_count - 1) // 2:
            self._topology_type = TopologyType.MESH
        elif self._is_star_topology():
            self._topology_type = TopologyType.STAR
        elif self._is_ring_topology():
            self._topology_type = TopologyType.RING
        else:
            self._topology_type = TopologyType.HYBRID

    def _is_star_topology(self) -> bool:
        """Check if the current topology is a star."""
        if not self._nodes:
            return False
        connection_counts = self._get_connection_counts()
        # Find the node connected to everyone
        others = len(self._nodes) - 1
        return any(c == others for c in connection_counts.values())

    def _is_ring_topology(self) -> bool:
        """Check if the current topology is a ring."""
        if len(self._nodes) < 3:
            return False
        connection_counts = self._get_connection_counts()
        # In a ring, every node has exactly 2 connections
        return all(c == 2 for c in connection_counts.values())

    def _get_connection_counts(self) -> Dict[str, int]:
        """Get the connection count for each node."""
        counts: Dict[str, int] = {}
        for source, target in self._links:
            counts[source] = counts.get(source, 0) + 1
            counts[target] = counts.get(target, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Partition detection
    # ------------------------------------------------------------------

    def is_connected_to(self, node_id: str) -> bool:
        """Check if this node is connected to a specific node."""
        if node_id == self._self_node_id:
            return True
        return self.get_link(self._self_node_id, node_id) is not None

    def get_partitioned_nodes(self) -> List[str]:
        """Get nodes that appear to be in a network partition."""
        with self._lock:
            partitioned = []
            for node_id in self._nodes:
                if node_id == self._self_node_id:
                    continue
                if not self.is_connected_to(node_id):
                    link = self.get_link(self._self_node_id, node_id)
                    if link and not link.is_active:
                        partitioned.append(node_id)
            return partitioned

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable topology snapshot."""
        with self._lock:
            return {
                "topology_type": self._topology_type.value,
                "node_count": len(self._nodes),
                "link_count": len(self._links),
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "hostname": n.hostname,
                        "role": n.role,
                        "is_active": n.is_active,
                    }
                    for n in self._nodes.values()
                ],
                "links": [
                    {
                        "source": l.source,
                        "target": l.target,
                        "latency_ms": l.latency_ms,
                        "is_active": l.is_active,
                    }
                    for l in self._links.values()
                ],
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return topology statistics."""
        with self._lock:
            return {
                "type": self._topology_type.value,
                "nodes": len(self._nodes),
                "links": len(self._links),
                "partitioned_nodes": len(self.get_partitioned_nodes()),
            }
