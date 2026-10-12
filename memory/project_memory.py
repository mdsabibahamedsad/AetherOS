"""
Project Memory — persistent memory scoped to a specific project.

Project memory stores project-level information that persists across
workspace sessions and agent conversations. Each project gets its own
isolated namespace. Supports project-level context, decisions,
architecture records, and progress tracking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)


class ProjectMemory:
    """Memory scoped to a specific project.

    Provides persistent, project-scoped storage for:
      - Architecture decisions and rationale
      - Project context and requirements
      - Key design patterns and conventions
      - Progress tracking and milestones
      - Team and role information

    Usage:
        pm = ProjectMemory(store, project_id="my-app")
        pm.record_decision("Use FastAPI", "Better async support", "tech-stack")
        pm.set("architecture", {"pattern": "microservices"})
        arch = pm.get("architecture")
        decisions = pm.get_decisions()
    """

    def __init__(self, store: MemoryStore, project_id: str = ""):
        self._store = store
        self._project_id = project_id or f"project:{id(self)}"
        self._namespace = f"project:{self._project_id}"

    # ------------------------------------------------------------------
    # Key-value operations
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any,
            tags: List[str] = None,
            importance: float = 0.7) -> MemoryEntry:
        """Store a value in project memory."""
        return self._store.save(
            key=key, value=value,
            memory_type="project",
            scope=MemoryScope.PROJECT,
            namespace=self._namespace,
            tags=tags or [],
            importance=importance,
            source="project",
        )

    def get(self, key: str) -> Any:
        """Get a value from project memory."""
        entry = self._store.get_by_key(
            key, scope=MemoryScope.PROJECT, namespace=self._namespace,
        )
        return entry.value if entry else None

    def delete(self, key: str) -> bool:
        """Delete a project memory entry."""
        return self._store.delete_by_key(
            key, scope=MemoryScope.PROJECT, namespace=self._namespace,
        )

    # ------------------------------------------------------------------
    # Decision records
    # ------------------------------------------------------------------

    def record_decision(self, title: str, rationale: str,
                        category: str = "",
                        alternatives: List[str] = None) -> MemoryEntry:
        """Record an architectural or design decision."""
        decision = {
            "title": title,
            "rationale": rationale,
            "category": category,
            "alternatives": alternatives or [],
            "timestamp": __import__("time").time(),
        }
        return self.set(
            f"decision:{len(title)}",
            decision,
            tags=["decision", category] if category else ["decision"],
            importance=0.9,
        )

    def get_decisions(self, category: str = "") -> List[Dict[str, Any]]:
        """Get all recorded decisions, optionally filtered by category."""
        entries = self._store.search(
            memory_type="project",
            scope=MemoryScope.PROJECT,
            namespace=self._namespace,
            tags=["decision"],
            limit=100,
        )
        decisions = []
        for e in entries:
            if isinstance(e.value, dict) and e.value.get("category", "") == category:
                decisions.append(e.value)
            elif not category:
                decisions.append(e.value)
        return decisions

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def set_context(self, key: str, value: Any) -> MemoryEntry:
        """Store project context (tagged as 'context')."""
        return self.set(key, value, tags=["context"], importance=0.8)

    def get_context(self) -> Dict[str, Any]:
        """Get all project context."""
        entries = self.search(tags=["context"], limit=100)
        return {e.key: e.value for e in entries}

    def get_all(self) -> Dict[str, Any]:
        """Get all project memory."""
        entries = self._store.search(
            memory_type="project",
            scope=MemoryScope.PROJECT,
            namespace=self._namespace,
            limit=1000,
        )
        return {e.key: e.value for e in entries}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str = "",
               tags: List[str] = None,
               limit: int = 50) -> List[MemoryEntry]:
        """Search within project memory."""
        return self._store.search(
            query=query, memory_type="project",
            scope=MemoryScope.PROJECT, namespace=self._namespace,
            tags=tags, limit=limit,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        return self._store.count(namespace=self._namespace)
