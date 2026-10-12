"""
Relationship Index — tracks relationships between entities.

Manages typed relationships between entities (e.g., "imports", "calls",
"contains", "depends_on", "implements"). Supports relationship traversal
for the knowledge graph and retrieval engine.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from memory.memory_store import MemoryStore, MemoryScope

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    """A typed relationship between two entities.

    Attributes:
        id: Unique relationship ID
        source_id: Source entity ID
        target_id: Target entity ID
        relationship_type: Type of relationship
        weight: Relationship strength (0.0 - 1.0)
        metadata: Additional metadata
        created_at: When the relationship was first observed
        last_observed: When last observed
        observation_count: How many times observed
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    source_id: str = ""
    target_id: str = ""
    relationship_type: str = "related_to"
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    observation_count: int = 1


# Standard relationship types
RELATION_IMPORTS = "imports"
RELATION_CALLS = "calls"
RELATION_CONTAINS = "contains"
RELATION_DEPENDS_ON = "depends_on"
RELATION_IMPLEMENTS = "implements"
RELATION_EXTENDS = "extends"
RELATION_USES = "uses"
RELATION_CREATED_BY = "created_by"
RELATION_RELATED_TO = "related_to"
RELATION_DERIVED_FROM = "derived_from"
RELATION_REFERENCES = "references"
RELATION_CONNECTED_TO = "connected_to"


