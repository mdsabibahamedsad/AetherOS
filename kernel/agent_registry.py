"""
Agent Registry — full metadata registry for every agent in the system.

Every agent has:
  - Unique ID
  - Name
  - Description
  - Capabilities
  - Priority
  - Dependencies
  - Permissions
  - Supported Models
  - Cost Estimate
  - Latency
  - Health Status
  - Version
  - Tags
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.agent_manager import (
    AgentMetadata, AgentInstance, AgentLifecycleStatus, AgentHealthStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class RegistryEntry:
    id: str = ""
    name: str = ""
    type: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    priority: int = 50
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    supported_models: List[str] = field(default_factory=list)
    cost_estimate_per_run: float = 0.0
    average_latency_ms: float = 0.0
    max_concurrent_tasks: int = 1
    health: str = "unknown"
    status: str = "registered"
    tags: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """Full metadata registry for every agent in the system.

    Provides query, search, and filter capabilities across all
    registered agents with complete metadata.

    Usage:
        registry = AgentRegistry()
        registry.register(agent_instance)
        entry = registry.get("agent-1")
        results = registry.find_by_capability("research")
        results = registry.search(name="research", priority_min=30)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._entries: Dict[str, RegistryEntry] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._capability_index: Dict[str, Set[str]] = {}
        self._model_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._version_history: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, instance: AgentInstance) -> RegistryEntry:
        meta = instance.metadata
        entry = RegistryEntry(
            id=meta.id,
            name=meta.name,
            type=meta.type,
            version=meta.version,
            description=meta.description,
            capabilities=list(meta.capabilities),
            priority=meta.priority,
            dependencies=list(meta.dependencies),
            permissions=list(meta.permissions),
            supported_models=list(meta.supported_models),
            cost_estimate_per_run=meta.cost_estimate_per_run,
            average_latency_ms=meta.average_latency_ms,
            max_concurrent_tasks=meta.max_concurrent_tasks,
            health=instance.health.value,
            status=instance.status.value,
            tags=list(meta.tags),
        )

        with self._lock:
            self._entries[meta.id] = entry
            self._type_index.setdefault(meta.type, set()).add(meta.id)
            for cap in meta.capabilities:
                self._capability_index.setdefault(cap, set()).add(meta.id)
            for model in meta.supported_models:
                self._model_index.setdefault(model, set()).add(meta.id)
            for tag in meta.tags:
                self._tag_index.setdefault(tag.lower(), set()).add(meta.id)
            self._version_history.setdefault(meta.id, []).append(meta.version)

        logger.info("AgentRegistry: registered '%s' (type=%s, v%s)",
                     meta.id, meta.type, meta.version)
        return entry

    def update(self, instance: AgentInstance) -> bool:
        with self._lock:
            existing = self._entries.get(instance.metadata.id)
            if existing is None:
                return False
            existing.health = instance.health.value
            existing.status = instance.status.value
            existing.average_latency_ms = instance.metadata.average_latency_ms
        return True

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            entry = self._entries.pop(agent_id, None)
            if entry is None:
                return False
            self._type_index.get(entry.type, set()).discard(agent_id)
            for cap in entry.capabilities:
                self._capability_index.get(cap, set()).discard(agent_id)
            for model in entry.supported_models:
                self._model_index.get(model, set()).discard(agent_id)
            for tag in entry.tags:
                self._tag_index.get(tag.lower(), set()).discard(agent_id)
        return True

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    def get(self, agent_id: str) -> Optional[RegistryEntry]:
        with self._lock:
            return self._entries.get(agent_id)

    def get_all(self) -> List[RegistryEntry]:
        with self._lock:
            return sorted(
                self._entries.values(),
                key=lambda e: (e.priority, e.name),
                reverse=True,
            )

    # ------------------------------------------------------------------
    # Search and filter
    # ------------------------------------------------------------------

    def find_by_capability(self, capability: str) -> List[RegistryEntry]:
        with self._lock:
            ids = self._capability_index.get(capability, set())
            return sorted(
                [self._entries[a] for a in ids if a in self._entries],
                key=lambda e: e.priority, reverse=True,
            )

    def find_by_type(self, agent_type: str) -> List[RegistryEntry]:
        with self._lock:
            ids = self._type_index.get(agent_type, set())
            return sorted(
                [self._entries[a] for a in ids if a in self._entries],
                key=lambda e: e.priority, reverse=True,
            )

    def find_by_model(self, model: str) -> List[RegistryEntry]:
        with self._lock:
            ids = self._model_index.get(model, set())
            return sorted(
                [self._entries[a] for a in ids if a in self._entries],
                key=lambda e: e.priority, reverse=True,
            )

    def find_by_tag(self, tag: str) -> List[RegistryEntry]:
        with self._lock:
            ids = self._tag_index.get(tag.lower(), set())
            return sorted(
                [self._entries[a] for a in ids if a in self._entries],
                key=lambda e: e.priority, reverse=True,
            )

    def search(self, name: str = "", type: str = "",
               capability: str = "", status: str = "",
               health: str = "", priority_min: int = 0,
               limit: int = 50) -> List[RegistryEntry]:
        with self._lock:
            results = list(self._entries.values())

        if name:
            results = [e for e in results if name.lower() in e.name.lower()]
        if type:
            results = [e for e in results if e.type == type]
        if capability:
            results = [e for e in results if capability in e.capabilities]
        if status:
            results = [e for e in results if e.status == status]
        if health:
            results = [e for e in results if e.health == health]
        if priority_min > 0:
            results = [e for e in results if e.priority >= priority_min]

        results.sort(key=lambda e: (e.priority, e.name), reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_capabilities_summary(self) -> Dict[str, int]:
        with self._lock:
            return {
                cap: len(ids)
                for cap, ids in sorted(self._capability_index.items())
            }

    def get_type_summary(self) -> Dict[str, int]:
        with self._lock:
            return {
                t: len(ids)
                for t, ids in sorted(self._type_index.items())
            }

    def get_model_summary(self) -> Dict[str, int]:
        with self._lock:
            return {
                m: len(ids)
                for m, ids in sorted(self._model_index.items())
            }

    def get_version_history(self, agent_id: str) -> List[str]:
        with self._lock:
            return list(self._version_history.get(agent_id, []))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            by_health: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            for e in self._entries.values():
                by_health[e.health] = by_health.get(e.health, 0) + 1
                by_status[e.status] = by_status.get(e.status, 0) + 1
        return {
            "total_agents": total,
            "by_health": by_health,
            "by_status": by_status,
            "by_type": self.get_type_summary(),
            "capabilities_total": len(self._capability_index),
            "models_total": len(self._model_index),
        }