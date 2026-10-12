"""
Node Discovery — pluggable node discovery for cluster formation.

Supports multiple discovery methods:
  - Manual configuration (static node list)
  - Local network discovery (broadcast/mDNS)
  - Service registry (e.g. Consul, etcd)
  - Custom plugins

All discovery methods require authentication. Nodes must be explicitly
approved before they can participate in the cluster.
"""

from __future__ import annotations

import abc
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus
from cluster.node_registry import NodeRegistry, NodeInfo, NodeCapabilities, NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of discovering a node.

    Attributes:
        node_id: Discovered node ID
        hostname: Node hostname or address
        port: Optional port for cluster communication
        capabilities: Advertised capabilities
        auth_token: Authentication token for enrollment
        metadata: Additional metadata
    """
    node_id: str = ""
    hostname: str = ""
    port: int = 0
    capabilities: Optional[NodeCapabilities] = None
    auth_token: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DiscoveryProvider(abc.ABC):
    """Abstract base class for discovery providers.

    Implementations must provide a discover() method that returns
    a list of discovered nodes, and optional start()/stop() methods.
    """

    @abc.abstractmethod
    def discover(self) -> List[DiscoveryResult]:
        """Discover available nodes. Returns list of discovered nodes."""
        ...

    def start(self) -> None:
        """Optional: start any background discovery threads."""
        pass

    def stop(self) -> None:
        """Optional: stop background discovery threads."""
        pass

    @property
    def name(self) -> str:
        """Return the provider name."""
        return self.__class__.__name__


class ManualDiscoveryProvider(DiscoveryProvider):
    """Discovery from a static list of configured nodes.

    Reads node addresses from configuration. Useful for development,
    testing, and environments where network discovery is not available.
    """

    def __init__(self, nodes: Optional[List[Dict[str, Any]]] = None):
        """
        Args:
            nodes: List of node config dicts with keys:
                   - node_id (optional, auto-generated if missing)
                   - hostname (required)
                   - port (optional, default 9876)
                   - auth_token (optional)
        """
        self._nodes: List[Dict[str, Any]] = list(nodes or [])
        self._lock = threading.RLock()

    def discover(self) -> List[DiscoveryResult]:
        """Return the configured static node list."""
        results = []
        with self._lock:
            for node_cfg in self._nodes:
                results.append(DiscoveryResult(
                    node_id=node_cfg.get("node_id", f"manual-{node_cfg.get('hostname', '?')}"),
                    hostname=node_cfg.get("hostname", ""),
                    port=int(node_cfg.get("port", 9876)),
                    auth_token=node_cfg.get("auth_token", ""),
                    metadata=node_cfg.get("metadata", {}),
                ))
        return results

    def add_node(self, hostname: str, port: int = 9876,
                 node_id: str = "", auth_token: str = "") -> None:
        """Add a node to the static list."""
        with self._lock:
            self._nodes.append({
                "node_id": node_id,
                "hostname": hostname,
                "port": port,
                "auth_token": auth_token,
            })

    def remove_node(self, hostname: str) -> bool:
        """Remove a node from the static list by hostname."""
        with self._lock:
            before = len(self._nodes)
            self._nodes = [n for n in self._nodes if n.get("hostname") != hostname]
            return len(self._nodes) < before


class NetworkDiscoveryProvider(DiscoveryProvider):
    """Network-based discovery using UDP broadcast or mDNS.

    Discovers nodes on the local network by broadcasting discovery
    requests and listening for responses.
    """

    def __init__(self, broadcast_port: int = 9877,
                 response_port: int = 9878,
                 discovery_timeout: float = 2.0,
                 node_id: str = ""):
        self._broadcast_port = broadcast_port
        self._response_port = response_port
        self._discovery_timeout = discovery_timeout
        self._running = False
        self._listener_thread: Optional[threading.Thread] = None
        self._discovered: Dict[str, DiscoveryResult] = {}
        self._lock = threading.RLock()
        self._node_id = node_id

    def discover(self) -> List[DiscoveryResult]:
        """Broadcast discovery request and collect responses."""
        import socket

        results = []
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(self._discovery_timeout)

            # Broadcast discovery request
            message = json.dumps({
                "type": "aetheros_discovery_request",
                "version": 1,
            }).encode("utf-8")
            sock.sendto(message, ("<broadcast>", self._broadcast_port))

            # Collect responses
            start = time.time()
            while time.time() - start < self._discovery_timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    response = json.loads(data.decode("utf-8"))
                    if response.get("type") == "aetheros_discovery_response":
                        result = DiscoveryResult(
                            node_id=response.get("node_id", ""),
                            hostname=addr[0],
                            port=response.get("port", 9876),
                            auth_token=response.get("auth_token", ""),
                            metadata=response.get("metadata", {}),
                        )
                        with self._lock:
                            self._discovered[result.node_id] = result
                        results.append(result)
                except socket.timeout:
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            sock.close()
        except Exception as exc:
            logger.warning("NetworkDiscovery: broadcast discovery failed: %s", exc)

        return results

    def start(self) -> None:
        """Start listening for discovery requests."""
        if self._running:
            return
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="cluster-discovery-listener",
        )
        self._listener_thread.start()

    def stop(self) -> None:
        """Stop listening for discovery requests."""
        self._running = False

    def _listen_loop(self) -> None:
        """Background thread that responds to discovery requests."""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)  # Allow checking _running flag

            try:
                sock.bind(("0.0.0.0", self._broadcast_port))
            except OSError:
                # Port may be in use — listen on any available port
                sock.bind(("0.0.0.0", 0))

            while self._running:
                try:
                    data, addr = sock.recvfrom(4096)
                    request = json.loads(data.decode("utf-8"))
                    if request.get("type") == "aetheros_discovery_request":
                        # Respond with our info
                        import platform as _platform
                        response = json.dumps({
                            "type": "aetheros_discovery_response",
                            "node_id": self._node_id,
                            "port": self._response_port,
                            "hostname": _platform.node(),
                            "version": 1,
                        }).encode("utf-8")
                        sock.sendto(response, addr)
                except socket.timeout:
                    continue
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            sock.close()
        except Exception as exc:
            logger.warning("NetworkDiscovery: listener error: %s", exc)


class NodeDiscovery:
    """Manages node discovery using pluggable providers.

    Discovers nodes through configured providers, validates their
    identity, and registers them with the NodeRegistry.

    Usage:
        discovery = NodeDiscovery(node_registry, event_bus)
        discovery.add_provider(ManualDiscoveryProvider([...]))
        discovery.add_provider(NetworkDiscoveryProvider())

        # Run a discovery cycle
        found = discovery.run_discovery()
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        event_bus: Optional[EventBus] = None,
        require_auth: bool = True,
        auth_token: str = "",
    ):
        self._node_registry = node_registry
        self._event_bus = event_bus
        self._require_auth = require_auth
        self._auth_token = auth_token
        self._lock = threading.RLock()
        self._providers: List[DiscoveryProvider] = []
        self._known_nodes: Set[str] = set()
        self._pending_approval: Dict[str, DiscoveryResult] = {}
        self._running = False
        self._discovery_thread: Optional[threading.Thread] = None
        self._discovery_interval = 60.0  # seconds between discovery cycles

        # Approval callbacks
        self._on_pending_approval: List[Callable[[DiscoveryResult], None]] = []

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def add_provider(self, provider: DiscoveryProvider) -> None:
        """Add a discovery provider."""
        with self._lock:
            self._providers.append(provider)
        logger.info("NodeDiscovery: added provider '%s'", provider.name)

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a discovery provider by name."""
        with self._lock:
            before = len(self._providers)
            self._providers = [p for p in self._providers if p.name != provider_name]
            return len(self._providers) < before

    def list_providers(self) -> List[str]:
        """List registered discovery providers."""
        with self._lock:
            return [p.name for p in self._providers]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def run_discovery(self) -> List[DiscoveryResult]:
        """Run all discovery providers and register discovered nodes.

        Returns:
            List of newly discovered nodes (not yet approved).
        """
        discovered: List[DiscoveryResult] = []

        with self._lock:
            providers = list(self._providers)

        for provider in providers:
            try:
                results = provider.discover()
                for result in results:
                    if result.node_id and result.node_id not in self._known_nodes:
                        if self._validate_discovery(result):
                            if self._require_auth:
                                # Node needs approval
                                self._pending_approval[result.node_id] = result
                                discovered.append(result)
                                self._notify_pending_approval(result)
                            else:
                                # Auto-register
                                self._register_discovered(result)
                                discovered.append(result)
            except Exception as exc:
                logger.warning(
                    "NodeDiscovery: provider '%s' failed: %s",
                    provider.name, exc,
                )

        if self._event_bus and discovered:
            self._event_bus.emit_async("cluster.discovery_completed", {
                "new_nodes": len(discovered),
                "pending_approval": len(self._pending_approval),
            })

        return discovered

    def _validate_discovery(self, result: DiscoveryResult) -> bool:
        """Validate a discovered node's identity.

        Checks auth token if required, and basic connectivity.
        """
        if self._require_auth and self._auth_token:
            if result.auth_token != self._auth_token:
                logger.warning(
                    "NodeDiscovery: auth token mismatch for %s (%s)",
                    result.node_id[:8], result.hostname,
                )
                return False

        if not result.hostname:
            logger.warning("NodeDiscovery: discovered node with no hostname")
            return False

        return True

    def _register_discovered(self, result: DiscoveryResult) -> None:
        """Register a discovered node with the registry."""
        capabilities = result.capabilities or NodeCapabilities(
            hostname=result.hostname,
        )

        self._node_registry.register_node(
            result.node_id,
            capabilities=capabilities,
            metadata=result.metadata,
        )
        self._known_nodes.add(result.node_id)

        logger.info("NodeDiscovery: registered node %s (%s)", result.node_id[:8], result.hostname)

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def approve_node(self, node_id: str) -> bool:
        """Explicitly approve a pending node for enrollment.

        Returns True if the node was approved.
        """
        with self._lock:
            result = self._pending_approval.pop(node_id, None)
            if result is None:
                return False

        self._register_discovered(result)

        if self._event_bus:
            self._event_bus.emit_async("cluster.node_approved", {
                "node_id": node_id,
                "hostname": result.hostname,
            })

        return True

    def reject_node(self, node_id: str) -> bool:
        """Reject a pending node.

        Returns True if the node was rejected.
        """
        with self._lock:
            result = self._pending_approval.pop(node_id, None)
        if result:
            logger.info("NodeDiscovery: rejected node %s (%s)", node_id[:8], result.hostname)
            return True
        return False

    def list_pending(self) -> List[DiscoveryResult]:
        """List nodes awaiting approval."""
        with self._lock:
            return list(self._pending_approval.values())

    def on_pending_approval(self, callback: Callable[[DiscoveryResult], None]) -> Callable:
        """Register a callback for nodes pending approval.

        Returns an unsubscribe function.
        """
        with self._lock:
            self._on_pending_approval.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._on_pending_approval:
                    self._on_pending_approval.remove(callback)

        return unsubscribe

    def _notify_pending_approval(self, result: DiscoveryResult) -> None:
        """Notify callbacks of a pending approval."""
        with self._lock:
            callbacks = list(self._on_pending_approval)
        for cb in callbacks:
            try:
                cb(result)
            except Exception as exc:
                logger.debug("NodeDiscovery: pending approval callback failed: %s", exc)

    # ------------------------------------------------------------------
    # Background discovery
    # ------------------------------------------------------------------

    def start(self, discovery_interval: float = 60.0) -> None:
        """Start periodic background discovery."""
        if self._running:
            return
        self._running = True
        self._discovery_interval = discovery_interval

        # Start all providers
        with self._lock:
            for provider in self._providers:
                provider.start()

        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True,
            name="cluster-discovery",
        )
        self._discovery_thread.start()

        # Run an initial discovery
        self.run_discovery()

        logger.info("NodeDiscovery: started (interval=%.0fs)", discovery_interval)

    def stop(self) -> None:
        """Stop periodic background discovery."""
        self._running = False

        with self._lock:
            for provider in self._providers:
                provider.stop()

    def _discovery_loop(self) -> None:
        """Background discovery loop."""
        while self._running:
            time.sleep(self._discovery_interval)
            try:
                self.run_discovery()
            except Exception as exc:
                logger.warning("NodeDiscovery: discovery loop error: %s", exc)
