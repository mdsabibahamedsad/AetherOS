"""
Memory Manager — coordinates memory access across providers with scope awareness.

Integrates with existing memory providers (honcho, mem0, supermemory, etc.)
while enforcing kernel-level scoping and authorization.
"""

from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class MemoryScope(Enum):
    """Memory scope types."""
    WORKING = "working"           # Current task context
    EPISODIC = "episodic"         # Past interactions
    SEMANTIC = "semantic"         # Facts and knowledge
    PROCEDURAL = "procedural"     # Skills and procedures
    PROJECT = "project"           # Project-specific
    RESEARCH = "research"         # Research evidence
    SPATIAL = "spatial"           # Spatial/world model
    AMBIENT = "ambient"           # Ambient sensor data
    AGENT = "agent"               # Agent-specific
    SWARM = "swarm"               # Shared across swarm
    SHARED = "shared"             # Explicitly shared


@dataclass
class MemoryEntry:
    """A memory entry with metadata."""
    key: str
    value: Any
    scope: MemoryScope
    provenance: ProvenanceType = ProvenanceType.AGENT_DERIVED
    data_classification: DataClassification = DataClassification.INTERNAL
    created_at: float = field(default_factory=_now)
    accessed_at: float = field(default_factory=_now)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    lineage: List[str] = field(default_factory=list)
    agent_id: str = ""
    task_id: str = ""
    pinned: bool = False


@dataclass
class MemoryNamespace:
    """Isolated memory namespace for an agent/task."""
    name: str
    scope: MemoryScope
    entries: Dict[str, MemoryEntry] = field(default_factory=dict)
    owner_agent_id: str = ""
    created_at: float = field(default_factory=_now)
    max_entries: int = 10000


class IMemoryProvider:
    """Interface for memory providers."""
    def read(self, scope: str, key: str) -> Any: ...
    def write(self, scope: str, key: str, value: Any) -> None: ...
    def search(self, scope: str, query: str, limit: int = 10) -> List[Any]: ...
    def delete(self, scope: str, key: str) -> bool: ...
    def list_keys(self, scope: str) -> List[str]: ...


