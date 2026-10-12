"""
Inter-Agent Communication — structured messaging between swarm agents.

Provides a message bus for agents to communicate without direct coupling.
Supports requests, responses, events, broadcast, and private messaging.

Agents communicate through the message bus, never directly.
This keeps the system decoupled and allows the event bus to
monitor all inter-agent communication.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class MessageType(enum.Enum):
    """Types of messages agents can send to each other."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    BROADCAST = "broadcast"
    PRIVATE = "private"
    QUERY = "query"
    RESULT = "result"
    STATUS = "status"
    ERROR = "error"
    CANCEL = "cancel"


@dataclass
class AgentMessage:
    """A structured message between agents in the swarm.

    Attributes:
        id: Unique message ID
        message_type: Type of message
        sender: Sender agent ID
        recipient: Recipient agent ID (None for broadcast)
        topic: Message topic / subject
        payload: Message payload (any serializable data)
        correlation_id: Links responses to requests
        timestamp: Creation timestamp
        priority: Message priority
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    message_type: MessageType = MessageType.EVENT
    sender: str = ""
    recipient: Optional[str] = None
    topic: str = ""
    payload: Any = None
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)


class InterAgentMessageBus:
    """Message bus for inter-agent communication.

    Provides topic-based pub/sub for agent-to-agent messages.
    Integrates with the kernel event bus for observability.

    Usage:
        bus = InterAgentMessageBus(kernel_event_bus)

        # Send a message to a specific agent
        bus.send(AgentMessage(
            message_type=MessageType.REQUEST,
            sender="coordinator",
            recipient="coding-agent",
            topic="write_code",
            payload={"file": "main.py", "content": "..."},
        ))

        # Subscribe to messages
        bus.subscribe("coordinator", my_handler)

        # Wait for a response
        response = bus.wait_for_response(request_id, timeout=30)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        # recipient -> list of callbacks
        self._subscriptions: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        # Wildcard subscribers (receive all messages)
        self._wildcard_subs: List[Callable[[AgentMessage], None]] = []
        # Correlation ID -> pending response
        self._pending_responses: Dict[str, "threading.Event"] = {}
        self._response_data: Dict[str, AgentMessage] = {}
        # Message history (for telemetry)
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def send(self, message: AgentMessage) -> None:
        """Send a message to its recipient."""
        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history = self._message_history[-self._max_history:]

        if self._event_bus:
            self._event_bus.emit_async("swarm.message_sent", {
                "message_id": message.id,
                "message_type": message.message_type.value,
                "sender": message.sender,
                "recipient": message.recipient,
                "topic": message.topic,
            })

        # Deliver to recipient
        if message.recipient:
            self._deliver(message.recipient, message)
        else:
            # Broadcast to all
            self._broadcast(message)

        # Also deliver to wildcard subscribers
        self._deliver_wildcard(message)

    def request(self, sender: str, recipient: str, topic: str,
                payload: Any = None, timeout: float = 30.0,
                priority: int = 50) -> Optional[AgentMessage]:
        """Send a request and wait for a response.

        Returns the response message, or None on timeout.
        """
        correlation_id = uuid.uuid4().hex[:12]
        request = AgentMessage(
            message_type=MessageType.REQUEST,
            sender=sender,
            recipient=recipient,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
        )

        response_event = threading.Event()
        with self._lock:
            self._pending_responses[correlation_id] = response_event

        self.send(request)

        # Wait for response
        response_event.wait(timeout=timeout)

        with self._lock:
            self._pending_responses.pop(correlation_id, None)
            response = self._response_data.pop(correlation_id, None)

        return response

    def respond(self, request: AgentMessage, payload: Any = None) -> None:
        """Send a response to a prior request."""
        response = AgentMessage(
            message_type=MessageType.RESPONSE,
            sender=request.recipient or "",
            recipient=request.sender,
            topic=request.topic,
            payload=payload,
            correlation_id=request.correlation_id or request.id,
        )

        # Signal waiting requesters
        corr_id = response.correlation_id
        if corr_id:
            with self._lock:
                self._response_data[corr_id] = response
                pending = self._pending_responses.get(corr_id)
                if pending:
                    pending.set()

        self.send(response)

    def broadcast(self, sender: str, topic: str, payload: Any = None) -> None:
        """Send a message to all agents."""
        message = AgentMessage(
            message_type=MessageType.BROADCAST,
            sender=sender,
            topic=topic,
            payload=payload,
        )
        self.send(message)

    def _deliver(self, recipient: str, message: AgentMessage) -> None:
        """Deliver a message to a specific subscriber."""
        with self._lock:
            subs = list(self._subscriptions.get(recipient, []))

        for cb in subs:
            try:
                cb(message)
            except Exception as exc:
                logger.warning(
                    "InterAgentMessageBus: subscriber %s failed: %s",
                    recipient, exc,
                )

    def _broadcast(self, message: AgentMessage) -> None:
        """Deliver to all subscribers."""
        with self._lock:
            all_subs = list(self._subscriptions.values())

        for subs in all_subs:
            for cb in subs:
                try:
                    cb(message)
                except Exception as exc:
                    logger.warning(
                        "InterAgentMessageBus: broadcast subscriber failed: %s",
                        exc,
                    )

    def _deliver_wildcard(self, message: AgentMessage) -> None:
        """Deliver to wildcard subscribers."""
        with self._lock:
            subs = list(self._wildcard_subs)
        for cb in subs:
            try:
                cb(message)
            except Exception as exc:
                logger.warning(
                    "InterAgentMessageBus: wildcard subscriber failed: %s",
                    exc,
                )

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, agent_id: str,
                  callback: Callable[[AgentMessage], None]) -> Callable:
        """Subscribe an agent to receive messages.

        Returns a function that can be called to unsubscribe.
        """
        with self._lock:
            self._subscriptions.setdefault(agent_id, []).append(callback)

        def unsubscribe():
            with self._lock:
                subs = self._subscriptions.get(agent_id, [])
                if callback in subs:
                    subs.remove(callback)

        return unsubscribe

    def subscribe_all(self, callback: Callable[[AgentMessage], None]) -> Callable:
        """Subscribe to ALL messages (wildcard).

        Returns an unsubscribe function.
        """
        with self._lock:
            self._wildcard_subs.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._wildcard_subs:
                    self._wildcard_subs.remove(callback)

        return unsubscribe

    def unsubscribe_all(self, agent_id: str) -> int:
        """Remove all subscriptions for an agent. Returns count removed."""
        with self._lock:
            subs = self._subscriptions.pop(agent_id, [])
            return len(subs)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return message bus statistics."""
        with self._lock:
            sub_count = sum(len(v) for v in self._subscriptions.values())
            sub_count += len(self._wildcard_subs)
            return {
                "total_messages": len(self._message_history),
                "subscriber_count": sub_count,
                "pending_responses": len(self._pending_responses),
                "agent_count": len(self._subscriptions),
            }

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages (for monitoring)."""
        with self._lock:
            recent = self._message_history[-limit:]
            return [
                {
                    "id": m.id,
                    "type": m.message_type.value,
                    "sender": m.sender,
                    "recipient": m.recipient,
                    "topic": m.topic,
                    "timestamp": m.timestamp,
                }
                for m in recent
            ]

    def clear_history(self) -> None:
        """Clear message history."""
        with self._lock:
            self._message_history.clear()
