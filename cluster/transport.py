"""
Transport Provider — abstract communication layer between cluster nodes.

Provides:
  - Request/response messaging (works over real TCP/HTTP in networked mode)
  - Streaming data transfer
  - Heartbeats
  - Automatic retries with backoff
  - Timeouts
  - Replaceable transport implementations

Built-in implementations:
  - RequestResponseTransport: HTTP/JSON-based transport (default).
    In standalone mode (single process) messages route in-process; in
    networked mode (standalone=False) they go over HTTP POST between
    nodes, with real request/response correlation.
"""

from __future__ import annotations

import abc
import enum
import json
import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MessageType(enum.Enum):
    """Types of messages exchanged between cluster nodes."""
    REQUEST = "request"
    RESPONSE = "response"
    STREAM_DATA = "stream_data"
    STREAM_END = "stream_end"
    STREAM_ERROR = "stream_error"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    EVENT = "event"
    ERROR = "error"
    CANCEL = "cancel"


@dataclass
class Message:
    """A structured message between cluster nodes."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    message_type: MessageType = MessageType.REQUEST
    source: str = ""
    destination: str = ""
    method: str = ""
    params: Any = None
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0
    requires_ordering: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "source": self.source,
            "destination": self.destination,
            "method": self.method,
            "params": self.params,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "timeout_seconds": self.timeout_seconds,
            "requires_ordering": self.requires_ordering,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            id=data.get("id", ""),
            message_type=MessageType(data.get("message_type", "request")),
            source=data.get("source", ""),
            destination=data.get("destination", ""),
            method=data.get("method", ""),
            params=data.get("params"),
            correlation_id=data.get("correlation_id"),
            timestamp=data.get("timestamp", time.time()),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            requires_ordering=data.get("requires_ordering", False),
            metadata=data.get("metadata", {}),
        )


class TransportProvider(abc.ABC):
    """Abstract base class for cluster transport providers."""

    @abc.abstractmethod
    def send(self, message: Message) -> Optional[Message]:
        """Send a message; returns the response for request/response."""
        ...

    @abc.abstractmethod
    def start(self) -> None:
        """Start the transport layer (open connections, start listeners)."""
        ...

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the transport layer (close connections)."""
        ...

    @abc.abstractmethod
    def is_connected(self, node_id: str) -> bool:
        """Check if connected to a specific node."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def send_request(self, destination: str, method: str,
                     params: Any = None,
                     timeout: float = 30.0,
                     requires_ordering: bool = False) -> Optional[Message]:
        message = Message(
            message_type=MessageType.REQUEST,
            source="",
            destination=destination,
            method=method,
            params=params,
            timeout_seconds=timeout,
            requires_ordering=requires_ordering,
        )
        return self.send(message)

    def send_response(self, request: Message, result: Any = None) -> None:
        response = Message(
            message_type=MessageType.RESPONSE,
            source=request.destination,
            destination=request.source,
            method=request.method,
            params=result,
            correlation_id=request.id,
        )
        self.send(response)

    def send_heartbeat(self, destination: str) -> Optional[Message]:
        message = Message(
            message_type=MessageType.HEARTBEAT,
            source="",
            destination=destination,
            params={"timestamp": time.time()},
        )
        return self.send(message)

    def send_stream_data(self, destination: str, stream_id: str,
                         data: Any, sequence: int) -> None:
        message = Message(
            message_type=MessageType.STREAM_DATA,
            source="",
            destination=destination,
            params={"stream_id": stream_id, "data": data, "sequence": sequence},
        )
        self.send(message)

    def send_stream_end(self, destination: str, stream_id: str) -> None:
        message = Message(
            message_type=MessageType.STREAM_END,
            source="",
            destination=destination,
            params={"stream_id": stream_id},
        )
        self.send(message)

    def on_message(self, callback: Callable[[Message], Optional[Message]]) -> Callable:
        """Register a message handler.

        Handlers may return a Message to respond synchronously to a
        request (used by the RPC server).
        """
        raise NotImplementedError


class RequestResponseTransport(TransportProvider):
    """HTTP/JSON request/response transport.

    In standalone mode (single node), messages route through in-process
    handlers. In networked mode, requests go over HTTP POST and responses
    are correlated by message ID — this is a real network round trip.
    """

    def __init__(
        self,
        node_id: str = "",
        host: str = "127.0.0.1",
        port: int = 0,
        use_ssl: bool = False,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        standalone: bool = True,
        retries: int = 2,
        retry_delay: float = 0.5,
        request_timeout: float = 30.0,
    ):
        self._node_id = node_id
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._ca_cert = ca_cert
        self._client_cert = client_cert
        self._client_key = client_key
        self._standalone = standalone
        self._retries = max(0, retries)
        self._retry_delay = retry_delay
        self._request_timeout = request_timeout

        self._lock = threading.RLock()
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._server: Optional[Any] = None

        # node_id -> (host, port)
        self._connections: Dict[str, Tuple[str, int]] = {}
        self._handlers: List[Callable[[Message], Optional[Message]]] = []
        # Pending async responses: correlation_id -> threading.Event
        self._pending: Dict[str, threading.Event] = {}
        self._responses: Dict[str, Message] = {}

        # Stats
        self._stats_lock = threading.Lock()
        self._stats: Dict[str, int] = {
            "requests_sent": 0,
            "responses_received": 0,
            "requests_received": 0,
            "timeouts": 0,
            "send_failures": 0,
        }

    # ------------------------------------------------------------------
    # TransportProvider implementation
    # ------------------------------------------------------------------

    def send(self, message: Message, retries: Optional[int] = None) -> Optional[Message]:
        """Send a message and return the correlated response (if any).

        In standalone mode messages route through in-process handlers; in
        networked mode they go over HTTP POST to the destination node.
        """
        message.source = self._node_id
        if not message.timestamp:
            message.timestamp = time.time()

        if self._standalone or not message.destination or message.destination == self._node_id:
            return self._handle_local(message)

        return self._send_remote(
            message,
            retries=self._retries if retries is None else retries,
        )

    # ------------------------------------------------------------------
    # Local (in-process) delivery
    # ------------------------------------------------------------------

    def _handle_local(self, message: Message) -> Optional[Message]:
        """Deliver a message to local handlers and return a response if any.

        - RESPONSE messages resolve any pending async request.
        - REQUEST messages are delivered to handlers; the first handler that
          returns a Message provides the response synchronously.
        """
        if message.message_type == MessageType.RESPONSE:
            # Resolve a pending async request, if any
            if message.correlation_id:
                with self._lock:
                    event = self._pending.pop(message.correlation_id, None)
                    if event is not None:
                        self._responses[message.correlation_id] = message
                        event.set()
                        self._stats["responses_received"] += 1
            self._deliver(message)
            return None

        response: Optional[Message] = None
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                result = handler(message)
            except Exception as exc:
                logger.warning("Transport: handler failed: %s", exc)
                continue
            if isinstance(result, Message):
                response = result
                break

        if message.message_type == MessageType.REQUEST:
            self._stats["requests_received"] += 1
            if response is None:
                # No synchronous response — wait for an async one.
                corr_id = message.id
                event = threading.Event()
                with self._lock:
                    self._pending[corr_id] = event
                event.wait(timeout=message.timeout_seconds or self._request_timeout)
                with self._lock:
                    self._pending.pop(corr_id, None)
                    response = self._responses.pop(corr_id, None)
                if response is None:
                    self._stats["timeouts"] += 1
        return response

    def _deliver(self, message: Message) -> None:
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(message)
            except Exception as exc:
                logger.warning("Transport: handler failed: %s", exc)

    # ------------------------------------------------------------------
    # Remote delivery (real HTTP round trip)
    # ------------------------------------------------------------------

    def _send_remote(self, message: Message, retries: int = 2) -> Optional[Message]:
        import http.client

        connection_info = self._connections.get(message.destination)
        if not connection_info:
            logger.warning(
                "Transport: no connection info for node %s",
                message.destination[:8],
            )
            self._stats["send_failures"] += 1
            return None

        host, port = connection_info
        payload = json.dumps(message.to_dict())

        attempt = 0
        while True:
            try:
                if self._use_ssl:
                    import ssl
                    context = ssl.create_default_context()
                    if self._ca_cert:
                        context.load_verify_locations(self._ca_cert)
                    if self._client_cert and self._client_key:
                        context.load_cert_chain(self._client_cert, self._client_key)
                    conn: Any = http.client.HTTPSConnection(
                        host, port,
                        timeout=message.timeout_seconds or self._request_timeout,
                        context=context,
                    )
                else:
                    conn = http.client.HTTPConnection(
                        host, port,
                        timeout=message.timeout_seconds or self._request_timeout,
                    )

                headers = {"Content-Type": "application/json"}
                if self._node_id:
                    headers["X-Cluster-Node"] = self._node_id
                conn.request("POST", "/cluster/message", body=payload, headers=headers)
                response = conn.getresponse()
                body = response.read().decode("utf-8")
                conn.close()

                if response.status != 200:
                    self._stats["send_failures"] += 1
                    raise ConnectionError(
                        f"HTTP {response.status} from {message.destination[:8]}"
                    )

                self._stats["requests_sent"] += 1
                if not body:
                    return None
                data = json.loads(body)
                reply = Message.from_dict(data)
                if reply.message_type == MessageType.RESPONSE:
                    self._stats["responses_received"] += 1
                return reply

            except Exception as exc:
                attempt += 1
                logger.warning(
                    "Transport: send to %s failed (%d/%d): %s",
                    message.destination[:8], attempt, retries + 1, exc,
                )
                if attempt > retries:
                    self._stats["timeouts"] += 1
                    return None
                time.sleep(self._retry_delay * attempt)

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the transport.

        Standalone: mark running (no network). Networked: bind and serve
        an HTTP endpoint on the configured host/port.
        """
        if self._standalone:
            self._running = True
            return

        if self._running:
            return
        self._running = True
        self._server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="cluster-transport",
        )
        self._server_thread.start()
        # Wait for the socket to bind so callers can discover the port.
        for _ in range(100):
            if self._server is not None:
                break
            time.sleep(0.02)
        logger.info(
            "Transport: started on %s:%d (ssl=%s)",
            self._host, self._port, self._use_ssl,
        )

    def _run_server(self) -> None:
        import http.server as http_server

        class ClusterHandler(http_server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                if self.path != "/cluster/message":
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    data = json.loads(body)
                    message = Message.from_dict(data)
                    reply = transport_ref._handle_local(message)
                    if reply is not None:
                        payload = json.dumps(reply.to_dict()).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                    else:
                        self.send_response(200)
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                except Exception as exc:
                    logger.warning("Transport: server handler error: %s", exc)
                    self.send_response(500)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

            def do_GET(self):
                if self.path == "/health":
                    payload = json.dumps({"ok": True}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, fmt, *args):  # suppress request logs
                pass

        transport_ref = self

        # Retry bind a few times (port may briefly be in TIME_WAIT).
        server = None
        for _ in range(50):
            try:
                server = http_server.ThreadingHTTPServer((self._host, self._port), ClusterHandler)
                break
            except OSError as exc:
                last_exc = exc
                time.sleep(0.2)
        if server is None:
            logger.error("Transport: could not bind %s:%d: %s", self._host, self._port, last_exc)
            self._running = False
            return

        self._server = server
        # If the port was 0 (auto-assign), record the real bound port.
        if self._port == 0:
            self._port = server.server_address[1]
        while self._running:
            try:
                server.handle_request()
            except Exception as exc:
                if not self._running:
                    break
                logger.warning("Transport: server loop error: %s", exc)
                time.sleep(0.1)
        server.server_close()

    def stop(self) -> None:
        """Stop the transport and close the server."""
        self._running = False
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        logger.info("Transport: stopped")

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def is_connected(self, node_id: str) -> bool:
        return node_id in self._connections

    def add_connection(self, node_id: str, host: str, port: int) -> None:
        with self._lock:
            self._connections[node_id] = (host, port)
        logger.info("Transport: added connection to %s at %s:%d", node_id[:8], host, port)

    def remove_connection(self, node_id: str) -> bool:
        with self._lock:
            return self._connections.pop(node_id, None) is not None

    def list_connections(self) -> Dict[str, Tuple[str, int]]:
        with self._lock:
            return dict(self._connections)

    def on_message(self, callback: Callable[[Message], Optional[Message]]) -> Callable:
        """Register a message handler (may return a response Message)."""
        with self._lock:
            self._handlers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._handlers:
                    self._handlers.remove(callback)

        return unsubscribe

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "standalone": self._standalone,
                "host": self._host,
                "port": self._port,
                "connections": len(self._connections),
                "pending_responses": len(self._pending),
                "handlers": len(self._handlers),
                **dict(self._stats),
            }
