"""Notification Bus — events for streaming, agent, tool, task, model, provider status.

Decoupled event system for runtime notifications.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.notifications")


class NotificationLevel(enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    title: str = ""
    message: str = ""
    level: NotificationLevel = NotificationLevel.INFO
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "data": self.data,
            "acknowledged": self.acknowledged,
        }


NotificationHandler = Callable[[Notification], None]


class NotificationBus:
    """Decoupled pub/sub notification system.

    Events:
    - streaming.complete
    - agent.waiting
    - tool.permission
    - task.finished
    - model.switched
    - provider.disconnected
    """

    def __init__(self, max_history: int = 500) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[NotificationHandler]] = {}
        self._history: List[Notification] = []
        self._max_history = max_history
        self._wildcard_subscribers: List[NotificationHandler] = []

    # ------------------------------------------------------------------
    # Subscribe / Publish
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, handler: NotificationHandler) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: NotificationHandler) -> None:
        with self._lock:
            self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: str, handler: NotificationHandler) -> bool:
        with self._lock:
            handlers = self._subscribers.get(event_type)
            if handlers and handler in handlers:
                handlers.remove(handler)
                return True
            return False

    def publish(
        self,
        event_type: str,
        title: str = "",
        message: str = "",
        level: NotificationLevel = NotificationLevel.INFO,
        source: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        notification = Notification(
            type=event_type,
            title=title,
            message=message,
            level=level,
            source=source,
            data=data or {},
        )

        with self._lock:
            self._history.append(notification)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            handlers = list(self._subscribers.get(event_type, []))
            wildcard = list(self._wildcard_subscribers)

        for handler in handlers + wildcard:
            try:
                handler(notification)
            except Exception as exc:
                logger.warning("Notification handler failed: %s", exc)

        logger.debug("Notification: [%s] %s", event_type, title or message[:60])
        return notification

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def publish_streaming_complete(self, stream_id: str, content_length: int = 0) -> Notification:
        return self.publish("streaming.complete", "Streaming Complete", f"Stream {stream_id[:8]} finished ({content_length} chars)", NotificationLevel.INFO, "streaming", {"stream_id": stream_id, "content_length": content_length})

    def publish_agent_waiting(self, agent_id: str, reason: str = "") -> Notification:
        return self.publish("agent.waiting", "Agent Waiting", f"Agent {agent_id[:8]} is waiting: {reason}", NotificationLevel.INFO, "agent", {"agent_id": agent_id, "reason": reason})

    def publish_tool_permission(self, tool_name: str, granted: bool = False) -> Notification:
        return self.publish("tool.permission", "Tool Permission", f"{'Granted' if granted else 'Denied'}: {tool_name}", NotificationLevel.WARNING, "tools", {"tool": tool_name, "granted": granted})

    def publish_task_finished(self, task_id: str, success: bool = True) -> Notification:
        return self.publish("task.finished", "Task Finished", f"Task {task_id[:8]} {'completed' if success else 'failed'}", NotificationLevel.INFO if success else NotificationLevel.ERROR, "tasks", {"task_id": task_id, "success": success})

    def publish_model_switched(self, model: str, provider: str = "") -> Notification:
        return self.publish("model.switched", "Model Switched", f"Switched to {model}", NotificationLevel.INFO, "model", {"model": model, "provider": provider})

    def publish_provider_disconnected(self, provider: str, reason: str = "") -> Notification:
        return self.publish("provider.disconnected", "Provider Disconnected", f"{provider}: {reason}", NotificationLevel.ERROR, "provider", {"provider": provider, "reason": reason})

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(
        self,
        event_type: Optional[str] = None,
        level: Optional[NotificationLevel] = None,
        limit: int = 50,
    ) -> List[Notification]:
        with self._lock:
            results = list(self._history)
        if event_type:
            results = [n for n in results if n.type == event_type]
        if level:
            results = [n for n in results if n.level == level]
        return results[-limit:]

    def acknowledge(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._history:
                if n.id == notification_id:
                    n.acknowledged = True
                    return True
            return False

    def acknowledge_all(self, event_type: Optional[str] = None) -> int:
        count = 0
        with self._lock:
            for n in self._history:
                if (not event_type or n.type == event_type) and not n.acknowledged:
                    n.acknowledged = True
                    count += 1
        return count

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def get_unacknowledged(self) -> List[Notification]:
        with self._lock:
            return [n for n in self._history if not n.acknowledged]

    def summary(self) -> str:
        with self._lock:
            unacked = sum(1 for n in self._history if not n.acknowledged)
            by_level = {}
            for n in self._history:
                by_level[n.level.value] = by_level.get(n.level.value, 0) + 1
            return f"Notification Bus: {len(self._history)} events ({unacked} unacknowledged), {by_level}"