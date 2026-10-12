"""
Extension Events and Observability
===================================

Event bus for extension lifecycle, health, and audit events.
Supports structured metrics and observability.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExtensionEventType(enum.Enum):
    """Types of extension lifecycle events."""
    INSTALLED = "installed"
    UNINSTALLED = "uninstalled"
    ENABLED = "enabled"
    DISABLED = "disabled"
    LOADED = "loaded"
    LOAD_FAILED = "load_failed"
    ERROR = "error"
    HEALTH_CHANGED = "health_changed"
    PERMISSION_CHECK = "permission_check"
    UPDATE_AVAILABLE = "update_available"
    UPDATED = "updated"
    CRASHED = "crashed"


@dataclass
class ExtensionEvent:
    """A structured event for extension observability."""
    type: ExtensionEventType
    extension: str
    timestamp: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class EventBus:
    """Event bus for extension lifecycle events.

    Supports both synchronous and asynchronous subscribers.
    Provides structured metrics export.

    Usage::

        bus = get_event_bus()
        bus.subscribe(ExtensionEventType.ENABLED, on_extension_enabled)
        bus.emit(ExtensionEvent(type=ExtensionEventType.ENABLED, extension="my-plugin"))
    """

    def __init__(self) -> None:
        self._subscribers: Dict[ExtensionEventType, List[Callable]] = {}
        self._history: List[ExtensionEvent] = []
        self._max_history: int = 1000

    def subscribe(
        self,
        event_type: ExtensionEventType,
        callback: Callable[[ExtensionEvent], None],
    ) -> Callable:
        """Subscribe to an event type.

        Returns a function that unsubscribes when called.
        """
        self._subscribers.setdefault(event_type, []).append(callback)

        def unsubscribe() -> None:
            handlers = self._subscribers.get(event_type, [])
            if callback in handlers:
                handlers.remove(callback)

        return unsubscribe

    def emit(self, event: ExtensionEvent) -> None:
        """Emit an event to all subscribers."""
        # Record history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Dispatch
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.warning("Event handler failed for %s: %s", event.type.value, exc)

    def get_history(
        self,
        event_type: Optional[ExtensionEventType] = None,
        extension: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExtensionEvent]:
        """Get event history, optionally filtered."""
        events = list(self._history)
        if event_type:
            events = [e for e in events if e.type == event_type]
        if extension:
            events = [e for e in events if e.extension == extension]
        return events[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get structured metrics about extension events.

        Returns dict with counts per event type and per extension.
        """
        metrics: Dict[str, Any] = {
            "total_events": len(self._history),
            "by_type": {},
            "by_extension": {},
            "errors": 0,
        }

        for event in self._history:
            type_str = event.type.value
            metrics["by_type"][type_str] = metrics["by_type"].get(type_str, 0) + 1
            metrics["by_extension"][event.extension] = metrics["by_extension"].get(event.extension, 0) + 1

            if event.type in (ExtensionEventType.ERROR, ExtensionEventType.LOAD_FAILED,
                              ExtensionEventType.CRASHED):
                metrics["errors"] += 1

        return metrics


# Global event bus singleton
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Return the global EventBus singleton."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


# Convenience functions

def emit_extension_event(
    event_type: ExtensionEventType,
    extension: str,
    message: str = "",
    **data: Any,
) -> None:
    """Emit an extension lifecycle event."""
    event = ExtensionEvent(
        type=event_type,
        extension=extension,
        message=message,
        data=data,
    )
    get_event_bus().emit(event)


def on_extension_installed(extension: str, version: str = "") -> None:
    emit_extension_event(
        ExtensionEventType.INSTALLED, extension,
        message=f"Installed v{version}" if version else "Installed",
        version=version,
    )


def on_extension_uninstalled(extension: str) -> None:
    emit_extension_event(
        ExtensionEventType.UNINSTALLED, extension,
        message="Uninstalled",
    )


def on_extension_error(extension: str, error: str) -> None:
    emit_extension_event(
        ExtensionEventType.ERROR, extension,
        message=error,
        error=error,
    )


def on_extension_crashed(extension: str, error: str) -> None:
    emit_extension_event(
        ExtensionEventType.CRASHED, extension,
        message=f"Crashed: {error}",
        error=error,
    )
