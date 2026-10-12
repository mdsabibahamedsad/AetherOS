"""Scope-isolated retrieval cache.

Caching is a risk surface: a shared cache keyed only by query would leak one
user's results to another, and stale cache could serve content that was later
poisoned/removed.  The cache key therefore includes the FULL access scope
(user/workspace/session/agent) and the query, and cache entries carry the
entry ids they were built from so invalidation is precise.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.boundaries import AccessContext
from aetheros_memory_intelligence.retrieval import RetrievalResult


@dataclass
class CacheEntry:
    key: str
    result: RetrievalResult
    entry_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class ScopeIsolatedCache:
    """LRU cache with scope-isolated keys and precise invalidation."""

    def __init__(self, *, ttl_seconds: int = 300, max_size: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._lock = threading.RLock()
        self._cache: Dict[str, CacheEntry] = {}
        self._order: List[str] = []
        self._entry_index: Dict[str, List[str]] = {}  # entry_id -> keys

    # ------------------------------------------------------------------

    @staticmethod
    def _scope_salt(actor: AccessContext) -> str:
        return "|".join([actor.user_id or "", actor.workspace_id or "",
                         actor.session_id or "", actor.agent_id or ""])

    def _key(self, actor: AccessContext, query: str, *extra: str) -> str:
        payload = self._scope_salt(actor) + "::" + query + "::" + "::".join(extra)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, actor: AccessContext, query: str, *extra: str) -> Optional[RetrievalResult]:
        key = self._key(actor, query, *extra)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() - entry.created_at > self.ttl_seconds:
                self._remove(key)
                return None
            entry.hits += 1
            return entry.result

    def put(self, actor: AccessContext, query: str, result: RetrievalResult, *extra: str) -> None:
        if not result.memories:
            return  # don't cache empty results
        key = self._key(actor, query, *extra)
        entry_ids = [m.id for m in result.memories]
        with self._lock:
            self._evict_if_full()
            self._cache[key] = CacheEntry(key=key, result=result, entry_ids=entry_ids)
            if key in self._order:
                self._order.remove(key)
            self._order.append(key)
            for eid in entry_ids:
                self._entry_index.setdefault(eid, [])
                if key not in self._entry_index[eid]:
                    self._entry_index[eid].append(key)

    def invalidate(self, entry_ids: List[str]) -> int:
        """Remove any cache entry that was built from these entry ids."""
        removed = 0
        with self._lock:
            keys = set()
            for eid in entry_ids:
                keys.update(self._entry_index.pop(eid, []))
            for key in keys:
                if key in self._cache:
                    self._remove(key)
                    removed += 1
        return removed

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()
            self._order.clear()
            self._entry_index.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_hits = sum(e.hits for e in self._cache.values())
            return {
                "entries": len(self._cache),
                "total_hits": total_hits,
                "indexed_entry_ids": len(self._entry_index),
            }

    def _remove(self, key: str) -> None:
        entry = self._cache.pop(key, None)
        if entry is None:
            return
        if key in self._order:
            self._order.remove(key)
        for eid in entry.entry_ids:
            keys = self._entry_index.get(eid, [])
            if key in keys:
                keys.remove(key)
                if not keys:
                    self._entry_index.pop(eid, None)

    def _evict_if_full(self) -> None:
        while len(self._cache) >= self.max_size and self._order:
            oldest = self._order.pop(0)
            self._remove(oldest)