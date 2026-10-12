"""
Central Event Bus — the nervous system of the AetherOS Kernel.

Every subsystem communicates through events. No tight coupling.
Events flow asynchronously via a thread-safe pub/sub mechanism.

Event Categories:
  - lifecycle:*       Component startup/shutdown/health
  - agent:*           Agent lifecycle (started, finished, error)
  - task:*            Task creation, completion, failure
  - tool:*            Tool execution events
  - memory:*          Memory read/write/update events
  - workspace:*       Workspace change events
  - plugin:*          Plugin load/unload events
  - system:*          System-wide events (config change, shutdown)
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventPriority(enum.IntEnum):
    """Priority levels for event delivery. Lower = delivered first."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100
    BACKGROUND = 200


@dataclass(frozen=True)
class Event:
    """An immutable event in the kernel event system.

    Attributes:
        topic: Event topic (e.g. "agent.started", "task.completed")
        data: Event payload (any serializable dict)
        source: Source component name
        id: Unique event ID (auto-generated)
        timestamp: Unix timestamp of creation
        priority: Delivery priority
    """
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "kernel"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL


class EventSubscription:
    """A subscription handle that can be cancelled."""

    def __init__(self, topic: str, callback: Callable[[Event], None],
                 subscription_id: str, priority: EventPriority = EventPriority.NORMAL):
        self.topic = topic
        self.callback = callback
        self.id = subscription_id
        self.priority = priority
        self.active = True
        self.created_at = time.time()

    def cancel(self) -> None:
        """Deactivate this subscription."""
        self.active = False

    def __repr__(self) -> str:
        return (
            f"EventSubscription(id={self.id}, topic={self.topic!r}, "
            f"active={self.active})"
        )


