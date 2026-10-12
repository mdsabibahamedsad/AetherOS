"""Jarvis Mode — notification intelligence.

Summarizes, prioritizes, groups duplicates, mutes distractions, and escalates
urgent events. Notifications are never delivered silently on top of each
other: the manager coalesces by group key and respects mute rules.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import NotificationItem, NotificationPriority

logger = logging.getLogger(__name__)

_PRIORITY_RANK = {
    NotificationPriority.LOW: 0,
    NotificationPriority.MEDIUM: 1,
    NotificationPriority.HIGH: 2,
    NotificationPriority.URGENT: 3,
}


class NotificationIntelligence:
    """Coalesces and prioritizes notifications before delivery.

    - :meth:`ingest` accepts a raw notification and returns the delivered
      item (or None when muted/duplicate).
    - Duplicates sharing a ``group_key`` are merged into a count.
    - Urgent items are emitted immediately; lower-priority items are
      delivered per the configured cadence.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: Dict[str, NotificationItem] = {}
        self._group_counts: Dict[str, int] = {}
        self._muted: Dict[str, float] = {}
        self._listeners: List[Callable[[NotificationItem], None]] = []
        self._history: List[NotificationItem] = []
        self._max_history = 200

    # ------------------------------------------------------------------
    # Muting
    # ------------------------------------------------------------------

    def mute(self, source: str, seconds: float = 3600.0) -> None:
        with self._lock:
            self._muted[source] = time.time() + seconds

    def unmute(self, source: str) -> None:
        with self._lock:
            self._muted.pop(source, None)

    def _is_muted(self, source: str) -> bool:
        with self._lock:
            expiry = self._muted.get(source, 0.0)
            if expiry > time.time():
                return True
            self._muted.pop(source, None)
            return False

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(
        self,
        *,
        title: str,
        body: str = "",
        source: str = "",
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        group_key: str = "",
    ) -> Optional[NotificationItem]:
        if self._is_muted(source):
            return None

        group_key = group_key or title.lower().strip()
        item = NotificationItem(
            title=title,
            body=body,
            source=source,
            priority=priority,
            group_key=group_key,
        )

        with self._lock:
            existing = self._items.get(group_key)
            if existing is not None:
                self._group_counts[group_key] = self._group_counts.get(group_key, 1) + 1
                existing.body = f"{body or title} (+{self._group_counts[group_key] - 1} more)"
                item = existing
                item.duplicate_of = group_key
            else:
                self._items[group_key] = item
                self._group_counts[group_key] = 1
            self._history.append(item)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            listeners = list(self._listeners)

        for cb in listeners:
            try:
                cb(item)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Notification listener error: %s", exc)
        return item

    # ------------------------------------------------------------------
    # Prioritization
    # ------------------------------------------------------------------

    def priority_queue(self) -> List[NotificationItem]:
        with self._lock:
            items = list(self._history)
        items.sort(key=lambda i: _PRIORITY_RANK[i.priority], reverse=True)
        return items

    def urgent(self) -> List[NotificationItem]:
        return [i for i in self.priority_queue() if i.priority == NotificationPriority.URGENT]

    def summarize(self) -> str:
        queue = self.priority_queue()
        if not queue:
            return "No notifications."
        groups: Dict[str, List[NotificationItem]] = {}
        for item in queue:
            groups.setdefault(item.priority, []).append(item)
        lines = []
        for priority in (NotificationPriority.URGENT, NotificationPriority.HIGH, NotificationPriority.MEDIUM, NotificationPriority.LOW):
            if priority not in groups:
                continue
            lines.append(f"{priority.value.upper()}:")
            for item in groups[priority][:5]:
                dup = f" (+{self._group_counts.get(item.group_key, 1) - 1} duplicates)" if self._group_counts.get(item.group_key, 1) > 1 else ""
                lines.append(f"  - {item.title}{dup}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def escalate(self, item: NotificationItem) -> NotificationItem:
        with self._lock:
            item.priority = NotificationPriority.URGENT
            self._items[item.group_key] = item
            return item

    def on_notification(self, callback: Callable[[NotificationItem], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "title": i.title,
                    "source": i.source,
                    "priority": i.priority.value,
                    "group_key": i.group_key,
                    "duplicates": self._group_counts.get(i.group_key, 1),
                }
                for i in self._history[-limit:]
            ]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total": len(self._history),
                "grouped": len(self._items),
                "muted_sources": list(self._muted.keys()),
                "urgent": sum(1 for i in self._history if i.priority == NotificationPriority.URGENT),
            }
