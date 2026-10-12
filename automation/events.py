"""
Normalized automation event bus (Master 13 Phases 10, 15, 17, 78).

Every event carries the full envelope required for auditable triggering:

    event_id, event_type, source, timestamp, payload, trust

Trust model: events are either ``internal`` (emitted by Aetheros subsystems)
or ``external`` (file watchers, webhooks). External payloads are UNTRUSTED
INPUT — they are size-capped before storage and are only ever used for
structured filter matching; they never widen permissions or reach a prompt
verbatim through this module.

The broker is process-local with bounded history and TTL deduplication on
``event_id``. It deliberately coexists with the Phase-16 orchestrator's
internal EventBus: that one remains private to its subsystem; this module is
the single trigger source feeding automations.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_PAYLOAD_CHARS = 4000
HISTORY_LIMIT = 512
DEDUP_TTL_SECONDS = 3600
DEDUP_MAX_ENTRIES = 4096


@dataclass
class AutomationEvent:
    """Normalized envelope every trigger consumer can rely on."""

    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    trust: str = "internal"          # "internal" | "external"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "trust": self.trust,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class AutomationBus:
    """Thread-safe publish/subscribe broker with dedup + bounded history."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: List[Callable[[AutomationEvent], None]] = []
        self._history: "OrderedDict[str, dict]" = OrderedDict()
        self._seen: "OrderedDict[str, float]" = OrderedDict()

    def subscribe(self, handler: Callable[[AutomationEvent], None]) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[AutomationEvent], None]) -> None:
        with self._lock:
            try:
                self._handlers.remove(handler)
            except ValueError:
                pass

    def publish(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        source: str = "unknown",
        trust: str = "internal",
        event_id: Optional[str] = None,
    ) -> Optional[AutomationEvent]:
        """Publish an event. Returns the event, or None when deduplicated."""
        if not isinstance(event_type, str) or not event_type.strip():
            logger.debug("Rejected event without type")
            return None
        event_id = str(event_id) if event_id else uuid.uuid4().hex
        now = time.time()

        with self._lock:
            seen_at = self._seen.get(event_id)
            if seen_at is not None and (now - seen_at) < DEDUP_TTL_SECONDS:
                self._seen.move_to_end(event_id)
                return None
            self._seen[event_id] = now
            while len(self._seen) > DEDUP_MAX_ENTRIES:
                self._seen.popitem(last=False)

        safe_payload = _cap_payload(payload)
        event = AutomationEvent(
            event_type=event_type.strip(),
            payload=safe_payload,
            source=source or "unknown",
            trust="external" if trust == "external" else "internal",
            timestamp=now,
            event_id=event_id,
        )

        with self._lock:
            self._history[event.event_id] = event.to_dict()
            self._history.move_to_end(event.event_id)
            while len(self._history) > HISTORY_LIMIT:
                self._history.popitem(last=False)

        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event.event_type)
        return event

    def recent(self, limit: int = 20, event_type: str = "") -> List[dict]:
        with self._lock:
            items = list(self._history.values())
        if event_type:
            items = [e for e in items if e.get("event_type") == event_type]
        return list(reversed(items[-max(1, limit):]))


def _cap_payload(payload: Any) -> Dict[str, Any]:
    """Bound external/untrusted payloads before they enter history/handlers.

    JSON scalars pass through untouched; long strings are truncated; complex
    values are serialized to bounded text. Total budget is enforced so one
    huge event cannot balloon history memory.
    """
    if not isinstance(payload, dict):
        return {"value": _cap_str(str(payload))}
    capped: Dict[str, Any] = {}
    total = 0
    for key, value in payload.items():
        remaining = MAX_PAYLOAD_CHARS - total
        if remaining <= 0:
            break
        if value is None or isinstance(value, bool):
            kept = value
            size = len(str(kept))
        elif isinstance(value, (int, float)):
            kept = value
            size = len(repr(kept))
        else:
            text = value if isinstance(value, str) else str(value)
            kept = text[:remaining]
            size = len(kept)
        capped[str(key)[:200]] = kept
        total += size + 1
    return capped


def _cap_str(text: str) -> str:
    text = str(text)
    return text[:MAX_PAYLOAD_CHARS]


_bus: Optional[AutomationBus] = None
_bus_lock = threading.Lock()


def get_bus() -> AutomationBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = AutomationBus()
        return _bus


def reset_bus() -> None:
    """Test helper — drop the process singleton."""
    global _bus
    with _bus_lock:
        _bus = None


def publish_internal(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    source: str = "aetheros",
    event_id: Optional[str] = None,
) -> Optional[AutomationEvent]:
    return get_bus().publish(
        event_type, payload, source=source, trust="internal", event_id=event_id
    )


def publish_external(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    source: str = "external",
    event_id: Optional[str] = None,
) -> Optional[AutomationEvent]:
    return get_bus().publish(
        event_type, payload, source=source, trust="external", event_id=event_id
    )
