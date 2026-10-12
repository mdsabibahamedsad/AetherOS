"""
Cluster Capability Registry — manages and discovers node capabilities
for capability-aware task routing.

Tracks:
  - GPU availability
  - Language/framework support
  - Installed tools and their versions
  - Plugin availability
  - Memory and compute limits
  - Policy constraints

Used by the scheduler to dispatch tasks to compatible nodes.
"""

from __future__ import annotations

import enum
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class CapabilityCategory(enum.Enum):
    """Categories of node capabilities."""
    HARDWARE = "hardware"           # GPU, CPU, memory, storage
    SOFTWARE = "software"           # Python, tools, frameworks
    NETWORK = "network"             # Bandwidth, latency, protocols
    TOOLS = "tools"                 # Installed AetherOS tools
    PLUGINS = "plugins"             # Installed plugins
    MODELS = "models"               # Available AI models
    POLICY = "policy"               # Security and access policies
    CUSTOM = "custom"               # User-defined capabilities


@dataclass
class NodeCapability:
    """A capability provided by a cluster node.

    Attributes:
        category: Capability category
        name: Capability name
        version: Capability version
        description: Human-readable description
        metadata: Additional detail
    """
    category: CapabilityCategory = CapabilityCategory.CUSTOM
    name: str = ""
    version: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.category, self.name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NodeCapability):
            return NotImplemented
        return self.category == other.category and self.name == other.name


class ClusterCapabilityRegistry:
    """Registry of node capabilities for capability-aware scheduling.

    Tracks which capabilities each node provides and supports
    capability-based filtering for task scheduling.

    Usage:
        cap_reg = ClusterCapabilityRegistry(event_bus)

        # Register a node's capabilities
        cap_reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu", "A100"),
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
        ])

        # Find nodes with specific capabilities
        nodes = cap_reg.find_nodes_with_capability("gpu")
        nodes = cap_reg.find_nodes_with_all(["gpu", "browser"])
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()

        # node_id -> set of capabilities
        self._node_capabilities: Dict[str, Set[NodeCapability]] = {}
        # capability -> set of node_ids that have it
        self._capability_index: Dict[str, Set[str]] = {}
        # capability name -> most common description
        self._capability_descriptions: Dict[str, str] = {}
        # category -> set of capability names
        self._category_index: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_node_capabilities(
        self,
        node_id: str,
        capabilities: List[NodeCapability],
    ) -> None:
        """Register or update capabilities for a node."""
        cap_set = set(capabilities)

        with self._lock:
            # Remove old capabilities for this node
            old_caps = self._node_capabilities.get(node_id, set())
            for old_cap in old_caps:
                cap_nodes = self._capability_index.get(old_cap.name)
                if cap_nodes:
                    cap_nodes.discard(node_id)
                    if not cap_nodes:
                        del self._capability_index[old_cap.name]

            # Register new capabilities
            self._node_capabilities[node_id] = cap_set
            for cap in cap_set:
                self._capability_index.setdefault(cap.name, set()).add(node_id)
                self._category_index.setdefault(cap.category.value, set()).add(cap.name)
                if cap.name not in self._capability_descriptions:
                    self._capability_descriptions[cap.name] = cap.description

        logger.debug(
            "CapabilityRegistry: registered %d capabilities for node %s",
            len(cap_set), node_id[:8],
        )

    def remove_node(self, node_id: str) -> None:
        """Remove all capabilities for a node."""
        with self._lock:
            caps = self._node_capabilities.pop(node_id, set())
            for cap in caps:
                cap_nodes = self._capability_index.get(cap.name)
                if cap_nodes:
                    cap_nodes.discard(node_id)
                    if not cap_nodes:
                        del self._capability_index[cap.name]

    def register_capability(
        self,
        category: CapabilityCategory,
        name: str,
        description: str = "",
        version: str = "",
    ) -> NodeCapability:
        """Register a new capability type (without associating to a node)."""
        cap = NodeCapability(
            category=category,
            name=name,
            version=version,
            description=description,
        )
        with self._lock:
            self._capability_descriptions[name] = description
        return cap

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def find_nodes_with_capability(self, capability: str) -> List[str]:
        """Find nodes that have a specific capability."""
        with self._lock:
            return list(self._capability_index.get(capability, set()))

    def find_nodes_with_all(self, capabilities: List[str]) -> List[str]:
        """Find nodes that have ALL specified capabilities."""
        with self._lock:
            if not capabilities:
                return list(self._node_capabilities.keys())

            result: Optional[Set[str]] = None
            for cap in capabilities:
                nodes = self._capability_index.get(cap, set())
                if result is None:
                    result = set(nodes)
                else:
                    result &= nodes
                    if not result:
                        break

            return list(result) if result else []

    def find_nodes_with_any(self, capabilities: List[str]) -> List[str]:
        """Find nodes that have ANY of the specified capabilities."""
        with self._lock:
            result: Set[str] = set()
            for cap in capabilities:
                nodes = self._capability_index.get(cap, set())
                result.update(nodes)
            return list(result)

    def get_node_capabilities(self, node_id: str) -> List[NodeCapability]:
        """Get all capabilities for a specific node."""
        with self._lock:
            caps = self._node_capabilities.get(node_id, set())
            return sorted(caps, key=lambda c: (c.category.value, c.name))

    def has_capability(self, node_id: str, capability: str) -> bool:
        """Check if a node has a specific capability."""
        with self._lock:
            nodes = self._capability_index.get(capability, set())
            return node_id in nodes

    def get_capability_description(self, capability: str) -> str:
        """Get the description for a capability name."""
        with self._lock:
            return self._capability_descriptions.get(capability, "")

    def list_capabilities_by_category(self) -> Dict[str, List[str]]:
        """List capabilities grouped by category."""
        with self._lock:
            result: Dict[str, List[str]] = {}
            for cap_name, cap_nodes in self._capability_index.items():
                # Find the category
                category = CapabilityCategory.CUSTOM.value
                for cat_name, cat_caps in self._category_index.items():
                    if cap_name in cat_caps:
                        category = cat_name
                        break
                result.setdefault(category, []).append(cap_name)
            return result

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the registry."""
        with self._lock:
            return {
                "total_nodes": len(self._node_capabilities),
                "total_capabilities": len(self._capability_index),
                "by_category": {
                    cat: list(caps)
                    for cat, caps in self._category_index.items()
                },
                "capability_nodes": {
                    cap: list(nodes)
                    for cap, nodes in sorted(self._capability_index.items())[:20]
                },
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            return {
                "tracked_nodes": len(self._node_capabilities),
                "unique_capabilities": len(self._capability_index),
                "categories": len(self._category_index),
            }
