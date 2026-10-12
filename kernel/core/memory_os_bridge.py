"""
memory_os provider bridge (Master 59 §15, migration path §47).

`agent/memory_os` is the richest memory implementation in the repo
(scopes, provenance, sensitivity, dedupe, retention). The kernel path
uses `kernel.core.memory_manager.MemoryManager` with `IMemoryProvider`
plugins. This bridge exposes a memory_os `MemoryManager` as an
`IMemoryProvider` so kernel/capsule memory traffic can flow into the
consolidated store — without rewriting either side:

    LEGACY/CAPSULE calls → kernel MemoryManager → MemoryOsProvider
                           → agent.memory_os manager

Scope mapping is explicit and documented (no silent promotion):
kernel task/project/shared → memory_os task/project/organization;
per-agent namespaces land in memory_os `user` scope owned by the agent
id. Access always carries an `AccessContext`, so memory_os ACLs
(`allow_agents`, roles, sensitivity) apply normally — the bridge never
bypasses them.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from kernel.core.types import IMemoryProvider

logger = logging.getLogger(__name__)


KERNEL_TO_MEMORY_OS_SCOPE = {
    "working": "session",
    "episodic": "session",
    "semantic": "user",
    "procedural": "user",
    "project": "project",
    "research": "project",
    "spatial": "session",
    "ambient": "session",
    "agent": "user",
    "swarm": "task",
    "shared": "organization",
    # Kernel callers may also use memory_os-native scope names directly;
    # identity entries keep them addressable through the bridge.
    "session": "session",
    "task": "task",
    "user": "user",
    "organization": "organization",
    "system": "system",
}


class MemoryOsProvider(IMemoryProvider):
    """IMemoryProvider backed by agent/memory_os (explicit identity)."""

    def __init__(self, manager: Any, *, actor_id: str = "kernel",
                 owner: str = "kernel", project_id: str = "") -> None:
        from agent.memory_os.manager import AccessContext, ActorKind, MemoryScope
        self._manager = manager
        self._AccessContext = AccessContext
        self._ActorKind = ActorKind
        self._MemoryScope = MemoryScope
        self._actor_id = actor_id
        self._owner = owner
        self._project_id = project_id
        self._lock = threading.RLock()
        self._bindings: Dict[str, str] = {}  # (scope,key) -> memory_id

    def _ctx(self) -> Any:
        return self._AccessContext(kind=self._ActorKind.SYSTEM,
                                   actor_id=self._actor_id,
                                   project_id=self._project_id,
                                   roles=frozenset({"kernel", "system"}))

    def _mapped_scope(self, scope: str) -> Any:
        name = KERNEL_TO_MEMORY_OS_SCOPE.get(scope, "session")
        return self._MemoryScope(name)

    def _bindkey(self, scope: str, key: str) -> str:
        return f"{scope}\x00{key}"

    def write(self, scope: str, key: str, value: Any) -> None:
        from agent.memory_os.manager import Confidence, Sensitivity, SourceType
        ctx = self._ctx()
        content = value if isinstance(value, str) else str(value)
        outcome = self._manager.remember(
            content, scope=self._mapped_scope(scope), owner=self._owner,
            project_id=self._project_id, semantic_key=key,
            source_type=SourceType.SYSTEM,  # kernel-mediated write
            confidence=Confidence.MEDIUM, sensitivity=Sensitivity.INTERNAL,
            actor=self._actor_id, ctx=ctx, dedupe=True)
        item = getattr(outcome, "item", None)
        mid = getattr(item, "memory_id", None) or getattr(item, "id", None)
        if mid:
            with self._lock:
                self._bindings[self._bindkey(scope, key)] = mid

    def read(self, scope: str, key: str) -> Any:
        with self._lock:
            mid = self._bindings.get(self._bindkey(scope, key))
        if not mid:
            return None
        try:
            item = self._manager.get(mid, self._ctx())
        except Exception as exc:
            logger.debug("MemoryOsProvider read failed: %s", exc)
            return None
        if item is None:
            return None
        return getattr(item, "content", None)

    def search(self, scope: str, query: str, limit: int = 10) -> List[Any]:
        try:
            result = self._manager.search(query, self._ctx())
        except Exception as exc:
            logger.debug("MemoryOsProvider search failed: %s", exc)
            return []
        out = []
        for hit in (getattr(result, "hits", None) or [])[:limit]:
            item = getattr(hit, "item", None)
            if item is None:
                continue
            out.append({"id": getattr(item, "memory_id", getattr(item, "id", "")),
                        "content": getattr(item, "content", ""),
                        "score": getattr(hit, "score", 0.0)})
        return out

    def delete(self, scope: str, key: str) -> bool:
        with self._lock:
            mid = self._bindings.pop(self._bindkey(scope, key), None)
        if not mid:
            return False
        try:
            self._manager.forget(mid, self._ctx())
            return True
        except Exception as exc:
            logger.debug("MemoryOsProvider delete failed: %s", exc)
            return False

    @staticmethod
    def scope_map() -> Dict[str, str]:
        """Documented kernel→memory_os scope correspondence."""
        return dict(KERNEL_TO_MEMORY_OS_SCOPE)


def register_memory_os_provider(kernel: Any, manager: Any = None, **kwargs: Any) -> str:
    """Register memory_os as a kernel memory provider for all mapped scopes.

    Returns the provider name. The kernel MemoryManager remains canonical;
    memory_os becomes one governed provider behind it (consolidation
    without rewrite, §47).
    """
    from kernel.core.memory_manager import MemoryScope as KernelScope
    if manager is None:
        from agent.memory_os.manager import MemoryManager as MemoryOsManager
        manager = MemoryOsManager()
    provider = MemoryOsProvider(manager, **kwargs)
    scopes = {KernelScope(s) for s in KERNEL_TO_MEMORY_OS_SCOPE
              if s in {m.value for m in KernelScope}}
    kernel.memory_manager.register_provider("memory_os", provider,
                                            scopes=sorted(scopes, key=lambda s: s.value))
    return "memory_os"


KERNEL_TO_MEMORY2_SCOPE = {
    "working": "session",
    "episodic": "session",
    "semantic": "user",
    "procedural": "user",
    "project": "project",
    "research": "research",
    "spatial": "workspace",
    "ambient": "session",
    "agent": "agent",
    "swarm": "task",
    "shared": "global",
    "session": "session",
    "task": "task",
    "user": "user",
    "organization": "global",
    "system": "global",
}


class Memory2Provider(IMemoryProvider):
    """IMemoryProvider backed by Memory 2.0 (`aetheros_memory_intelligence`).

    The Master-41 store of record, exposed as a governed kernel provider.
    Provenance is marked kernel-mediated; Memory 2.0's own gates
    (explicit > inferred, isolation rules) apply normally.
    """

    def __init__(self, service: Any = None, *, actor_id: str = "kernel") -> None:
        if service is None:
            from aetheros_memory_intelligence.service import MemoryService
            service = MemoryService()
        self._service = service
        self._actor_id = actor_id
        self._lock = threading.RLock()
        self._bindings: Dict[str, str] = {}

    def _bindkey(self, scope: str, key: str) -> str:
        return f"{scope}\x00{key}"

    def _mapped_scope(self, scope: str) -> Any:
        from aetheros_memory_intelligence.record import RecordScope
        return RecordScope(KERNEL_TO_MEMORY2_SCOPE.get(scope, "session"))

    def write(self, scope: str, key: str, value: Any) -> None:
        from aetheros_memory_intelligence.record import ProvenanceKind
        content = value if isinstance(value, str) else str(value)
        result = self._service.remember(
            content, scope=self._mapped_scope(scope),
            provenance=ProvenanceKind.SYSTEM,
            actor=self._actor_id,
            metadata={"kernel_key": key, "kernel_scope": scope})
        rid = result.get("id") if isinstance(result, dict) else None
        if rid:
            with self._lock:
                self._bindings[self._bindkey(scope, key)] = rid

    def read(self, scope: str, key: str) -> Any:
        with self._lock:
            rid = self._bindings.get(self._bindkey(scope, key))
        if not rid:
            return None
        try:
            record = self._service.get(rid)
        except Exception as exc:
            logger.debug("Memory2Provider read failed: %s", exc)
            return None
        if not record:
            return None
        return record.get("content")

    def search(self, scope: str, query: str, limit: int = 10) -> List[Any]:
        try:
            result = self._service.search(query, scope=self._mapped_scope(scope),
                                          top_k=limit)
        except Exception as exc:
            logger.debug("Memory2Provider search failed: %s", exc)
            return []
        out = []
        records = result.get("records", result.get("results", [])) \
            if isinstance(result, dict) else []
        for rec in records[:limit]:
            if isinstance(rec, dict):
                out.append({"id": rec.get("id", ""),
                            "content": rec.get("content", ""),
                            "score": rec.get("score", 0.0)})
        return out

    def delete(self, scope: str, key: str) -> bool:
        with self._lock:
            rid = self._bindings.pop(self._bindkey(scope, key), None)
        if not rid:
            return False
        try:
            self._service.forget(record_id=rid, actor=self._actor_id)
            return True
        except Exception as exc:
            logger.debug("Memory2Provider delete failed: %s", exc)
            return False

    @staticmethod
    def scope_map() -> Dict[str, str]:
        """Documented kernel→Memory-2.0 scope correspondence."""
        return dict(KERNEL_TO_MEMORY2_SCOPE)


def register_memory2_provider(kernel: Any, service: Any = None, **kwargs: Any) -> str:
    """Register Memory 2.0 as a kernel memory provider. Returns the name."""
    from kernel.core.memory_manager import MemoryScope as KernelScope
    provider = Memory2Provider(service, **kwargs)
    scopes = {KernelScope(s) for s in KERNEL_TO_MEMORY2_SCOPE
              if s in {m.value for m in KernelScope}}
    kernel.memory_manager.register_provider("memory2", provider,
                                            scopes=sorted(scopes, key=lambda s: s.value))
    return "memory2"
