"""Versioning & conflict detection for memory entries.

The fabric keeps a version history per entry id (append-only) and detects
conflicts — two entries that claim the same semantic key/fact with divergent
content — so the write pipeline can either bump a version (same author) or
flag a conflict for resolution instead of silently overwriting knowledge.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aetheros_memory_intelligence.schema import MemoryEntry


@dataclass
class EntryVersion:
    entry_id: str
    version: int
    content: str
    checksum: str
    created_at: float
    actor: str = ""

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "version": self.version,
            "content": self.content,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "actor": self.actor,
        }


@dataclass
class Conflict:
    key: str
    entry_a: str   # id
    entry_b: str   # id
    detected_at: float = field(default_factory=time.time)
    reason: str = ""


class VersionHistory:
    """Append-only per-entry version history."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: Dict[str, List[EntryVersion]] = {}

    def record(self, entry: MemoryEntry, actor: str = "") -> EntryVersion:
        with self._lock:
            versions = self._history.setdefault(entry.id, [])
            ver = EntryVersion(
                entry_id=entry.id,
                version=entry.version,
                content=entry.content,
                checksum=entry.checksum,
                created_at=time.time(),
                actor=actor,
            )
            versions.append(ver)
            return ver

    def history(self, entry_id: str) -> List[EntryVersion]:
        with self._lock:
            return list(self._history.get(entry_id, []))

    def version_count(self, entry_id: str) -> int:
        with self._lock:
            return len(self._history.get(entry_id, []))

    def truncate(self, entry_id: str, keep: int = 20) -> None:
        with self._lock:
            versions = self._history.get(entry_id)
            if versions and len(versions) > keep:
                self._history[entry_id] = versions[-keep:]


class ConflictDetector:
    """Finds entries that contradict on the same semantic key."""

    def __init__(self, *, enabled: bool = True, threshold: float = 0.6) -> None:
        self.enabled = enabled
        self.threshold = threshold
        self._conflicts: List[Conflict] = []
        self._lock = threading.RLock()

    def _similarity(self, a: str, b: str) -> float:
        """Token Jaccard similarity in [0,1]."""
        ta = set(a.lower().split())
        tb = set(b.lower().split())
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union

    def find_conflicts(self, candidates: List[MemoryEntry]) -> List[Conflict]:
        if not self.enabled or len(candidates) < 2:
            return []
        conflicts: List[Conflict] = []
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                a, b = candidates[i], candidates[j]
                key_a = a.metadata.get("semantic_key", "") or a.content[:80]
                key_b = b.metadata.get("semantic_key", "") or b.content[:80]
                same_key = bool(a.metadata.get("semantic_key") and
                                a.metadata.get("semantic_key") == b.metadata.get("semantic_key"))
                if not same_key:
                    continue
                sim = self._similarity(a.content, b.content)
                if sim < self.threshold:
                    conflicts.append(Conflict(
                        key=key_a, entry_a=a.id, entry_b=b.id,
                        reason=f"same semantic_key, similarity={sim:.2f}",
                    ))
        with self._lock:
            self._conflicts.extend(conflicts)
        return conflicts

    def all_conflicts(self) -> List[Conflict]:
        with self._lock:
            return list(self._conflicts)

    def resolve(self, conflict: Conflict, winner_id: str) -> None:
        """Record manual resolution of a conflict."""
        with self._lock:
            self._conflicts = [c for c in self._conflicts if c != conflict]