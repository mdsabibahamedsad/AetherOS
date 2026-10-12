from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Coroutine

EventHandler = Callable[..., Coroutine[Any, Any, None] | None]


class EventBus:
    def __init__(self, loop: asyncio.AbstractEventLoop | None = None):
        self._loop = loop or asyncio.get_event_loop()
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[dict] = []
        self._max_history = 1000
        self._running = False

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False
        self._subscribers.clear()
        self._history.clear()

    def subscribe(self, topic: str, handler: EventHandler):
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler):
        if handler in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, data: Any = None, source: str = ""):
        if not self._running:
            return
        event = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "data": data,
            "source": source,
            "timestamp": time.time(),
        }
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for handler in self._subscribers.get(topic, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    async def publish_many(self, events: list[tuple[str, Any, str]]):
        for topic, data, source in events:
            await self.publish(topic, data, source)

    def get_history(self, topic: str | None = None, limit: int = 50) -> list[dict]:
        if topic is None:
            return list(self._history[-limit:])
        return [e for e in self._history[-limit:] if e["topic"] == topic]

    def subscriber_count(self, topic: str) -> int:
        return len(self._subscribers.get(topic, []))
