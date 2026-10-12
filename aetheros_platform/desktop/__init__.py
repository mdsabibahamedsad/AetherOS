"""Desktop Environment — Python bridge for Electron/Tauri integration."""

from aetheros_platform.desktop.bridge import DesktopBridge
from aetheros_platform.desktop.window import WindowManager, WindowDefinition
from aetheros_platform.desktop.tray import TrayManager, TrayAction
from aetheros_platform.desktop.notifications import NotificationService, Notification

__all__ = [
    "DesktopBridge", "WindowManager", "WindowDefinition",
    "TrayManager", "TrayAction",
    "NotificationService", "Notification",
]
