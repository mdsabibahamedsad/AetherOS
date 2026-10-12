from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[dict] = []
        self._history_limit = 1000
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable):
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            pass

    def emit(self, event: str, data: dict = None):
        entry = {
            "event": event,
            "data": data or {},
            "timestamp": time.time(),
        }
        self._history.append(entry)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]
        for handler in self._handlers.get(event, []):
            try:
                handler(entry)
            except Exception as e:
                logger.error("Event handler error for %s: %s", event, e)
        for handler in self._handlers.get("*", []):
            try:
                handler(entry)
            except Exception:
                pass

    def subscribe(self, subscriber_id: str, handler: Callable):
        self._subscribers[subscriber_id].append(handler)

    def unsubscribe(self, subscriber_id: str):
        self._subscribers.pop(subscriber_id, None)

    def get_history(
        self,
        event_filter: str = "",
        limit: int = 100,
        since: float = 0.0,
    ) -> list[dict]:
        events = self._history
        if event_filter:
            events = [e for e in events if e["event"] == event_filter]
        if since:
            events = [e for e in events if e["timestamp"] > since]
        return events[-limit:]

    def clear_history(self):
        self._history.clear()

    def wait_for(
        self, event: str, timeout: float = 30.0
    ) -> dict:
        future: asyncio.Future = asyncio.Future()
        def handler(entry):
            if not future.done():
                future.set_result(entry)
        self.on(event, handler)
        try:
            return asyncio.get_event_loop().run_until_complete(
                asyncio.wait_for(future, timeout=timeout)
            )
        except (asyncio.TimeoutError, RuntimeError):
            return {}
        finally:
            self.off(event, handler)

    def get_stats(self) -> dict:
        return {
            "total_events": len(self._history),
            "unique_events": len(set(e["event"] for e in self._history)),
            "handlers": sum(len(v) for v in self._handlers.values()),
            "subscribers": len(self._subscribers),
        }
