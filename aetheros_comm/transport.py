"""
Agent Communication Fabric — transport abstraction (master spec step 2).

Every physical transport (in-process bus, kernel inter-agent bus, swarm bus,
the async orchestrator event bus, or the cluster HTTP transport) exposes the
same logical :class:`AgentTransport` interface. The fabric never forces a
physical protocol — it drives whichever existing transport is configured, and
applies the envelope / security / reliability layers uniformly on top.

The default implementation, :class:`LocalAgentBus`, is a thread-safe
in-process bus used by the fabric's own agents and by the security and stress
tests. Adapters wrap the *existing* AetherOS buses rather than duplicating
them:

    - :class:`KernelBusTransport`  -> ``kernel.inter_agent.InterAgentBus``
    - :class:`SwarmBusTransport`   -> ``swarm.communication.InterAgentMessageBus``
    - :class:`OrchestratorBusTransport` -> ``aetheros_orchestrator.bus.EventBus``
    - :class:`ClusterTransport`    -> ``cluster.transport.RequestResponseTransport``

Connection lifecycle states follow master spec step 49:
CONNECTING, AUTHENTICATING, READY, DEGRADED, RECONNECTING, CLOSING, CLOSED,
FAILED.
"""

from __future__ import annotations

import abc
import asyncio
import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .envelope import AgentMessageEnvelope

logger = logging.getLogger(__name__)

#: Inbound handler signature: ``callable(envelope) -> Optional[response]``
InboundHandler = Callable[[AgentMessageEnvelope], Optional[AgentMessageEnvelope]]


class TransportState(str, enum.Enum):
    """Connection lifecycle states (master spec step 49)."""

    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


@dataclass
class SendReceipt:
    """Result of a transport send attempt."""

    message_id: str
    delivered: bool
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "delivered": self.delivered,
            "error": self.error,
        }


@dataclass
class TransportHealth:
    """Health snapshot for a transport."""

    state: TransportState
    latency_ms: float = 0.0
    last_error: str = ""
    agents_connected: int = 0

    @property
    def ready(self) -> bool:
        return self.state in (TransportState.READY, TransportState.DEGRADED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "latency_ms": self.latency_ms,
            "last_error": self.last_error,
            "agents_connected": self.agents_connected,
        }


