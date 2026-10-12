"""Desktop integration package for AetherOS interaction layer."""

from interaction.desktop.desktop_manager import (
    DesktopManager,
    DesktopConfig,
    DesktopEvent,
    DesktopPermission,
)
from interaction.desktop.window_tracker import (
    WindowTracker,
    WindowInfo,
    WindowEvent,
)
from interaction.desktop.workspace_monitor import (
    WorkspaceMonitor,
    WorkspaceInfo,
    WorkspaceChange,
)
from interaction.desktop.clipboard import (
    ClipboardMonitor,
    ClipboardEntry,
    ClipboardPermission,
)
from interaction.desktop.notifications import (
    NotificationManager,
    Notification,
    NotificationPriority,
    NotificationAction,
    NotificationChannel,
)
from interaction.desktop.shortcuts import (
    ShortcutManager,
    GlobalShortcut,
    ShortcutAction,
)

__all__ = [
    "DesktopManager",
    "DesktopConfig",
    "DesktopEvent",
    "DesktopPermission",
    "WindowTracker",
    "WindowInfo",
    "WindowEvent",
    "WorkspaceMonitor",
    "WorkspaceInfo",
    "WorkspaceChange",
    "ClipboardMonitor",
    "ClipboardEntry",
    "ClipboardPermission",
    "NotificationManager",
    "Notification",
    "NotificationPriority",
    "NotificationAction",
    "NotificationChannel",
    "ShortcutManager",
    "GlobalShortcut",
    "ShortcutAction",
]
