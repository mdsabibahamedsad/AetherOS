"""
Context Manager — provides shared context across agents, tools, and components.

Enables:
  - Conversation context sharing across agents
  - Workspace context propagation
  - Memory integration
  - Task graph context
  - Execution history sharing

The context manager is NOT a replacement for existing memory systems
(MEMORY.md, memory providers). It provides ephemeral runtime context
that flows through the kernel during a session.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SharedContext:
    """A named context namespace shared across agents.

    Attributes:
        name: Context namespace name
        data: Key-value data store
        created_at: Creation timestamp
        ttl_seconds: Time-to-live (None = no expiry)
        metadata: Additional metadata
    """
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if this context has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds


class ContextManager:
    """Shared context manager for the AetherOS Kernel.

    Provides isolated context namespaces that agents and tools can
    read from and write to.

    Usage:
        cm = ContextManager(event_bus)

        # Set shared context for a conversation
        cm.set("conversation:agent-1", "goal", "Deploy the app")
        cm.set("conversation:agent-1", "files", ["main.py", "config.py"])

        # Read in another agent
        goal = cm.get("conversation:agent-1", "goal")

        # Create a scoped context that auto-cleans
        with cm.scoped("task:build") as ctx:
            ctx["status"] = "building"
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._contexts: Dict[str, SharedContext] = {}
        self._expiry_thread: Optional[threading.Thread] = None
        self._shutdown_flag = False

    # ------------------------------------------------------------------
    # Context operations
    # ------------------------------------------------------------------

    def get_or_create(self, name: str,
                      ttl_seconds: float = None) -> SharedContext:
        """Get an existing context or create a new one."""
        with self._lock:
            ctx = self._contexts.get(name)
            if ctx is None or ctx.is_expired:
                ctx = SharedContext(name=name, ttl_seconds=ttl_seconds)
                self._contexts[name] = ctx
            return ctx

    def get(self, name: str, key: str = None) -> Any:
        """Get a value from a context namespace.

        If key is None, returns the full SharedContext.
        If key is specified, returns the value for that key (or None).
        """
        ctx = self.get_or_create(name)
        if ctx.is_expired:
            return None
        if key is None:
            return ctx.data
        return ctx.data.get(key)

    def set(self, name: str, key: str, value: Any,
            ttl_seconds: float = None) -> None:
        """Set a value in a context namespace."""
        ctx = self.get_or_create(name, ttl_seconds=ttl_seconds)
        with self._lock:
            ctx.data[key] = value

        if self._event_bus:
            self._event_bus.emit_async("context.updated", {
                "context": name,
                "key": key,
            })

    def set_many(self, name: str, values: Dict[str, Any],
                 ttl_seconds: float = None) -> None:
        """Set multiple values in a context namespace at once."""
        ctx = self.get_or_create(name, ttl_seconds=ttl_seconds)
        with self._lock:
            ctx.data.update(values)

    def delete(self, name: str, key: str = None) -> bool:
        """Delete a key or entire context namespace."""
        with self._lock:
            if key is None:
                return self._contexts.pop(name, None) is not None
            ctx = self._contexts.get(name)
            if ctx is None:
                return False
            return ctx.data.pop(key, None) is not None

    def clear(self, name: str = None) -> int:
        """Clear all contexts, or a single context if name is given."""
        with self._lock:
            if name:
                ctx = self._contexts.pop(name, None)
                return 1 if ctx else 0
            count = len(self._contexts)
            self._contexts.clear()
            return count

    # ------------------------------------------------------------------
    # Namespace management
    # ------------------------------------------------------------------

    def list_contexts(self) -> List[str]:
        """List all active context namespaces."""
        with self._lock:
            now = time.time()
            return [
                name for name, ctx in self._contexts.items()
                if not (ctx.ttl_seconds and now - ctx.created_at > ctx.ttl_seconds)
            ]

    def prune_expired(self) -> int:
        """Remove all expired contexts. Returns count removed."""
        count = 0
        with self._lock:
            now = time.time()
            expired = [
                name for name, ctx in self._contexts.items()
                if ctx.ttl_seconds and now - ctx.created_at > ctx.ttl_seconds
            ]
            for name in expired:
                del self._contexts[name]
                count += 1
        if count > 0:
            logger.debug("Context: pruned %d expired contexts", count)
        return count

    # ------------------------------------------------------------------
    # Scoped context
    # ------------------------------------------------------------------

    def scoped(self, name: str, ttl_seconds: float = 3600.0):
        """Context manager for ephemeral context.

        Usage:
            with cm.scoped("task:build") as ctx:
                ctx["status"] = "building"
                # ... do work ...
        """
        return _ScopedContext(self, name, ttl_seconds)


class _ScopedContext:
    """Context manager support for scoped contexts."""

    def __init__(self, manager: ContextManager, name: str,
                 ttl_seconds: float):
        self._manager = manager
        self._name = name
        self._ttl = ttl_seconds
        self.data: Dict[str, Any] = {}

    def __enter__(self):
        return self.data

    def __exit__(self, *args):
        if self.data:
            self._manager.set_many(self._name, self.data, ttl_seconds=self._ttl)

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def update(self, values: Dict[str, Any]) -> None:
        self.data.update(values)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Clean up all contexts on shutdown."""
        count = self.clear()
        if count > 0:
            logger.info("Context: cleared %d contexts on shutdown", count)
