"""
Short-term Memory — ephemeral, in-progress conversation memory.

Short-term memory holds recent conversation context, current task state,
and intermediate results. It has limited capacity and data is promoted
to long-term memory when important enough.

Mirrors the concept of working memory in cognitive systems.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Ephemeral short-term memory with limited capacity.

    Holds recent context. Older/low-importance entries are automatically
    evicted when capacity is exceeded.

    Usage:
        stm = ShortTermMemory(store, capacity=50)
        stm.add("current_task", "Implement login")
        task = stm.get("current_task")
        stm.clear()
    """

    def __init__(self, store: MemoryStore, capacity: int = 100,
                 namespace: str = ""):
        self._store = store
        self._capacity = capacity
        self._namespace = namespace or f"short-term:{id(self)}"
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add(self, key: str, value: Any,
            tags: List[str] = None,
            importance: float = 0.5,
            ttl: float = 3600.0) -> MemoryEntry:
        """Add a short-term memory entry.

        Args:
            key: Namespaced key
            value: The value to store
            tags: Optional categorization tags
            importance: Importance score (0.0 - 1.0)
            ttl: Time-to-live in seconds (default 1 hour)

        Returns:
            The stored MemoryEntry
        """
        self._enforce_capacity()
        return self._store.save(
            key=key, value=value,
            memory_type="short_term",
            scope=MemoryScope.CONVERSATION,
            namespace=self._namespace,
            tags=tags or [],
            importance=importance,
            ttl=ttl,
            source="short_term",
        )

    def get(self, key: str) -> Any:
        """Get a value from short-term memory by key."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.CONVERSATION, namespace=self._namespace,
        )
        return entry.value if entry else None

    def get_entry(self, key: str) -> Optional[MemoryEntry]:
        """Get the full MemoryEntry by key."""
        return self._store.get_by_key(
            key, scope=MemoryScope.CONVERSATION, namespace=self._namespace,
        )

    def update(self, key: str, value: Any) -> bool:
        """Update a short-term memory value."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.CONVERSATION, namespace=self._namespace,
        )
        if entry:
            return self._store.update(entry.id, value=value)
        return self.add(key, value) is not None

    def delete(self, key: str) -> bool:
        """Delete a short-term memory entry."""
        return self._store.delete_by_key(
            key, scope=MemoryScope.CONVERSATION, namespace=self._namespace,
        )

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def add_many(self, items: Dict[str, Any],
                 importance: float = 0.5) -> int:
        """Add multiple entries at once."""
        count = 0
        for key, value in items.items():
            self.add(key, value, importance=importance)
            count += 1
        return count

    def get_all(self) -> Dict[str, Any]:
        """Get all short-term memory as a dict."""
        entries = self._store.search(
            memory_type="short_term",
            namespace=self._namespace,
            limit=self._capacity,
        )
        return {e.key: e.value for e in entries}

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get the most recent short-term entries."""
        entries = self._store.search(
            memory_type="short_term",
            namespace=self._namespace,
            limit=limit,
        )
        return entries

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """Evict oldest/lowest-importance entries if over capacity."""
        entries = self._store.search(
            memory_type="short_term",
            namespace=self._namespace,
            limit=self._capacity + 1,
        )
        if len(entries) >= self._capacity:
            # Remove the lowest-importance entry
            to_remove = min(entries, key=lambda e: (e.importance, e.created_at))
            self._store.delete(to_remove.id)

    def clear(self) -> int:
        """Clear all short-term memory. Returns count removed."""
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        """Get the number of short-term memory entries."""
        return self._store.count(namespace=self._namespace)

    def promote(self, key: str, importance: float = 0.8) -> bool:
        """Promote a short-term entry to higher importance (for later LTM promotion)."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.CONVERSATION, namespace=self._namespace,
        )
        if entry:
            return self._store.update(entry.id, importance=importance)
        return False
