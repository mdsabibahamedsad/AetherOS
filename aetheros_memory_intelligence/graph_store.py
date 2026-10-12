"""Personal knowledge graph: entities + typed relationships (sections 11-13).

File-backed (JSON, atomic writes like the fabric store), lazy-loaded,
bounded traversal.  The graph is retrieval infrastructure, not decoration:
``neighbors()`` / ``traverse()`` feed the hybrid retriever's graph channel.
"""

from __future__ import annotations

import enum
import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class EntityType(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    PRODUCT = "product"
    SOFTWARE = "software"
    FILE = "file"
    DOCUMENT = "document"
    WEBSITE = "website"
    SOURCE = "source"
    TASK = "task"
    CONCEPT = "concept"
    LOCATION = "location"
    EVENT = "event"
    MODEL = "model"
    TOOL = "tool"
    SKILL = "skill"
    ARTIFACT = "artifact"


class RelationType(str, enum.Enum):
    OWNS = "owns"
    USES = "uses"
    PREFERS = "prefers"
    WORKS_ON = "works_on"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    CREATED = "created"
    MODIFIED = "modified"
    MENTIONED_IN = "mentioned_in"
    DECIDED = "decided"
    REJECTED = "rejected"
    REQUIRES = "requires"
    BLOCKS = "blocks"
    SOLVES = "solves"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    DERIVED_FROM = "derived_from"


@dataclass
class Entity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType = EntityType.CONCEPT
    canonical_name: str = ""
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    source_ids: List[str] = field(default_factory=list)
    project_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type.value, "canonical_name": self.canonical_name,
                "aliases": list(self.aliases), "description": self.description,
                "attributes": dict(self.attributes), "confidence": self.confidence,
                "first_seen": self.first_seen, "last_seen": self.last_seen,
                "source_ids": list(self.source_ids), "project_id": self.project_id,
                "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Entity":
        e = cls()
        e.id = str(d.get("id", e.id))
        e.type = EntityType(str(d.get("type", e.type.value)))
        e.canonical_name = str(d.get("canonical_name", ""))
        e.aliases = [str(a) for a in (d.get("aliases") or [])]
        e.description = str(d.get("description", ""))
        e.attributes = dict(d.get("attributes") or {})
        e.confidence = float(d.get("confidence", 0.5))
        e.first_seen = float(d.get("first_seen", e.first_seen))
        e.last_seen = float(d.get("last_seen", e.last_seen))
        e.source_ids = [str(s) for s in (d.get("source_ids") or [])]
        e.project_id = str(d.get("project_id", ""))
        e.metadata = dict(d.get("metadata") or {})
        return e


@dataclass
class Relationship:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: RelationType = RelationType.RELATED_TO
    source_id: str = ""
    target_id: str = ""
    confidence: float = 0.5
    source: str = ""
    provenance: str = "model_inferred"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    valid_from: float = 0.0
    valid_until: float = 0.0
    project_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type.value, "source_id": self.source_id,
                "target_id": self.target_id, "confidence": self.confidence,
                "source": self.source, "provenance": self.provenance,
                "created_at": self.created_at, "updated_at": self.updated_at,
                "valid_from": self.valid_from, "valid_until": self.valid_until,
                "project_id": self.project_id, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Relationship":
        r = cls()
        r.id = str(d.get("id", r.id))
        r.type = RelationType(str(d.get("type", r.type.value)))
        for k in ("source_id", "target_id", "source", "provenance", "project_id"):
            setattr(r, k, str(d.get(k, "")))
        for k in ("confidence", "created_at", "updated_at", "valid_from", "valid_until"):
            try:
                setattr(r, k, float(d.get(k, getattr(r, k))))
            except (TypeError, ValueError):
                pass
        r.metadata = dict(d.get("metadata") or {})
        return r


class GraphStore:
    """Atomic JSON graph store with canonical-name dedup and tombstones."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relationship] = {}
        self._name_index: Dict[str, str] = {}  # normalized name -> entity id
        self._tombstones: Set[str] = set()

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./temp_graph")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    @staticmethod
    def _norm(name: str) -> str:
        return " ".join(name.lower().strip().split())

    # -- entities ------------------------------------------------------
    def upsert_entity(self, entity: Entity) -> Entity:
        with self._lock:
            key = self._norm(entity.canonical_name)
            existing_id = self._name_index.get(key)
            if existing_id and existing_id in self._entities and not entity.id:
                entity.id = existing_id
            if entity.id in self._entities:
                cur = self._entities[entity.id]
                # Merge: keep strongest confidence, union aliases/sources.
                cur.aliases = sorted(set(cur.aliases) | set(entity.aliases))
                cur.source_ids = sorted(set(cur.source_ids) | set(entity.source_ids))
                cur.last_seen = max(cur.last_seen, entity.last_seen)
                cur.confidence = max(cur.confidence, entity.confidence)
                if entity.description:
                    cur.description = entity.description
                cur.attributes.update(entity.attributes)
                entity = cur
            else:
                if not entity.id:
                    entity.id = str(uuid.uuid4())
                self._entities[entity.id] = entity
            if key:
                self._name_index[key] = entity.id
                for alias in entity.aliases:
                    self._name_index.setdefault(self._norm(alias), entity.id)
            self._persist()
            return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with self._lock:
            return self._entities.get(entity_id)

    def find_entity(self, name: str) -> Optional[Entity]:
        with self._lock:
            eid = self._name_index.get(self._norm(name))
            return self._entities.get(eid) if eid else None

    def delete_entity(self, entity_id: str) -> bool:
        """Tombstone: node removed, incident edges dropped (section 57)."""
        with self._lock:
            if entity_id not in self._entities:
                return False
            self._entities.pop(entity_id)
            self._tombstones.add(entity_id)
            self._relations = {rid: r for rid, r in self._relations.items()
                               if r.source_id != entity_id and r.target_id != entity_id}
            self._name_index = {k: v for k, v in self._name_index.items() if v != entity_id}
            self._persist()
            return True

    # -- relationships ---------------------------------------------------
    def add_relationship(self, rel: Relationship) -> Relationship:
        with self._lock:
            if rel.source_id in self._tombstones or rel.target_id in self._tombstones:
                raise ValueError("endpoint is tombstoned")
            # Dedup identical (src, type, dst).
            for existing in self._relations.values():
                if (existing.source_id, existing.type, existing.target_id) == \
                   (rel.source_id, rel.type, rel.target_id):
                    existing.confidence = max(existing.confidence, rel.confidence)
                    existing.updated_at = time.time()
                    self._persist()
                    return existing
            if not rel.id:
                rel.id = str(uuid.uuid4())
            self._relations[rel.id] = rel
            self._persist()
            return rel

    def neighbors(self, entity_id: str, *, depth: int = 1,
                  project_id: str = "") -> Dict[str, Any]:
        """Bounded BFS traversal. Returns {entities, relationships}."""
        with self._lock:
            seen: Set[str] = {entity_id}
            frontier = {entity_id}
            out_rels: List[Relationship] = []
            for _ in range(max(1, depth)):
                nxt: Set[str] = set()
                for rel in self._relations.values():
                    if project_id and rel.project_id and rel.project_id != project_id:
                        continue
                    if rel.source_id in frontier and rel.target_id not in seen:
                        out_rels.append(rel)
                        seen.add(rel.target_id)
                        nxt.add(rel.target_id)
                    elif rel.target_id in frontier and rel.source_id not in seen:
                        out_rels.append(rel)
                        seen.add(rel.source_id)
                        nxt.add(rel.source_id)
                frontier = nxt
                if not frontier:
                    break
            return {"entities": [self._entities[i].to_dict() for i in seen if i in self._entities],
                    "relationships": [r.to_dict() for r in out_rels]}

    def relations_of(self, entity_id: str) -> List[Relationship]:
        with self._lock:
            return [r for r in self._relations.values()
                    if r.source_id == entity_id or r.target_id == entity_id]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"entities": len(self._entities), "relationships": len(self._relations),
                    "tombstones": len(self._tombstones)}

    def all_entities(self) -> List[Entity]:
        with self._lock:
            return list(self._entities.values())

    def all_relationships(self) -> List[Relationship]:
        with self._lock:
            return list(self._relations.values())

    # -- persistence -------------------------------------------------------
    def _path(self) -> Path:
        assert self._root is not None
        return self._root / "graph.json"

    def _persist(self) -> None:
        if self._root is None:
            return
        data = {"entities": {i: e.to_dict() for i, e in self._entities.items()},
                "relationships": {i: r.to_dict() for i, r in self._relations.items()},
                "tombstones": sorted(self._tombstones)}
        fd, tmp = tempfile.mkstemp(dir=str(self._root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, str(self._path()))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _load(self) -> None:
        path = self._path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for raw in (data.get("entities") or {}).values():
            try:
                e = Entity.from_dict(raw)
                self._entities[e.id] = e
                if e.canonical_name:
                    self._name_index[self._norm(e.canonical_name)] = e.id
            except (ValueError, KeyError):
                continue
        for raw in (data.get("relationships") or {}).values():
            try:
                r = Relationship.from_dict(raw)
                self._relations[r.id] = r
            except (ValueError, KeyError):
                continue
        self._tombstones = set(data.get("tombstones") or [])
