"""Memory Manager — core orchestrator for the memory platform.

Responsibilities: initialize, load, store, retrieve, delete, archive,
compact, backup, restore all memory types.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import enum
import math
from aetheros_memory.embedding_engine import EmbeddingEngine, EmbeddingConfig, EmbeddingProvider
from aetheros_memory.vector_database import (
    VectorDatabase, VectorDBConfig, VectorDBType, VectorRecord,
)
from aetheros_memory.knowledge_graph import (
    KnowledgeGraph, GraphEntity, GraphRelationship,
    EntityType, RelationshipType,
)

logger = logging.getLogger("aetheros_memory.manager")


class MemoryCategory(str, enum.Enum):
    DECISION = "decision"
    CONVERSATION = "conversation"
    PROJECT = "project"
    WORKSPACE = "workspace"
    USER_PREFERENCES = "user_preferences"
    AGENT = "agent"
    TOOL = "tool"
    RESEARCH = "research"
    CODE = "code"
    TASK = "task"
    PINNED = "pinned"
    TEMPORARY = "temporary"
    LONG_TERM = "long_term"


@dataclass
class MemoryRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: MemoryCategory = MemoryCategory.CONVERSATION
    content: str = ""
    summary: str = ""
    key: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 1.0
    embedding: List[float] = field(default_factory=list)
    permissions: str = "private"
    source: str = ""
    workspace_id: str = ""
    project_id: str = ""
    conversation_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 0.0
    archived: bool = False
    pinned: bool = False
    encrypted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "content": self.content,
            "summary": self.summary,
            "key": self.key,
            "tags": self.tags,
            "importance": self.importance,
            "permissions": self.permissions,
            "source": self.source,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "ttl": self.ttl,
            "archived": self.archived,
            "pinned": self.pinned,
            "encrypted": self.encrypted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        data = dict(data)
        data["category"] = MemoryCategory(data.pop("category", "conversation"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.updated_at) > self.ttl


@dataclass
class MemoryManagerConfig:
    storage_dir: str = ""
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    embedding_model: str = ""
    vector_db_backend: VectorDBType = VectorDBType.SQLITE
    vector_db_path: str = ""
    auto_index: bool = True
    auto_backup_interval: float = 3600.0
    max_memories_per_category: int = 10000
    enable_compression: bool = True
    enable_dedup: bool = True


@dataclass
class MemoryStats:
    total: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    archived: int = 0
    pinned: int = 0
    expired: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    vector_db_size: int = 0


@dataclass
class BackupManifest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    path: str = ""
    size_bytes: int = 0
    memory_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0


@dataclass
class ArchiveEntry:
    id: str = ""
    original_id: str = ""
    archived_at: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    def __init__(
        self,
        config: Optional[MemoryManagerConfig] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        vector_db: Optional[VectorDatabase] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
    ) -> None:
        self._config = config or MemoryManagerConfig()
        self._lock = threading.RLock()
        self._memories: Dict[str, MemoryRecord] = {}
        self._archives: Dict[str, ArchiveEntry] = {}
        self._by_category: Dict[MemoryCategory, Set[str]] = {mc: set() for mc in MemoryCategory}
        self._by_key: Dict[str, str] = {}
        self._by_workspace: Dict[str, Set[str]] = {}
        self._by_project: Dict[str, Set[str]] = {}
        self._by_conversation: Dict[str, Set[str]] = {}

        self._embedding_engine = embedding_engine or EmbeddingEngine()
        self._vector_db = vector_db
        self._knowledge_graph = knowledge_graph
        self._initialized = False
        self._backup_timer: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._initialized:
            return
        config = self._config
        storage_dir = Path(config.storage_dir) if config.storage_dir else Path.cwd() / "memory_data"
        storage_dir.mkdir(parents=True, exist_ok=True)

        embed_config = EmbeddingConfig(
            provider=config.embedding_provider,
            model=config.embedding_model,
        )
        self._embedding_engine = EmbeddingEngine(embed_config)

        if self._vector_db is None:
            vdb_config = VectorDBConfig(
                backend=config.vector_db_backend,
                path=config.vector_db_path or str(storage_dir / "vector_db"),
                dimensions=self._embedding_engine.dimensions,
            )
            self._vector_db = VectorDatabase(vdb_config)
            self._vector_db.initialize()

        if self._knowledge_graph is None:
            self._knowledge_graph = KnowledgeGraph(storage_dir / "knowledge_graph")

        self._load()
        self._initialized = True
        logger.info("MemoryManager initialized: %s", storage_dir)

        if config.auto_backup_interval > 0:
            self._start_auto_backup()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.CONVERSATION,
        key: str = "",
        tags: Optional[List[str]] = None,
        importance: float = 1.0,
        source: str = "",
        workspace_id: str = "",
        project_id: str = "",
        conversation_id: str = "",
        permissions: str = "private",
        ttl: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        self._require_init()

        if key:
            with self._lock:
                existing_id = self._by_key.get(f"{category.value}:{key}")
                if existing_id and existing_id in self._memories:
                    existing = self._memories[existing_id]
                    existing.content = content
                    existing.updated_at = time.time()
                    existing.importance = importance
                    if tags:
                        existing.tags = list(set(existing.tags + tags))
                    if metadata:
                        existing.metadata.update(metadata)
                    self._save()
                    return existing

        record = MemoryRecord(
            category=category,
            content=content,
            key=key,
            tags=tags or [],
            importance=importance,
            source=source,
            workspace_id=workspace_id,
            project_id=project_id,
            conversation_id=conversation_id,
            permissions=permissions,
            ttl=ttl,
            metadata=metadata or {},
        )

        if self._config.auto_index:
            try:
                result = self._embedding_engine.embed(content)
                record.embedding = result.vector
            except Exception as exc:
                logger.warning("Embedding failed during store: %s", exc)

        with self._lock:
            self._memories[record.id] = record
            self._by_category[category].add(record.id)
            if key:
                self._by_key[f"{category.value}:{key}"] = record.id
            if workspace_id:
                if workspace_id not in self._by_workspace:
                    self._by_workspace[workspace_id] = set()
                self._by_workspace[workspace_id].add(record.id)
            if project_id:
                if project_id not in self._by_project:
                    self._by_project[project_id] = set()
                self._by_project[project_id].add(record.id)
            if conversation_id:
                if conversation_id not in self._by_conversation:
                    self._by_conversation[conversation_id] = set()
                self._by_conversation[conversation_id].add(record.id)
            self._enforce_limit(category)

        if record.embedding and self._vector_db:
            try:
                self._vector_db.insert(
                    id=record.id,
                    vector=record.embedding,
                    text=content,
                    metadata={
                        "category": category.value,
                        "key": key,
                        "importance": importance,
                        "workspace_id": workspace_id,
                        "project_id": project_id,
                        "permissions": permissions,
                        "tags": ",".join(record.tags),
                    },
                )
            except Exception as exc:
                logger.warning("Vector DB insert failed: %s", exc)

        if self._knowledge_graph:
            try:
                entity = GraphEntity(
                    id=record.id,
                    type=self._category_to_entity_type(category),
                    name=key or content[:80],
                    description=content[:500],
                    importance=importance,
                    properties={
                        "category": category.value,
                        "source": source,
                        "workspace_id": workspace_id,
                        "project_id": project_id,
                    },
                )
                self._knowledge_graph.add_entity(entity)
            except Exception as exc:
                logger.warning("Knowledge graph add failed: %s", exc)

        self._save()
        return record

    def store_batch(self, records: List[MemoryRecord]) -> List[MemoryRecord]:
        self._require_init()
        stored: List[MemoryRecord] = []
        for record in records:
            stored.append(self.store(
                content=record.content,
                category=record.category,
                key=record.key,
                tags=record.tags,
                importance=record.importance,
                source=record.source,
                workspace_id=record.workspace_id,
                project_id=record.project_id,
                conversation_id=record.conversation_id,
                permissions=record.permissions,
                ttl=record.ttl,
                metadata=record.metadata,
            ))
        return stored

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(self, memory_id: str) -> Optional[MemoryRecord]:
        self._require_init()
        with self._lock:
            record = self._memories.get(memory_id)
            if record and not record.archived and not record.is_expired:
                record.accessed_at = time.time()
                record.access_count += 1
                return record
            return None

    def retrieve_by_key(self, key: str, category: Optional[MemoryCategory] = None) -> Optional[MemoryRecord]:
        self._require_init()
        cats = [category] if category else list(MemoryCategory)
        for cat in cats:
            with self._lock:
                record_id = self._by_key.get(f"{cat.value}:{key}")
                if record_id and record_id in self._memories:
                    record = self._memories[record_id]
                    if not record.archived and not record.is_expired:
                        record.accessed_at = time.time()
                        record.access_count += 1
                        return record
        return None

    def retrieve_content(self, memory_id: str, default: str = "") -> str:
        record = self.retrieve(memory_id)
        return record.content if record else default

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        category: Optional[MemoryCategory] = None,
        tags: Optional[List[str]] = None,
        workspace_id: str = "",
        limit: int = 20,
        include_archived: bool = False,
    ) -> List[MemoryRecord]:
        self._require_init()
        query_lower = query.lower()
        scored: List[Tuple[MemoryRecord, float]] = []

        with self._lock:
            candidates: List[MemoryRecord] = []
            if category:
                for cid in self._by_category.get(category, set()):
                    if cid in self._memories:
                        candidates.append(self._memories[cid])
            elif workspace_id:
                for cid in self._by_workspace.get(workspace_id, set()):
                    if cid in self._memories:
                        candidates.append(self._memories[cid])
            else:
                candidates = list(self._memories.values())

            for record in candidates:
                if not include_archived and record.archived:
                    continue
                if record.is_expired:
                    continue
                if tags and not any(t in record.tags for t in tags):
                    continue

                score = 0.0
                if query_lower in record.content.lower():
                    score += 5.0
                if query_lower in record.key.lower():
                    score += 10.0
                if query_lower in record.summary.lower():
                    score += 8.0
                for tag in record.tags:
                    if query_lower in tag.lower():
                        score += 3.0
                for meta_val in record.metadata.values():
                    if isinstance(meta_val, str) and query_lower in meta_val.lower():
                        score += 1.0

                score *= record.importance
                score *= (1.0 + 0.1 * math.log1p(record.access_count))
                score *= (1.0 / (1.0 + (time.time() - record.accessed_at) / 86400.0))

                if score > 0:
                    scored.append((record, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, s in scored[:limit]]

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[MemoryCategory] = None,
    ) -> List[Tuple[MemoryRecord, float]]:
        self._require_init()
        if not self._vector_db:
            return []
        try:
            result = self._embedding_engine.embed(query)
        except Exception as exc:
            logger.warning("Embedding for search failed: %s", exc)
            return []

        try:
            results = self._vector_db.search(result.vector, top_k=top_k * 2)
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

        matched: List[Tuple[MemoryRecord, float]] = []
        for sr in results:
            with self._lock:
                record = self._memories.get(sr.id)
            if record and not record.archived and not record.is_expired:
                if category is None or record.category == category:
                    matched.append((record, sr.score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return matched[:top_k]

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, memory_id: str) -> bool:
        self._require_init()
        with self._lock:
            record = self._memories.pop(memory_id, None)
            if not record:
                return False
            self._by_category[record.category].discard(memory_id)
            key = f"{record.category.value}:{record.key}" if record.key else ""
            if key and self._by_key.get(key) == memory_id:
                del self._by_key[key]
            for ws_set in self._by_workspace.values():
                ws_set.discard(memory_id)
            for pj_set in self._by_project.values():
                pj_set.discard(memory_id)
            for cv_set in self._by_conversation.values():
                cv_set.discard(memory_id)

        if self._vector_db:
            try:
                self._vector_db.delete(memory_id)
            except Exception:
                pass
        if self._knowledge_graph:
            try:
                self._knowledge_graph.delete_entity(memory_id)
            except Exception:
                pass
        self._save()
        return True

    def delete_by_filter(self, category: Optional[MemoryCategory] = None, key: str = "") -> int:
        self._require_init()
        ids_to_delete: List[str] = []
        with self._lock:
            for record in list(self._memories.values()):
                if category and record.category != category:
                    continue
                if key and record.key != key:
                    continue
                ids_to_delete.append(record.id)
        for rid in ids_to_delete:
            self.delete(rid)
        return len(ids_to_delete)

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def archive(self, memory_id: str) -> bool:
        self._require_init()
        with self._lock:
            record = self._memories.get(memory_id)
            if not record or record.archived:
                return False
            entry = ArchiveEntry(
                original_id=memory_id,
                data=record.to_dict(),
            )
            self._archives[memory_id] = entry
            record.archived = True
        self._save()
        return True

    def unarchive(self, memory_id: str) -> bool:
        self._require_init()
        with self._lock:
            record = self._memories.get(memory_id)
            if not record or not record.archived:
                return False
            record.archived = False
            self._archives.pop(memory_id, None)
        self._save()
        return True

    def list_archived(self) -> List[MemoryRecord]:
        self._require_init()
        with self._lock:
            return [r for r in self._memories.values() if r.archived]

    # ------------------------------------------------------------------
    # Compact
    # ------------------------------------------------------------------

    def compact(self) -> Dict[str, int]:
        self._require_init()
        stats: Dict[str, int] = {"removed_expired": 0, "removed_duplicates": 0, "removed_low_importance": 0}
        now = time.time()

        with self._lock:
            expired = [
                rid for rid, r in self._memories.items()
                if r.ttl > 0 and (now - r.updated_at) > r.ttl
            ]
            for rid in expired:
                self.delete(rid)
            stats["removed_expired"] = len(expired)

            if self._config.enable_dedup:
                seen: Dict[str, str] = {}
                for record in list(self._memories.values()):
                    content_key = record.content[:200].strip().lower()
                    if content_key in seen:
                        existing = self._memories.get(seen[content_key])
                        if existing and existing.importance >= record.importance:
                            self.delete(record.id)
                            stats["removed_duplicates"] += 1
                        else:
                            self.delete(existing.id)
                            stats["removed_duplicates"] += 1
                            seen[content_key] = record.id
                    else:
                        seen[content_key] = record.id

            low_importance = [
                rid for rid, r in self._memories.items()
                if r.importance < 0.1 and r.access_count == 0 and not r.pinned
                and (now - r.created_at) > 86400 * 7
            ]
            for rid in low_importance:
                self.delete(rid)
            stats["removed_low_importance"] = len(low_importance)

        self._save()
        return stats

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup(self, backup_dir: Optional[str] = None) -> BackupManifest:
        self._require_init()
        storage_dir = Path(self._config.storage_dir) if self._config.storage_dir else Path.cwd() / "memory_data"
        backup_path = Path(backup_dir) if backup_dir else storage_dir / "backups"
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"memory_backup_{timestamp}.json"

        with self._lock:
            data = {
                "manifest_version": "1.0",
                "timestamp": time.time(),
                "memories": {rid: r.to_dict() for rid, r in self._memories.items()},
                "archives": {aid: a.__dict__ for aid, a in self._archives.items()},
                "config": {
                    "embedding_provider": self._config.embedding_provider.value,
                    "vector_db_backend": self._config.vector_db_backend.value,
                },
            }

            if self._knowledge_graph:
                data["knowledge_graph"] = json.loads(self._knowledge_graph.export_json())

            content = json.dumps(data, indent=2, ensure_ascii=False)
            backup_file.write_text(content, encoding="utf-8")

            manifest = BackupManifest(
                timestamp=time.time(),
                path=str(backup_file),
                size_bytes=len(content.encode("utf-8")),
                memory_count=len(data["memories"]),
                entity_count=len(data.get("knowledge_graph", {}).get("entities", {})),
                relationship_count=len(data.get("knowledge_graph", {}).get("relationships", {})),
            )

        logger.info("Backup created: %s (%d memories)", backup_file, manifest.memory_count)
        return manifest

    def restore(self, backup_path: str) -> int:
        self._require_init()
        path = Path(backup_path)
        if not path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0

        for rid, raw in data.get("memories", {}).items():
            record = MemoryRecord.from_dict(raw)
            with self._lock:
                self._memories[rid] = record
                self._by_category[record.category].add(rid)
                if record.key:
                    self._by_key[f"{record.category.value}:{record.key}"] = rid
            count += 1

        if "knowledge_graph" in data:
            kg_data = data["knowledge_graph"]
            for eid, raw in kg_data.get("entities", {}).items():
                entity = GraphEntity.from_dict(raw)
                self._knowledge_graph.add_entity(entity)
            for rid, raw in kg_data.get("relationships", {}).items():
                rel = GraphRelationship.from_dict(raw)
                if self._knowledge_graph.get_entity(rel.source_id) and self._knowledge_graph.get_entity(rel.target_id):
                    pass

        self._save()
        logger.info("Restored %d memories from %s", count, backup_path)
        return count

    def list_backups(self, backup_dir: Optional[str] = None) -> List[Path]:
        storage_dir = Path(self._config.storage_dir) if self._config.storage_dir else Path.cwd() / "memory_data"
        backup_path = Path(backup_dir) if backup_dir else storage_dir / "backups"
        if not backup_path.exists():
            return []
        return sorted(backup_path.glob("memory_backup_*.json"), reverse=True)

    def _start_auto_backup(self) -> None:
        def _backup_loop() -> None:
            while self._initialized:
                time.sleep(self._config.auto_backup_interval)
                try:
                    self.backup()
                except Exception as exc:
                    logger.warning("Auto backup failed: %s", exc)

        self._backup_timer = threading.Thread(target=_backup_loop, daemon=True, name="memory-backup")
        self._backup_timer.start()

    # ------------------------------------------------------------------
    # Memory editing
    # ------------------------------------------------------------------

    def update(self, memory_id: str, **kwargs) -> Optional[MemoryRecord]:
        self._require_init()
        with self._lock:
            record = self._memories.get(memory_id)
            if not record:
                return None
            for key, value in kwargs.items():
                if hasattr(record, key) and key not in ("id", "created_at"):
                    setattr(record, key, value)
            record.updated_at = time.time()
        self._save()
        return record

    def pin(self, memory_id: str) -> bool:
        record = self.update(memory_id, pinned=True)
        return record is not None

    def unpin(self, memory_id: str) -> bool:
        record = self.update(memory_id, pinned=False)
        return record is not None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> MemoryStats:
        self._require_init()
        with self._lock:
            by_cat: Dict[str, int] = {}
            archived = 0
            pinned = 0
            expired = 0
            now = time.time()
            for record in self._memories.values():
                cat = record.category.value
                by_cat[cat] = by_cat.get(cat, 0) + 1
                if record.archived:
                    archived += 1
                if record.pinned:
                    pinned += 1
                if record.ttl > 0 and (now - record.updated_at) > record.ttl:
                    expired += 1

            kg_stats = self._knowledge_graph.stats() if self._knowledge_graph else {}
            vdb_size = self._vector_db.count() if self._vector_db else 0

            return MemoryStats(
                total=len(self._memories),
                by_category=by_cat,
                archived=archived,
                pinned=pinned,
                expired=expired,
                total_entities=kg_stats.get("total_entities", 0),
                total_relationships=kg_stats.get("total_relationships", 0),
                vector_db_size=vdb_size,
            )

    def get_by_workspace(self, workspace_id: str) -> List[MemoryRecord]:
        self._require_init()
        with self._lock:
            ids = self._by_workspace.get(workspace_id, set())
            return [self._memories[eid] for eid in ids if eid in self._memories and not self._memories[eid].archived]

    def get_by_project(self, project_id: str) -> List[MemoryRecord]:
        self._require_init()
        with self._lock:
            ids = self._by_project.get(project_id, set())
            return [self._memories[eid] for eid in ids if eid in self._memories and not self._memories[eid].archived]

    def get_by_conversation(self, conversation_id: str) -> List[MemoryRecord]:
        self._require_init()
        with self._lock:
            ids = self._by_conversation.get(conversation_id, set())
            return [self._memories[eid] for eid in ids if eid in self._memories and not self._memories[eid].archived]

    def list_pinned(self) -> List[MemoryRecord]:
        self._require_init()
        with self._lock:
            return [r for r in self._memories.values() if r.pinned and not r.archived]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._config.storage_dir:
            return
        try:
            storage_dir = Path(self._config.storage_dir)
            storage_dir.mkdir(parents=True, exist_ok=True)
            path = storage_dir / "memory_manager.json"
            tmp = path.with_suffix(".tmp")
            data = {
                "memories": {rid: r.to_dict() for rid, r in self._memories.items()},
                "archives": {aid: {
                    "original_id": a.original_id,
                    "archived_at": a.archived_at,
                    "data": a.data,
                } for aid, a in self._archives.items()},
                "by_key": self._by_key,
                "by_workspace": {ws: list(ids) for ws, ids in self._by_workspace.items()},
                "by_project": {pj: list(ids) for pj, ids in self._by_project.items()},
                "by_conversation": {cv: list(ids) for cv, ids in self._by_conversation.items()},
            }
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save memory manager: %s", exc)

    def _load(self) -> None:
        if not self._config.storage_dir:
            return
        path = Path(self._config.storage_dir) / "memory_manager.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for rid, raw in data.get("memories", {}).items():
                record = MemoryRecord.from_dict(raw)
                self._memories[rid] = record
                self._by_category[record.category].add(rid)
                if record.key:
                    self._by_key[f"{record.category.value}:{record.key}"] = rid
                if record.workspace_id:
                    if record.workspace_id not in self._by_workspace:
                        self._by_workspace[record.workspace_id] = set()
                    self._by_workspace[record.workspace_id].add(rid)
                if record.project_id:
                    if record.project_id not in self._by_project:
                        self._by_project[record.project_id] = set()
                    self._by_project[record.project_id].add(rid)
                if record.conversation_id:
                    if record.conversation_id not in self._by_conversation:
                        self._by_conversation[record.conversation_id] = set()
                    self._by_conversation[record.conversation_id].add(rid)

            for aid, raw in data.get("archives", {}).items():
                self._archives[aid] = ArchiveEntry(
                    original_id=raw.get("original_id", ""),
                    archived_at=raw.get("archived_at", time.time()),
                    data=raw.get("data", {}),
                )

            self._by_key.update(data.get("by_key", {}))
            for ws, ids in data.get("by_workspace", {}).items():
                self._by_workspace[ws] = set(ids)
            for pj, ids in data.get("by_project", {}).items():
                self._by_project[pj] = set(ids)
            for cv, ids in data.get("by_conversation", {}).items():
                self._by_conversation[cv] = set(ids)

            logger.info("Loaded memory manager: %d memories", len(self._memories))
        except Exception as exc:
            logger.warning("Failed to load memory manager: %s", exc)

    def _enforce_limit(self, category: MemoryCategory) -> None:
        ids = self._by_category.get(category, set())
        if len(ids) > self._config.max_memories_per_category:
            sorted_records = sorted(
                [self._memories[eid] for eid in ids if eid in self._memories],
                key=lambda r: r.importance,
            )
            to_remove = len(sorted_records) - self._config.max_memories_per_category
            for record in sorted_records[:to_remove]:
                if not record.pinned:
                    self._memories.pop(record.id, None)
                    self._by_category[category].discard(record.id)

    def _require_init(self) -> None:
        if not self._initialized:
            raise RuntimeError("MemoryManager not initialized. Call initialize() first.")

    def _category_to_entity_type(self, category: MemoryCategory) -> EntityType:
        mapping = {
            MemoryCategory.CONVERSATION: EntityType.CONVERSATION,
            MemoryCategory.PROJECT: EntityType.PROJECT,
            MemoryCategory.WORKSPACE: EntityType.WORKSPACE,
            MemoryCategory.USER_PREFERENCES: EntityType.KNOWLEDGE,
            MemoryCategory.AGENT: EntityType.AGENT,
            MemoryCategory.TOOL: EntityType.TOOL,
            MemoryCategory.RESEARCH: EntityType.RESEARCH_SESSION,
            MemoryCategory.CODE: EntityType.CODE_SNIPPET,
            MemoryCategory.TASK: EntityType.TASK,
            MemoryCategory.PINNED: EntityType.KNOWLEDGE,
            MemoryCategory.TEMPORARY: EntityType.KNOWLEDGE,
            MemoryCategory.LONG_TERM: EntityType.KNOWLEDGE,
        }
        return mapping.get(category, EntityType.KNOWLEDGE)

    def summary(self) -> str:
        s = self.stats()
        lines = [
            f"Memory Manager: {s.total} memories",
            f"  Categories: {', '.join(f'{k}={v}' for k, v in sorted(s.by_category.items()))}",
            f"  Archived: {s.archived}, Pinned: {s.pinned}, Expired: {s.expired}",
            f"  Knowledge Graph: {s.total_entities} entities, {s.total_relationships} relationships",
            f"  Vector DB: {s.vector_db_size} vectors",
        ]
        return "\n".join(lines)

    @property
    def embedding_engine(self) -> EmbeddingEngine:
        return self._embedding_engine

    @property
    def vector_db(self) -> Optional[VectorDatabase]:
        return self._vector_db

    @property
    def knowledge_graph(self) -> Optional[KnowledgeGraph]:
        return self._knowledge_graph

    @property
    def config(self) -> MemoryManagerConfig:
        return self._config