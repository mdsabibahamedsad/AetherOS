"""Component heartbeats and stale detection.

A heartbeat is a cheap, non-persistent liveness signal a component emits
periodically.  Heartbeat payload:

    componentId, timestamp, status, version, lastSuccessfulOperation,
    health metadata.

Staleness is derived, never polled from the component — the registry only
compares ``now`` against ``timestamp`` when asked.  Heartbeat *emitters*
are the component owners (agent loop, gateway, backend, desktop main,
workers); the watchdog (``aetheros_reliability.watchdog``) consumes the
registry to detect timeout.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Heartbeat:
    component_id: str
    status: str = "alive"            # alive | busy | degraded | stopping | dead
    version: str = ""
    last_successful_operation: str = ""
    health: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "componentId": self.component_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "version": self.version,
            "lastSuccessfulOperation": self.last_successful_operation,
            "health": dict(self.health),
        }


class HeartbeatRegistry:
    """Tracks the latest heartbeat per component and detects staleness.

    Usage::

        registry = get_heartbeat_registry()
        registry.beat(Heartbeat(component_id="gateway", version="1.2.3"))
        registry.is_stale("gateway", timeout=60)   # False
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._heartbeats: Dict[str, Heartbeat] = {}
        self._history: Dict[str, list] = {}
        self._max_history = 50

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def beat(self, component_id: str, *, status: str = "alive",
             version: str = "", last_successful_operation: str = "",
             health: Optional[Dict[str, Any]] = None) -> Heartbeat:
        """Record a heartbeat for *component_id* (upsert)."""
        hb = Heartbeat(
            component_id=component_id,
            status=status,
            version=version,
            last_successful_operation=last_successful_operation,
            health=health or {},
        )
        with self._lock:
            self._heartbeats[component_id] = hb
            hist = self._history.setdefault(component_id, [])
            hist.append(hb.to_dict())
            if len(hist) > self._max_history:
                self._history[component_id] = hist[-self._max_history:]
        return hb

    def mark_stopping(self, component_id: str) -> None:
        """Graceful-shutdown heartbeat so the watchdog does not treat an
        intentional stop as a crash."""
        self.beat(component_id, status="stopping")

    def remove(self, component_id: str) -> None:
        with self._lock:
            self._heartbeats.pop(component_id, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, component_id: str) -> Optional[Heartbeat]:
        with self._lock:
            hb = self._heartbeats.get(component_id)
            if hb is None:
                return None
            return Heartbeat(
                component_id=hb.component_id,
                status=hb.status,
                version=hb.version,
                last_successful_operation=hb.last_successful_operation,
                health=dict(hb.health),
                timestamp=hb.timestamp,
            )

    def age(self, component_id: str) -> Optional[float]:
        """Seconds since the last heartbeat for *component_id* (None if none)."""
        with self._lock:
            hb = self._heartbeats.get(component_id)
        if hb is None:
            return None
        return max(0.0, time.time() - hb.timestamp)

    def is_stale(self, component_id: str, timeout: float) -> Optional[bool]:
        """True when no heartbeat within *timeout*; None when never seen."""
        age = self.age(component_id)
        if age is None:
            return None
        return age > timeout

    def all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {cid: hb.to_dict() for cid, hb in self._heartbeats.items()}

    def history(self, component_id: str, limit: int = 10) -> list:
        with self._lock:
            return list(self._history.get(component_id, [])[-limit:])

    def components(self) -> list:
        with self._lock:
            return sorted(self._heartbeats.keys())


_registry: Optional[HeartbeatRegistry] = None
_registry_lock = threading.Lock()


def get_heartbeat_registry() -> HeartbeatRegistry:
    """Return the process-wide HeartbeatRegistry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = HeartbeatRegistry()
    return _registry