from __future__ import annotations

import os
import json
import time
import uuid
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    id: str
    type: str
    key: str
    content: Any
    timestamp: float
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class PersistentMemory:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "jarvis" / "memory.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._entries: dict[str, MemoryEntry] = {}
        self._key_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._load()

    def _load(self):
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text())
                for entry_data in data:
                    entry = MemoryEntry(**entry_data)
                    self._entries[entry.id] = entry
                    self._index_entry(entry)
        except Exception as e:
            logger.debug(f"Could not load memory: {e}")

    def _save(self):
        try:
            data = [{
                "id": e.id, "type": e.type, "key": e.key,
                "content": e.content, "timestamp": e.timestamp,
                "metadata": e.metadata, "tags": e.tags,
            } for e in self._entries.values()]
            self._storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Could not save memory: {e}")

    def _index_entry(self, entry: MemoryEntry):
        self._key_index.setdefault(entry.key, []).append(entry.id)
        for tag in entry.tags:
            self._tag_index.setdefault(tag, []).append(entry.id)

    def _deindex_entry(self, entry: MemoryEntry):
        if entry.key in self._key_index:
            ids = self._key_index[entry.key]
            if entry.id in ids:
                ids.remove(entry.id)
        for tag in entry.tags:
            if tag in self._tag_index:
                ids = self._tag_index[tag]
                if entry.id in ids:
                    ids.remove(entry.id)

    def remember(self, key: str, content: Any, type: str = "fact",
                 tags: Optional[list[str]] = None,
                 metadata: Optional[dict] = None) -> MemoryEntry:
        entry = MemoryEntry(
            id=f"mem-{uuid.uuid4().hex[:12]}",
            type=type,
            key=key,
            content=content,
            timestamp=time.time(),
            tags=tags or [],
            metadata=metadata or {},
        )
        with self._lock:
            self._entries[entry.id] = entry
            self._index_entry(entry)
            self._save()
        return entry

    def recall(self, key: str) -> Optional[MemoryEntry]:
        with self._lock:
            ids = self._key_index.get(key, [])
            if ids:
                entry = self._entries.get(ids[-1])
                if entry:
                    return entry
            return None

    def forget(self, key: str) -> bool:
        with self._lock:
            ids = self._key_index.get(key, [])
            removed = False
            for eid in ids:
                entry = self._entries.pop(eid, None)
                if entry:
                    self._deindex_entry(entry)
                    removed = True
            if removed:
                self._save()
            return removed

    def search(self, query: str, type: Optional[str] = None,
               tags: Optional[list[str]] = None,
               limit: int = 20) -> list[MemoryEntry]:
        query = query.lower()
        results = []
        with self._lock:
            for entry in self._entries.values():
                if type and entry.type != type:
                    continue
                if tags and not all(t in entry.tags for t in tags):
                    continue
                if query in entry.key.lower() or query in str(entry.content).lower():
                    results.append(entry)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_all(self) -> list[MemoryEntry]:
        with self._lock:
            return sorted(self._entries.values(), key=lambda e: e.timestamp, reverse=True)

    def get_by_type(self, type: str) -> list[MemoryEntry]:
        with self._lock:
            return sorted(
                [e for e in self._entries.values() if e.type == type],
                key=lambda e: e.timestamp, reverse=True,
            )

    def get_stats(self) -> dict:
        with self._lock:
            types = {}
            for e in self._entries.values():
                types[e.type] = types.get(e.type, 0) + 1
            return {
                "total": len(self._entries),
                "types": types,
                "tags": {t: len(ids) for t, ids in self._tag_index.items()},
            }

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._key_index.clear()
            self._tag_index.clear()
            self._save()

    def seed_default(self):
        defaults = [
            ("preference:theme", "dark", "preference", ["theme"]),
            ("preference:language", "python", "preference", ["language"]),
            ("system:first_run", True, "system", ["boot"]),
        ]
        for key, content, type, tags in defaults:
            if not self.recall(key):
                self.remember(key, content, type=type, tags=tags)
