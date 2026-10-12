"""IPC health, disconnect detection and safe reconnect.

Channels monitored:

* ``electron-backend``  — Electron main ↔ Python backend
* ``backend-gateway``   — Python backend ↔ messaging gateway
* ``agent-tool``        — agent loop ↔ tool runtime
* ``agent-mcp``         — agent loop ↔ MCP server

For each channel we track last-seen-activity and state; reconnection is
*requested* by the caller through an explicit ``on_reconnect`` hook so
messages are never replayed automatically and capabilities are revalidated
after every reconnect (a reconnected MCP server is never assumed to have
identical capabilities).
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class IPCChannel(str, enum.Enum):
    ELECTRON_BACKEND = "electron-backend"
    BACKEND_GATEWAY = "backend-gateway"
    AGENT_TOOL = "agent-tool"
    AGENT_MCP = "agent-mcp"


class IPCState(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class IPCChannelHealth:
    channel: str
    state: IPCState = IPCState.CONNECTED
    last_activity: float = field(default_factory=time.time)
    connect_count: int = 0
    disconnect_count: int = 0
    last_error: str = ""
    protocol_version: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "state": self.state.value,
            "last_activity": self.last_activity,
            "connect_count": self.connect_count,
            "disconnect_count": self.disconnect_count,
            "last_error": self.last_error,
            "protocol_version": self.protocol_version,
            "capability_count": len(self.capabilities),
        }


class IPCHealth:
    """Tracks per-channel IPC state and drives reconnect with revalidation.

    Usage::

        ipc = IPCHealth()
        ipc.activity(IPCChannel.ELECTRON_BACKEND)
        ipc.disconnect(IPCChannel.AGENT_MCP, error="connection reset")
        ipc.set_on_reconnect(IPCChannel.AGENT_MCP, my_reconnect_fn)
        ipc.reconnect(IPCChannel.AGENT_MCP)
        ipc.set_capabilities(IPCChannel.AGENT_MCP, {"tools": [...]})
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._channels: Dict[str, IPCChannelHealth] = {
            c.value: IPCChannelHealth(channel=c.value) for c in IPCChannel
        }
        self._reconnect_hooks: Dict[str, Callable[[str, Dict[str, Any]], str]] = {}
        self._revalidate_hooks: Dict[str, Callable[[str], Dict[str, Any]]] = {}
        self._max_reconnects = 3
        self._cooldown = 30.0

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def activity(self, channel: IPCChannel, protocol_version: str = "") -> None:
        with self._lock:
            ch = self._channels[channel.value]
            ch.last_activity = time.time()
            if protocol_version:
                ch.protocol_version = protocol_version

    def disconnect(self, channel: IPCChannel, error: str = "") -> None:
        with self._lock:
            ch = self._channels[channel.value]
            if ch.state == IPCState.CONNECTED:
                ch.disconnect_count += 1
            ch.state = IPCState.DISCONNECTED
            ch.last_error = error
        logger.warning("IPC channel %s disconnected: %s", channel.value, error)

    def set_capabilities(self, channel: IPCChannel,
                         capabilities: Dict[str, Any]) -> None:
        """Record capabilities AFTER a (re)connection — never before."""
        with self._lock:
            self._channels[channel.value].capabilities = dict(capabilities)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def set_on_reconnect(self, channel: IPCChannel,
                         hook: Callable[[str, Dict[str, Any]], str]) -> None:
        """Register a reconnect handler (returns a status message)."""
        with self._lock:
            self._reconnect_hooks[channel.value] = hook

    def set_on_revalidate(self, channel: IPCChannel,
                          hook: Callable[[str], Dict[str, Any]]) -> None:
        """Register a capability-revalidation hook (runs after reconnect)."""
        with self._lock:
            self._revalidate_hooks[channel.value] = hook

    # ------------------------------------------------------------------
    # Reconnect
    # ------------------------------------------------------------------

    def reconnect(self, channel: IPCChannel, *,
                  context: Optional[Dict[str, Any]] = None) -> bool:
        """Reconnect a channel safely.

        Never replays messages; always revalidates capabilities after a
        successful reconnect.
        """
        with self._lock:
            ch = self._channels[channel.value]
            hook = self._reconnect_hooks.get(channel.value)
            revalidate = self._revalidate_hooks.get(channel.value)
            if ch.connect_count >= self._max_reconnects:
                ch.state = IPCState.FAILED
                logger.error("IPC channel %s reconnect budget exhausted", channel.value)
                return False
            ch.state = IPCState.RECONNECTING
        if hook is None:
            with self._lock:
                ch.state = IPCState.DISCONNECTED
            return False
        try:
            message = hook(channel.value, context or {})
            with self._lock:
                ch.connect_count += 1
                ch.last_activity = time.time()
                ch.state = IPCState.CONNECTED
            # Capability revalidation — never assume identical capabilities.
            if revalidate is not None:
                try:
                    caps = revalidate(channel.value)
                    self.set_capabilities(channel, caps)
                except Exception as exc:
                    with self._lock:
                        ch.state = IPCState.DEGRADED
                        ch.last_error = f"revalidation failed: {exc}"
                    logger.error("IPC channel %s capability revalidation failed", channel.value)
                    return False
            return True
        except Exception as exc:
            with self._lock:
                ch.last_error = f"{type(exc).__name__}: {exc}"
                ch.state = IPCState.DISCONNECTED
            return False

    def reset(self, channel: IPCChannel) -> None:
        with self._lock:
            ch = self._channels[channel.value]
            ch.connect_count = 0
            ch.disconnect_count = 0
            ch.last_error = ""
            ch.state = IPCState.CONNECTED
            ch.last_activity = time.time()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def state(self, channel: IPCChannel) -> IPCState:
        with self._lock:
            return self._channels[channel.value].state

    def get(self, channel: IPCChannel) -> IPCChannelHealth:
        with self._lock:
            return self._channels[channel.value]

    def all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {c: h.to_dict() for c, h in self._channels.items()}

    def unhealthy(self) -> List[str]:
        with self._lock:
            return [
                c for c, h in self._channels.items()
                if h.state in (IPCState.DISCONNECTED, IPCState.DEGRADED, IPCState.FAILED)
            ]

    def summary(self) -> Dict[str, Any]:
        all_health = self.all()
        return {
            "channels": all_health,
            "unhealthy": self.unhealthy(),
            "total": len(all_health),
        }


_ipc: Optional[IPCHealth] = None
_ipc_lock = threading.Lock()


def get_ipc_health() -> IPCHealth:
    """Return the process-wide IPCHealth singleton."""
    global _ipc
    if _ipc is None:
        with _ipc_lock:
            if _ipc is None:
                _ipc = IPCHealth()
    return _ipc