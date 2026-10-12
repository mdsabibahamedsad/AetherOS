"""Knowledge Graph — entity relationship graph with automatic relationship detection.

Automatically creates relationships between projects, repositories, files,
functions, classes, conversations, tasks, people, ideas, and every other entity.
"""

from __future__ import annotations

import enum
import json
import logging
import math
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("aetheros_memory.knowledge_graph")


class EntityType(str, enum.Enum):
    PROJECT = "project"
    REPOSITORY = "repository"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    TASK = "task"
    PERSON = "person"
    IDEA = "idea"
    CONCEPT = "concept"
    DECISION = "decision"
    GOAL = "goal"
    WORKSPACE = "workspace"
    DOCUMENT = "document"
    CODE_SNIPPET = "code_snippet"
    RESEARCH_SESSION = "research_session"
    AGENT = "agent"
    TOOL = "tool"
    KNOWLEDGE = "knowledge"


class RelationshipType(str, enum.Enum):
    CONTAINS = "contains"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    DEPENDED_BY = "depended_by"
    REFERENCES = "references"
    REFERENCED_BY = "referenced_by"
    IMPLEMENTS = "implements"
    IMPLEMENTED_BY = "implemented_by"
    EXTENDS = "extends"
    EXTENDED_BY = "extended_by"
    CREATED = "created"
    CREATED_BY = "created_by"
    MODIFIED = "modified"
    MODIFIED_BY = "modified_by"
    OWNS = "owns"
    OWNED_BY = "owned_by"
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    DISCUSSES = "discusses"
    DISCUSSED_IN = "discussed_in"
    DECIDES = "decides"
    DECIDED_BY = "decided_by"
    PINNED_TO = "pinned_to"
    ARCHIVED_IN = "archived_in"


