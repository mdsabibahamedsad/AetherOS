from __future__ import annotations

import time
import uuid
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable


class NotificationLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationSource(Enum):
    SYSTEM = "system"
    AUTONOMY = "autonomy"
    TASK = "task"
    AGENT = "agent"
    USER = "user"
    SCHEDULER = "scheduler"


@dataclass
class JarvisNotification:
    id: str
    title: str
    message: str
    level: NotificationLevel
    source: NotificationSource
    timestamp: float
    read: bool = False
    action: Optional[dict] = None


class NotificationCenter:
    def __init__(self, max_notifications: int = 200):
        self._max = max_notifications
        self._notifications: list[JarvisNotification] = []
        self._lock = threading.Lock()
        self._listeners: list[Callable] = []

    def on_notification(self, listener: Callable) -> Callable:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify(self, notif: JarvisNotification):
        for listener in self._listeners:
            try:
                listener(notif)
            except Exception:
                pass

    def notify(
        self,
        title: str,
        message: str = "",
        level: NotificationLevel | str = NotificationLevel.INFO,
        source: NotificationSource | str = NotificationSource.SYSTEM,
        action: Optional[dict] = None,
    ) -> JarvisNotification:
        if isinstance(level, str):
            level = NotificationLevel(level)
        if isinstance(source, str):
            source = NotificationSource(source)

        notif = JarvisNotification(
            id=f"jarvis-notif-{uuid.uuid4().hex[:12]}",
            title=title,
            message=message,
            level=level,
            source=source,
            timestamp=time.time(),
            action=action,
        )

        with self._lock:
            self._notifications.insert(0, notif)
            if len(self._notifications) > self._max:
                self._notifications = self._notifications[:self._max]

        self._notify(notif)
        return notif

    def mark_read(self, notif_id: str):
        with self._lock:
            for n in self._notifications:
                if n.id == notif_id:
                    n.read = True
                    break

    def mark_all_read(self):
        with self._lock:
            for n in self._notifications:
                n.read = True

    def clear(self):
        with self._lock:
            self._notifications.clear()

    @property
    def notifications(self) -> list[JarvisNotification]:
        with self._lock:
            return list(self._notifications)

    @property
    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)

    def get_stats(self) -> dict:
        with self._lock:
            total = len(self._notifications)
            unread = sum(1 for n in self._notifications if not n.read)
            by_level = {}
            by_source = {}
            for n in self._notifications:
                by_level[n.level.value] = by_level.get(n.level.value, 0) + 1
                by_source[n.source.value] = by_source.get(n.source.value, 0) + 1
            return {
                "total": total,
                "unread": unread,
                "by_level": by_level,
                "by_source": by_source,
            }
