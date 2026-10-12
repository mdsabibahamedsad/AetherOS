from __future__ import annotations

import time
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from core.jarvis.reasoning import ReasoningSuggestion, ReasoningResult
from core.jarvis.notifications import NotificationCenter, NotificationLevel, NotificationSource

logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    OFF = "off"
    SUGGESTIONS = "suggestions"
    SEMI = "semi"
    FULL = "full"


@dataclass
class PendingSuggestion:
    result: ReasoningResult
    timestamp: float
    accepted: bool = False
    rejected: bool = False
    auto_accepted: bool = False


class AutonomyController:
    def __init__(self, notification_center: NotificationCenter):
        self._level = AutonomyLevel.OFF
        self._enabled = False
        self._pending: list[PendingSuggestion] = []
        self._lock = threading.Lock()
        self._notifications = notification_center
        self._listeners: list[callable] = []

    def on_change(self, listener: callable) -> callable:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify(self):
        for listener in self._listeners:
            try:
                listener({"level": self._level.value, "enabled": self._enabled})
            except Exception:
                pass

    @property
    def level(self) -> AutonomyLevel:
        return self._level

    @level.setter
    def level(self, level: AutonomyLevel | str):
        if isinstance(level, str):
            level = AutonomyLevel(level)
        self._level = level
        self._enabled = level != AutonomyLevel.OFF
        self._notify()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self._level = AutonomyLevel.OFF
        elif self._level == AutonomyLevel.OFF:
            self._level = AutonomyLevel.SUGGESTIONS
        self._notify()

    @property
    def state(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "level": self._level.value,
                "pending_count": len(self._pending),
            }

    def evaluate(self, result: ReasoningResult) -> Optional[PendingSuggestion]:
        if not self._enabled:
            return None

        suggestion = PendingSuggestion(result=result, timestamp=time.time())

        high_priority = any(s.priority >= 8 for s in result.suggestions)
        auto_accept = self._level == AutonomyLevel.FULL or (
            self._level == AutonomyLevel.SEMI and high_priority
        )

        if auto_accept:
            suggestion.auto_accepted = True
            suggestion.accepted = True
            level = NotificationLevel.INFO
        else:
            with self._lock:
                self._pending.append(suggestion)
            level = NotificationLevel.INFO

        for s in result.suggestions[:2]:
            self._notifications.notify(
                title=s.title,
                message=s.description,
                level=level,
                source=NotificationSource.AUTONOMY,
                action={"suggestion_id": s.title, "auto_accepted": auto_accept},
            )

        return suggestion

    def get_pending(self) -> list[PendingSuggestion]:
        with self._lock:
            results = [s for s in self._pending if not s.accepted and not s.rejected]
            self._pending = [s for s in self._pending if s.accepted or s.rejected]
            self._pending.extend(results)
            return [
                PendingSuggestion(result=s.result, timestamp=s.timestamp)
                for s in results
            ]

    def accept(self, index: int) -> Optional[ReasoningResult]:
        with self._lock:
            pending = [s for s in self._pending if not s.accepted and not s.rejected]
            if 0 <= index < len(pending):
                s = pending[index]
                s.accepted = True
                return s.result
            return None

    def reject(self, index: int):
        with self._lock:
            pending = [s for s in self._pending if not s.accepted and not s.rejected]
            if 0 <= index < len(pending):
                pending[index].rejected = True

    def clear_suggestions(self):
        with self._lock:
            self._pending.clear()

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._level = AutonomyLevel.SUGGESTIONS
        self._notify()
        self._notifications.notify(
            "Autonomy Mode",
            "Jarvis autonomy mode enabled",
            NotificationLevel.INFO,
            NotificationSource.AUTONOMY,
        )

    def stop(self):
        self._enabled = False
        self._level = AutonomyLevel.OFF
        with self._lock:
            self._pending.clear()
        self._notify()
        self._notifications.notify(
            "Autonomy Mode",
            "Jarvis autonomy mode disabled",
            NotificationLevel.INFO,
            NotificationSource.AUTONOMY,
        )