class AgentTransport(abc.ABC):
    """Logical transport interface shared by every implementation."""

    name: str = "abstract"
    state: TransportState = TransportState.CLOSED

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish the connection (open bus / sockets / listener)."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection, releasing all resources."""

    @abc.abstractmethod
    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        """Deliver ``envelope`` to its recipient (or broadcast)."""

    @abc.abstractmethod
    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        """Subscribe ``handler`` to envelopes addressed to ``agent_id``.

        Returns an unsubscribe callable.
        """

    def request(self, envelope: AgentMessageEnvelope,
                timeout: float = 30.0) -> Optional[AgentMessageEnvelope]:
        """Send a request and wait for the correlated response.

        Default implementation raises ``NotImplementedError``; transports
        with native request/response override it.
        """
        raise NotImplementedError(
            f"transport {self.name} does not support request/response")

    def broadcast(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        return self.send(envelope)

    def health(self) -> TransportHealth:
        return TransportHealth(state=self.state)

    @property
    def is_ready(self) -> bool:
        return self.state in (TransportState.READY, TransportState.DEGRADED)


# ---------------------------------------------------------------------------
# Local in-process bus (default transport)
# ---------------------------------------------------------------------------


@dataclass
class _PendingResponse:
    correlation_id: str
    request_message_id: str
    event: threading.Event
    response: Optional[AgentMessageEnvelope] = None


class LocalAgentBus(AgentTransport):
    """Thread-safe, in-process message bus.

    Supports directed delivery, broadcast, and correlation-based
    request/response. This is the default fabric transport: no external
    dependencies, deterministic, and ideal for the security / stress tests.
    """

    name = "local"

    def __init__(self) -> None:
        self.state = TransportState.CLOSED
        self._lock = threading.RLock()
        self._agents: set[str] = set()
        self._subscriptions: Dict[str, List[InboundHandler]] = {}
        self._wildcards: List[InboundHandler] = []
        self._pending: Dict[str, _PendingResponse] = {}
        self._dead_letter: List[AgentMessageEnvelope] = []
        self._history: List[str] = []
        self._max_history = 10000

    # -- lifecycle ----------------------------------------------------------

    def connect(self) -> None:
        self.state = TransportState.READY

    def disconnect(self) -> None:
        with self._lock:
            self.state = TransportState.CLOSED
            self._subscriptions.clear()
            self._wildcards.clear()
            self._agents.clear()
            self._pending.clear()

    # -- agent registration -------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agents.add(agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agents.discard(agent_id)
            self._subscriptions.pop(agent_id, None)

    def registered_agents(self) -> List[str]:
        with self._lock:
            return sorted(self._agents)

    # -- subscription -------------------------------------------------------

    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        with self._lock:
            self._subscriptions.setdefault(agent_id, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                subs = self._subscriptions.get(agent_id, [])
                if handler in subs:
                    subs.remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: InboundHandler) -> Callable[[], None]:
        """Subscribe to every envelope (used by the fabric inbound pipeline)."""
        with self._lock:
            self._wildcards.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._wildcards:
                    self._wildcards.remove(handler)

        return unsubscribe

    # -- delivery -----------------------------------------------------------

    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        with self._lock:
            if self.state != TransportState.READY:
                return SendReceipt(envelope.messageId, False,
                                   "transport not ready")
            recipient = envelope.receiverAgentId
            if recipient:
                if recipient not in self._agents:
                    self._dead_letter.append(envelope)
                    return SendReceipt(
                        envelope.messageId, False,
                        f"no such agent: {recipient}")
                subs = list(self._subscriptions.get(recipient, []))
                # The fabric pipeline subscribes a wildcard handler; agent
                # handlers may also be attached for tests / standalone use.
                deliver = list(subs)
                if not deliver and not self._wildcards:
                    self._dead_letter.append(envelope)
                    return SendReceipt(
                        envelope.messageId, False, "no subscriber")
            else:
                deliver = []
                for other in self._agents:
                    if other == envelope.senderAgentId:
                        continue
                    deliver.extend(
                        self._subscriptions.get(other, []))
                if not deliver and not self._wildcards:
                    self._dead_letter.append(envelope)
                    return SendReceipt(
                        envelope.messageId, False, "no broadcast subscribers")

            wildcards = list(self._wildcards)

        self._record_history(envelope)

        # Correlated responses are captured directly (a response envelope sent
        # back through the bus), but never the request itself.
        if envelope.correlationId:
            with self._lock:
                pending = self._pending.get(envelope.correlationId)
            if pending is not None and envelope.messageId != pending.request_message_id:
                pending.response = envelope
                pending.event.set()

        errors = []
        responses_returned = []
        for handler in deliver + wildcards:
            try:
                result = handler(envelope)
                if isinstance(result, AgentMessageEnvelope):
                    responses_returned.append(result)
            except Exception as exc:  # noqa: BLE001 - isolate handlers
                errors.append(str(exc))
                logger.warning("LocalAgentBus handler failed: %s", exc)

        # Capture correlated responses returned by handlers (a handler may
        # produce the response to an outstanding request instead of sending
        # it back through the bus).
        for response in responses_returned:
            if response.correlationId:
                with self._lock:
                    pending = self._pending.get(response.correlationId)
                if pending is not None and response.messageId != pending.request_message_id:
                    pending.response = response
                    pending.event.set()

        if errors:
            return SendReceipt(envelope.messageId, True,
                               "; ".join(errors)[:500])
        return SendReceipt(envelope.messageId, True)

    def request(self, envelope: AgentMessageEnvelope,
                timeout: float = 30.0) -> Optional[AgentMessageEnvelope]:
        """Send ``envelope`` and wait for the correlated response.

        Returns the response envelope, or ``None`` on timeout.
        """
        correlation_id = envelope.correlationId or uuid.uuid4().hex
        envelope.correlationId = correlation_id
        pending = _PendingResponse(correlation_id=correlation_id,
                                   request_message_id=envelope.messageId,
                                   event=threading.Event())
        with self._lock:
            self._pending[correlation_id] = pending
        try:
            self.send(envelope)
            pending.event.wait(timeout=timeout)
            return pending.response
        finally:
            with self._lock:
                self._pending.pop(correlation_id, None)

    # -- state --------------------------------------------------------------

    def _record_history(self, envelope: AgentMessageEnvelope) -> None:
        with self._lock:
            self._history.append(envelope.messageId)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def health(self) -> TransportHealth:
        return TransportHealth(
            state=self.state,
            latency_ms=0.0,
            agents_connected=len(self.registered_agents()),
        )

    def get_dead_letter(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            batch = self._dead_letter[-limit:]
            return [e.to_dict() for e in batch]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "messages": len(self._history),
            "agents": len(self.registered_agents()),
            "dead_letter": len(self._dead_letter),
            "pending": len(self._pending),
            "state": self.state.value,
        }


# ---------------------------------------------------------------------------
# Adapters over existing AetherOS buses
# ---------------------------------------------------------------------------


class KernelBusTransport(AgentTransport):
    """Adapter over ``kernel.inter_agent.InterAgentBus``.

    Envelopes are carried inside the existing bus's payload so the kernel bus
    remains the substrate (no competing transport is created).
    """

    name = "kernel"

    def __init__(self, bus: Any = None) -> None:
        self.state = TransportState.CLOSED
        self._bus = bus
        self._owned_bus = bus is None
        self._unsubs: List[Callable[[], None]] = []

    def connect(self) -> None:
        if self._bus is None:
            from kernel.inter_agent import InterAgentBus
            self._bus = InterAgentBus()
        self.state = TransportState.READY

    def disconnect(self) -> None:
        self.state = TransportState.CLOSED
        if self._owned_bus and self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
        self._unsubs.clear()

    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        if self._bus is None or self.state != TransportState.READY:
            return SendReceipt(envelope.messageId, False, "not ready")
        from kernel.inter_agent import AgentMessage, MessageType
        recipient = envelope.receiverAgentId or None
        msg = AgentMessage(
            type=MessageType.DIRECT if recipient else MessageType.BROADCAST,
            sender=envelope.senderAgentId,
            recipient=recipient or "",
            payload=envelope.to_dict(),
            correlation_id=envelope.correlationId,
            metadata=envelope.metadata,
        )
        try:
            ok = self._bus.send(msg)
            return SendReceipt(envelope.messageId, ok)
        except Exception as exc:
            return SendReceipt(envelope.messageId, False, str(exc))

    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        if self._bus is None:
            self.connect()
        self._bus.register_agent(agent_id)

        def wrapped(message: Any) -> None:
            data = getattr(message, "payload", None)
            if isinstance(data, dict):
                handler(AgentMessageEnvelope.from_dict(data))

        # Kernel bus delivers to inboxes; also attach a channel subscription
        # so messages addressed to this agent reach the handler.
        self._bus.subscribe(agent_id, agent_id, wrapped)

        def unsubscribe() -> None:
            try:
                self._bus.unsubscribe(agent_id, agent_id)
            except Exception:
                pass

        self._unsubs.append(unsubscribe)
        return unsubscribe


class SwarmBusTransport(AgentTransport):
    """Adapter over ``swarm.communication.InterAgentMessageBus``."""

    name = "swarm"

    def __init__(self, bus: Any = None) -> None:
        self.state = TransportState.CLOSED
        self._bus = bus
        self._unsubs: List[Callable[[], None]] = []

    def connect(self) -> None:
        if self._bus is None:
            from swarm.communication import InterAgentMessageBus
            self._bus = InterAgentMessageBus()
        self.state = TransportState.READY

    def disconnect(self) -> None:
        self.state = TransportState.CLOSED
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._unsubs.clear()

    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        if self._bus is None or self.state != TransportState.READY:
            return SendReceipt(envelope.messageId, False, "not ready")
        from swarm.communication import AgentMessage, MessageType
        msg = AgentMessage(
            id=envelope.messageId[:12],
            message_type=(MessageType.REQUEST
                          if envelope.correlationId else MessageType.EVENT),
            sender=envelope.senderAgentId,
            recipient=envelope.receiverAgentId or None,
            payload=envelope.to_dict(),
            correlation_id=envelope.correlationId or None,
            priority=envelope.priority,
        )
        try:
            self._bus.send(msg)
            return SendReceipt(envelope.messageId, True)
        except Exception as exc:
            return SendReceipt(envelope.messageId, False, str(exc))

    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        if self._bus is None:
            self.connect()

        def wrapped(message: Any) -> None:
            data = getattr(message, "payload", None)
            if isinstance(data, dict):
                handler(AgentMessageEnvelope.from_dict(data))

        unsub = self._bus.subscribe(agent_id, wrapped)
        self._unsubs.append(unsub)
        return unsub


class OrchestratorBusTransport(AgentTransport):
    """Async adapter over ``aetheros_orchestrator.bus.event_bus.EventBus``.

    The existing event bus is driven from its own background event loop, so
    this transport exposes the synchronous :class:`AgentTransport` interface
    while publishing on ``agent.comm.<receiver>`` topics.
    """

    name = "orchestrator"

    def __init__(self, bus: Any = None) -> None:
        self.state = TransportState.CLOSED
        self._bus = bus
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._unsubs: List[Callable[[], None]] = []

    def connect(self) -> None:
        if self._bus is None:
            from aetheros_orchestrator.bus.event_bus import EventBus
            self._bus = EventBus()
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._run_loop, name="comm-orchestrator-bus",
                daemon=True)
            self._thread.start()
        self._submit(self._bus.start())
        self.state = TransportState.READY

    def _run_loop(self) -> None:
        if self._loop is not None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

    def _submit(self, coro):
        if self._loop is None:
            return
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def disconnect(self) -> None:
        self.state = TransportState.CLOSED
        if self._loop is not None and self._bus is not None:
            future = self._submit(self._bus.stop())
            if future is not None:
                try:
                    future.result(timeout=2.0)
                except Exception:
                    pass
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=2.0)
        self._loop = None
        self._thread = None
        self._unsubs.clear()

    def _topic(self, agent_id: str) -> str:
        return f"agent.comm.{agent_id}"

    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        if self._bus is None or self.state != TransportState.READY:
            return SendReceipt(envelope.messageId, False, "not ready")
        target = envelope.receiverAgentId or "*"
        try:
            self._submit(self._bus.publish(
                self._topic(target), envelope.to_dict(), source=envelope.senderAgentId))
            return SendReceipt(envelope.messageId, True)
        except Exception as exc:
            return SendReceipt(envelope.messageId, False, str(exc))

    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        if self._bus is None:
            self.connect()

        def wrapped(event: Dict[str, Any]) -> None:
            data = event.get("data")
            if isinstance(data, dict):
                handler(AgentMessageEnvelope.from_dict(data))

        self._bus.subscribe(self._topic(agent_id), wrapped)

        def unsubscribe() -> None:
            try:
                self._bus.unsubscribe(self._topic(agent_id), wrapped)
            except Exception:
                pass

        self._unsubs.append(unsubscribe)
        return unsubscribe

    def health(self) -> TransportHealth:
        return TransportHealth(
            state=self.state,
            agents_connected=len(self._unsubs),
        )


