from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    TASK = "task"
    AGENT = "agent"
    PREFERENCE = "preference"
    DOCUMENT = "document"
    RESEARCH = "research"
    CONTACT = "contact"
    WORKFLOW = "workflow"
    TEMPORARY = "temporary"


class MemoryConfidence(str, Enum):
    EXPLICIT = "explicit"
    VERIFIED = "verified"
    INFERRED = "inferred"
    TEMPORARY = "temporary"


class RetentionPolicy(str, Enum):
    NEVER_DELETE = "never_delete"
    DELETE_AFTER_TIME = "delete_after_time"
    DELETE_AFTER_PROJECT = "delete_after_project"
    TEMPORARY = "temporary"
    USER_CONTROLLED = "user_controlled"


@dataclass
class MemoryEntry:
    id: str
    type: MemoryType
    key: str
    value: Any
    summary: str = ""
    source: str = ""
    source_id: str = ""
    confidence: MemoryConfidence = MemoryConfidence.INFERRED
    tags: list[str] = field(default_factory=list)
    space_id: str = "default"
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    expires_at: str = ""
    retention: RetentionPolicy = RetentionPolicy.USER_CONTROLLED
    retention_days: int = 0
    access_count: int = 0
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "key": self.key,
            "value": self.value if isinstance(self.value, str) else json.dumps(self.value, default=str),
            "summary": self.summary,
            "source": self.source,
            "source_id": self.source_id,
            "confidence": self.confidence.value,
            "tags": self.tags,
            "space_id": self.space_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed_at": self.last_accessed_at,
            "expires_at": self.expires_at,
            "retention": self.retention.value,
            "retention_days": self.retention_days,
            "access_count": self.access_count,
            "importance": self.importance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryEntry:
        value = data.get("value", "")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls(
            id=data["id"],
            type=MemoryType(data.get("type", "temporary")),
            key=data.get("key", ""),
            value=value,
            summary=data.get("summary", ""),
            source=data.get("source", ""),
            source_id=data.get("source_id", ""),
            confidence=MemoryConfidence(data.get("confidence", "inferred")),
            tags=data.get("tags", []),
            space_id=data.get("space_id", "default"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            last_accessed_at=data.get("last_accessed_at", ""),
            expires_at=data.get("expires_at", ""),
            retention=RetentionPolicy(data.get("retention", "user_controlled")),
            retention_days=data.get("retention_days", 0),
            access_count=data.get("access_count", 0),
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
        )


class UnifiedMemoryManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "memory_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = {}
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "memory_entries.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for item in data:
                    entry = MemoryEntry.from_dict(item)
                    self._entries[entry.id] = entry
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([e.to_dict() for e in self._entries.values()], indent=2, default=str),
            encoding="utf-8",
        )

    def _generate_id(self) -> str:
        import uuid
        return f"mem_{uuid.uuid4().hex[:12]}"

    def _clean_expired(self):
        now = datetime.now()
        expired_ids = []
        for eid, entry in self._entries.items():
            if entry.expires_at:
                try:
                    exp = datetime.fromisoformat(entry.expires_at)
                    if exp <= now:
                        expired_ids.append(eid)
                except (ValueError, TypeError):
                    pass
            if entry.retention == RetentionPolicy.DELETE_AFTER_TIME and entry.retention_days > 0 and entry.created_at:
                try:
                    created = datetime.fromisoformat(entry.created_at)
                    age = (now - created).days
                    if age >= entry.retention_days:
                        expired_ids.append(eid)
                except (ValueError, TypeError):
                    pass
        for eid in expired_ids:
            del self._entries[eid]
        if expired_ids:
            self._save()

    def remember(self, key: str, value: Any, type: MemoryType = MemoryType.TEMPORARY,
                 source: str = "", source_id: str = "",
                 confidence: MemoryConfidence = MemoryConfidence.INFERRED,
                 tags: list[str] | None = None, space_id: str = "default",
                 summary: str = "", importance: float = 0.5,
                 retention: RetentionPolicy = RetentionPolicy.USER_CONTROLLED,
                 retention_days: int = 0, ttl_seconds: int = 0) -> MemoryEntry:
        now = datetime.now().isoformat()
        expires_at = ""
        if ttl_seconds > 0:
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
        entry = MemoryEntry(
            id=self._generate_id(),
            type=type,
            key=key,
            value=value,
            summary=summary or (key if isinstance(key, str) else str(key)),
            source=source,
            source_id=source_id,
            confidence=confidence,
            tags=tags or [],
            space_id=space_id,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
            expires_at=expires_at,
            retention=retention,
            retention_days=retention_days,
            access_count=1,
            importance=importance,
        )
        self._entries[entry.id] = entry
        self._save()
        self._clean_expired()
        return entry

    def recall(self, key: str, space_id: str = "") -> Optional[MemoryEntry]:
        for entry in self._entries.values():
            if entry.key == key:
                if space_id and entry.space_id != space_id:
                    continue
                entry.access_count += 1
                entry.last_accessed_at = datetime.now().isoformat()
                self._save()
                return entry
        return None

    def forget(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False
        del self._entries[entry_id]
        self._save()
        return True

    def forget_by_key(self, key: str, space_id: str = "") -> int:
        ids = [eid for eid, e in self._entries.items() if e.key == key and (not space_id or e.space_id == space_id)]
        for eid in ids:
            del self._entries[eid]
        if ids:
            self._save()
        return len(ids)

    def forget_by_topic(self, topic: str, space_id: str = "") -> int:
        tl = topic.lower()
        ids = [eid for eid, e in self._entries.items()
               if (tl in e.key.lower() or tl in e.summary.lower() or any(tl in t.lower() for t in e.tags))
               and (not space_id or e.space_id == space_id)]
        for eid in ids:
            del self._entries[eid]
        if ids:
            self._save()
        return len(ids)

    def update_entry(self, entry_id: str, **updates) -> Optional[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if not entry:
            return None
        for key, value in updates.items():
            if hasattr(entry, key) and key != "id":
                if key == "type":
                    setattr(entry, key, MemoryType(value) if isinstance(value, str) else value)
                elif key == "confidence":
                    setattr(entry, key, MemoryConfidence(value) if isinstance(value, str) else value)
                elif key == "retention":
                    setattr(entry, key, RetentionPolicy(value) if isinstance(value, str) else value)
                else:
                    setattr(entry, key, value)
        entry.updated_at = datetime.now().isoformat()
        self._save()
        return entry

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(entry_id)

    def list_by_type(self, type: MemoryType, space_id: str = "") -> list[MemoryEntry]:
        results = [e for e in self._entries.values() if e.type == type]
        if space_id:
            results = [e for e in results if e.space_id == space_id]
        return sorted(results, key=lambda x: x.updated_at, reverse=True)

    def search(self, query: str = "", type: Optional[MemoryType] = None,
               tags: Optional[list[str]] = None, space_id: str = "",
               min_importance: float = 0.0) -> list[MemoryEntry]:
        results = list(self._entries.values())
        if query:
            q = query.lower()
            results = [e for e in results if q in e.key.lower() or q in e.summary.lower()
                       or q in str(e.value).lower()]
        if type:
            results = [e for e in results if e.type == type]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if space_id:
            results = [e for e in results if e.space_id == space_id]
        if min_importance > 0:
            results = [e for e in results if e.importance >= min_importance]
        return sorted(results, key=lambda x: (x.importance, x.access_count), reverse=True)

    def get_all(self, space_id: str = "") -> list[MemoryEntry]:
        results = list(self._entries.values())
        if space_id:
            results = [e for e in results if e.space_id == space_id]
        return sorted(results, key=lambda x: x.updated_at, reverse=True)

    def get_stats(self) -> dict:
        type_counts: dict[str, int] = {}
        for e in self._entries.values():
            t = e.type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        now = datetime.now()
        expired = 0
        for e in self._entries.values():
            if e.expires_at:
                try:
                    if datetime.fromisoformat(e.expires_at) <= now:
                        expired += 1
                except (ValueError, TypeError):
                    pass
        return {
            "total_entries": len(self._entries),
            "entries_by_type": type_counts,
            "expired": expired,
        }

    def clear_type(self, type: MemoryType, space_id: str = "") -> int:
        ids = [eid for eid, e in self._entries.items() if e.type == type and (not space_id or e.space_id == space_id)]
        for eid in ids:
            del self._entries[eid]
        if ids:
            self._save()
        return len(ids)

    def clear_space(self, space_id: str) -> int:
        ids = [eid for eid, e in self._entries.items() if e.space_id == space_id]
        for eid in ids:
            del self._entries[eid]
        if ids:
            self._save()
        return len(ids)

    def clear_all(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        self._save()
        return count
