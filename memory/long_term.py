"""
Long-term Memory — persistent, durable storage for important information.

Long-term memory holds information that survives across sessions.
Entries are promoted from short-term memory when they reach sufficient
importance or are explicitly pinned. Supports archival and retrieval
by various dimensions.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)


class LongTermMemory:
    """Persistent long-term memory storage.

    Information stored here survives across sessions and is used for
    learning, context building, and knowledge retention.

    Usage:
        ltm = LongTermMemory(store, namespace="user-1")
        ltm.store("user_preferences", {"theme": "dark"}, importance=0.9)
        prefs = ltm.recall("user_preferences")
        results = ltm.search("preferences")
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"long-term:{id(self)}"

    # ------------------------------------------------------------------
    # Store / Recall
    # ------------------------------------------------------------------

    def store(self, key: str, value: Any,
              tags: List[str] = None,
              metadata: Dict[str, Any] = None,
              importance: float = 0.7,
              source: str = "user") -> MemoryEntry:
        """Store a value in long-term memory.

        Args:
            key: Unique key for the memory
            value: The value to store (JSON-serializable)
            tags: Categorization tags
            metadata: Additional metadata
            importance: Importance (0.0-1.0). Higher = more durable.
            source: Source identifier

        Returns:
            The stored MemoryEntry
        """
        return self._store.save(
            key=key, value=value,
            memory_type="long_term",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=tags or [],
            metadata=metadata or {},
            importance=importance,
            source=source,
        )

    def recall(self, key: str) -> Any:
        """Recall a value by key from long-term memory."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        return entry.value if entry else None

    def recall_entry(self, key: str) -> Optional[MemoryEntry]:
        """Get the full MemoryEntry by key."""
        return self._store.get_by_key(
            key, scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )

    def update(self, key: str, value: Any) -> bool:
        """Update a long-term memory value."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        if entry:
            return self._store.update(entry.id, value=value)
        return False

    def forget(self, key: str) -> bool:
        """Delete a long-term memory entry."""
        return self._store.delete_by_key(
            key, scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )

    # ------------------------------------------------------------------
    # Search & query
    # ------------------------------------------------------------------

    def search(self, query: str = "",
               tags: List[str] = None,
               limit: int = 50) -> List[MemoryEntry]:
        """Search long-term memory by query text and/or tags."""
        return self._store.search(
            query=query,
            memory_type="long_term",
            namespace=self._namespace,
            tags=tags,
            limit=limit,
        )

    def list_by_tags(self, tags: List[str],
                     limit: int = 50) -> List[MemoryEntry]:
        """List entries matching one or more tags."""
        return self.search(tags=tags, limit=limit)

    def list_important(self, min_importance: float = 0.8,
                       limit: int = 20) -> List[MemoryEntry]:
        """List entries above a minimum importance threshold."""
        entries = self._store.search(
            memory_type="long_term",
            namespace=self._namespace,
            limit=100,
        )
        return [e for e in entries if e.importance >= min_importance][:limit]

    def list_all(self, limit: int = 100) -> List[MemoryEntry]:
        """List all long-term memory entries."""
        return self._store.search(
            memory_type="long_term",
            namespace=self._namespace,
            limit=limit,
        )

    def count(self) -> int:
        """Count long-term memory entries."""
        return self._store.count(
            namespace=self._namespace,
            scope=MemoryScope.GLOBAL,
        )

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def store_many(self, items: Dict[str, Any],
                   importance: float = 0.7) -> int:
        """Store multiple key-value pairs at once."""
        count = 0
        for key, value in items.items():
            self.store(key, value, importance=importance)
            count += 1
        return count

    def promote_from_stm(self, key: str, value: Any,
                         importance: float = 0.8) -> MemoryEntry:
        """Promote information from short-term to long-term memory."""
        return self.store(key, value, importance=importance,
                         tags=["promoted"], source="stm_promotion")

    def clear(self) -> int:
        """Delete all long-term memory entries. Returns count."""
        return self._store.clear_namespace(self._namespace)