class ClusterTransport(AgentTransport):
    """Adapter over ``cluster.transport.RequestResponseTransport``.

    Designed for distributed deployments: envelopes travel as cluster
    ``Message`` frames (HTTP POST or TLS-secured, per the cluster config).
    Remote communication must never silently downgrade to an insecure
    transport — the caller configures TLS via the cluster transport
    (step 48).
    """

    name = "cluster"

    def __init__(self, transport: Any = None,
                 *, local_node_id: str = "") -> None:
        self.state = TransportState.CLOSED
        self._transport = transport
        self._local_node_id = local_node_id
        self._unsubs: List[Callable[[], None]] = []

    def connect(self) -> None:
        if self._transport is None:
            from cluster.transport import RequestResponseTransport
            self._transport = RequestResponseTransport(
                node_id=self._local_node_id or "comm-fabric")
        try:
            self._transport.start()
            self.state = TransportState.READY
        except Exception as exc:
            logger.error("ClusterTransport connect failed: %s", exc)
            self.state = TransportState.FAILED
            raise

    def disconnect(self) -> None:
        if self._transport is not None:
            try:
                self._transport.stop()
            except Exception:
                pass
        self.state = TransportState.CLOSED
        self._unsubs.clear()

    def send(self, envelope: AgentMessageEnvelope) -> SendReceipt:
        if self._transport is None or self.state != TransportState.READY:
            return SendReceipt(envelope.messageId, False, "not ready")
        try:
            from cluster.transport import Message, MessageType
            message = Message(
                message_type=MessageType.REQUEST,
                source=envelope.senderAgentId,
                destination=envelope.receiverAgentId,
                method=envelope.messageType,
                params=envelope.to_dict(),
                correlation_id=envelope.correlationId or None,
                metadata={"protocolVersion": envelope.protocolVersion},
            )
            response = self._transport.send(message)
            ok = response is not None or not envelope.receiverAgentId
            return SendReceipt(envelope.messageId, ok)
        except Exception as exc:
            return SendReceipt(envelope.messageId, False, str(exc))

    def subscribe(self, agent_id: str,
                  handler: InboundHandler) -> Callable[[], None]:
        # The cluster transport is request/response; the remote endpoint
        # answers via the fabric's own inbound pipeline. Local subscriptions
        # are tracked so health reporting stays accurate.
        def unsubscribe() -> None:
            pass

        self._unsubs.append(unsubscribe)
        return unsubscribe

    def health(self) -> TransportHealth:
        connected = 0
        try:
            if self._transport is not None:
                for node in getattr(self._transport, "nodes", []) or []:
                    if self._transport.is_connected(node):
                        connected += 1
        except Exception:
            pass
        return TransportHealth(state=self.state,
                               agents_connected=connected)