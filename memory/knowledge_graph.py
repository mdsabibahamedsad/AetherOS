"""
Knowledge Graph — a graph connecting entities, relationships, and memory.

The knowledge graph provides a unified view across all memory types by
connecting entities (from entity_index) via relationships (from
relationship_index). Supports graph traversal, path finding, subgraph
extraction, and integration with the retrieval engine.

Nodes represent: projects, files, tasks, people, repositories, tools,
agents, plugins, documents, concepts, functions, classes, packages, APIs.

Edges represent: depends_on, contains, imports, calls, implements,
extends, uses, created_by, references, related_to, connected_to.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from memory.memory_store import MemoryStore, MemoryScope
from memory.entity_index import EntityIndex, Entity, ENTITY_TYPE_CONCEPT
from memory.relationship_index import (
    RelationshipIndex, Relationship,
    RELATION_RELATED_TO, RELATION_DEPENDS_ON, RELATION_CONTAINS,
    RELATION_REFERENCES, RELATION_USES,
)

logger = logging.getLogger(__name__)


class NodeType(enum.Enum):
    """Types of nodes in the knowledge graph."""
    PROJECT = "project"
    FILE = "file"
    TASK = "task"
    PERSON = "person"
    REPOSITORY = "repository"
    TOOL = "tool"
    AGENT = "agent"
    PLUGIN = "plugin"
    DOCUMENT = "document"
    CONCEPT = "concept"
    FUNCTION = "function"
    CLASS = "class"
    PACKAGE = "package"
    MODULE = "module"
    API = "api"
    ENTITY = "entity"


class RelationType(enum.Enum):
    """Types of relationships in the knowledge graph."""
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    USES = "uses"
    CREATED_BY = "created_by"
    REFERENCES = "references"
    RELATED_TO = "related_to"
    CONNECTED_TO = "connected_to"
    DERIVED_FROM = "derived_from"


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph.

    Attributes:
        id: Unique node ID
        name: Node name/label
        node_type: Type of node
        description: Description
        metadata: Additional metadata
        created_at: When the node was added
        updated_at: When last updated
        importance: Importance score (0.0 - 1.0)
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    node_type: NodeType = NodeType.ENTITY
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    importance: float = 0.5


@dataclass
class KnowledgeRelation:
    """A relationship between two nodes in the knowledge graph.

    Attributes:
        id: Unique relation ID
        source_id: Source node ID
        target_id: Target node ID
        relation_type: Type of relationship
        weight: Relationship strength (0.0 - 1.0)
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Unified graph connecting entities and relationships.

    Provides a graph view across all indexed entities and relationships.
    Supports traversal, subgraph extraction, path finding, and
    context-aware retrieval.

    Usage:
        kg = KnowledgeGraph(entity_index, relationship_index, store)
        kg.sync()  # Load entities into graph
        path = kg.find_path("entity-1", "entity-2")
        subgraph = kg.get_subgraph("entity-1", depth=2)
        related = kg.get_related("entity-1", relation_type="depends_on")
    """

    def __init__(self, entity_index: EntityIndex,
                 relationship_index: RelationshipIndex,
                 store: MemoryStore):
        self._entity_index = entity_index
        self._relationship_index = relationship_index
        self._store = store
        self._lock = threading.RLock()
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, List[KnowledgeRelation]] = {}
        self._edge_by_id: Dict[str, KnowledgeRelation] = {}
        self._synced = False

    # ------------------------------------------------------------------
    # Graph building
    # ------------------------------------------------------------------

    def sync(self) -> int:
        """Sync the knowledge graph with the entity and relationship indexes.

        Loads all entities from entity_index into graph nodes and all
        relationships into graph edges.

        Returns number of nodes in the graph after sync.
        """
        self._synced = True

        # Load entities as nodes
        entities = self._entity_index.search("", limit=10000)
        node_count = 0
        for entity in entities:
            node_type = self._entity_type_to_node_type(entity.type)
            node = KnowledgeNode(
                id=entity.id,
                name=entity.name,
                node_type=node_type,
                description=entity.description[:200],
                importance=min(entity.confidence, 1.0),
            )
            with self._lock:
                self._nodes[node.id] = node
            node_count += 1

        # Load relationships as edges
        for rel in self._relationship_index.get_by_type(""):
            edge = KnowledgeRelation(
                id=rel.id,
                source_id=rel.source_id,
                target_id=rel.target_id,
                relation_type=self._str_to_relation_type(rel.relationship_type),
                weight=rel.weight,
            )
            with self._lock:
                self._edges.setdefault(rel.source_id, []).append(edge)
                self._edge_by_id[rel.id] = edge

        logger.info(
            "KnowledgeGraph: synced %d nodes and %d edges",
            len(self._nodes), len(self._edge_by_id),
        )
        return len(self._nodes)

    def add_node(self, name: str, node_type: NodeType = NodeType.ENTITY,
                 description: str = "",
                 metadata: Dict[str, Any] = None,
                 importance: float = 0.5) -> KnowledgeNode:
        """Add a node to the graph."""
        node = KnowledgeNode(
            name=name, node_type=node_type,
            description=description, metadata=metadata or {},
            importance=importance,
        )
        with self._lock:
            self._nodes[node.id] = node
        return node

    def add_relation(self, source_id: str, target_id: str,
                     relation_type: RelationType = RelationType.RELATED_TO,
                     weight: float = 1.0,
                     metadata: Dict[str, Any] = None) -> Optional[KnowledgeRelation]:
        """Add an edge between two nodes."""
        with self._lock:
            if source_id not in self._nodes or target_id not in self._nodes:
                return None
        edge = KnowledgeRelation(
            source_id=source_id, target_id=target_id,
            relation_type=relation_type, weight=weight,
            metadata=metadata or {},
        )
        with self._lock:
            self._edges.setdefault(source_id, []).append(edge)
            self._edge_by_id[edge.id] = edge
        return edge

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Get a node by its ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_edges(self, node_id: str) -> List[KnowledgeRelation]:
        """Get all outgoing edges from a node."""
        with self._lock:
            return list(self._edges.get(node_id, []))

    def get_neighbors(self, node_id: str) -> List[KnowledgeNode]:
        """Get all neighboring nodes (connected by any edge)."""
        neighbor_ids = set()
        with self._lock:
            for edge in self._edges.get(node_id, []):
                neighbor_ids.add(edge.target_id)
        # Also check incoming edges
        with self._lock:
            for edges in self._edges.values():
                for edge in edges:
                    if edge.target_id == node_id:
                        neighbor_ids.add(edge.source_id)
        with self._lock:
            return [
                self._nodes[nid] for nid in neighbor_ids
                if nid in self._nodes
            ]

    def get_subgraph(self, center_id: str, depth: int = 2) -> Dict[str, Any]:
        """Extract a subgraph centered on a node, up to depth hops."""
        nodes: Dict[str, KnowledgeNode] = {}
        edges: Dict[str, KnowledgeRelation] = {}
        visited: Set[str] = set()
        current_level = {center_id}

        for _ in range(depth):
            next_level = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)
                with self._lock:
                    node = self._nodes.get(nid)
                    if node:
                        nodes[nid] = node
                    for edge in self._edges.get(nid, []):
                        edges[edge.id] = edge
                        next_level.add(edge.target_id)
            current_level = next_level - visited
            if not current_level:
                break

        return {
            "center_id": center_id,
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def find_path(self, from_id: str, to_id: str,
                  max_depth: int = 5) -> Optional[List[str]]:
        """Find the shortest path between two nodes using BFS."""
        if from_id == to_id:
            return [from_id]

        visited: Set[str] = {from_id}
        queue = [[from_id]]

        for _ in range(max_depth):
            next_queue = []
            for path in queue:
                current = path[-1]
                with self._lock:
                    for edge in self._edges.get(current, []):
                        if edge.target_id not in visited:
                            new_path = path + [edge.target_id]
                            if edge.target_id == to_id:
                                return new_path
                            visited.add(edge.target_id)
                            next_queue.append(new_path)
            queue = next_queue
            if not queue:
                break
        return None

    def get_related(self, node_id: str,
                    relation_type: Optional[RelationType] = None,
                    min_weight: float = 0.0) -> List[KnowledgeNode]:
        """Get nodes related by a specific relationship type."""
        related = []
        with self._lock:
            for edge in self._edges.get(node_id, []):
                if relation_type and edge.relation_type != relation_type:
                    continue
                if edge.weight < min_weight:
                    continue
                target = self._nodes.get(edge.target_id)
                if target:
                    related.append(target)
        return related

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search_nodes(self, query: str, node_type: Optional[NodeType] = None,
                     limit: int = 50) -> List[KnowledgeNode]:
        """Search for nodes by name or description."""
        query = query.lower()
        results = []
        with self._lock:
            for node in self._nodes.values():
                if node_type and node.node_type != node_type:
                    continue
                if query in node.name.lower() or query in node.description.lower():
                    results.append(node)
        results.sort(key=lambda n: n.importance, reverse=True)
        return results[:limit]

    def get_nodes_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        """Get all nodes of a given type."""
        with self._lock:
            return [
                n for n in self._nodes.values() if n.node_type == node_type
            ]

    def get_connected_components(self) -> List[List[KnowledgeNode]]:
        """Find all connected components in the graph."""
        visited: Set[str] = set()
        components: List[List[KnowledgeNode]] = []

        with self._lock:
            all_ids = set(self._nodes.keys())

        for nid in all_ids:
            if nid in visited:
                continue
            component = []
            queue = [nid]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                with self._lock:
                    node = self._nodes.get(current)
                    if node:
                        component.append(node)
                    for edge in self._edges.get(current, []):
                        if edge.target_id not in visited:
                            queue.append(edge.target_id)
            if component:
                components.append(component)

        return components

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        with self._lock:
            by_type: Dict[str, int] = {}
            for node in self._nodes.values():
                by_type[node.node_type.value] = by_type.get(
                    node.node_type.value, 0
                ) + 1
            by_rel: Dict[str, int] = {}
            for edges in self._edges.values():
                for edge in edges:
                    by_rel[edge.relation_type.value] = by_rel.get(
                        edge.relation_type.value, 0
                    ) + 1
            components = len(self.get_connected_components())
            return {
                "nodes": len(self._nodes),
                "edges": len(self._edge_by_id),
                "by_node_type": by_type,
                "by_relation_type": by_rel,
                "connected_components": components,
                "synced": self._synced,
            }

    @staticmethod
    def _entity_type_to_node_type(entity_type: str) -> NodeType:
        mapping = {
            "class": NodeType.CLASS,
            "function": NodeType.FUNCTION,
            "package": NodeType.PACKAGE,
            "repository": NodeType.REPOSITORY,
            "person": NodeType.PERSON,
            "api": NodeType.API,
            "document": NodeType.DOCUMENT,
            "task": NodeType.TASK,
            "tool": NodeType.TOOL,
            "project": NodeType.PROJECT,
            "file": NodeType.FILE,
            "plugin": NodeType.PLUGIN,
        }
        return mapping.get(entity_type, NodeType.ENTITY)

    @staticmethod
    def _str_to_relation_type(rel_type: str) -> RelationType:
        mapping = {
            "depends_on": RelationType.DEPENDS_ON,
            "contains": RelationType.CONTAINS,
            "imports": RelationType.IMPORTS,
            "calls": RelationType.CALLS,
            "implements": RelationType.IMPLEMENTS,
            "extends": RelationType.EXTENDS,
            "uses": RelationType.USES,
            "created_by": RelationType.CREATED_BY,
            "references": RelationType.REFERENCES,
            "related_to": RelationType.RELATED_TO,
            "connected_to": RelationType.CONNECTED_TO,
            "derived_from": RelationType.DERIVED_FROM,
        }
        return mapping.get(rel_type, RelationType.RELATED_TO)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._edge_by_id.clear()
        self._synced = False
