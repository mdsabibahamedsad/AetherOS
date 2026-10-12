"""
Notification Manager — Structured notification framework.

Provides structured notifications for completed tasks, approval requests,
errors, long-running jobs, and workflow milestones. Supports desktop
and future mobile adapters.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationPriority(enum.IntEnum):
    """Priority levels for notifications."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class NotificationAction(enum.Enum):
    """Standard actions that can be taken on a notification."""
    DISMISS = "dismiss"
    SNOOZE = "snooze"
    OPEN = "open"
    APPROVE = "approve"
    DENY = "deny"
    VIEW_DETAILS = "view_details"
    RETRY = "retry"
    CUSTOM = "custom"


@dataclass
class NotificationChannel:
    """A notification delivery channel configuration.

    Attributes:
        name: Channel name (desktop, desktop_toast, voice, email, etc.)
        enabled: Whether this channel is active
        priority_threshold: Minimum priority level for this channel
        config: Channel-specific configuration
    """
    name: str = ""
    enabled: bool = True
    priority_threshold: NotificationPriority = NotificationPriority.NORMAL
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    """A structured notification.

    Attributes:
        id: Unique notification identifier
        title: Notification title
        message: Notification body text
        priority: Priority level
        category: Category (task_complete, approval, error, milestone, etc.)
        actions: Available actions
        source: Source component (workflow, engineering, swarm, etc.)
        source_id: Source-specific identifier
        expires_at: When the notification expires (auto-dismiss)
        data: Additional structured data
    """
    id: str = ""
    title: str = ""
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: str = "general"
    actions: List[NotificationAction] = field(default_factory=list)
    source: str = ""
    source_id: str = ""
    expires_at: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)


class NotificationManager:
    """Manages structured notification delivery across channels.

    Supports multiple delivery channels with per-channel priority
    thresholds. Notifications can include actions for user response.

    Usage:
        mgr = NotificationManager()
        mgr.initialize()
        mgr.add_channel(NotificationChannel(name="desktop", priority_threshold=NotificationPriority.NORMAL))

        notification = Notification(
            title="Task Complete",
            message="Your build finished successfully",
            priority=NotificationPriority.NORMAL,
            source="workflow",
        )
        mgr.send(notification)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._channels: Dict[str, NotificationChannel] = {}
        self._history: List[Notification] = []
        self._max_history: int = 200
        self._delivery_adapters: Dict[str, Callable[[Notification], bool]] = {}
        self._pending_actions: Dict[str, Notification] = {}
        self._notification_id_counter = 0

    def initialize(self) -> None:
        """Initialize the notification manager with default channels."""
        self.add_channel(NotificationChannel(
            name="in_memory",
            enabled=True,
            priority_threshold=NotificationPriority.NORMAL,
        ))
        # Register built-in in-memory delivery adapter
        self.register_delivery_adapter(
            "in_memory",
            lambda n: True,
        )
        logger.info("NotificationManager: initialized")

    def add_channel(self, channel: NotificationChannel) -> None:
        """Register a notification channel.

        Args:
            channel: Channel configuration
        """
        with self._lock:
            self._channels[channel.name] = channel
        logger.debug("NotificationManager: added channel '%s'", channel.name)

    def remove_channel(self, name: str) -> bool:
        """Remove a notification channel.

        Args:
            name: Channel name

        Returns:
            True if removed
        """
        with self._lock:
            return self._channels.pop(name, None) is not None

    def register_delivery_adapter(
        self, channel_name: str,
        adapter_fn: Callable[[Notification], bool],
    ) -> None:
        """Register a delivery adapter for a channel.

        Args:
            channel_name: Channel name
            adapter_fn: Callable receiving Notification, returning success
        """
        with self._lock:
            self._delivery_adapters[channel_name] = adapter_fn

    def send(self, notification: Notification) -> bool:
        """Send a notification through all eligible channels.

        Args:
            notification: The notification to send

        Returns:
            True if delivered to at least one channel
        """
        if not notification.id:
            notification.id = uuid.uuid4().hex[:12]

        with self._lock:
            self._notification_id_counter += 1

        delivered = False
        with self._lock:
            channels = dict(self._channels)
            adapters = dict(self._delivery_adapters)

        for name, channel in channels.items():
            if not channel.enabled:
                continue
            if notification.priority.value < channel.priority_threshold.value:
                continue

            adapter = adapters.get(name)
            if adapter:
                try:
                    if adapter(notification):
                        delivered = True
                except Exception as exc:
                    logger.warning("NotificationManager: adapter %s failed: %s", name, exc)

        # Always store in history
        with self._lock:
            self._history.append(notification)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Track notifications with pending actions
            if notification.actions:
                self._pending_actions[notification.id] = notification

        return delivered

    def send_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: str = "general",
        actions: Optional[List[NotificationAction]] = None,
        source: str = "",
    ) -> Notification:
        """Create and send a notification in one call.

        Args:
            title: Notification title
            message: Notification body
            priority: Priority level
            category: Notification category
            actions: Available actions
            source: Source component

        Returns:
            The created Notification
        """
        notification = Notification(
            id=uuid.uuid4().hex[:12],
            title=title,
            message=message,
            priority=priority,
            category=category,
            actions=actions or [],
            source=source,
        )
        self.send(notification)
        return notification

    def handle_action(self, notification_id: str, action: NotificationAction) -> bool:
        """Handle an action taken on a notification.

        Args:
            notification_id: Notification identifier
            action: Action taken

        Returns:
            True if processed
        """
        with self._lock:
            notification = self._pending_actions.pop(notification_id, None)
            if notification is None:
                return False
        logger.info("NotificationManager: action %s on notification %s", action.value, notification_id[:8])
        return True

    def get_history(
        self,
        category: Optional[str] = None,
        priority_min: Optional[NotificationPriority] = None,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notification history.

        Args:
            category: Optional category filter
            priority_min: Minimum priority filter
            limit: Max results

        Returns:
            List of matching Notifications
        """
        with self._lock:
            results = list(self._history)
        if category:
            results = [n for n in results if n.category == category]
        if priority_min:
            results = [n for n in results if n.priority.value >= priority_min.value]
        return results[-limit:]

    def get_pending_actions(self) -> List[Notification]:
        """Get notifications with pending actions.

        Returns:
            List of notifications awaiting action
        """
        with self._lock:
            return list(self._pending_actions.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get notification manager statistics."""
        with self._lock:
            return {
                "total_sent": self._notification_id_counter,
                "history_size": len(self._history),
                "pending_actions": len(self._pending_actions),
                "channels": list(self._channels.keys()),
                "adapters": list(self._delivery_adapters.keys()),
            }
