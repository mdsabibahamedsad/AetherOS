"""
Provenance Engine — tracks provenance of all state and data.

Ensures every important state has verifiable provenance:
user-provided, model-generated, tool-returned, web-derived, etc.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ProvenanceRelation(Enum):
    """Relations in provenance graph."""
    DERIVED_FROM = "derived_from"
    GENERATED_BY = "generated_by"
    RETURNED_BY = "returned_by"
    TRANSFORMED_BY = "transformed_by"
    COMBINED_WITH = "combined_with"
    VERIFIED_BY = "verified_by"
    APPROVED_BY = "approved_by"


@dataclass
class ProvenanceNode:
    """A node in the provenance graph."""
    node_id: str
    entity_type: str  # data, artifact, decision, action, state
    provenance: ProvenanceType
    data_classification: DataClassification
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    creator_id: str = ""  # agent, human, tool, model
    source_refs: List[str] = field(default_factory=list)  # Parent node IDs


@dataclass
class ProvenanceEdge:
    """An edge in the provenance graph."""
    edge_id: str
    from_node: str
    to_node: str
    relation: ProvenanceRelation
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)


class ProvenanceEngine:
    """
    Tracks provenance of all kernel state and data.
    
    Maintains a directed acyclic graph of provenance relationships.
    Never represents inference as fact, simulation as reality, prediction as observation.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._nodes: Dict[str, ProvenanceNode] = {}
        self._edges: Dict[str, ProvenanceEdge] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # node_id -> child node_ids
        self._reverse_adjacency: Dict[str, Set[str]] = {}  # node_id -> parent node_ids

    def create_node(
        self,
        entity_type: str,
        provenance: ProvenanceType,
        data_classification: DataClassification,
        content: Any = None,
        creator_id: str = "",
        source_refs: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> ProvenanceNode:
        """Create a provenance node."""
        # Compute content hash
        content_hash = self._hash_content(content)
        
        node = ProvenanceNode(
            node_id=new_id("prov"),
            entity_type=entity_type,
            provenance=provenance,
            data_classification=data_classification,
            content_hash=content_hash,
            metadata=metadata or {},
            creator_id=creator_id,
            source_refs=source_refs or [],
        )

        with self._lock:
            self._nodes[node.node_id] = node
            self._adjacency[node.node_id] = set()
            self._reverse_adjacency[node.node_id] = set()
            
            # Add edges from sources
            for src_id in source_refs or []:
                self._add_edge(src_id, node.node_id, ProvenanceRelation.DERIVED_FROM)

        if self.event_bus:
            self.event_bus.emit("provenance.node_created", {
                "node_id": node.node_id,
                "entity_type": entity_type,
                "provenance": provenance.value,
                "creator": creator_id,
            })

        return node

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        relation: ProvenanceRelation,
        metadata: Dict[str, Any] = None,
    ) -> ProvenanceEdge:
        """Add a provenance edge."""
        return self._add_edge(from_id, to_id, relation, metadata)

    def _add_edge(
        self,
        from_id: str,
        to_id: str,
        relation: ProvenanceRelation,
        metadata: Dict[str, Any] = None,
    ) -> ProvenanceEdge:
        """Internal edge addition."""
        if from_id not in self._nodes or to_id not in self._nodes:
            raise ValueError("Both nodes must exist")

        edge = ProvenanceEdge(
            edge_id=new_id("edge"),
            from_node=from_id,
            to_node=to_id,
            relation=relation,
            metadata=metadata or {},
        )

        with self._lock:
            self._edges[edge.edge_id] = edge
            self._adjacency[from_id].add(to_id)
            self._reverse_adjacency[to_id].add(from_id)

        return edge

    def get_lineage(self, node_id: str, max_depth: int = 10) -> List[ProvenanceNode]:
        """Get full lineage (ancestors) of a node."""
        lineage = []
        visited = set()
        current_level = {node_id}
        depth = 0

        while current_level and depth < max_depth:
            next_level = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)
                node = self._nodes.get(nid)
                if node:
                    lineage.append(node)
                    # Add parents
                    for parent_id in self._reverse_adjacency.get(nid, set()):
                        if parent_id not in visited:
                            next_level.add(parent_id)
            current_level = next_level
            depth += 1

        return lineage

    def get_descendants(self, node_id: str, max_depth: int = 10) -> List[ProvenanceNode]:
        """Get all descendants of a node."""
        descendants = []
        visited = set()
        current_level = {node_id}
        depth = 0

        while current_level and depth < max_depth:
            next_level = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)
                node = self._nodes.get(nid)
                if node and nid != node_id:
                    descendants.append(node)
                for child_id in self._adjacency.get(nid, set()):
                    if child_id not in visited:
                        next_level.add(child_id)
            current_level = next_level
            depth += 1

        return descendants

    def verify_provenance_chain(
        self,
        node_id: str,
        trusted_sources: Set[str] = None,
    ) -> Dict[str, Any]:
        """Verify a provenance chain back to trusted sources."""
        trusted = trusted_sources or {"user_provided", "human_approved", "verified"}
        lineage = self.get_lineage(node_id)
        
        result = {
            "verified": False,
            "trusted_ancestor_found": False,
            "untrusted_nodes": [],
            "chain_length": len(lineage),
            "terminal_provenance": [],
        }

        for node in lineage:
            if node.provenance.value in trusted:
                result["trusted_ancestor_found"] = True
                result["verified"] = True
                break
            elif node.provenance in (ProvenanceType.INFERRED, ProvenanceType.SIMULATED, ProvenanceType.PREDICTED, ProvenanceType.UNVERIFIED):
                result["untrusted_nodes"].append({
                    "node_id": node.node_id,
                    "provenance": node.provenance.value,
                    "creator": node.creator_id,
                })

        if lineage:
            result["terminal_provenance"] = [n.provenance.value for n in lineage[-3:]]

        return result

    def get_node(self, node_id: str) -> Optional[ProvenanceNode]:
        """Get a provenance node."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[ProvenanceEdge]:
        """Get a provenance edge."""
        with self._lock:
            return self._edges.get(edge_id)

    def query_nodes(
        self,
        entity_type: str = "",
        provenance: ProvenanceType = None,
        creator_id: str = "",
        since: float = 0,
    ) -> List[ProvenanceNode]:
        """Query nodes with filters."""
        with self._lock:
            nodes = list(self._nodes.values())

        if entity_type:
            nodes = [n for n in nodes if n.entity_type == entity_type]
        if provenance:
            nodes = [n for n in nodes if n.provenance == provenance]
        if creator_id:
            nodes = [n for n in nodes if n.creator_id == creator_id]
        if since > 0:
            nodes = [n for n in nodes if n.created_at >= since]

        return nodes

    def _hash_content(self, content: Any) -> str:
        """Compute content hash."""
        import hashlib
        if content is None:
            return ""
        content_str = str(content)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        """Get provenance engine statistics."""
        with self._lock:
            total_nodes = len(self._nodes)
            total_edges = len(self._edges)
            by_provenance: Dict[str, int] = {}
            by_type: Dict[str, int] = {}
            for node in self._nodes.values():
                by_provenance[node.provenance.value] = by_provenance.get(node.provenance.value, 0) + 1
                by_type[node.entity_type] = by_type.get(node.entity_type, 0) + 1

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "by_provenance": by_provenance,
            "by_entity_type": by_type,
        }

    def shutdown(self) -> None:
        """Shutdown the provenance engine."""
        logger.info("ProvenanceEngine: shutting down")
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._adjacency.clear()
            self._reverse_adjacency.clear()