@dataclass
class GraphEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType = EntityType.CONCEPT
    name: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    importance: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEntity":
        data = dict(data)
        data["type"] = EntityType(data.pop("type", "concept"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GraphRelationship:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    type: RelationshipType = RelationshipType.RELATED_TO
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "properties": self.properties,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphRelationship":
        data = dict(data)
        data["type"] = RelationshipType(data.pop("type", "related_to"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def reverse_type(self) -> RelationshipType:
        _reverse_map: Dict[str, str] = {
            "contains": "part_of",
            "part_of": "contains",
            "depends_on": "depended_by",
            "depended_by": "depends_on",
            "references": "referenced_by",
            "referenced_by": "references",
            "implements": "implemented_by",
            "implemented_by": "implements",
            "extends": "extended_by",
            "extended_by": "extends",
            "created": "created_by",
            "created_by": "created",
            "modified": "modified_by",
            "modified_by": "modified",
            "owns": "owned_by",
            "owned_by": "owns",
            "precedes": "follows",
            "follows": "precedes",
            "discusses": "discussed_in",
            "discussed_in": "discusses",
            "decides": "decided_by",
            "decided_by": "decides",
            "pinned_to": "pinned_to",
            "archived_in": "archived_in",
        }
        reverse = _reverse_map.get(self.type.value, "related_to")
        return RelationshipType(reverse)


@dataclass
class GraphQuery:
    entity_type: Optional[EntityType] = None
    relationship_type: Optional[RelationshipType] = None
    name_pattern: str = ""
    min_importance: float = 0.0
    max_depth: int = 3
    limit: int = 50


class KnowledgeGraph:
    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._entities: Dict[str, GraphEntity] = {}
        self._relationships: Dict[str, GraphRelationship] = {}
        self._entity_by_name: Dict[str, str] = {}
        self._entity_by_type: Dict[EntityType, Set[str]] = {et: set() for et in EntityType}
        self._outgoing: Dict[str, Set[str]] = {}
        self._incoming: Dict[str, Set[str]] = {}
        self._storage_dir = storage_dir
        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # Entity operations
    # ------------------------------------------------------------------

    def add_entity(self, entity: GraphEntity) -> GraphEntity:
        with self._lock:
            self._entities[entity.id] = entity
            self._entity_by_type[entity.type].add(entity.id)
            if entity.name:
                self._entity_by_name[entity.name.lower()] = entity.id
            if entity.id not in self._outgoing:
                self._outgoing[entity.id] = set()
            if entity.id not in self._incoming:
                self._incoming[entity.id] = set()
        self._save()
        return entity

    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        with self._lock:
            return self._entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional[GraphEntity]:
        with self._lock:
            eid = self._entity_by_name.get(name.lower())
            if eid:
                return self._entities.get(eid)
            for entity in self._entities.values():
                if entity.name.lower() == name.lower():
                    return entity
            return None

    def find_entities(self, entity_type: EntityType) -> List[GraphEntity]:
        with self._lock:
            return [self._entities[eid] for eid in self._entity_by_type.get(entity_type, set()) if eid in self._entities]

    def delete_entity(self, entity_id: str) -> bool:
        with self._lock:
            entity = self._entities.pop(entity_id, None)
            if not entity:
                return False
            self._entity_by_type[entity.type].discard(entity_id)
            if entity.name:
                name_key = entity.name.lower()
                if self._entity_by_name.get(name_key) == entity_id:
                    del self._entity_by_name[name_key]
            for rid in list(self._outgoing.get(entity_id, set())):
                self._relationships.pop(rid, None)
            for rid in list(self._incoming.get(entity_id, set())):
                self._relationships.pop(rid, None)
            self._outgoing.pop(entity_id, None)
            self._incoming.pop(entity_id, None)
            for eid in self._outgoing:
                self._outgoing[eid] = {r for r in self._outgoing[eid] if r in self._relationships}
            for eid in self._incoming:
                self._incoming[eid] = {r for r in self._incoming[eid] if r in self._relationships}
        self._save()
        return True

    def update_entity(self, entity_id: str, **kwargs) -> Optional[GraphEntity]:
        with self._lock:
            entity = self._entities.get(entity_id)
            if not entity:
                return None
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            entity.updated_at = time.time()
            self._save()
            return entity

    def count_entities(self, entity_type: Optional[EntityType] = None) -> int:
        with self._lock:
            if entity_type:
                return len(self._entity_by_type.get(entity_type, set()))
            return len(self._entities)

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType = RelationshipType.RELATED_TO,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphRelationship]:
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                logger.warning("Cannot create relationship: entity not found")
                return None
            existing = self._find_relationship(source_id, target_id, rel_type)
            if existing:
                existing.weight = max(existing.weight, weight)
                return existing
            rel = GraphRelationship(
                source_id=source_id,
                target_id=target_id,
                type=rel_type,
                weight=weight,
                properties=properties or {},
            )
            self._relationships[rel.id] = rel
            self._outgoing[source_id].add(rel.id)
            self._incoming[target_id].add(rel.id)
        self._save()
        return rel

    def add_bidirectional_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType = RelationshipType.RELATED_TO,
        weight: float = 1.0,
    ) -> Tuple[Optional[GraphRelationship], Optional[GraphRelationship]]:
        fwd = self.add_relationship(source_id, target_id, rel_type, weight)
        rev_type = rel_type  # use related_to for reverse by default
        _rev_map = {
            RelationshipType.CONTAINS: RelationshipType.PART_OF,
            RelationshipType.PART_OF: RelationshipType.CONTAINS,
            RelationshipType.DEPENDS_ON: RelationshipType.DEPENDED_BY,
            RelationshipType.DEPENDED_BY: RelationshipType.DEPENDS_ON,
            RelationshipType.OWNS: RelationshipType.OWNED_BY,
            RelationshipType.OWNED_BY: RelationshipType.OWNS,
            RelationshipType.CREATED: RelationshipType.CREATED_BY,
            RelationshipType.CREATED_BY: RelationshipType.CREATED,
            RelationshipType.PRECEDES: RelationshipType.FOLLOWS,
            RelationshipType.FOLLOWS: RelationshipType.PRECEDES,
        }
        rev_type = _rev_map.get(rel_type, RelationshipType.RELATED_TO)
        rev = self.add_relationship(target_id, source_id, rev_type, weight)
        return fwd, rev

    def get_relationships(
        self,
        entity_id: str,
        direction: str = "both",
        rel_type: Optional[RelationshipType] = None,
    ) -> List[GraphRelationship]:
        with self._lock:
            results: List[GraphRelationship] = []
            if direction in ("outgoing", "both"):
                for rid in self._outgoing.get(entity_id, set()):
                    rel = self._relationships.get(rid)
                    if rel and (rel_type is None or rel.type == rel_type):
                        results.append(rel)
            if direction in ("incoming", "both"):
                for rid in self._incoming.get(entity_id, set()):
                    rel = self._relationships.get(rid)
                    if rel and (rel_type is None or rel.type == rel_type):
                        results.append(rel)
            return results

    def get_related_entities(
        self,
        entity_id: str,
        max_depth: int = 2,
        min_importance: float = 0.0,
    ) -> List[Tuple[GraphEntity, GraphRelationship, int]]:
        visited: Set[str] = set()
        results: List[Tuple[GraphEntity, GraphRelationship, int]] = []
        queue: List[Tuple[str, int]] = [(entity_id, 0)]
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            if depth > 0:
                pass
            for rel in self.get_relationships(current_id, "outgoing"):
                target = self._entities.get(rel.target_id)
                if target and target.importance >= min_importance:
                    results.append((target, rel, depth))
                    if depth + 1 <= max_depth:
                        queue.append((rel.target_id, depth + 1))
            for rel in self.get_relationships(current_id, "incoming"):
                source = self._entities.get(rel.source_id)
                if source and source.importance >= min_importance:
                    results.append((source, rel, depth))
                    if depth + 1 <= max_depth:
                        queue.append((rel.source_id, depth + 1))
        return results

    def remove_relationship(self, relationship_id: str) -> bool:
        with self._lock:
            rel = self._relationships.pop(relationship_id, None)
            if not rel:
                return False
            self._outgoing.get(rel.source_id, set()).discard(relationship_id)
            self._incoming.get(rel.target_id, set()).discard(relationship_id)
        self._save()
        return True

    def count_relationships(self) -> int:
        with self._lock:
            return len(self._relationships)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, query: GraphQuery) -> List[GraphEntity]:
        with self._lock:
            results: List[GraphEntity] = []
            for entity in self._entities.values():
                if query.entity_type and entity.type != query.entity_type:
                    continue
                if query.min_importance and entity.importance < query.min_importance:
                    continue
                if query.name_pattern:
                    import re as regex
                    if not regex.search(query.name_pattern, entity.name, regex.IGNORECASE):
                        continue
                results.append(entity)
            results.sort(key=lambda e: e.importance, reverse=True)
            return results[:query.limit]

    def search(self, text: str) -> List[Tuple[GraphEntity, float]]:
        text_lower = text.lower()
        with self._lock:
            scored: List[Tuple[GraphEntity, float]] = []
            for entity in self._entities.values():
                score = 0.0
                if text_lower in entity.name.lower():
                    score += 10.0
                if text_lower in entity.description.lower():
                    score += 5.0
                for prop_val in entity.properties.values():
                    if isinstance(prop_val, str) and text_lower in prop_val.lower():
                        score += 2.0
                if score > 0:
                    score *= entity.importance
                    scored.append((entity, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:50]

    # ------------------------------------------------------------------
    # Auto-linking
    # ------------------------------------------------------------------

    def auto_link(self, entity_id: str) -> int:
        entity = self.get_entity(entity_id)
        if not entity:
            return 0
        count = 0
        with self._lock:
            for other in self._entities.values():
                if other.id == entity_id:
                    continue
                if self._should_link(entity, other):
                    if not self._find_relationship(entity_id, other.id, RelationshipType.RELATED_TO):
                        self.add_relationship(
                            entity_id, other.id,
                            RelationshipType.RELATED_TO,
                            weight=self._compute_link_weight(entity, other),
                        )
                        count += 1
        if count:
            self._save()
        return count

    def auto_link_all(self) -> int:
        total = 0
        with self._lock:
            eids = list(self._entities.keys())
        for eid in eids:
            total += self.auto_link(eid)
        return total

    def _should_link(self, a: GraphEntity, b: GraphEntity) -> bool:
        if a.type == b.type and a.name.lower() == b.name.lower():
            return False
        if a.type == b.type:
            return False
        a_words = set(re.findall(r'\w+', a.name.lower()))
        b_words = set(re.findall(r'\w+', b.name.lower()))
        common = a_words & b_words
        if len(common) >= 2:
            return True
        a_desc_words = set(re.findall(r'\w+', a.description.lower()))
        b_desc_words = set(re.findall(r'\w+', b.description.lower()))
        desc_common = a_desc_words & b_desc_words
        return len(desc_common) >= 3

    def _compute_link_weight(self, a: GraphEntity, b: GraphEntity) -> float:
        weight = 0.5
        a_words = set(re.findall(r'\w+', a.name.lower()))
        b_words = set(re.findall(r'\w+', b.name.lower()))
        common = a_words & b_words
        if common:
            weight += min(len(common) * 0.15, 0.5)
        weight *= min(a.importance, b.importance)
        return min(weight, 1.0)

    def _find_relationship(
        self, source_id: str, target_id: str, rel_type: RelationshipType
    ) -> Optional[GraphRelationship]:
        for rid in self._outgoing.get(source_id, set()):
            rel = self._relationships.get(rid)
            if rel and rel.target_id == target_id and rel.type == rel_type:
                return rel
        return None

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_json(self) -> str:
        with self._lock:
            data = {
                "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
                "relationships": {rid: r.to_dict() for rid, r in self._relationships.items()},
            }
            return json.dumps(data, indent=2, ensure_ascii=False)

    def import_json(self, json_str: str) -> int:
        data = json.loads(json_str)
        count = 0
        for eid, raw in data.get("entities", {}).items():
            entity = GraphEntity.from_dict(raw)
            self.add_entity(entity)
            count += 1
        for rid, raw in data.get("relationships", {}).items():
            rel = GraphRelationship.from_dict(raw)
            with self._lock:
                if rel.source_id in self._entities and rel.target_id in self._entities:
                    self._relationships[rel.id] = rel
                    self._outgoing[rel.source_id].add(rel.id)
                    self._incoming[rel.target_id].add(rel.id)
                    count += 1
        if count:
            self._save()
        return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            type_counts = {et.value: len(ids) for et, ids in self._entity_by_type.items() if ids}
            type_counts["total_entities"] = len(self._entities)
            type_counts["total_relationships"] = len(self._relationships)
            return type_counts

    def get_subgraph(self, entity_ids: List[str]) -> Dict[str, Any]:
        with self._lock:
            entities = {}
            relationships = {}
            eid_set = set(entity_ids)
            for eid in entity_ids:
                entity = self._entities.get(eid)
                if entity:
                    entities[eid] = entity.to_dict()
            for rel in self._relationships.values():
                if rel.source_id in eid_set and rel.target_id in eid_set:
                    relationships[rel.id] = rel.to_dict()
            return {"entities": entities, "relationships": relationships}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._storage_dir:
            return
        try:
            path = self._storage_dir / "knowledge_graph.json"
            tmp = path.with_suffix(".tmp")
            data = {
                "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
                "relationships": {rid: r.to_dict() for rid, r in self._relationships.items()},
            }
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save knowledge graph: %s", exc)

    def _load(self) -> None:
        if not self._storage_dir:
            return
        path = self._storage_dir / "knowledge_graph.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for eid, raw in data.get("entities", {}).items():
                entity = GraphEntity.from_dict(raw)
                self._entities[eid] = entity
                self._entity_by_type[entity.type].add(eid)
                if entity.name:
                    self._entity_by_name[entity.name.lower()] = eid
                self._outgoing[eid] = set()
                self._incoming[eid] = set()
            for rid, raw in data.get("relationships", {}).items():
                rel = GraphRelationship.from_dict(raw)
                self._relationships[rid] = rel
                if rel.source_id in self._outgoing:
                    self._outgoing[rel.source_id].add(rid)
                if rel.target_id in self._incoming:
                    self._incoming[rel.target_id].add(rid)
            logger.info("Loaded knowledge graph: %d entities, %d relationships",
                        len(self._entities), len(self._relationships))
        except Exception as exc:
            logger.warning("Failed to load knowledge graph: %s", exc)

    def clear(self) -> None:
        with self._lock:
            self._entities.clear()
            self._relationships.clear()
            self._entity_by_name.clear()
            self._entity_by_type = {et: set() for et in EntityType}
            self._outgoing.clear()
            self._incoming.clear()
        self._save()

    def summary(self) -> str:
        s = self.stats()
        return (
            f"Knowledge Graph: {s['total_entities']} entities, {s['total_relationships']} relationships\n"
            f"Entity types: {', '.join(k for k, v in s.items() if k not in ('total_entities', 'total_relationships') and v > 0)}"
        )