"""
Window Tracker — Active window awareness for desktop context.

Monitors changes in the active window to derive user context
and trigger workspace-related events.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WindowEvent(enum.Enum):
    """Events related to window tracking."""
    WINDOW_ACTIVATED = "window.activated"
    WINDOW_DEACTIVATED = "window.deactivated"
    WINDOW_TITLE_CHANGED = "window.title_changed"
    WINDOW_CLOSED = "window.closed"
    WINDOW_MINIMIZED = "window.minimized"
    WINDOW_RESTORED = "window.restored"


@dataclass
class WindowInfo:
    """Information about a desktop window.

    Attributes:
        window_id: Platform-specific window identifier
        title: Window title
        process_name: Process name (e.g. "code", "chrome")
        process_path: Full process path (if available)
        workspace: Virtual desktop / workspace number
        is_visible: Whether the window is visible
        is_minimized: Whether the window is minimized
        is_focused: Whether the window is focused
        bounds: Window bounds (x, y, width, height)
        pid: Process ID (if available)
        metadata: Additional platform-specific data
    """
    window_id: str = ""
    title: str = ""
    process_name: str = ""
    process_path: str = ""
    workspace: int = 0
    is_visible: bool = True
    is_minimized: bool = False
    is_focused: bool = True
    bounds: Optional[Dict[str, int]] = None
    pid: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WindowTracker:
    """Tracks active windows to derive user context.

    Monitors the currently focused window and emits events when
    it changes. Provides APIs to query the active window and
    register for window change notifications.

    Usage:
        tracker = WindowTracker()
        tracker.initialize()

        active = tracker.get_active_window()
        tracker.subscribe(lambda event, info: print(f"Switched to {info.process_name}"))
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._active_window: Optional[WindowInfo] = None
        self._subscribers: List[Callable[[WindowEvent, WindowInfo], None]] = []
        self._history: List[WindowInfo] = []
        self._max_history: int = 100
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval: float = 2.0
        self._running = False

        # Platform-specific adapter
        self._platform_adapter: Optional[Callable[[], Optional[WindowInfo]]] = None

    def initialize(self) -> None:
        """Initialize the window tracker."""
        logger.info("WindowTracker: initialized")

    def set_platform_adapter(self, adapter: Callable[[], Optional[WindowInfo]]) -> None:
        """Set a platform-specific window detection adapter.

        Args:
            adapter: Callable returning current WindowInfo or None
        """
        self._platform_adapter = adapter

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active window.

        Returns:
            WindowInfo for the active window, or None
        """
        if self._platform_adapter:
            try:
                return self._platform_adapter()
            except Exception as exc:
                logger.debug("WindowTracker: platform adapter failed: %s", exc)
        return self._active_window

    def get_window_history(self, limit: int = 10) -> List[WindowInfo]:
        """Get recent window history.

        Args:
            limit: Maximum entries to return

        Returns:
            List of recent WindowInfo objects
        """
        with self._lock:
            return self._history[-limit:]

    def subscribe(self, callback: Callable[[WindowEvent, WindowInfo], None]) -> Callable:
        """Subscribe to window change events.

        Args:
            callback: Receives (event, window_info)

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self, event: WindowEvent, info: WindowInfo) -> None:
        """Notify subscribers of a window event.

        Args:
            event: The event type
            info: The window info
        """
        with self._lock:
            subscribers = list(self._subscribers)
        for cb in subscribers:
            try:
                cb(event, info)
            except Exception as exc:
                logger.debug("WindowTracker: subscriber failed: %s", exc)

    def start_polling(self, interval: float = 2.0) -> None:
        """Start polling for window changes in a background thread.

        Args:
            interval: Poll interval in seconds
        """
        if self._running:
            return
        self._running = True
        self._poll_interval = interval

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="window-tracker",
        )
        self._poll_thread.start()
        logger.info("WindowTracker: polling started (interval=%.1fs)", interval)

    def stop_polling(self) -> None:
        """Stop polling for window changes."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        logger.info("WindowTracker: polling stopped")

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            if self._platform_adapter:
                try:
                    window = self._platform_adapter()
                    if window:
                        self._update_active(window)
                except Exception as exc:
                    logger.debug("WindowTracker: poll iteration failed: %s", exc)
            time.sleep(self._poll_interval)

    def _update_active(self, window: WindowInfo) -> None:
        """Update the active window and notify if changed.

        Args:
            window: Current window info
        """
        with self._lock:
            prev = self._active_window
            self._active_window = window

            if prev is None or prev.window_id != window.window_id:
                self._history.append(window)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]

            # Notify if window changed
            if prev is None or prev.window_id != window.window_id:
                self._notify(WindowEvent.WINDOW_ACTIVATED, window)
            elif prev.title != window.title:
                self._notify(WindowEvent.WINDOW_TITLE_CHANGED, window)

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        with self._lock:
            return {
                "active_window": self._active_window.process_name if self._active_window else None,
                "history_size": len(self._history),
                "polling": self._running,
                "subscribers": len(self._subscribers),
            }
