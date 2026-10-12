"""
UI Events — Structured event models for interaction layer observability.

Provides a unified event dispatch system for all interaction events,
used by the interaction manager, desktop, voice, and presence subsystems.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIEventType(enum.Enum):
    """Canonical UI event types for the interaction layer."""
    # System events
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Interaction lifecycle
    INTERACTION_STARTED = "interaction.started"
    INTERACTION_STOPPED = "interaction.stopped"
    CHANNEL_ACTIVATED = "interaction.channel_activated"
    CHANNEL_DEACTIVATED = "interaction.channel_deactivated"

    # Voice events
    VOICE_SESSION_START = "voice.session_start"
    VOICE_SESSION_END = "voice.session_end"
    VOICE_LISTENING_START = "voice.listening_start"
    VOICE_LISTENING_STOP = "voice.listening_stop"
    VOICE_SPEECH_DETECTED = "voice.speech_detected"
    VOICE_TRANSCRIPTION = "voice.transcription"
    VOICE_SPEAKING_START = "voice.speaking_start"
    VOICE_SPEAKING_END = "voice.speaking_end"
    VOICE_WAKE_WORD = "voice.wake_word"
    VOICE_ERROR = "voice.error"

    # Desktop events
    DESKTOP_WINDOW_CHANGED = "desktop.window_changed"
    DESKTOP_WORKSPACE_CHANGED = "desktop.workspace_changed"
    DESKTOP_CLIPBOARD_UPDATED = "desktop.clipboard_updated"
    DESKTOP_NOTIFICATION = "desktop.notification"
    DESKTOP_SHORTCUT = "desktop.shortcut"

    # Presence events
    PRESENCE_ACTIVITY = "presence.activity"
    PRESENCE_IDLE = "presence.idle"
    PRESENCE_RETURN = "presence.return"
    PRESENCE_FOCUS = "presence.focus"
    PRESENCE_CONTEXT = "presence.context"

    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_ACTION = "notification.action"
    NOTIFICATION_DISMISSED = "notification.dismissed"

    # Permission events
    PERMISSION_REQUESTED = "permission.requested"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"

    # Session events
    SESSION_CREATED = "session.created"
    SESSION_RESUMED = "session.resumed"
    SESSION_ENDED = "session.ended"
    SESSION_SNAPSHOT = "session.snapshot"

    # Error events
    ERROR_GENERIC = "error.generic"
    ERROR_PERMISSION = "error.permission"
    ERROR_TIMEOUT = "error.timeout"


@dataclass
class UIEvent:
    """A structured interaction event.

    Attributes:
        id: Unique event identifier
        type: Event type
        source: Source component
        timestamp: When the event occurred
        data: Event payload
        severity: Event severity
        correlation_id: Optional correlation ID for event chains
    """
    id: str = ""
    type: UIEventType = UIEventType.ERROR_GENERIC
    source: str = ""
    timestamp: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    correlation_id: str = ""


class UIEventHandler:
    """Protocol for UI event handler callables.

    Any callable that accepts a :class:`UIEvent` and returns ``None``.
    """

    def __call__(self, event: UIEvent) -> None:
        """Handle a UI event.

        Args:
            event: The event to handle
        """
        raise NotImplementedError


class EventDispatch:
    """Event dispatch hub for the interaction layer.

    Provides pub/sub for structured UI events, used by all
    interaction subsystems to emit and consume events.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._handlers: Dict[str, List[Callable[[UIEvent], None]]] = {}
        self._wildcard_handlers: List[Callable[[UIEvent], None]] = []
        self._history: List[UIEvent] = []
        self._max_history: int = 500

    def publish(self, event_type: UIEventType, data: Dict[str, Any] = None,
                source: str = "") -> UIEvent:
        """Create and dispatch an event.

        Args:
            event_type: Event type
            data: Event payload
            source: Source component name

        Returns:
            The created UIEvent
        """
        event = UIEvent(
            id=uuid.uuid4().hex[:12],
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=data or {},
        )

        self.dispatch(event)
        return event

    def dispatch(self, event: UIEvent) -> None:
        """Dispatch an event to all matching handlers.

        Args:
            event: Event to dispatch
        """
        with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Get direct handlers
            handlers = list(self._handlers.get(event.type.value, []))
            wildcard = list(self._wildcard_handlers)

        # Dispatch to direct handlers
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.debug("EventDispatch: handler failed on %s: %s", event.type.value, exc)

        # Dispatch to wildcard handlers
        for handler in wildcard:
            try:
                handler(event)
            except Exception as exc:
                logger.debug("EventDispatch: wildcard handler failed: %s", exc)

    def subscribe(self, event_type: UIEventType,
                  handler: Callable[[UIEvent], None]) -> Callable:
        """Subscribe to a specific event type.

        Args:
            event_type: Event type to subscribe to
            handler: Event handler callback

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._handlers.setdefault(event_type.value, []).append(handler)

        def unsubscribe():
            with self._lock:
                handlers = self._handlers.get(event_type.value, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: Callable[[UIEvent], None]) -> Callable:
        """Subscribe to ALL events.

        Args:
            handler: Event handler callback

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._wildcard_handlers.append(handler)

        def unsubscribe():
            with self._lock:
                if handler in self._wildcard_handlers:
                    self._wildcard_handlers.remove(handler)

        return unsubscribe

    def get_history(self, event_type: Optional[UIEventType] = None,
                    limit: int = 50) -> List[UIEvent]:
        """Get recent event history.

        Args:
            event_type: Optional type filter
            limit: Max entries

        Returns:
            List of recent UIEvent objects
        """
        with self._lock:
            if event_type:
                events = [e for e in self._history if e.type == event_type]
            else:
                events = list(self._history)
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get dispatch statistics."""
        with self._lock:
            return {
                "total_events": len(self._history),
                "event_types": len(set(e.type.value for e in self._history)),
                "handlers": sum(len(h) for h in self._handlers.values()),
                "wildcard_handlers": len(self._wildcard_handlers),
            }
