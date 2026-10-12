"""
Context Manager — OS-style context allocation and coordination.

Manages finite context resources with allocation, compression, prioritization,
eviction, restoration, snapshots, lineage, and provenance.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ContextClass(Enum):
    """Context priority classes for eviction."""
    CRITICAL = "critical"      # Never evict
    HIGH = "high"              # Evict last
    NORMAL = "normal"          # Standard eviction
    LOW = "low"                # Evict first
    EPHEMERAL = "ephemeral"    # Auto-evict after TTL
    DERIVED = "derived"        # Can be recomputed
    UNTRUSTED = "untrusted"    # External content, never authoritative
    SENSITIVE = "sensitive"    # Requires special handling
    PRIVATE = "private"        # User-private
    PUBLIC = "public"          # Shareable


@dataclass
class ContextEntry:
    """A context entry with metadata."""
    key: str
    value: Any
    context_class: ContextClass = ContextClass.NORMAL
    provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED
    data_classification: DataClassification = DataClassification.INTERNAL
    created_at: float = field(default_factory=_now)
    accessed_at: float = field(default_factory=_now)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_estimate: int = 0  # Rough token estimate
    tags: List[str] = field(default_factory=list)
    lineage: List[str] = field(default_factory=list)  # Derived from keys
    pinned: bool = False  # Never evict if pinned


@dataclass
class ContextNamespace:
    """Isolated context namespace."""
    name: str
    entries: Dict[str, ContextEntry] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    owner_agent_id: str = ""
    max_size: int = 32000  # Token budget
    current_size: int = 0


class ContextManager:
    """
    Manages context allocation across agents and tasks.
    
    Context is a finite resource. The manager implements:
    - Allocation with budgets
    - Compression and summarization
    - Prioritized eviction
    - Restoration from checkpoints
    - Lineage tracking
    - Provenance tracking
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._namespaces: Dict[str, ContextNamespace] = {}
        self._global_context = ContextNamespace(name="global", max_size=100000)
        self._compression_strategies: Dict[str, Callable] = {}
        self._eviction_callbacks: List[Callable[[ContextEntry], bool]] = []

        # Register default compression
        self._register_default_compression()

    def _register_default_compression(self) -> None:
        """Register default compression strategies."""
        self._compression_strategies["summarize"] = self._compress_summarize
        self._compression_strategies["truncate"] = self._compress_truncate
        self._compression_strategies["extract_key"] = self._compress_extract_key

    def register_compression_strategy(self, name: str, strategy: Callable) -> None:
        """Register a custom compression strategy."""
        self._compression_strategies[name] = strategy

    def register_eviction_callback(self, callback: Callable[[ContextEntry], bool]) -> None:
        """Register a callback for eviction decisions."""
        self._eviction_callbacks.append(callback)

    def create_namespace(
        self,
        name: str,
        agent_id: str = "",
        max_size: int = None,
    ) -> ContextNamespace:
        """Create a new context namespace."""
        with self._lock:
            if name in self._namespaces:
                raise ValueError(f"Namespace already exists: {name}")

            namespace = ContextNamespace(
                name=name,
                owner_agent_id=agent_id,
                max_size=max_size or self.config.default_context_budget,
            )
            self._namespaces[name] = namespace

        if self.event_bus:
            self.event_bus.emit("context.namespace.created", {
                "namespace": name,
                "agent_id": agent_id,
                "max_size": namespace.max_size,
            })

        return namespace

    def get_namespace(self, name: str) -> Optional[ContextNamespace]:
        """Get a namespace by name."""
        with self._lock:
            return self._namespaces.get(name)

    def set_context(
        self,
        namespace: str,
        key: str,
        value: Any,
        context_class: ContextClass = ContextClass.NORMAL,
        provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED,
        data_classification: DataClassification = DataClassification.INTERNAL,
        ttl_seconds: float = None,
        tags: List[str] = None,
        lineage: List[str] = None,
        pinned: bool = False,
    ) -> bool:
        """Set a context value."""
        ns = self.get_namespace(namespace)
        if not ns:
            # Try global namespace
            ns = self._global_context
            namespace = "global"

        # Estimate size (rough token count)
        size_estimate = self._estimate_size(value)

        # Check budget
        if ns.current_size + size_estimate > ns.max_size:
            # Try to evict
            if not self._evict_to_fit(ns, size_estimate):
                logger.warning("Context budget exceeded for namespace %s", namespace)
                return False

        entry = ContextEntry(
            key=key,
            value=value,
            context_class=context_class,
            provenance=provenance,
            data_classification=data_classification,
            ttl_seconds=ttl_seconds,
            size_estimate=size_estimate,
            tags=tags or [],
            lineage=lineage or [],
            pinned=pinned,
        )

        # Remove old entry if exists
        old_entry = ns.entries.get(key)
        if old_entry:
            ns.current_size -= old_entry.size_estimate

        ns.entries[key] = entry
        ns.current_size += size_estimate

        if self.event_bus:
            self.event_bus.emit("context.set", {
                "namespace": namespace,
                "key": key,
                "size": size_estimate,
                "class": context_class.value,
            })

        return True

    def get_context(self, namespace: str, key: str) -> Any:
        """Get a context value."""
        ns = self.get_namespace(namespace)
        if not ns:
            ns = self._global_context
            namespace = "global"

        entry = ns.entries.get(key)
        if not entry:
            return None

        # Check TTL
        if entry.ttl_seconds and (_now() - entry.created_at) > entry.ttl_seconds:
            self.delete_context(namespace, key)
            return None

        # Update access stats
        entry.accessed_at = _now()
        entry.access_count += 1

        return entry.value

    def get_context_entry(self, namespace: str, key: str) -> Optional[ContextEntry]:
        """Get full context entry with metadata."""
        ns = self.get_namespace(namespace)
        if not ns:
            ns = self._global_context
            namespace = "global"
        return ns.entries.get(key)

    def delete_context(self, namespace: str, key: str) -> bool:
        """Delete a context entry."""
        ns = self.get_namespace(namespace)
        if not ns:
            ns = self._global_context
            namespace = "global"

        entry = ns.entries.pop(key, None)
        if entry:
            ns.current_size -= entry.size_estimate
            return True
        return False

    def list_keys(self, namespace: str) -> List[str]:
        """List all keys in a namespace."""
        ns = self.get_namespace(namespace)
        if not ns:
            return []
        return list(ns.entries.keys())

    def get_all_context(self, namespace: str) -> Dict[str, Any]:
        """Get all context values in a namespace."""
        ns = self.get_namespace(namespace)
        if not ns:
            return {}
        return {k: v.value for k, v in ns.entries.items()}

    def compress_context(
        self,
        namespace: str,
        strategy: str = "summarize",
        target_size: int = None,
    ) -> int:
        """Compress context in a namespace."""
        ns = self.get_namespace(namespace)
        if not ns:
            return 0

        compressor = self._compression_strategies.get(strategy)
        if not compressor:
            raise ValueError(f"Unknown compression strategy: {strategy}")

        target = target_size or (ns.max_size // 2)
        compressed = compressor(ns, target)
        
        if self.event_bus:
            self.event_bus.emit("context.compressed", {
                "namespace": namespace,
                "strategy": strategy,
                "compressed_entries": compressed,
                "new_size": ns.current_size,
            })

        return compressed

    def _compress_summarize(self, ns: ContextNamespace, target_size: int) -> int:
        """Compress by summarizing low-priority entries."""
        compressed = 0
        # Sort by class (ephemeral first), then by access time
        entries = sorted(
            ns.entries.values(),
            key=lambda e: (e.context_class.value, e.accessed_at)
        )

        for entry in entries:
            if ns.current_size <= target_size:
                break
            if entry.pinned or entry.context_class == ContextClass.CRITICAL:
                continue

            # Compress the value
            if isinstance(entry.value, str) and len(entry.value) > 500:
                summary = f"[SUMMARIZED: {len(entry.value)} chars] {entry.value[:200]}...{entry.value[-100:]}"
                old_size = entry.size_estimate
                entry.value = summary
                entry.size_estimate = self._estimate_size(summary)
                entry.context_class = ContextClass.DERIVED
                entry.lineage.append(f"compressed_from:{entry.key}")
                ns.current_size = ns.current_size - old_size + entry.size_estimate
                compressed += 1

        return compressed

    def _compress_truncate(self, ns: ContextNamespace, target_size: int) -> int:
        """Compress by truncating large entries."""
        compressed = 0
        for entry in ns.entries.values():
            if ns.current_size <= target_size:
                break
            if entry.pinned or entry.context_class == ContextClass.CRITICAL:
                continue
            if isinstance(entry.value, str) and len(entry.value) > 1000:
                truncated = entry.value[:500] + f"... [TRUNCATED {len(entry.value)} chars] ..."
                old_size = entry.size_estimate
                entry.value = truncated
                entry.size_estimate = self._estimate_size(truncated)
                ns.current_size = ns.current_size - old_size + entry.size_estimate
                compressed += 1
        return compressed

    def _compress_extract_key(self, ns: ContextNamespace, target_size: int) -> int:
        """Compress by extracting key information."""
        compressed = 0
        for entry in ns.entries.values():
            if ns.current_size <= target_size:
                break
            if entry.pinned or entry.context_class == ContextClass.CRITICAL:
                continue
            if isinstance(entry.value, dict):
                # Keep only keys, not values
                keys = list(entry.value.keys())
                extracted = f"[KEYS: {', '.join(keys)}]"
                old_size = entry.size_estimate
                entry.value = extracted
                entry.size_estimate = self._estimate_size(extracted)
                entry.context_class = ContextClass.DERIVED
                ns.current_size = ns.current_size - old_size + entry.size_estimate
                compressed += 1
        return compressed

    def _evict_to_fit(self, ns: ContextNamespace, needed: int) -> bool:
        """Evict entries to make room."""
        # Sort by eviction priority: EPHEMERAL > LOW > NORMAL > HIGH > CRITICAL
        eviction_order = [
            ContextClass.EPHEMERAL,
            ContextClass.LOW,
            ContextClass.UNTRUSTED,
            ContextClass.DERIVED,
            ContextClass.NORMAL,
            ContextClass.HIGH,
            ContextClass.SENSITIVE,
            ContextClass.PRIVATE,
            ContextClass.CRITICAL,
        ]

        for cls in eviction_order:
            candidates = [
                e for e in ns.entries.values()
                if e.context_class == cls and not e.pinned
            ]
            candidates.sort(key=lambda e: e.accessed_at)  # LRU

            for entry in candidates:
                if ns.current_size + needed <= ns.max_size:
                    return True

                # Check eviction callbacks
                can_evict = True
                for callback in self._eviction_callbacks:
                    if not callback(entry):
                        can_evict = False
                        break

                if can_evict:
                    ns.current_size -= entry.size_estimate
                    del ns.entries[entry.key]
                    
                    if self.event_bus:
                        self.event_bus.emit("context.evicted", {
                            "namespace": ns.name,
                            "key": entry.key,
                            "class": entry.context_class.value,
                            "reason": "budget",
                        })

        return ns.current_size + needed <= ns.max_size

    def _estimate_size(self, value: Any) -> int:
        """Rough token estimate for a value."""
        if isinstance(value, str):
            return len(value) // 4  # ~4 chars per token
        elif isinstance(value, dict):
            return sum(self._estimate_size(v) for v in value.values()) + len(value) * 10
        elif isinstance(value, list):
            return sum(self._estimate_size(v) for v in value) + len(value) * 5
        else:
            return len(str(value)) // 4

    def create_snapshot(self, namespace: str) -> Dict[str, Any]:
        """Create a snapshot of a namespace."""
        ns = self.get_namespace(namespace)
        if not ns:
            return {}

        return {
            "namespace": namespace,
            "snapshot_id": new_id("snap"),
            "timestamp": _now(),
            "entries": {
                k: {
                    "value": v.value,
                    "class": v.context_class.value,
                    "provenance": v.provenance.value,
                    "classification": v.data_classification.value,
                    "created_at": v.created_at,
                    "size": v.size_estimate,
                    "tags": v.tags,
                    "lineage": v.lineage,
                    "pinned": v.pinned,
                }
                for k, v in ns.entries.items()
            },
            "total_size": ns.current_size,
        }

    def restore_snapshot(self, namespace: str, snapshot: Dict[str, Any]) -> bool:
        """Restore a namespace from a snapshot."""
        ns = self.get_namespace(namespace)
        if not ns:
            return False

        # Clear current
        ns.entries.clear()
        ns.current_size = 0

        # Restore entries
        for key, data in snapshot.get("entries", {}).items():
            entry = ContextEntry(
                key=key,
                value=data["value"],
                context_class=ContextClass(data["class"]),
                provenance=ProvenanceType(data["provenance"]),
                data_classification=DataClassification(data["classification"]),
                created_at=data["created_at"],
                size_estimate=data["size"],
                tags=data.get("tags", []),
                lineage=data.get("lineage", []),
                pinned=data.get("pinned", False),
            )
            ns.entries[key] = entry
            ns.current_size += entry.size_estimate

        return True

    def prune_expired(self) -> int:
        """Remove all expired entries across namespaces."""
        count = 0
        now = _now()
        
        for ns in list(self._namespaces.values()) + [self._global_context]:
            expired = [
                k for k, v in ns.entries.items()
                if v.ttl_seconds and (now - v.created_at) > v.ttl_seconds
            ]
            for key in expired:
                entry = ns.entries.pop(key)
                ns.current_size -= entry.size_estimate
                count += 1

        if count > 0:
            logger.debug("ContextManager: pruned %d expired entries", count)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        with self._lock:
            total_namespaces = len(self._namespaces)
            total_entries = sum(len(ns.entries) for ns in self._namespaces.values())
            total_entries += len(self._global_context.entries)
            total_size = sum(ns.current_size for ns in self._namespaces.values())
            total_size += self._global_context.current_size

            by_class: Dict[str, int] = {}
            for ns in list(self._namespaces.values()) + [self._global_context]:
                for entry in ns.entries.values():
                    by_class[entry.context_class.value] = by_class.get(entry.context_class.value, 0) + 1

        return {
            "namespaces": total_namespaces,
            "total_entries": total_entries,
            "total_size_estimate": total_size,
            "by_class": by_class,
            "global_namespace_size": self._global_context.current_size,
        }

    def shutdown(self) -> None:
        """Shutdown the context manager."""
        logger.info("ContextManager: shutting down")
        with self._lock:
            self._namespaces.clear()
            self._global_context.entries.clear()