"""
Desktop Manager — Coordinates desktop integration features.

Manages window tracking, workspace detection, clipboard monitoring,
notification delivery, and global shortcuts. Everything requires
explicit permission before activation.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class DesktopEvent(enum.Enum):
    """Events emitted by the desktop manager."""
    DESKTOP_INITIALIZED = "desktop.initialized"
    DESKTOP_SHUTDOWN = "desktop.shutdown"
    WINDOW_CHANGED = "desktop.window_changed"
    WORKSPACE_CHANGED = "desktop.workspace_changed"
    CLIPBOARD_UPDATED = "desktop.clipboard_updated"
    NOTIFICATION_DELIVERED = "desktop.notification_delivered"
    NOTIFICATION_ACTION = "desktop.notification_action"
    SHORTCUT_TRIGGERED = "desktop.shortcut_triggered"
    PERMISSION_REQUIRED = "desktop.permission_required"


class DesktopPermission(enum.Enum):
    """Permissions required for desktop features."""
    WINDOW_ACCESS = "window_access"
    WORKSPACE_CONTEXT = "workspace_context"
    CLIPBOARD_READ = "clipboard_read"
    NOTIFICATIONS = "notifications"
    SHORTCUTS = "shortcuts"
    FILE_SELECTION = "file_selection"


@dataclass
class DesktopConfig:
    """Configuration for desktop integration.

    Attributes:
        enable_window_tracking: Track active windows
        enable_workspace_detection: Detect workspace/project context
        enable_clipboard_monitoring: Monitor clipboard changes
        enable_notifications: Deliver desktop notifications
        enable_shortcuts: Register global shortcuts
        clipboard_monitor_interval: Clipboard poll interval in seconds
        window_poll_interval: Window poll interval in seconds
        permissions_required: Require explicit permission for features
    """
    enable_window_tracking: bool = True
    enable_workspace_detection: bool = True
    enable_clipboard_monitoring: bool = False
    enable_notifications: bool = True
    enable_shortcuts: bool = True
    clipboard_monitor_interval: float = 1.0
    window_poll_interval: float = 2.0
    permissions_required: bool = True


class DesktopManager:
    """Coordinates all desktop integration features.

    Manages sub-modules for window tracking, workspace detection,
    clipboard monitoring, notifications, and global shortcuts.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[DesktopConfig] = None,
    ):
        self._event_bus = event_bus
        self.config = config or DesktopConfig()
        self._lock = threading.RLock()
        self._initialized = False

        # Permissions cache
        self._permissions: Dict[str, bool] = {
            "window_access": False,
            "workspace_context": False,
            "clipboard_read": False,
            "notifications": True,
            "shortcuts": True,
            "file_selection": False,
        }

        # Sub-adapter registries
        self._window_adapters: Dict[str, Callable] = {}
        self._clipboard_adapters: Dict[str, Callable] = {}

    def initialize(self) -> None:
        """Initialize desktop integration."""
        if self._initialized:
            return
        self._initialized = True

        logger.info("DesktopManager: initialized (window=%s, workspace=%s, clipboard=%s, notifications=%s)",
                     self.config.enable_window_tracking,
                     self.config.enable_workspace_detection,
                     self.config.enable_clipboard_monitoring,
                     self.config.enable_notifications)

        if self._event_bus:
            self._event_bus.emit(DesktopEvent.DESKTOP_INITIALIZED.value, {
                "config": {
                    "window_tracking": self.config.enable_window_tracking,
                    "workspace_detection": self.config.enable_workspace_detection,
                    "clipboard": self.config.enable_clipboard_monitoring,
                    "notifications": self.config.enable_notifications,
                    "shortcuts": self.config.enable_shortcuts,
                },
            })

    def shutdown(self) -> None:
        """Shut down desktop integration."""
        self._initialized = False
        logger.info("DesktopManager: shut down")

        if self._event_bus:
            self._event_bus.emit(DesktopEvent.DESKTOP_SHUTDOWN.value, {})

    # ------------------------------------------------------------------
    # Permission management
    # ------------------------------------------------------------------

    def check_permission(self, permission: DesktopPermission) -> bool:
        """Check if a permission is granted.

        Args:
            permission: Permission to check

        Returns:
            True if granted or permissions not required
        """
        if not self.config.permissions_required:
            return True
        return self._permissions.get(permission.value, False)

    def grant_permission(self, permission: DesktopPermission) -> None:
        """Grant a desktop permission.

        Args:
            permission: Permission to grant
        """
        with self._lock:
            self._permissions[permission.value] = True
        logger.info("DesktopManager: permission granted: %s", permission.value)

    def revoke_permission(self, permission: DesktopPermission) -> None:
        """Revoke a desktop permission.

        Args:
            permission: Permission to revoke
        """
        with self._lock:
            self._permissions[permission.value] = False
        logger.info("DesktopManager: permission revoked: %s", permission.value)

    # ------------------------------------------------------------------
    # Plugin adapter registration
    # ------------------------------------------------------------------

    def register_window_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register a window tracking adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable that returns current window info
        """
        with self._lock:
            self._window_adapters[name] = adapter_fn
        logger.debug("DesktopManager: registered window adapter '%s'", name)

    def register_clipboard_adapter(self, name: str, adapter_fn: Callable) -> None:
        """Register a clipboard monitoring adapter.

        Args:
            name: Unique adapter name
            adapter_fn: Callable that returns clipboard content
        """
        with self._lock:
            self._clipboard_adapters[name] = adapter_fn
        logger.debug("DesktopManager: registered clipboard adapter '%s'", name)

    def get_active_window_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active window.

        Returns:
            Dict with window info, or None if unavailable
        """
        if not self.config.enable_window_tracking:
            return None
        if not self.check_permission(DesktopPermission.WINDOW_ACCESS):
            return None

        for name, adapter in self._window_adapters.items():
            try:
                result = adapter()
                if result:
                    return result
            except Exception as exc:
                logger.debug("DesktopManager: window adapter %s failed: %s", name, exc)
        return None

    def get_workspace_context(self) -> Optional[Dict[str, Any]]:
        """Detect current workspace/project context.

        Returns:
            Dict with workspace context, or None
        """
        if not self.config.enable_workspace_detection:
            return None
        if not self.check_permission(DesktopPermission.WORKSPACE_CONTEXT):
            return None

        window_info = self.get_active_window_info()
        if not window_info:
            return None

        # Derive workspace context from active window
        context: Dict[str, Any] = {
            "active_window_title": window_info.get("title", ""),
            "active_window_process": window_info.get("process", ""),
            "detected_at": time.time(),
        }

        # Try to determine project from window title or process
        title = (window_info.get("title") or "").lower()
        for indicator, project_type in [
            ("visual studio code", "vscode"),
            ("code", "vscode"),
            ("terminal", "terminal"),
            ("idea", "intellij"),
            ("pycharm", "pycharm"),
            ("vim", "vim"),
            ("neovim", "nvim"),
            ("emacs", "emacs"),
            ("chrome", "chrome"),
            ("browser", "browser"),
        ]:
            if indicator in title:
                context["application_type"] = project_type
                break

        return context

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get desktop manager statistics."""
        return {
            "initialized": self._initialized,
            "window_tracking": self.config.enable_window_tracking,
            "workspace_detection": self.config.enable_workspace_detection,
            "clipboard_monitoring": self.config.enable_clipboard_monitoring,
            "shortcuts": self.config.enable_shortcuts,
            "permissions": dict(self._permissions),
            "window_adapters": len(self._window_adapters),
            "clipboard_adapters": len(self._clipboard_adapters),
        }
