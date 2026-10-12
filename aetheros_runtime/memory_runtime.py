"""Memory Runtime — conversation, project, long-term, temporary, pinned memory with automatic retrieval.

Multi-tier memory system that persists and retrieves context automatically.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.memory")


class MemoryType(enum.Enum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    LONG_TERM = "long_term"
    TEMPORARY = "temporary"
    PINNED = "pinned"


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.CONVERSATION
    key: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    score: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl: float = 0.0  # 0 = permanent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "key": self.key,
            "content": self.content,
            "tags": self.tags,
            "score": self.score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        data = dict(data)
        data["memory_type"] = MemoryType(data.pop("memory_type", "conversation"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.updated_at) > self.ttl


MemoryProvider = Callable[[str, str], Optional[str]]


class MemoryRuntime:
    """Multi-tier memory runtime with automatic retrieval.

    Tiers:
    - Conversation memory: short-term, per-chat
    - Project memory: per-project persistent
    - Long-term memory: cross-session persistent
    - Temporary memory: auto-expiring
    - Pinned memory: always retained
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._stores: Dict[MemoryType, Dict[str, MemoryEntry]] = {
            mt: {} for mt in MemoryType
        }
        self._providers: Dict[str, MemoryProvider] = {}
        self._storage_dir = storage_dir
        self._max_entries_per_type: int = 1000
        self._auto_cleanup_interval: float = 300.0
        self._cleanup_thread: Optional[threading.Thread] = None

        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # Memory operations
    # ------------------------------------------------------------------

    def store(
        self,
        key: str,
        content: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        tags: Optional[List[str]] = None,
        source: str = "",
        ttl: float = 0.0,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            key=key,
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            source=source,
            ttl=ttl,
        )
        with self._lock:
            store = self._stores[memory_type]
            existing = self._find_by_key(memory_type, key)
            if existing:
                existing.content = content
                existing.updated_at = time.time()
                existing.access_count += 1
                if tags:
                    existing.tags = list(set(existing.tags + tags))
                logger.debug("Memory updated: %s/%s", memory_type.value, key)
                return existing
            store[entry.id] = entry
            self._enforce_max(memory_type)
        self._save()
        logger.debug("Memory stored: %s/%s", memory_type.value, key)
        return entry

    def retrieve(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Optional[MemoryEntry]:
        types = [memory_type] if memory_type else list(MemoryType)
        for mt in types:
            with self._lock:
                entry = self._find_by_key(mt, key)
                if entry and not entry.is_expired:
                    entry.accessed_at = time.time()
                    entry.access_count += 1
                    return entry
        return None

    def retrieve_content(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None,
        default: str = "",
    ) -> str:
        entry = self.retrieve(key, memory_type)
        return entry.content if entry else default

    def delete(self, key: str, memory_type: Optional[MemoryType] = None) -> bool:
        types = [memory_type] if memory_type else list(MemoryType)
        for mt in types:
            with self._lock:
                entry = self._find_by_key(mt, key)
                if entry:
                    del self._stores[mt][entry.id]
                    self._save()
                    return True
        return False

    def clear_type(self, memory_type: MemoryType) -> int:
        with self._lock:
            count = len(self._stores[memory_type])
            self._stores[memory_type].clear()
        self._save()
        return count

    def clear_all(self) -> Dict[str, int]:
        counts = {}
        with self._lock:
            for mt in MemoryType:
                if mt != MemoryType.PINNED:
                    counts[mt.value] = len(self._stores[mt])
                    self._stores[mt].clear()
        self._save()
        return counts

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        query_lower = query.lower()
        results: List[MemoryEntry] = []
        types = [memory_type] if memory_type else list(MemoryType)
        with self._lock:
            for mt in types:
                for entry in self._stores[mt].values():
                    if entry.is_expired:
                        continue
                    if (query_lower in entry.key.lower() or
                            query_lower in entry.content.lower()):
                        results.append(entry)
        return sorted(results, key=lambda e: e.score, reverse=True)

    def search_by_tag(self, tag: str, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        results: List[MemoryEntry] = []
        types = [memory_type] if memory_type else list(MemoryType)
        with self._lock:
            for mt in types:
                for entry in self._stores[mt].values():
                    if tag in entry.tags and not entry.is_expired:
                        results.append(entry)
        return sorted(results, key=lambda e: e.score, reverse=True)

    # ------------------------------------------------------------------
    # Pin
    # ------------------------------------------------------------------

    def pin(self, entry_id: str) -> bool:
        return self._change_type(entry_id, MemoryType.PINNED)

    def unpin(self, entry_id: str) -> bool:
        with self._lock:
            pinned = self._stores[MemoryType.PINNED].pop(entry_id, None)
            if pinned:
                pinned.memory_type = MemoryType.LONG_TERM
                self._stores[MemoryType.LONG_TERM][entry_id] = pinned
                self._save()
                return True
        return False

    # ------------------------------------------------------------------
    # Providers (external memory backends)
    # ------------------------------------------------------------------

    def register_provider(self, name: str, provider: MemoryProvider) -> None:
        with self._lock:
            self._providers[name] = provider

    def recall_from_provider(self, provider_name: str, key: str) -> Optional[str]:
        provider = self._providers.get(provider_name)
        if not provider:
            return None
        try:
            return provider(provider_name, key)
        except Exception as exc:
            logger.warning("Memory provider %s recall failed: %s", provider_name, exc)
            return None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def start_auto_cleanup(self, interval: Optional[float] = None) -> None:
        if interval:
            self._auto_cleanup_interval = interval
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True,
            name="memory-cleanup",
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        while True:
            time.sleep(self._auto_cleanup_interval)
            self.cleanup_expired()

    def cleanup_expired(self) -> int:
        count = 0
        with self._lock:
            for mt in [MemoryType.TEMPORARY, MemoryType.CONVERSATION]:
                store = self._stores[mt]
                expired = [eid for eid, e in store.items() if e.is_expired]
                for eid in expired:
                    del store[eid]
                    count += 1
        if count:
            self._save()
        return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        with self._lock:
            if memory_type:
                return len(self._stores[memory_type])
            return sum(len(s) for s in self._stores.values())

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {mt.value: len(store) for mt, store in self._stores.items()}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._storage_dir:
            return
        try:
            data = {}
            for mt in [MemoryType.CONVERSATION, MemoryType.PROJECT, MemoryType.LONG_TERM, MemoryType.PINNED]:
                store = self._stores[mt]
                if store:
                    data[mt.value] = {eid: e.to_dict() for eid, e in store.items()}
            path = self._storage_dir / "memory.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save memory: %s", exc)

    def _load(self) -> None:
        if not self._storage_dir:
            return
        path = self._storage_dir / "memory.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for mt_name, entries in data.items():
                try:
                    mt = MemoryType(mt_name)
                    for eid, raw in entries.items():
                        entry = MemoryEntry.from_dict(raw)
                        self._stores[mt][eid] = entry
                except ValueError:
                    pass
            logger.info("Loaded memory: %s", {mt.value: len(s) for mt, s in self._stores.items() if s})
        except Exception as exc:
            logger.warning("Failed to load memory: %s", exc)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_by_key(self, memory_type: MemoryType, key: str) -> Optional[MemoryEntry]:
        for entry in self._stores[memory_type].values():
            if entry.key == key:
                return entry
        return None

    def _enforce_max(self, memory_type: MemoryType) -> None:
        store = self._stores[memory_type]
        if len(store) > self._max_entries_per_type:
            sorted_entries = sorted(store.values(), key=lambda e: e.accessed_at)
            to_remove = len(store) - self._max_entries_per_type
            for entry in sorted_entries[:to_remove]:
                del store[entry.id]

    def _change_type(self, entry_id: str, target_type: MemoryType) -> bool:
        with self._lock:
            for mt in list(MemoryType):
                if mt == target_type:
                    continue
                entry = self._stores[mt].pop(entry_id, None)
                if entry:
                    entry.memory_type = target_type
                    entry.updated_at = time.time()
                    self._stores[target_type][entry_id] = entry
                    self._save()
                    return True
        return False

    def summary(self) -> str:
        s = self.stats()
        total = sum(s.values())
        parts = [f"Memory Runtime: {total} entries"]
        for mt_name, count in s.items():
            if count:
                parts.append(f"  {mt_name}: {count}")
        return "\n".join(parts)