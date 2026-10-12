from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EntityType(str, Enum):
    PERSON = "person"
    PROJECT = "project"
    ORGANIZATION = "organization"
    FILE = "file"
    DOCUMENT = "document"
    TOPIC = "topic"
    TASK = "task"
    MESSAGE = "message"
    EVENT = "event"
    WEBSITE = "website"
    CODE_MODULE = "code_module"
    AGENT = "agent"
    CONVERSATION = "conversation"
    MEMORY = "memory"
    CONCEPT = "concept"
    LOCATION = "location"


class RelationType(str, Enum):
    CREATED_BY = "created_by"
    RELATED_TO = "related_to"
    MENTIONED_IN = "mentioned_in"
    DEPENDS_ON = "depends_on"
    PART_OF = "part_of"
    ASSIGNED_TO = "assigned_to"
    COMMUNICATED_WITH = "communicated_with"
    REFERENCED_BY = "referenced_by"
    BELONGS_TO = "belongs_to"
    CONTAINS = "contains"
    FOLLOWS = "follows"
    PRECEDES = "precedes"
    ATTACHED_TO = "attached_to"
    DERIVED_FROM = "derived_from"


class EntityConfidence(str, Enum):
    EXPLICIT = "explicit"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFERRED = "inferred"


@dataclass
class GraphEntity:
    id: str
    name: str
    type: EntityType
    source: str
    source_id: str = ""
    confidence: EntityConfidence = EntityConfidence.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    space_id: str = "default"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "source": self.source,
            "source_id": self.source_id,
            "confidence": self.confidence.value,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "space_id": self.space_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GraphEntity:
        return cls(
            id=data["id"],
            name=data["name"],
            type=EntityType(data["type"]),
            source=data.get("source", ""),
            source_id=data.get("source_id", ""),
            confidence=EntityConfidence(data.get("confidence", "medium")),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            space_id=data.get("space_id", "default"),
        )


@dataclass
class GraphRelation:
    id: str
    source_id: str
    target_id: str
    type: RelationType
    confidence: EntityConfidence = EntityConfidence.MEDIUM
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    space_id: str = "default"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "confidence": self.confidence.value,
            "weight": self.weight,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "space_id": self.space_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GraphRelation:
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            type=RelationType(data["type"]),
            confidence=EntityConfidence(data.get("confidence", "medium")),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            space_id=data.get("space_id", "default"),
        )


class KnowledgeGraphManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "knowledge_graph_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._entities: dict[str, GraphEntity] = {}
        self._relations: dict[str, GraphRelation] = {}
        self._entity_index: dict[str, dict[str, list[str]]] = {}  # type -> list of ids
        self._load()

    def _entities_path(self) -> Path:
        return self._storage_path / "entities.json"

    def _relations_path(self) -> Path:
        return self._storage_path / "relations.json"

    def _load(self):
        e_path = self._entities_path()
        if e_path.exists():
            try:
                data = json.loads(e_path.read_text(encoding="utf-8"))
                for item in data:
                    entity = GraphEntity.from_dict(item)
                    self._entities[entity.id] = entity
                    self._index_entity(entity)
            except (json.JSONDecodeError, KeyError):
                pass
        r_path = self._relations_path()
        if r_path.exists():
            try:
                data = json.loads(r_path.read_text(encoding="utf-8"))
                for item in data:
                    rel = GraphRelation.from_dict(item)
                    self._relations[rel.id] = rel
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._entities_path().write_text(
            json.dumps([e.to_dict() for e in self._entities.values()], indent=2, default=str),
            encoding="utf-8",
        )
        self._relations_path().write_text(
            json.dumps([r.to_dict() for r in self._relations.values()], indent=2, default=str),
            encoding="utf-8",
        )

    def _index_entity(self, entity: GraphEntity):
        t = entity.type.value
        if t not in self._entity_index:
            self._entity_index[t] = {}
        prefix = entity.name[0].lower() if entity.name else "#"
        if prefix not in self._entity_index[t]:
            self._entity_index[t][prefix] = []
        if entity.id not in self._entity_index[t][prefix]:
            self._entity_index[t][prefix].append(entity.id)

    def _generate_id(self) -> str:
        import uuid
        return f"ent_{uuid.uuid4().hex[:12]}"

    def add_entity(self, name: str, type: EntityType, source: str = "", source_id: str = "",
                   confidence: EntityConfidence = EntityConfidence.MEDIUM,
                   metadata: dict | None = None, tags: list[str] | None = None,
                   space_id: str = "default") -> GraphEntity:
        now = datetime.now().isoformat()
        entity = GraphEntity(
            id=self._generate_id(),
            name=name,
            type=type,
            source=source,
            source_id=source_id,
            confidence=confidence,
            metadata=metadata or {},
            tags=tags or [],
            created_at=now,
            updated_at=now,
            space_id=space_id,
        )
        self._entities[entity.id] = entity
        self._index_entity(entity)
        self._save()
        return entity

    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, **updates) -> Optional[GraphEntity]:
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        for key, value in updates.items():
            if hasattr(entity, key):
                if key == "type":
                    setattr(entity, key, EntityType(value) if isinstance(value, str) else value)
                elif key == "confidence":
                    setattr(entity, key, EntityConfidence(value) if isinstance(value, str) else value)
                else:
                    setattr(entity, key, value)
        entity.updated_at = datetime.now().isoformat()
        self._save()
        return entity

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id not in self._entities:
            return False
        del self._entities[entity_id]
        self._relations = {k: v for k, v in self._relations.items()
                          if v.source_id != entity_id and v.target_id != entity_id}
        self._save()
        return True

    def search_entities(self, query: str = "", type: Optional[EntityType] = None,
                        tags: Optional[list[str]] = None, space_id: str = "",
                        min_confidence: Optional[EntityConfidence] = None) -> list[GraphEntity]:
        results = list(self._entities.values())
        if query:
            q = query.lower()
            results = [e for e in results if q in e.name.lower() or q in str(e.metadata).lower()]
        if type:
            results = [e for e in results if e.type == type]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if space_id:
            results = [e for e in results if e.space_id == space_id]
        if min_confidence:
            levels = ["inferred", "low", "medium", "high", "explicit"]
            min_idx = levels.index(min_confidence.value)
            results = [e for e in results if levels.index(e.confidence.value) >= min_idx]
        return results

    def list_entities_by_type(self, type: EntityType, space_id: str = "") -> list[GraphEntity]:
        results = [e for e in self._entities.values() if e.type == type]
        if space_id:
            results = [e for e in results if e.space_id == space_id]
        return results

    def add_relation(self, source_id: str, target_id: str, type: RelationType,
                     confidence: EntityConfidence = EntityConfidence.MEDIUM,
                     weight: float = 1.0, metadata: dict | None = None,
                     space_id: str = "default") -> Optional[GraphRelation]:
        if source_id not in self._entities or target_id not in self._entities:
            return None
        now = datetime.now().isoformat()
        rel = GraphRelation(
            id=f"rel_{self._generate_id()}",
            source_id=source_id,
            target_id=target_id,
            type=type,
            confidence=confidence,
            weight=weight,
            metadata=metadata or {},
            created_at=now,
            space_id=space_id,
        )
        self._relations[rel.id] = rel
        self._save()
        return rel

    def get_relations(self, entity_id: str) -> list[GraphRelation]:
        return [r for r in self._relations.values()
                if r.source_id == entity_id or r.target_id == entity_id]

    def remove_relation(self, relation_id: str) -> bool:
        if relation_id not in self._relations:
            return False
        del self._relations[relation_id]
        self._save()
        return True

    def get_connected_entities(self, entity_id: str, max_depth: int = 2) -> list[GraphEntity]:
        visited = {entity_id}
        result = []
        current = {entity_id}
        for _ in range(max_depth):
            next_ids = set()
            for rel in self._relations.values():
                if rel.source_id in current and rel.target_id not in visited:
                    next_ids.add(rel.target_id)
                if rel.target_id in current and rel.source_id not in visited:
                    next_ids.add(rel.source_id)
            for nid in next_ids:
                if nid in self._entities:
                    result.append(self._entities[nid])
            visited.update(next_ids)
            current = next_ids
            if not current:
                break
        return result

    def get_subgraph(self, entity_ids: list[str]) -> dict:
        entities = {eid: self._entities[eid].to_dict() for eid in entity_ids if eid in self._entities}
        relations = [r.to_dict() for r in self._relations.values()
                     if r.source_id in entity_ids and r.target_id in entity_ids]
        return {"entities": list(entities.values()), "relations": relations}

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> list[list[GraphRelation]]:
        if source_id not in self._entities or target_id not in self._entities:
            return []
        paths = []
        visited = set()

        def dfs(current: str, target: str, path: list[GraphRelation], depth: int):
            if depth > max_depth:
                return
            if current == target and path:
                paths.append(list(path))
                return
            visited.add(current)
            for rel in self._relations.values():
                next_id = None
                if rel.source_id == current and rel.target_id not in visited:
                    next_id = rel.target_id
                elif rel.target_id == current and rel.source_id not in visited:
                    next_id = rel.source_id
                if next_id:
                    path.append(rel)
                    dfs(next_id, target, path, depth + 1)
                    path.pop()
            visited.discard(current)

        dfs(source_id, target_id, [], 0)
        return paths

    def get_graph_stats(self) -> dict:
        type_counts: dict[str, int] = {}
        for e in self._entities.values():
            t = e.type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        relation_counts: dict[str, int] = {}
        for r in self._relations.values():
            t = r.type.value
            relation_counts[t] = relation_counts.get(t, 0) + 1
        return {
            "total_entities": len(self._entities),
            "total_relations": len(self._relations),
            "entities_by_type": type_counts,
            "relations_by_type": relation_counts,
        }

    def clear_space(self, space_id: str) -> int:
        count = 0
        eids = [eid for eid, e in self._entities.items() if e.space_id == space_id]
        for eid in eids:
            del self._entities[eid]
            count += 1
        self._relations = {k: v for k, v in self._relations.items() if v.space_id != space_id}
        self._save()
        return count