class RelationshipIndex:
    """Manages typed relationships between entities.

    Supports adding, querying, and traversing relationships.
    Relationships are directional but can be traversed in both directions.

    Usage:
        idx = RelationshipIndex(store)
        idx.add_relationship(src_id, tgt_id, "depends_on")
        deps = idx.get_dependencies(src_id)
        affected = idx.get_dependents(tgt_id)
        graph = idx.get_related(src_id)
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"relationship:{id(self)}"
        self._lock = threading.RLock()
        # In-memory indexes
        self._outgoing: Dict[str, List[Relationship]] = {}  # source -> rels
        self._incoming: Dict[str, List[Relationship]] = {}  # target -> rels
        self._by_type: Dict[str, List[Relationship]] = {}  # type -> rels

    # ------------------------------------------------------------------
    # Adding relationships
    # ------------------------------------------------------------------

    def add_relationship(self, source_id: str, target_id: str,
                         relationship_type: str = RELATION_RELATED_TO,
                         weight: float = 1.0,
                         metadata: Dict[str, Any] = None) -> Relationship:
        """Add or update a relationship between two entities."""
        # Check for existing relationship
        existing = self._find_exact(source_id, target_id, relationship_type)
        if existing:
            existing.last_observed = time.time()
            existing.observation_count += 1
            existing.weight = max(existing.weight, weight)
            if metadata:
                existing.metadata.update(metadata)
            return existing

        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            weight=weight,
            metadata=metadata or {},
        )

        with self._lock:
            self._outgoing.setdefault(source_id, []).append(rel)
            self._incoming.setdefault(target_id, []).append(rel)
            self._by_type.setdefault(relationship_type, []).append(rel)

        # Persist
        self._store.save(
            key=f"rel:{rel.id}",
            value=rel,
            memory_type="relationship",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=[relationship_type, "relationship"],
            metadata={
                "source_id": source_id,
                "target_id": target_id,
                "type": relationship_type,
                "weight": weight,
            },
            importance=min(weight * 0.8, 1.0),
            source="relationship",
        )
        return rel

    def add_relationships_batch(self, relationships: List[tuple]) -> int:
        """Add multiple relationships at once.

        Args:
            relationships: List of (source_id, target_id, type, weight) tuples

        Returns:
            Count of relationships added
        """
        count = 0
        for rel in relationships:
            source, target = rel[0], rel[1]
            rtype = rel[2] if len(rel) > 2 else RELATION_RELATED_TO
            weight = rel[3] if len(rel) > 3 else 1.0
            self.add_relationship(source, target, rtype, weight)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_outgoing(self, entity_id: str) -> List[Relationship]:
        """Get all outgoing relationships from an entity."""
        with self._lock:
            return list(self._outgoing.get(entity_id, []))

    def get_incoming(self, entity_id: str) -> List[Relationship]:
        """Get all incoming relationships to an entity."""
        with self._lock:
            return list(self._incoming.get(entity_id, []))

    def get_by_type(self, relationship_type: str) -> List[Relationship]:
        """Get all relationships of a given type."""
        with self._lock:
            return list(self._by_type.get(relationship_type, []))

    def get_all_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships (incoming + outgoing) for an entity."""
        outgoing = self.get_outgoing(entity_id)
        incoming = self.get_incoming(entity_id)
        return outgoing + incoming

    def get_related_entities(self, entity_id: str) -> List[str]:
        """Get IDs of all entities related to a given entity."""
        related = set()
        for rel in self.get_outgoing(entity_id):
            related.add(rel.target_id)
        for rel in self.get_incoming(entity_id):
            related.add(rel.source_id)
        return list(related)

    def get_dependencies(self, entity_id: str) -> List[str]:
        """Get entities that this entity depends on."""
        deps = []
        for rel in self.get_outgoing(entity_id):
            if rel.relationship_type in (RELATION_DEPENDS_ON, RELATION_IMPORTS,
                                        RELATION_EXTENDS, RELATION_USES):
                deps.append(rel.target_id)
        return deps

    def get_dependents(self, entity_id: str) -> List[str]:
        """Get entities that depend on this entity."""
        deps = []
        for rel in self.get_incoming(entity_id):
            if rel.relationship_type in (RELATION_DEPENDS_ON, RELATION_IMPORTS,
                                        RELATION_EXTENDS, RELATION_USES):
                deps.append(rel.source_id)
        return deps

    def is_related(self, source_id: str, target_id: str) -> bool:
        """Check if two entities are directly related."""
        return self._find_any(source_id, target_id) is not None

    def shortest_path(self, from_id: str, to_id: str,
                      max_depth: int = 5) -> Optional[List[str]]:
        """Find the shortest path between two entities using BFS."""
        if from_id == to_id:
            return [from_id]

        visited = {from_id}
        queue = [[from_id]]

        for _ in range(max_depth):
            next_queue = []
            for path in queue:
                current = path[-1]
                for rel in self.get_outgoing(current):
                    if rel.target_id not in visited:
                        new_path = path + [rel.target_id]
                        if rel.target_id == to_id:
                            return new_path
                        visited.add(rel.target_id)
                        next_queue.append(new_path)
                for rel in self.get_incoming(current):
                    if rel.source_id not in visited:
                        new_path = path + [rel.source_id]
                        if rel.source_id == to_id:
                            return new_path
                        visited.add(rel.source_id)
                        next_queue.append(new_path)
            queue = next_queue
            if not queue:
                break
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_exact(self, source_id: str, target_id: str,
                    rel_type: str) -> Optional[Relationship]:
        """Find an exact relationship match."""
        with self._lock:
            rels = self._outgoing.get(source_id, [])
            for r in rels:
                if r.target_id == target_id and r.relationship_type == rel_type:
                    return r
        return None

    def _find_any(self, source_id: str, target_id: str) -> Optional[Relationship]:
        """Find any relationship between two entities."""
        with self._lock:
            for r in self._outgoing.get(source_id, []):
                if r.target_id == target_id:
                    return r
            for r in self._incoming.get(source_id, []):
                if r.source_id == target_id:
                    return r
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        with self._lock:
            count = (
                sum(len(v) for v in self._outgoing.values())
                + sum(len(v) for v in self._incoming.values())
            )
            self._outgoing.clear()
            self._incoming.clear()
            self._by_type.clear()
        self._store.clear_namespace(self._namespace)
        return count

    def count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._outgoing.values())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type = {
                t: len(rels) for t, rels in self._by_type.items()
            }
            return {
                "total_relationships": sum(len(v) for v in self._outgoing.values()),
                "unique_entities_out": len(self._outgoing),
                "unique_entities_in": len(self._incoming),
                "by_type": by_type,
            }
