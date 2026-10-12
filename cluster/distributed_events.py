"""
Distributed Event Bus — propagates cluster events across all connected nodes.

Extends the kernel EventBus with cluster-wide event distribution.
Events are propagated to remote nodes through the transport layer.
Supports scoped events (local, cluster-wide, directed).
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus, Event as KernelEvent, EventPriority

from cluster.transport import TransportProvider, Message, MessageType

logger = logging.getLogger(__name__)


class EventScope(enum.Enum):
    """Scope for event distribution."""
    LOCAL = "local"            # Only on this node
    CLUSTER = "cluster"        # All nodes in the cluster
    DIRECTED = "directed"      # Specific target node


@dataclass
class ClusterEvent:
    """An event in the distributed cluster event bus.

    Attributes:
        id: Unique event ID
        topic: Event topic
        data: Event payload
        source: Source node ID
        scope: Distribution scope
        target_node: Target node (for DIRECTED scope)
        timestamp: Event creation time
        priority: Event priority
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    scope: EventScope = EventScope.CLUSTER
    target_node: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL


class DistributedEventBus:
    """Distributed event bus that propagates events across cluster nodes.

    Integrates with the kernel EventBus for local events and propagates
    cluster-scoped events to all connected nodes via the transport layer.

    Usage:
        local_bus = EventBus()
        transport = RequestResponseTransport(...)
        dist_bus = DistributedEventBus(local_bus, transport, node_id="node-1")

        # Emit a cluster-wide event
        dist_bus.emit_cluster("cluster.workflow_started", {"workflow_id": "..."})

        # Subscribe to local + cluster events
        dist_bus.subscribe("cluster.*", my_handler)
    """

    def __init__(
        self,
        local_bus: EventBus,
        transport: Optional[TransportProvider] = None,
        node_id: str = "",
    ):
        self._local_bus = local_bus
        self._transport = transport
        self._node_id = node_id
        self._lock = threading.RLock()

        # Remote event listeners
        self._remote_listeners: Dict[str, List[Callable[[ClusterEvent], None]]] = {}

        # Event deduplication (prevent echo loops)
        self._seen_events: Dict[str, float] = {}
        self._dedup_ttl = 5.0  # seconds

        # Propagation statistics
        self._events_published = 0
        self._events_received = 0
        self._events_filtered = 0

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def emit_local(self, topic: str, data: Dict[str, Any] = None) -> None:
        """Emit an event locally only (no cluster propagation)."""
        event = ClusterEvent(
            topic=topic,
            data=data or {},
            source=self._node_id,
            scope=EventScope.LOCAL,
        )
        self._deliver_local(event)

    def emit_cluster(self, topic: str, data: Dict[str, Any] = None) -> None:
        """Emit an event to all cluster nodes."""
        event = ClusterEvent(
            topic=topic,
            data=data or {},
            source=self._node_id,
            scope=EventScope.CLUSTER,
        )
        self._deliver_local(event)
        self._propagate(event)

    def emit_directed(self, topic: str, data: Dict[str, Any],
                      target_node: str) -> None:
        """Emit an event to a specific node."""
        event = ClusterEvent(
            topic=topic,
            data=data,
            source=self._node_id,
            scope=EventScope.DIRECTED,
            target_node=target_node,
        )
        self._deliver_local(event)
        self._propagate(event)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, topic_pattern: str,
                  callback: Callable[[ClusterEvent], None],
                  local_only: bool = False) -> Callable:
        """Subscribe to cluster events matching a topic pattern.

        Subscribes both locally (via kernel EventBus) and to remote events.

        Args:
            topic_pattern: Topic pattern (supports * and ** wildcards)
            callback: Callback receiving ClusterEvent
            local_only: Only receive local events

        Returns:
            Unsubscribe function
        """
        # Subscribe to local events
        local_sub = self._local_bus.subscribe(
            topic_pattern,
            lambda ke: callback(ClusterEvent(
                id=ke.id,
                topic=ke.topic,
                data=ke.data,
                source=ke.source,
                scope=EventScope.LOCAL,
                timestamp=ke.timestamp,
            )),
        )

        # Also register for remote events
        if not local_only:
            with self._lock:
                self._remote_listeners.setdefault(topic_pattern, []).append(callback)

        def unsubscribe():
            local_sub.cancel()
            with self._lock:
                listeners = self._remote_listeners.get(topic_pattern, [])
                if callback in listeners:
                    listeners.remove(callback)

        return unsubscribe

    # ------------------------------------------------------------------
    # Local delivery
    # ------------------------------------------------------------------

    def _deliver_local(self, event: ClusterEvent) -> None:
        """Deliver an event to local subscribers."""
        kernel_event = KernelEvent(
            topic=event.topic,
            data=event.data,
            source=event.source or "cluster",
            id=event.id,
            timestamp=event.timestamp,
            priority=event.priority,
        )
        self._local_bus.publish(kernel_event)
        self._events_published += 1

    # ------------------------------------------------------------------
    # Remote propagation
    # ------------------------------------------------------------------

    def _propagate(self, event: ClusterEvent) -> None:
        """Propagate an event to remote nodes via transport."""
        if self._transport is None:
            return

        # Deduplication check
        dedup_key = f"{event.id}:{event.topic}"
        with self._lock:
            if dedup_key in self._seen_events:
                return  # Already seen — skip propagation
            self._seen_events[dedup_key] = time.time()
            # Clean stale entries
            self._prune_seen()

        message = Message(
            id=event.id,
            message_type=MessageType.EVENT,
            source=self._node_id,
            method=event.topic,
            params={
                "id": event.id,
                "topic": event.topic,
                "data": event.data,
                "source": event.source,
                "scope": event.scope.value,
                "target_node": event.target_node,
                "timestamp": event.timestamp,
            },
        )

        try:
            self._transport.send(message)
        except Exception as exc:
            logger.warning(
                "DistributedEventBus: propagation failed for %s: %s",
                event.topic, exc,
            )

    def receive_event(self, message: Message) -> None:
        """Receive an event from a remote node via transport."""
        params = message.params or {}

        # Deduplication
        dedup_key = f"{message.id}:{message.method}"
        with self._lock:
            if dedup_key in self._seen_events:
                return
            self._seen_events[dedup_key] = time.time()

        event = ClusterEvent(
            id=message.id,
            topic=message.method,
            data=params.get("data", {}),
            source=params.get("source", message.source),
            scope=EventScope(
                params.get("scope", EventScope.CLUSTER.value)
            ),
            target_node=params.get("target_node"),
            timestamp=params.get("timestamp", time.time()),
        )

        # Check directed events
        if event.scope == EventScope.DIRECTED:
            if event.target_node and event.target_node != self._node_id:
                self._events_filtered += 1
                return  # Not for us

        # Deliver locally
        self._deliver_local(event)
        self._events_received += 1

        # Deliver to remote listeners
        self._deliver_to_listeners(event)

    def _deliver_to_listeners(self, event: ClusterEvent) -> None:
        """Deliver event to registered remote event listeners."""
        with self._lock:
            listeners = list(self._remote_listeners.items())

        for pattern, callbacks in listeners:
            if self._topic_matches(pattern, event.topic):
                for cb in callbacks:
                    try:
                        cb(event)
                    except Exception as exc:
                        logger.debug(
                            "DistributedEventBus: listener failed: %s", exc,
                        )

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Check if a wildcard pattern matches a topic string."""
        if pattern == "**":
            return True
        if pattern.endswith(".**"):
            prefix = pattern[:-3]
            return topic.startswith(prefix)
        if pattern.endswith(".*"):
            prefix = pattern[:-1]
            return topic.startswith(prefix) and "." not in topic[len(prefix):]
        return pattern == topic

    def _prune_seen(self) -> None:
        """Remove stale deduplication entries."""
        now = time.time()
        stale = [
            k for k, v in self._seen_events.items()
            if now - v > self._dedup_ttl
        ]
        for k in stale:
            del self._seen_events[k]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return distributed event bus statistics."""
        with self._lock:
            return {
                "events_published": self._events_published,
                "events_received": self._events_received,
                "events_filtered": self._events_filtered,
                "dedup_cache_size": len(self._seen_events),
                "remote_listeners": sum(
                    len(v) for v in self._remote_listeners.values()
                ),
            }