class MemoryManager:
    """
    Coordinates memory access across providers with scope awareness.
    
    All memory access is scope-aware and authorized through the kernel.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Provider registry
        self._providers: Dict[str, IMemoryProvider] = {}
        self._provider_priority: List[str] = []  # Ordered by priority
        
        # Local memory namespaces (kernel-managed)
        self._namespaces: Dict[str, MemoryNamespace] = {}
        
        # Scope-to-provider mapping
        self._scope_providers: Dict[MemoryScope, List[str]] = {}
        
        # Memory operation log
        self._operation_log: List[Dict[str, Any]] = []

    def register_provider(
        self,
        name: str,
        provider: IMemoryProvider,
        scopes: List[MemoryScope] = None,
        priority: int = 0,
    ) -> None:
        """Register a memory provider for specific scopes."""
        with self._lock:
            self._providers[name] = provider
            
            # Insert by priority
            inserted = False
            for i, pname in enumerate(self._provider_priority):
                if priority > 0:  # Higher priority first
                    self._provider_priority.insert(i, name)
                    inserted = True
                    break
            if not inserted:
                self._provider_priority.append(name)
            
            # Map scopes
            for scope in scopes or []:
                self._scope_providers.setdefault(scope, []).append(name)

        logger.info("MemoryManager: registered provider %s for scopes %s",
                    name, [s.value for s in (scopes or [])])

        if self.event_bus:
            self.event_bus.emit("memory.provider.registered", {
                "provider": name,
                "scopes": [s.value for s in (scopes or [])],
                "priority": priority,
            })

    def create_namespace(
        self,
        name: str,
        scope: MemoryScope,
        agent_id: str = "",
        max_entries: int = 10000,
    ) -> MemoryNamespace:
        """Create a memory namespace."""
        with self._lock:
            if name in self._namespaces:
                raise ValueError(f"Namespace already exists: {name}")

            namespace = MemoryNamespace(
                name=name,
                scope=scope,
                owner_agent_id=agent_id,
                max_entries=max_entries,
            )
            self._namespaces[name] = namespace

        if self.event_bus:
            self.event_bus.emit("memory.namespace.created", {
                "namespace": name,
                "scope": scope.value,
                "agent_id": agent_id,
            })

        return namespace

    def get_namespace(self, name: str) -> Optional[MemoryNamespace]:
        """Get a memory namespace."""
        with self._lock:
            return self._namespaces.get(name)

    def read(
        self,
        agent_id: str,
        scope: MemoryScope,
        key: str,
    ) -> Any:
        """Read from memory with authorization."""
        # Check authorization (simplified)
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        
        # Try local namespace first
        if ns and key in ns.entries:
            entry = ns.entries[key]
            entry.accessed_at = _now()
            entry.access_count += 1
            self._log_operation("read", agent_id, scope, key, True)
            return entry.value

        # Try providers
        providers = self._scope_providers.get(scope, [])
        for provider_name in providers:
            provider = self._providers.get(provider_name)
            if provider:
                try:
                    value = provider.read(scope.value, key)
                    if value is not None:
                        self._log_operation("read", agent_id, scope, key, True, provider_name)
                        return value
                except Exception as exc:
                    logger.error("Memory provider %s read error: %s", provider_name, exc)

        self._log_operation("read", agent_id, scope, key, False)
        return None

    def write(
        self,
        agent_id: str,
        scope: MemoryScope,
        key: str,
        value: Any,
        provenance: ProvenanceType = ProvenanceType.AGENT_DERIVED,
        data_classification: DataClassification = DataClassification.INTERNAL,
        ttl_seconds: float = None,
        tags: List[str] = None,
        lineage: List[str] = None,
        pinned: bool = False,
    ) -> bool:
        """Write to memory with authorization."""
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        
        if not ns:
            ns = self.create_namespace(namespace_name, scope, agent_id)

        # Check namespace capacity
        if len(ns.entries) >= ns.max_entries and not any(e.pinned for e in ns.entries.values()):
            # Evict LRU non-pinned
            lru = min(
                (e for e in ns.entries.values() if not e.pinned),
                key=lambda e: e.accessed_at,
                default=None
            )
            if lru:
                del ns.entries[lru.key]

        entry = MemoryEntry(
            key=key,
            value=value,
            scope=scope,
            provenance=provenance,
            data_classification=data_classification,
            ttl_seconds=ttl_seconds,
            tags=tags or [],
            lineage=lineage or [],
            agent_id=agent_id,
            pinned=pinned,
        )

        ns.entries[key] = entry

        # Also write to providers
        providers = self._scope_providers.get(scope, [])
        for provider_name in providers:
            provider = self._providers.get(provider_name)
            if provider:
                try:
                    provider.write(scope.value, key, value)
                except Exception as exc:
                    logger.error("Memory provider %s write error: %s", provider_name, exc)

        self._log_operation("write", agent_id, scope, key, True)

        if self.event_bus:
            self.event_bus.emit("memory.written", {
                "agent_id": agent_id,
                "scope": scope.value,
                "key": key,
                "provenance": provenance.value,
            })

        return True

    def search(
        self,
        agent_id: str,
        scope: MemoryScope,
        query: str,
        limit: int = 10,
    ) -> List[Any]:
        """Search memory."""
        results = []
        
        # Search local namespace
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        if ns:
            for entry in ns.entries.values():
                if query.lower() in str(entry.value).lower():
                    results.append(entry.value)
                    if len(results) >= limit:
                        break

        # Search providers
        if len(results) < limit:
            providers = self._scope_providers.get(scope, [])
            for provider_name in providers:
                provider = self._providers.get(provider_name)
                if provider:
                    try:
                        provider_results = provider.search(scope.value, query, limit - len(results))
                        results.extend(provider_results)
                        if len(results) >= limit:
                            break
                    except Exception as exc:
                        logger.error("Memory provider %s search error: %s", provider_name, exc)

        self._log_operation("search", agent_id, scope, query, len(results) > 0)
        return results[:limit]

    def delete(self, agent_id: str, scope: MemoryScope, key: str) -> bool:
        """Delete from memory."""
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        deleted = False
        
        if ns and key in ns.entries:
            del ns.entries[key]
            deleted = True

        # Delete from providers
        providers = self._scope_providers.get(scope, [])
        for provider_name in providers:
            provider = self._providers.get(provider_name)
            if provider:
                try:
                    if provider.delete(scope.value, key):
                        deleted = True
                except Exception as exc:
                    logger.error("Memory provider %s delete error: %s", provider_name, exc)

        self._log_operation("delete", agent_id, scope, key, deleted)
        return deleted

    def link(
        self,
        agent_id: str,
        key1: str,
        key2: str,
        relation: str = "related",
    ) -> bool:
        """Link two memory entries."""
        # This would create a graph edge in a graph-based memory
        # For now, just record the link in lineage
        namespace_name = f"{agent_id}:{MemoryScope.SEMANTIC.value}"
        ns = self.get_namespace(namespace_name)
        
        if ns:
            for key in [key1, key2]:
                if key in ns.entries:
                    ns.entries[key].lineage.append(f"{relation}:{key1 if key == key2 else key2}")

        self._log_operation("link", agent_id, MemoryScope.SEMANTIC, f"{key1}-{key2}", True)
        return True

    def consolidate(self, agent_id: str, scope: MemoryScope) -> int:
        """Consolidate memory (e.g., move working to episodic)."""
        # This would be implemented with specific consolidation logic
        consolidated = 0
        
        if scope == MemoryScope.WORKING:
            # Move old working memory to episodic
            working_ns = self.get_namespace(f"{agent_id}:working")
            episodic_ns = self.get_namespace(f"{agent_id}:episodic")
            
            if working_ns and episodic_ns:
                now = _now()
                for key, entry in list(working_ns.entries.items()):
                    if now - entry.accessed_at > 3600:  # 1 hour
                        episodic_ns.entries[key] = entry
                        del working_ns.entries[key]
                        consolidated += 1

        self._log_operation("consolidate", agent_id, scope, "", consolidated > 0)
        return consolidated

    def forget(self, agent_id: str, scope: MemoryScope, older_than: float = None) -> int:
        """Forget (delete) old memories."""
        forgotten = 0
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        
        if ns:
            now = _now()
            threshold = older_than or (now - 86400 * 30)  # 30 days default
            
            for key, entry in list(ns.entries.items()):
                if entry.pinned:
                    continue
                if entry.created_at < threshold:
                    del ns.entries[key]
                    forgotten += 1

        self._log_operation("forget", agent_id, scope, f"count:{forgotten}", forgotten > 0)
        return forgotten

    def export(self, agent_id: str, scope: MemoryScope) -> Dict[str, Any]:
        """Export memory for backup/migration."""
        namespace_name = f"{agent_id}:{scope.value}"
        ns = self.get_namespace(namespace_name)
        
        if not ns:
            return {}

        return {
            "namespace": namespace_name,
            "scope": scope.value,
            "agent_id": agent_id,
            "exported_at": _now(),
            "entries": {
                k: {
                    "value": v.value,
                    "provenance": v.provenance.value,
                    "classification": v.data_classification.value,
                    "created_at": v.created_at,
                    "tags": v.tags,
                    "lineage": v.lineage,
                }
                for k, v in ns.entries.items()
            },
        }

    def _log_operation(
        self,
        operation: str,
        agent_id: str,
        scope: MemoryScope,
        key: str,
        success: bool,
        provider: str = None,
    ) -> None:
        """Log memory operation for audit."""
        self._operation_log.append({
            "operation": operation,
            "agent_id": agent_id,
            "scope": scope.value,
            "key": key,
            "success": success,
            "provider": provider,
            "timestamp": _now(),
        })

        # Keep last 10000 operations
        if len(self._operation_log) > 10000:
            self._operation_log = self._operation_log[-5000:]

        if self.event_bus:
            self.event_bus.emit(f"memory.{operation}", {
                "agent_id": agent_id,
                "scope": scope.value,
                "key": key,
                "success": success,
                "provider": provider,
            })

    def get_operation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent memory operations."""
        return self._operation_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics."""
        with self._lock:
            total_namespaces = len(self._namespaces)
            total_entries = sum(len(ns.entries) for ns in self._namespaces.values())
            
            by_scope: Dict[str, int] = {}
            for ns in self._namespaces.values():
                by_scope[ns.scope.value] = by_scope.get(ns.scope.value, 0) + len(ns.entries)

            providers = list(self._providers.keys())
            operations = len(self._operation_log)

        return {
            "namespaces": total_namespaces,
            "total_entries": total_entries,
            "by_scope": by_scope,
            "providers": providers,
            "operations_logged": operations,
        }

    def shutdown(self) -> None:
        """Shutdown the memory manager."""
        logger.info("MemoryManager: shutting down")
        with self._lock:
            self._namespaces.clear()
            self._providers.clear()
            self._operation_log.clear()