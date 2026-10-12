"""AetherOS Integrations — unified Event Bus.

In-process pub/sub with durable event history, deduplication, and replay.
Covers workspace, agent, provider, tool, workflow, plugin, integration,
webhook, and scheduler events. Dedup keys prevent duplicate events; the
history enables auditing and replay.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_integrations.models import EventEnvelope, EventKind

logger = logging.getLogger(__name__)


class EventBus:
    """Unified event system with dedup, history, and replay."""

    def __init__(self, dirpath=None):
        from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings

        settings = load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._history_path = self._dir / "events.json"
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[EventEnvelope], Any]]] = {}
        self._history: Dict[str, EventEnvelope] = {}
        self._load_history()

    def _load_history(self) -> None:
        if not self._history_path.exists():
            return
        try:
            data = json.loads(self._history_path.read_text(encoding="utf-8"))
            for item in data:
                env = EventEnvelope(**item)
                self._history[env.id] = env
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load event history: %s", exc)

    def _save_history(self) -> None:
        payload = [e.to_dict() for e in self._history.values()]
        if len(payload) > 5000:
            payload = payload[-5000:]
        self._history_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- subscriptions ----------------------------------------------------

    def subscribe(self, event_type: str, handler: Callable[[EventEnvelope], Any]) -> Callable[[EventEnvelope], Any]:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)
        return handler

    def unsubscribe(self, event_type: str, handler: Callable[[EventEnvelope], Any]) -> bool:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
                return True
        return False

    def subscribe_wildcard(self, handler: Callable[[EventEnvelope], Any]) -> Callable[[EventEnvelope], Any]:
        return self.subscribe("*", handler)

    # -- publishing -------------------------------------------------------

    def publish(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        kind: EventKind = EventKind.WORKFLOW,
        source: str = "",
        dedup_key: str = "",
    ) -> EventEnvelope:
        dkey = dedup_key or f"{event_type}:{json.dumps(data or {}, sort_keys=True, default=str)}"
        with self._lock:
            for existing in self._history.values():
                if existing.dedup_key == dkey and time.time() - existing.timestamp < 3600:
                    logger.debug("Event deduped: %s", dkey)
                    return existing
            envelope = EventEnvelope(kind=kind, type=event_type, source=source, data=data or {}, dedup_key=dkey)
            self._history[envelope.id] = envelope
            self._save_history()
            targets = list(self._subscribers.get(event_type, []))
            targets += self._subscribers.get("*", [])
        for handler in targets:
            try:
                handler(envelope)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Event handler for %s failed: %s", event_type, exc)
        return envelope

    # -- introspection ----------------------------------------------------

    def history(self, event_type: str = "", limit: int = 100) -> List[EventEnvelope]:
        with self._lock:
            items = list(self._history.values())
        if event_type:
            items = [e for e in items if e.type == event_type]
        items.sort(key=lambda e: e.timestamp, reverse=True)
        return items[:limit]

    def replay(self, event_type: str = "", handler: Optional[Callable[[EventEnvelope], Any]] = None) -> int:
        """Re-deliver historical events to matching subscribers (or a given handler)."""
        count = 0
        for envelope in self.history(event_type, limit=1000):
            if handler:
                try:
                    handler(envelope)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Replay handler failed: %s", exc)
                continue
            targets = self._subscribers.get(envelope.type, []) + self._subscribers.get("*", [])
            for h in targets:
                try:
                    h(envelope)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Replay subscriber failed: %s", exc)
        return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type: Dict[str, int] = {}
            for e in self._history.values():
                by_type[e.type] = by_type.get(e.type, 0) + 1
        return {"total": len(self._history), "by_type": by_type}
