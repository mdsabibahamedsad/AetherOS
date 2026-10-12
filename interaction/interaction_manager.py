"""
Interaction Manager — Unified interface for all interaction channels.

Coordinates voice, desktop, notifications, user actions, and interaction
history through a single entry point. Integrates with the Kernel EventBus,
provides plugin hooks for adapters, and enforces privacy permissions.

Usage:
    config = InteractionConfig()
    mgr = InteractionManager(event_bus, config)
    mgr.initialize()

    # Start a voice session
    result = mgr.start_voice_session()
    mgr.notify(Notification("Task complete!"))

    mgr.shutdown()
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class InteractionChannel(enum.Enum):
    """Available interaction channels."""
    VOICE = "voice"
    DESKTOP = "desktop"
    NOTIFICATION = "notification"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    TOUCH = "touch"
    GESTURE = "gesture"
    API = "api"
    CLI = "cli"
    PLUGIN = "plugin"


class InteractionEvent(enum.Enum):
    """Events emitted by the interaction manager."""
    INTERACTION_STARTED = "interaction.started"
    INTERACTION_STOPPED = "interaction.stopped"
    VOICE_SESSION_STARTED = "interaction.voice_session_started"
    VOICE_SESSION_ENDED = "interaction.voice_session_ended"
    DESKTOP_EVENT = "interaction.desktop_event"
    NOTIFICATION_DELIVERED = "interaction.notification_delivered"
    NOTIFICATION_ACTION = "interaction.notification_action"
    WORKSPACE_CHANGED = "interaction.workspace_changed"
    PERMISSION_PROMPTED = "interaction.permission_prompted"
    PERMISSION_GRANTED = "interaction.permission_granted"
    PERMISSION_DENIED = "interaction.permission_denied"
    INTERACTION_ERROR = "interaction.error"


class InteractionState(enum.Enum):
    """States for the interaction manager lifecycle."""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class InteractionConfig:
    """Configuration for the interaction layer.

    Attributes:
        enable_voice: Enable voice interaction capabilities
        enable_desktop: Enable desktop integration
        enable_notifications: Enable notification delivery
        enable_presence: Enable presence awareness
        enable_session_continuity: Enable session persistence/resume
        enable_history: Enable interaction history tracking
        permissions_required: Require explicit user permission for capabilities
        voice_provider: Voice provider name (plugin or built-in)
        notification_provider: Notification provider name
        desktop_provider: Desktop integration provider name
        verbose: Enable verbose logging
    """
    enable_voice: bool = True
    enable_desktop: bool = True
    enable_notifications: bool = True
    enable_presence: bool = True
    enable_session_continuity: bool = True
    enable_history: bool = True
    permissions_required: bool = True
    voice_provider: str = ""
    notification_provider: str = "builtin"
    desktop_provider: str = "builtin"
    verbose: bool = False


@dataclass
class InteractionResult:
    """Result of an interaction operation.

    Attributes:
        success: Whether the operation succeeded
        channel: Which channel handled it
        data: Result payload
        error: Error message (if failed)
        duration_ms: Time taken in milliseconds
    """
    success: bool = True
    channel: Optional[InteractionChannel] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0


class InteractionManager:
    """Unified interface for all interaction channels.

    The InteractionManager is the central entry point for ambient interaction.
    It coordinates voice sessions, desktop events, notifications, and user
    actions, routing them through appropriate adapters with permission checks.

    Plugin adapters can be registered for voice providers, desktop
    integrations, and notification channels without core modifications.

    Usage:
        config = InteractionConfig(enable_voice=True, enable_desktop=True)
        mgr = InteractionManager(event_bus, config)
        mgr.initialize()

        # Start voice interaction
        session = mgr.start_voice_session()

        # Send notification
        mgr.notify(Notification("Workflow complete"))

        # Query workspace context
        ctx = mgr.capture_context()

        mgr.shutdown()
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[InteractionConfig] = None,
    ):
        self._event_bus = event_bus
        self.config = config or InteractionConfig()
        self._state = InteractionState.STOPPED
        self._lock = threading.RLock()

        # Channel adapters
        self._voice_adapters: Dict[str, Callable] = {}
        self._desktop_adapters: Dict[str, Callable] = {}
        self._notification_adapters: Dict[str, Callable] = {}
        self._automation_adapters: Dict[str, Callable] = {}

        # Active sessions
        self._active_voice_sessions: Dict[str, Dict[str, Any]] = {}
        self._active_workspace: Optional[Dict[str, Any]] = None

        # Permission state
        self._permissions: Dict[str, bool] = {
            "microphone": False,
            "clipboard": False,
            "desktop_context": False,
            "notifications": False,
            "workspace_metadata": False,
        }

        # Interaction history buffer
        self._history_buffer: List[Dict[str, Any]] = []
        self._max_history: int = 1000

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> InteractionState:
        with self._lock:
            return self._state

    def initialize(self) -> None:
        """Initialize the interaction layer.

        Sets up configured capabilities, checks environment readiness,
        and transitions to READY state.
        """
        with self._lock:
            if self._state != InteractionState.STOPPED:
                logger.warning("InteractionManager: already initialized")
                return
            self._state = InteractionState.INITIALIZING

        logger.info("InteractionManager: initializing...")

        # Check environment readiness
        env_status = self._check_environment()
        if not env_status["ready"]:
            logger.warning(
                "InteractionManager: environment not fully ready: %s",
                env_status.get("warnings", []),
            )

        with self._lock:
            self._state = InteractionState.READY

        if self._event_bus:
            self._event_bus.emit(InteractionEvent.INTERACTION_STARTED.value, {
                "config": {
                    "voice": self.config.enable_voice,
                    "desktop": self.config.enable_desktop,
                    "notifications": self.config.enable_notifications,
                    "presence": self.config.enable_presence,
                    "session_continuity": self.config.enable_session_continuity,
                },
                "environment": env_status,
            })

        logger.info("InteractionManager: ready (voice=%s, desktop=%s, notifications=%s)",
                     self.config.enable_voice, self.config.enable_desktop,
                     self.config.enable_notifications)

    def shutdown(self) -> None:
        """Gracefully shut down all interaction channels."""
        with self._lock:
            if self._state in (InteractionState.STOPPED, InteractionState.SHUTDOWN):
                return
            self._state = InteractionState.SHUTDOWN

        # End active voice sessions
        session_ids = list(self._active_voice_sessions.keys())
        for sid in session_ids:
            try:
                self.stop_voice_session(sid)
            except Exception as exc:
                logger.debug("InteractionManager: voice session %s shutdown: %s", sid, exc)

        logger.info("InteractionManager: shut down")

        if self._event_bus:
            self._event_bus.emit(InteractionEvent.INTERACTION_STOPPED.value, {})

    def _check_environment(self) -> Dict[str, Any]:
        """Check environment readiness for interaction capabilities.

        Returns:
            Dict with ``ready``, ``warnings``, and capability-specific checks.
        """
        warnings: List[str] = []

        # Check audio environment if voice is enabled
        if self.config.enable_voice:
            try:
                from tools.voice_mode import detect_audio_environment
                audio_env = detect_audio_environment()
                if not audio_env.get("available", False):
                    warnings.extend(audio_env.get("warnings", []))
            except Exception as exc:
                warnings.append(f"Audio environment detection failed: {exc}")

        return {
            "ready": len(warnings) == 0,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Permission management
    # ------------------------------------------------------------------

    def request_permission(self, permission: str) -> bool:
        """Request a permission from the user.

        Args:
            permission: Permission name (microphone, clipboard, etc.)

        Returns:
            True if granted (or permissions not required)
        """
        if not self.config.permissions_required:
            self._permissions[permission] = True
            return True

        if self._permissions.get(permission, False):
            return True

        if self._event_bus:
            self._event_bus.emit(InteractionEvent.PERMISSION_PROMPTED.value, {
                "permission": permission,
            })

        # In the interaction layer, permission state is tracked.
        # Actual user prompt is handled by the calling context (CLI, gateway, TUI).
        logger.info("InteractionManager: permission requested: %s", permission)
        return False

    def grant_permission(self, permission: str) -> None:
        """Grant a previously requested permission.

        Args:
            permission: Permission name to grant
        """
        with self._lock:
            self._permissions[permission] = True

        if self._event_bus:
            self._event_bus.emit(InteractionEvent.PERMISSION_GRANTED.value, {
                "permission": permission,
            })
        logger.info("InteractionManager: permission granted: %s", permission)

    def deny_permission(self, permission: str) -> None:
        """Deny a previously requested permission.

        Args:
            permission: Permission name to deny
        """
        with self._lock:
            self._permissions[permission] = False

        if self._event_bus:
            self._event_bus.emit(InteractionEvent.PERMISSION_DENIED.value, {
                "permission": permission,
            })
        logger.info("InteractionManager: permission denied: %s", permission)

    def has_permission(self, permission: str) -> bool:
        """Check if a permission is granted.

        Args:
            permission: Permission name

        Returns:
            True if granted
        """
        return self._permissions.get(permission, False)

    # ------------------------------------------------------------------
    # Voice interaction
    # ------------------------------------------------------------------

    def start_voice_session(
        self,
        session_type: str = "push_to_talk",
        config: Optional[Dict[str, Any]] = None,
    ) -> InteractionResult:
        """Start a voice interaction session.

        Args:
            session_type: Type of session (push_to_talk, continuous, wake_word)
            config: Optional session configuration

        Returns:
            InteractionResult with session ID and status
        """
        if not self.config.enable_voice:
            return InteractionResult(
                success=False,
                channel=InteractionChannel.VOICE,
                error="Voice interaction is disabled",
            )

        if not self.has_permission("microphone"):
            granted = self.request_permission("microphone")
            if not granted:
                return InteractionResult(
                    success=False,
                    channel=InteractionChannel.VOICE,
                    error="Microphone permission not granted",
                )

        session_id = uuid.uuid4().hex[:12]
        session = {
            "id": session_id,
            "type": session_type,
            "config": config or {},
            "started_at": time.time(),
        }

        with self._lock:
            self._active_voice_sessions[session_id] = session

        self._record_history("voice_session_started", {
            "session_id": session_id,
            "session_type": session_type,
        })

        if self._event_bus:
            self._event_bus.emit_async(InteractionEvent.VOICE_SESSION_STARTED.value, {
                "session_id": session_id,
                "session_type": session_type,
            })

        logger.info("InteractionManager: voice session %s started (%s)", session_id[:8], session_type)

        return InteractionResult(
            success=True,
            channel=InteractionChannel.VOICE,
            data={"session_id": session_id, "type": session_type},
        )

    def stop_voice_session(self, session_id: str) -> InteractionResult:
        """Stop an active voice session.

        Args:
            session_id: Session ID to stop

        Returns:
            InteractionResult with session status
        """
        with self._lock:
            session = self._active_voice_sessions.pop(session_id, None)
            if session is None:
                return InteractionResult(
                    success=False,
                    channel=InteractionChannel.VOICE,
                    error=f"Voice session not found: {session_id}",
                )

        self._record_history("voice_session_ended", {
            "session_id": session_id,
            "duration_seconds": time.time() - session.get("started_at", time.time()),
        })

        if self._event_bus:
            self._event_bus.emit_async(InteractionEvent.VOICE_SESSION_ENDED.value, {
                "session_id": session_id,
            })

        logger.info("InteractionManager: voice session %s ended", session_id[:8])

        return InteractionResult(
            success=True,
            channel=InteractionChannel.VOICE,
            data={"session_id": session_id},
        )

    # ------------------------------------------------------------------
    # Notification delivery
    # ------------------------------------------------------------------

    def notify(self, notification: Any) -> InteractionResult:
        """Deliver a notification through configured channels.

        Args:
            notification: Notification object with title, message, priority, etc.

        Returns:
            InteractionResult with delivery status
        """
        if not self.config.enable_notifications:
            return InteractionResult(
                success=False,
                channel=InteractionChannel.NOTIFICATION,
                error="Notifications are disabled",
            )

        if not self.has_permission("notifications"):
            granted = self.request_permission("notifications")
            if not granted:
                return InteractionResult(
                    success=False,
                    channel=InteractionChannel.NOTIFICATION,
                    error="Notification permission not granted",
                )

        # Route through registered notification adapters
        delivery_results = []
        for name, adapter_fn in self._notification_adapters.items():
            try:
                adapter_ok = adapter_fn(notification)
                delivery_results.append({"adapter": name, "success": adapter_ok})
            except Exception as exc:
                logger.warning("InteractionManager: notification adapter %s failed: %s", name, exc)
                delivery_results.append({"adapter": name, "success": False, "error": str(exc)})

        # Always log to history
        self._record_history("notification", {
            "title": getattr(notification, "title", ""),
            "priority": getattr(notification, "priority", "normal"),
            "deliveries": delivery_results,
        })

        if self._event_bus:
            self._event_bus.emit_async(InteractionEvent.NOTIFICATION_DELIVERED.value, {
                "deliveries": delivery_results,
            })

        # Notifications with no adapters still succeed (logged to history)
        # If there are adapters, at least one must succeed
        if not delivery_results:
            success = True
        else:
            success = any(r["success"] for r in delivery_results)

        return InteractionResult(
            success=success,
            channel=InteractionChannel.NOTIFICATION,
            data={"deliveries": delivery_results},
        )

    # ------------------------------------------------------------------
    # Workspace context
    # ------------------------------------------------------------------

    def capture_context(self) -> Optional[Dict[str, Any]]:
        """Capture current workspace context.

        Returns workspace information including active window,
        open projects, recent files, and engineering tasks.

        Returns:
            Workspace context dict, or None if unavailable
        """
        if not self.config.enable_desktop:
            return None

        if not self.has_permission("workspace_metadata"):
            return None

        context = {}

        # Active window info
        if self._active_workspace:
            context["workspace"] = self._active_workspace

        return context or None

    def update_workspace_context(self, context: Dict[str, Any]) -> None:
        """Update the current workspace context.

        Args:
            context: Workspace context data
        """
        with self._lock:
            self._active_workspace = context

        self._record_history("workspace_updated", context)

        if self._event_bus:
            self._event_bus.emit_async(InteractionEvent.WORKSPACE_CHANGED.value, context)

    # ------------------------------------------------------------------
    # Interaction history
    # ------------------------------------------------------------------

    def _record_history(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an interaction event in the history buffer.

        Args:
            event_type: Type of event
            data: Event payload
        """
        if not self.config.enable_history:
            return

        with self._lock:
            self._history_buffer.append({
                "event_type": event_type,
                "data": data,
                "timestamp": time.time(),
            })
            # Trim buffer to max size
            if len(self._history_buffer) > self._max_history:
                self._history_buffer = self._history_buffer[-self._max_history:]

    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve interaction history.

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of entries to return

        Returns:
            List of history entries
        """
        with self._lock:
            if event_type:
                entries = [e for e in self._history_buffer if e.get("event_type") == event_type]
            else:
                entries = list(self._history_buffer)
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Plugin adapter registration
    # ------------------------------------------------------------------

    def register_voice_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register a voice provider adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable for voice operations
        """
        with self._lock:
            self._voice_adapters[name] = adapter_fn
        logger.info("InteractionManager: registered voice adapter '%s'", name)

    def register_desktop_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register a desktop integration adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable for desktop operations
        """
        with self._lock:
            self._desktop_adapters[name] = adapter_fn
        logger.info("InteractionManager: registered desktop adapter '%s'", name)

    def register_notification_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register a notification channel adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable[[Notification], bool] returning delivery success
        """
        with self._lock:
            self._notification_adapters[name] = adapter_fn
        logger.info("InteractionManager: registered notification adapter '%s'", name)

    def register_automation_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register an automation/presence adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable for automation triggers
        """
        with self._lock:
            self._automation_adapters[name] = adapter_fn
        logger.info("InteractionManager: registered automation adapter '%s'", name)

    def unregister_voice_adapter(self, name: str) -> bool:
        with self._lock:
            return self._voice_adapters.pop(name, None) is not None

    def unregister_desktop_adapter(self, name: str) -> bool:
        with self._lock:
            return self._desktop_adapters.pop(name, None) is not None

    def unregister_notification_adapter(self, name: str) -> bool:
        with self._lock:
            return self._notification_adapters.pop(name, None) is not None

    def unregister_automation_adapter(self, name: str) -> bool:
        with self._lock:
            return self._automation_adapters.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Status & health
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Get comprehensive interaction layer status."""
        with self._lock:
            return {
                "state": self._state.value,
                "config": {
                    "voice": self.config.enable_voice,
                    "desktop": self.config.enable_desktop,
                    "notifications": self.config.enable_notifications,
                    "presence": self.config.enable_presence,
                },
                "voice": {
                    "active_sessions": len(self._active_voice_sessions),
                    "adapters": list(self._voice_adapters.keys()),
                },
                "desktop": {
                    "adapters": list(self._desktop_adapters.keys()),
                    "active_workspace": self._active_workspace is not None,
                },
                "notifications": {
                    "adapters": list(self._notification_adapters.keys()),
                },
                "permissions": dict(self._permissions),
                "history_size": len(self._history_buffer),
            }

    def health(self) -> Dict[str, Any]:
        """Get interaction layer health status."""
        return {
            "state": self._state.value,
            "ready": self._state == InteractionState.READY,
            "voice_sessions": len(self._active_voice_sessions),
            "desktop_active": self._active_workspace is not None,
            "permissions_granted": sum(1 for v in self._permissions.values() if v),
            "permissions_total": len(self._permissions),
        }
