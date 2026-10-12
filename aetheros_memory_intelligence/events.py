"""Memory event bus (section 61): deduplicated, observable in-process events."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

EVENT_KINDS = (
    "MEMORY_CREATED", "MEMORY_UPDATED", "MEMORY_SUPERSEDED", "MEMORY_DELETED",
    "MEMORY_CONFLICTED", "MEMORY_RETRIEVED", "MEMORY_CONSOLIDATED",
    "ENTITY_CREATED", "ENTITY_UPDATED", "RELATIONSHIP_CREATED", "RELATIONSHIP_UPDATED",
)


@dataclass
class MemoryEvent:
    kind: str
    record_id: str = ""
    actor: str = ""
    at: float = field(default_factory=time.time)
    detail: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self, *, history: int = 500) -> None:
        self._lock = threading.Lock()
        self._subs: Dict[str, List[Callable[[MemoryEvent], None]]] = {}
        self._history: Deque[MemoryEvent] = deque(maxlen=history)
        self._seen: set = set()

    def subscribe(self, kind: str, fn: Callable[[MemoryEvent], None]) -> None:
        with self._lock:
            self._subs.setdefault(kind, []).append(fn)

    def emit(self, event: MemoryEvent) -> bool:
        """Returns False when deduplicated (same kind+record within 1s)."""
        key = (event.kind, event.record_id, int(event.at))
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            if len(self._seen) > 5000:
                self._seen.clear()
            self._history.append(event)
            subs = list(self._subs.get(event.kind, [])) + list(self._subs.get("*", []))
        for fn in subs:
            try:
                fn(event)
            except Exception:
                continue
        return True

    def recent(self, limit: int = 50) -> List[MemoryEvent]:
        with self._lock:
            return list(self._history)[-limit:]

    def counts(self) -> Dict[str, int]:
        with self._lock:
            out: Dict[str, int] = {}
            for e in self._history:
                out[e.kind] = out.get(e.kind, 0) + 1
            return out
