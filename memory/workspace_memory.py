"""
Workspace Memory — memory scoped to a specific workspace.

Each workspace gets an isolated memory namespace. Information stored
in workspace memory is only visible to agents operating within that
workspace. Supports workspace-level context, file relationships,
project state, and agent state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)


class WorkspaceMemory:
    """Memory scoped to a specific workspace.

    Provides an isolated memory namespace for each workspace.
    Supports context, file state, agent state, and task state.

    Usage:
        wm = WorkspaceMemory(store, workspace_id="my-project")
        wm.set("current_task", "Implement login")
        task = wm.get("current_task")
        context = wm.get_context()  # Get all context bundled
    """

    def __init__(self, store: MemoryStore, workspace_id: str = ""):
        self._store = store
        self._workspace_id = workspace_id or f"workspace:{id(self)}"
        self._namespace = f"workspace:{self._workspace_id}"

    # ------------------------------------------------------------------
    # Key-value operations
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any,
            tags: List[str] = None,
            importance: float = 0.5) -> MemoryEntry:
        """Store a workspace-scoped memory entry."""
        return self._store.save(
            key=key, value=value,
            memory_type="workspace",
            scope=MemoryScope.WORKSPACE,
            namespace=self._namespace,
            tags=tags or [],
            importance=importance,
            source="workspace",
        )

    def get(self, key: str) -> Any:
        """Get a value from workspace memory."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.WORKSPACE, namespace=self._namespace,
        )
        return entry.value if entry else None

    def delete(self, key: str) -> bool:
        """Delete a workspace memory entry."""
        return self._store.delete_by_key(
            key, scope=MemoryScope.WORKSPACE, namespace=self._namespace,
        )

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def set_context(self, key: str, value: Any) -> MemoryEntry:
        """Store context information (tagged as 'context')."""
        return self.set(key, value, tags=["context"], importance=0.7)

    def get_context(self) -> Dict[str, Any]:
        """Get all workspace context as a dict."""
        entries = self._store.search(
            memory_type="workspace",
            scope=MemoryScope.WORKSPACE,
            namespace=self._namespace,
            tags=["context"],
            limit=100,
        )
        return {e.key: e.value for e in entries}

    def get_all(self) -> Dict[str, Any]:
        """Get all workspace memory as a dict."""
        entries = self._store.search(
            memory_type="workspace",
            scope=MemoryScope.WORKSPACE,
            namespace=self._namespace,
            limit=1000,
        )
        return {e.key: e.value for e in entries}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str = "", limit: int = 50) -> List[MemoryEntry]:
        """Search within workspace memory."""
        return self._store.search(
            query=query,
            memory_type="workspace",
            scope=MemoryScope.WORKSPACE,
            namespace=self._namespace,
            limit=limit,
        )

    def get_relevant(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Get workspace context relevant to a query."""
        entries = self.search(query=query, limit=limit)
        return {e.key: e.value for e in entries}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        """Clear all workspace memory. Returns count removed."""
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        """Count workspace memory entries."""
        return self._store.count(namespace=self._namespace)