class EventBus:
    """Thread-safe publish/subscribe event bus.

    Usage:
        bus = EventBus()
        sub = bus.subscribe("agent.started", my_handler)
        bus.publish(Event("agent.started", {"id": "agent-1"}))
        sub.cancel()
    """

    def __init__(self):
        self._lock = threading.RLock()
        # topic -> list of EventSubscription
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        # Wildcard subscribers (topic pattern with * or **)
        self._wildcard_subs: List[EventSubscription] = []
        # Total events published (for telemetry)
        self._publish_count = 0
        self._error_count = 0
        # Thread pool for async delivery
        self._async_mode = True
        self._shutdown_flag = False

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, topic: str, callback: Callable[[Event], None],
                  priority: EventPriority = EventPriority.NORMAL,
                  description: str = "") -> EventSubscription:
        """Subscribe to an event topic.

        Topics support wildcards:
          - ``agent.*`` matches agent.started, agent.finished, etc.
          - ``**`` matches everything

        Args:
            topic: Event topic (supports * and ** wildcards)
            callback: Callable receiving the Event
            priority: Subscriber priority (lower = first)
            description: Optional human-readable description

        Returns:
            EventSubscription handle (call .cancel() to unsubscribe)
        """
        sub = EventSubscription(
            topic=topic,
            callback=callback,
            subscription_id=uuid.uuid4().hex[:12],
            priority=priority,
        )
        with self._lock:
            if "**" in topic or "*" in topic:
                self._wildcard_subs.append(sub)
            else:
                subs = self._subscriptions.setdefault(topic, [])
                subs.append(sub)
                subs.sort(key=lambda s: s.priority)
        logger.debug(
            "EventBus: subscribed %s to %s", description or callback.__name__, topic,
        )
        return sub

    def subscribe_many(self, topics: List[str],
                       callback: Callable[[Event], None],
                       priority: EventPriority = EventPriority.NORMAL) -> List[EventSubscription]:
        """Subscribe the same callback to multiple topics."""
        return [
            self.subscribe(t, callback, priority=priority)
            for t in topics
        ]

    def unsubscribe_all(self, callback: Callable[[Event], None]) -> int:
        """Remove all subscriptions for a given callback. Returns count removed."""
        count = 0
        with self._lock:
            for subs in self._subscriptions.values():
                before = len(subs)
                subs[:] = [s for s in subs if s.callback != callback]
                count += before - len(subs)
            before = len(self._wildcard_subs)
            self._wildcard_subs[:] = [
                s for s in self._wildcard_subs if s.callback != callback
            ]
            count += before - len(self._wildcard_subs)
        return count

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------

    def publish(self, event: Event) -> int:
        """Publish an event to all matching subscribers.

        Args:
            event: The event to publish

        Returns:
            Number of subscribers that received the event
        """
        if self._shutdown_flag:
            return 0

        with self._lock:
            self._publish_count += 1

        delivered = 0

        # Direct topic match
        for sub in self._get_subscribers(event.topic):
            if sub.active:
                try:
                    sub.callback(event)
                    delivered += 1
                except Exception as exc:
                    self._error_count += 1
                    logger.error(
                        "EventBus: subscriber %s failed on topic %s: %s",
                        sub.callback.__name__, event.topic, exc,
                    )

        return delivered

    def publish_async(self, event: Event) -> int:
        """Publish event in a background thread (fire-and-forget).

        Returns the number of subscribers immediately matched.
        Delivery happens in a daemon thread.
        """
        matched = self._match_count(event.topic)
        if matched > 0:
            threading.Thread(
                target=self.publish,
                args=(event,),
                daemon=True,
                name=f"evt-{event.topic[:20]}",
            ).start()
        return matched

    def _get_subscribers(self, topic: str) -> List[EventSubscription]:
        """Get all active subscribers matching a topic (direct + wildcard)."""
        with self._lock:
            subs = list(self._subscriptions.get(topic, []))
            for wsub in self._wildcard_subs:
                if wsub.active and self._topic_matches(wsub.topic, topic):
                    subs.append(wsub)
            subs.sort(key=lambda s: (s.priority, s.created_at))
            return subs

    def _match_count(self, topic: str) -> int:
        """Count active subscribers for a topic (without delivery)."""
        count = 0
        with self._lock:
            count += len([
                s for s in self._subscriptions.get(topic, []) if s.active
            ])
            for wsub in self._wildcard_subs:
                if wsub.active and self._topic_matches(wsub.topic, topic):
                    count += 1
        return count

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Check if a wildcard pattern matches a topic string.

        Simple wildcard support:
          - ``**`` matches everything
          - ``agent.*`` matches agent.started, agent.finished
          - ``agent.**`` matches agent.x.y.z
        """
        if pattern == "**":
            return True
        if pattern.endswith(".**"):
            prefix = pattern[:-3]
            return topic.startswith(prefix)
        if pattern.endswith(".*"):
            prefix = pattern[:-1]
            return topic.startswith(prefix) and "." not in topic[len(prefix):]
        return pattern == topic

    # ------------------------------------------------------------------
    # Convenience event helpers
    # ------------------------------------------------------------------

    def emit(self, topic: str, data: Dict[str, Any] = None,
             source: str = "kernel", priority: EventPriority = EventPriority.NORMAL) -> int:
        """Create and publish an event in one call."""
        event = Event(
            topic=topic,
            data=data or {},
            source=source,
            priority=priority,
        )
        return self.publish(event)

    def emit_async(self, topic: str, data: Dict[str, Any] = None,
                   source: str = "kernel") -> int:
        """Create and fire-and-forget an event."""
        event = Event(
            topic=topic,
            data=data or {},
            source=source,
        )
        return self.publish_async(event)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Shut down the event bus — no more events accepted."""
        self._shutdown_flag = True
        with self._lock:
            self._subscriptions.clear()
            self._wildcard_subs.clear()
        logger.info("EventBus: shut down (%d events delivered)", self._publish_count)

    def get_stats(self) -> Dict[str, Any]:
        """Return event bus statistics."""
        with self._lock:
            sub_count = sum(len(v) for v in self._subscriptions.values()) + len(self._wildcard_subs)
            active_count = sum(
                1 for subs in self._subscriptions.values()
                for s in subs if s.active
            ) + sum(1 for s in self._wildcard_subs if s.active)
        return {
            "publish_count": self._publish_count,
            "error_count": self._error_count,
            "subscriptions_total": sub_count,
            "subscriptions_active": active_count,
            "topics": list(self._subscriptions.keys()),
        }


# Predefined event topics for kernel-wide use
class EventTopics:
    """Canonical event topic constants."""
    # Lifecycle
    LIFECYCLE_STARTING = "lifecycle.starting"
    LIFECYCLE_STARTED = "lifecycle.started"
    LIFECYCLE_STOPPING = "lifecycle.stopping"
    LIFECYCLE_STOPPED = "lifecycle.stopped"
    LIFECYCLE_HEALTH = "lifecycle.health"

    # Agent
    AGENT_STARTED = "agent.started"
    AGENT_FINISHED = "agent.finished"
    AGENT_ERROR = "agent.error"
    AGENT_INTERRUPTED = "agent.interrupted"

    # Task
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_PROGRESS = "task.progress"

    # Tool
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Memory
    MEMORY_UPDATED = "memory.updated"
    MEMORY_READ = "memory.read"

    # Workspace
    WORKSPACE_CHANGED = "workspace.changed"
    WORKSPACE_CREATED = "workspace.created"

    # Plugin
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"

    # System
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_CONFIG_CHANGED = "system.config_changed"
    SYSTEM_ERROR = "system.error"
