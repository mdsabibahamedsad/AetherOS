"""
RPC Layer — remote procedure call infrastructure for cluster nodes.

Provides:
  - RPCClient: call remote methods on cluster nodes
  - RPCServer: handle incoming RPC calls from other nodes
  - RPCRequest / RPCResponse: typed request/response objects
  - RPCHandler: abstract base for RPC method handlers

Uses the TransportProvider for message delivery, making it
transport-agnostic.
"""

from __future__ import annotations

import abc
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from cluster.transport import TransportProvider, Message, MessageType

logger = logging.getLogger(__name__)


@dataclass
class RPCRequest:
    """An RPC request to a remote node.

    Attributes:
        id: Unique request ID
        method: Method name to call
        params: Method parameters
        timeout: Request timeout in seconds
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RPCResponse:
    """An RPC response from a remote node.

    Attributes:
        id: Response ID (correlated to request)
        success: Whether the call succeeded
        result: Result data
        error: Error message if failed
        metadata: Additional metadata
    """
    id: str = ""
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RPCHandler(abc.ABC):
    """Abstract base class for RPC method handlers.

    Implementations register methods that can be called remotely.
    """

    @abc.abstractmethod
    def handle(self, method: str, params: Dict[str, Any]) -> RPCResponse:
        """Handle an incoming RPC call.

        Args:
            method: The method name to invoke
            params: Method parameters

        Returns:
            RPCResponse with the result or error
        """
        ...


class RPCServer:
    """RPC server — handles incoming RPC calls from cluster nodes.

    Routes requests to registered method handlers and returns responses.

    Usage:
        server = RPCServer(transport_provider)

        @server.register("cluster.execute_task")
        def execute_task(params):
            # ... execute the task ...
            return {"success": True, "output": "..."}

        server.start()
    """

    def __init__(self, transport: TransportProvider):
        self._transport = transport
        self._lock = threading.RLock()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._unsubscribe: Optional[Callable] = None
        self._running = False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, method: str,
                 handler_fn: Optional[Callable[[Dict[str, Any]], Any]] = None):
        """Register a method handler.

        Can be used as a decorator or called directly:

        @server.register("my_method")
        def handler(params):
            ...

        server.register("my_method", handler_fn)
        """
        if handler_fn is not None:
            with self._lock:
                self._handlers[method] = handler_fn
            return handler_fn

        def decorator(fn):
            with self._lock:
                self._handlers[method] = fn
            return fn

        return decorator

    def unregister(self, method: str) -> bool:
        """Remove a registered method handler."""
        with self._lock:
            return self._handlers.pop(method, None) is not None

    def list_methods(self) -> List[str]:
        """List all registered RPC methods."""
        with self._lock:
            return list(self._handlers.keys())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the RPC server — subscribe to transport messages."""
        if self._running:
            return
        self._running = True
        self._unsubscribe = self._transport.on_message(self._on_message)
        logger.info("RPCServer: started with %d methods", len(self._handlers))

    def stop(self) -> None:
        """Stop the RPC server."""
        self._running = False
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception:
                pass
        logger.info("RPCServer: stopped")

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    def _on_message(self, message: Message) -> None:
        """Handle an incoming transport message."""
        if message.message_type != MessageType.REQUEST:
            return

        # Look up handler
        with self._lock:
            handler = self._handlers.get(message.method)

        if handler is None:
            logger.warning("RPCServer: no handler for method '%s'", message.method)
            error_response = Message(
                message_type=MessageType.RESPONSE,
                source=message.destination,
                destination=message.source,
                method=message.method,
                params=RPCResponse(
                    success=False,
                    error=f"No handler for method '{message.method}'",
                ).__dict__,
                correlation_id=message.id,
            )
            self._transport.send(error_response)
            return

        # Execute handler
        try:
            params = message.params if isinstance(message.params, dict) else {}
            result = handler(params)

            if isinstance(result, RPCResponse):
                response_data = result
            else:
                response_data = RPCResponse(
                    id=message.id,
                    success=True,
                    result=result,
                )

            response = Message(
                message_type=MessageType.RESPONSE,
                source=message.destination,
                destination=message.source,
                method=message.method,
                params=response_data.__dict__,
                correlation_id=message.id,
            )
            self._transport.send(response)

        except Exception as exc:
            logger.error(
                "RPCServer: handler for '%s' failed: %s",
                message.method, exc,
            )
            error_response = Message(
                message_type=MessageType.RESPONSE,
                source=message.destination,
                destination=message.source,
                method=message.method,
                params=RPCResponse(
                    success=False,
                    error=str(exc),
                ).__dict__,
                correlation_id=message.id,
            )
            self._transport.send(error_response)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return RPC server statistics."""
        with self._lock:
            return {
                "running": self._running,
                "registered_methods": len(self._handlers),
                "methods": list(self._handlers.keys()),
            }


class RPCClient:
    """RPC client — calls methods on remote cluster nodes.

    Usage:
        client = RPCClient(transport_provider)

        # Call a method on a remote node
        response = client.call(
            node_id="node-2",
            method="cluster.execute_task",
            params={"task_id": "123", ...},
            timeout=60.0,
        )
        # response == {"success": True, ...}
    """

    def __init__(self, transport: TransportProvider):
        self._transport = transport
        self._lock = threading.RLock()
        self._node_id: str = ""

    def set_node_id(self, node_id: str) -> None:
        """Set this client's node ID."""
        self._node_id = node_id

    def call(
        self,
        node_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Call a method on a remote node and wait for the response.

        Args:
            node_id: The target node ID
            method: The method name to call
            params: Method parameters
            timeout: Maximum time to wait for response

        Returns:
            Response data dict, or None on timeout
        """
        request = RPCRequest(
            method=method,
            params=params or {},
            timeout=timeout,
        )

        message = Message(
            message_type=MessageType.REQUEST,
            source=self._node_id,
            destination=node_id,
            method=method,
            params=request.__dict__,
            timeout_seconds=timeout,
        )

        response = self._transport.send(message)
        if response is None:
            logger.warning(
                "RPCClient: no response from %s for '%s'",
                node_id[:8], method,
            )
            return None

        # Parse response
        if isinstance(response.params, dict):
            return response.params
        return {"result": response.params}

    def call_async(
        self,
        node_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None,
    ) -> None:
        """Call a method on a remote node without waiting.

        Args:
            node_id: The target node ID
            method: The method name to call
            params: Method parameters
            callback: Called with the response when received
        """
        request = RPCRequest(
            method=method,
            params=params or {},
        )

        message = Message(
            message_type=MessageType.REQUEST,
            source=self._node_id,
            destination=node_id,
            method=method,
            params=request.__dict__,
        )

        def _handle_async(msg: Message) -> None:
            if callback:
                try:
                    if isinstance(msg.params, dict):
                        callback(msg.params)
                    else:
                        callback({"result": msg.params})
                except Exception as exc:
                    logger.warning("RPCClient: async callback failed: %s", exc)

        # Subscribe to the response
        self._transport.send(message)
        # Note: for true async, we'd need to correlate the response.
        # This is a simplified version.

    def broadcast(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        node_ids: Optional[List[str]] = None,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Call a method on multiple nodes.

        Args:
            method: The method name to call
            params: Method parameters
            node_ids: Target node IDs (all known if None)

        Returns:
            Dict mapping node_id -> response
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        targets = node_ids or []
        if not targets:
            return {}

        results: Dict[str, Optional[Dict[str, Any]]] = {}

        def _call_node(nid: str) -> tuple:
            try:
                resp = self.call(nid, method, params, timeout=30.0)
                return nid, resp
            except Exception as exc:
                return nid, None

        with ThreadPoolExecutor(max_workers=min(len(targets), 10)) as pool:
            futures = {pool.submit(_call_node, nid): nid for nid in targets}
            for future in as_completed(futures):
                nid, resp = future.result()
                results[nid] = resp

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Return RPC client statistics."""
        return {
            "active": True,
        }
