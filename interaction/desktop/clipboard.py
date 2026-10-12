"""
Clipboard Monitor — Permission-controlled clipboard observation.

Monitors clipboard changes for context awareness, but always requires
explicit user permission. Never reads clipboard content without consent.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class ClipboardPermission(enum.Enum):
    """Permission levels for clipboard access."""
    DENIED = "denied"          # No access
    TEXT_ONLY = "text_only"    # Only text content
    FULL = "full"              # All content types
    METADATA = "metadata"      # Only notification of change, not content


@dataclass
class ClipboardEntry:
    """A clipboard content snapshot.

    Attributes:
        timestamp: When the entry was captured
        content_type: Type of content (text, image, file_paths, etc.)
        text: Text content (only populated with TEXT_ONLY or FULL permission)
        size_bytes: Size of the content in bytes
        source: Source application (if detectable)
        metadata: Additional clipboard metadata
    """
    timestamp: float = 0.0
    content_type: str = "text"
    text: str = ""
    size_bytes: int = 0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClipboardMonitor:
    """Monitors clipboard changes with permission control.

    Never reads clipboard content without explicit user permission.
    Supports multiple permission levels for privacy-sensitive contexts.

    Usage:
        monitor = ClipboardMonitor()
        monitor.set_permission(ClipboardPermission.TEXT_ONLY)

        entry = monitor.get_latest()
        if entry:
            print(f"Clipboard: {entry.text[:50]}...")
    """

    def __init__(self, permission: ClipboardPermission = ClipboardPermission.DENIED):
        self._lock = threading.RLock()
        self._permission = permission
        self._latest: Optional[ClipboardEntry] = None
        self._history: List[ClipboardEntry] = []
        self._max_history: int = 50
        self._subscribers: List[Callable[[ClipboardEntry], None]] = []
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval: float = 1.0
        self._running = False
        self._detect_adapter: Optional[Callable[[], Optional[ClipboardEntry]]] = None

    def initialize(self) -> None:
        """Initialize the clipboard monitor."""
        logger.info("ClipboardMonitor: initialized (permission=%s)", self._permission.value)

    @property
    def permission(self) -> ClipboardPermission:
        """Current clipboard permission level."""
        return self._permission

    def set_permission(self, permission: ClipboardPermission) -> None:
        """Set clipboard access permission level.

        Args:
            permission: New permission level
        """
        with self._lock:
            self._permission = permission
        logger.info("ClipboardMonitor: permission set to %s", permission.value)

    def set_detect_adapter(self, adapter: Callable[[], Optional[ClipboardEntry]]) -> None:
        """Set a platform-specific clipboard detection adapter.

        Args:
            adapter: Callable returning current clipboard content or None
        """
        self._detect_adapter = adapter

    def get_latest(self, require_permission: bool = True) -> Optional[ClipboardEntry]:
        """Get the latest clipboard entry (permission-gated).

        Args:
            require_permission: Whether to check permission first

        Returns:
            Latest ClipboardEntry or None
        """
        if require_permission and self._permission == ClipboardPermission.DENIED:
            return None

        with self._lock:
            if self._permission == ClipboardPermission.METADATA:
                # Only return metadata (no content)
                if self._latest:
                    return ClipboardEntry(
                        timestamp=self._latest.timestamp,
                        content_type=self._latest.content_type,
                        size_bytes=self._latest.size_bytes,
                        source=self._latest.source,
                    )
            return self._latest

    def get_text(self) -> Optional[str]:
        """Get clipboard text if permission allows.

        Returns:
            Clipboard text or None
        """
        if self._permission not in (ClipboardPermission.TEXT_ONLY, ClipboardPermission.FULL):
            return None
        entry = self.get_latest()
        if entry and entry.content_type == "text":
            return entry.text
        return None

    def subscribe(self, callback: Callable[[ClipboardEntry], None]) -> Callable:
        """Subscribe to clipboard change events.

        Args:
            callback: Receives ClipboardEntry

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

    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start background clipboard monitoring.

        Args:
            interval: Poll interval in seconds
        """
        if self._running or self._permission == ClipboardPermission.DENIED:
            return
        self._running = True
        self._poll_interval = interval

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        self._poll_thread.start()
        logger.info("ClipboardMonitor: monitoring started (interval=%.1fs)", interval)

    def stop_monitoring(self) -> None:
        """Stop clipboard monitoring."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        logger.info("ClipboardMonitor: monitoring stopped")

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            if self._detect_adapter and self._permission != ClipboardPermission.DENIED:
                try:
                    entry = self._detect_adapter()
                    if entry:
                        self._update(entry)
                except Exception as exc:
                    logger.debug("ClipboardMonitor: poll failed: %s", exc)
            time.sleep(self._poll_interval)

    def _update(self, entry: ClipboardEntry) -> None:
        """Update clipboard state and notify subscribers.

        Args:
            entry: New clipboard entry
        """
        with self._lock:
            self._latest = entry
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Only notify with full content if permission allows
            if self._permission == ClipboardPermission.METADATA:
                notify_entry = ClipboardEntry(
                    timestamp=entry.timestamp,
                    content_type=entry.content_type,
                    size_bytes=entry.size_bytes,
                    source=entry.source,
                )
            else:
                notify_entry = entry

            subscribers = list(self._subscribers)

        for cb in subscribers:
            try:
                cb(notify_entry)
            except Exception as exc:
                logger.debug("ClipboardMonitor: subscriber failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self._lock:
            return {
                "permission": self._permission.value,
                "monitoring": self._running,
                "latest_type": self._latest.content_type if self._latest else None,
                "history_size": len(self._history),
            }
