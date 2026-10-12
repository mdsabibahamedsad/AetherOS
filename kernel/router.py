"""
Router — routes requests to the appropriate agent, component, or handler.

The router decouples request origin from request handling:
  - Routes requests to registered handlers by pattern matching
  - Supports priority-based routing
  - Allows fallback chains
  - Integrates with the kernel event bus for observability
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class RouteEntry:
    """A registered route.

    Attributes:
        name: Route name (for identification)
        pattern: Regex pattern to match against request targets
        handler: Callable(request_data) -> response
        priority: Route priority (lower = checked first)
        description: Human-readable description
        metadata: Additional metadata
    """
    name: str
    pattern: str
    handler: Callable[[Dict[str, Any]], Any]
    priority: int = 50
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, target: str) -> bool:
        """Check if this route matches a target string."""
        try:
            return bool(re.match(self.pattern, target))
        except re.error:
            return False


class Router:
    """Request router for the AetherOS Kernel.

    Routes requests to registered handlers based on pattern matching.
    Supports priority ordering, fallback chains, and middleware patterns.

    Usage:
        router = Router(event_bus)

        @router.route(r"^agent/", name="agent-handler")
        def handle_agent(data):
            return f"Handling: {data}"

        result = router.route_request("agent/chat", {"message": "hello"})
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._routes: List[RouteEntry] = []
        # Middleware functions: Callable(target, data, handler) -> response
        self._middleware: List[Callable] = []

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def register(self, name: str, pattern: str,
                 handler: Callable[[Dict[str, Any]], Any],
                 priority: int = 50,
                 description: str = "",
                 metadata: Dict[str, Any] = None) -> RouteEntry:
        """Register a route."""
        entry = RouteEntry(
            name=name,
            pattern=pattern,
            handler=handler,
            priority=priority,
            description=description,
            metadata=metadata or {},
        )
        with self._lock:
            self._routes.append(entry)
            # Sort by priority (lower = first)
            self._routes.sort(key=lambda r: (r.priority, r.name))
        logger.debug(
            "Router: registered route '%s' -> %s", name, pattern,
        )
        return entry

    def route(self, pattern: str, name: str = None,
              priority: int = 50, description: str = ""):
        """Decorator-based route registration.

        Usage:
            @router.route(r"^tool/", name="tool-handler")
            def handle(data):
                pass
        """
        def decorator(func):
            route_name = name or func.__name__
            self.register(route_name, pattern, func, priority, description)
            return func
        return decorator

    def unregister(self, name: str) -> bool:
        """Remove a route by name."""
        with self._lock:
            before = len(self._routes)
            self._routes = [r for r in self._routes if r.name != name]
            return len(self._routes) < before

    # ------------------------------------------------------------------
    # Request routing
    # ------------------------------------------------------------------

    def route_request(self, target: str, data: Dict[str, Any] = None) -> Any:
        """Route a request to the first matching handler.

        Args:
            target: Request target string (e.g. "agent/chat", "tool/web_search")
            data: Request payload

        Returns:
            Handler response, or None if no route matches

        Raises:
            RouteNotFoundError if no route matches
        """
        data = data or {}
        with self._lock:
            routes = list(self._routes)

        for entry in routes:
            if entry.matches(target):
                logger.debug(
                    "Router: routing '%s' -> '%s' (%s)",
                    target, entry.name, entry.pattern,
                )
                try:
                    # Run through middleware
                    return self._apply_middleware(target, data, entry.handler)
                except Exception as exc:
                    logger.error(
                        "Router: handler '%s' failed for '%s': %s",
                        entry.name, target, exc,
                    )
                    raise

        # No route matched
        raise RouteNotFoundError(f"No route found for target '{target}'")

    def route_first(self, target: str, data: Dict[str, Any] = None) -> Optional[Any]:
        """Route to the first matching handler, returning None if no match."""
        try:
            return self.route_request(target, data)
        except RouteNotFoundError:
            return None

    def route_all(self, target: str, data: Dict[str, Any] = None) -> List[Any]:
        """Route to ALL matching handlers and collect results."""
        data = data or {}
        results = []

        with self._lock:
            routes = list(self._routes)

        for entry in routes:
            if entry.matches(target):
                try:
                    result = entry.handler(data)
                    results.append((entry.name, result))
                except Exception as exc:
                    logger.warning(
                        "Router: handler '%s' error for '%s': %s",
                        entry.name, target, exc,
                    )

        return results

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    def add_middleware(self, middleware_fn: Callable) -> None:
        """Add a middleware function.

        Middleware receives (target, data, handler) and must return
        the handler's response (or a modified version).
        Middleware can also return early without calling the handler.
        """
        with self._lock:
            self._middleware.append(middleware_fn)

    def _apply_middleware(self, target: str, data: Dict[str, Any],
                          handler: Callable) -> Any:
        """Apply middleware chain to a request."""
        mw_list = list(self._middleware)

        def _execute(current_data: Dict[str, Any]) -> Any:
            return handler(current_data)

        # Build middleware chain from inside out
        for mw in reversed(mw_list):
            handler_fn = _execute

            def _make_mw_wrapper(mw_fn, next_handler):
                def _wrap(inner_data):
                    return mw_fn(target, inner_data, next_handler)
                return _wrap

            _execute = _make_mw_wrapper(mw, _execute)

        return _execute(data)

    # ------------------------------------------------------------------
    # Route inspection
    # ------------------------------------------------------------------

    def list_routes(self) -> List[Dict[str, Any]]:
        """List all registered routes."""
        with self._lock:
            return [
                {
                    "name": r.name,
                    "pattern": r.pattern,
                    "priority": r.priority,
                    "description": r.description,
                }
                for r in sorted(self._routes, key=lambda r: r.priority)
            ]

    def find_routes(self, target: str) -> List[RouteEntry]:
        """Find all routes that would match a target."""
        with self._lock:
            return [r for r in self._routes if r.matches(target)]

    def clear(self) -> None:
        """Remove all routes."""
        with self._lock:
            self._routes.clear()
        logger.info("Router: all routes cleared")


class RouteNotFoundError(LookupError):
    """Raised when no route matches a request target."""
