"""
Shortcut Manager — Global keyboard shortcut registration.

Allows registering global shortcuts that trigger Aetheros actions
from anywhere on the desktop. Shortcuts are registered with platform
adapters.
"""

from __future__ import annotations

import enum
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ShortcutAction(enum.Enum):
    """Built-in shortcut actions."""
    SHOW_AETHEROS = "show_aetheros"
    START_VOICE = "start_voice"
    STOP_VOICE = "stop_voice"
    TOGGLE_VOICE = "toggle_voice"
    CAPTURE_SCREENSHOT = "capture_screenshot"
    OPEN_SEARCH = "open_search"
    OPEN_COMMAND_PALETTE = "open_command_palette"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    CUSTOM = "custom"


@dataclass
class GlobalShortcut:
    """A registered global shortcut binding.

    Attributes:
        id: Unique shortcut identifier
        name: Human-readable shortcut name
        keys: Key combination (e.g. "Ctrl+Shift+A")
        action: Action to trigger
        action_fn: Custom action callback (for CUSTOM type)
        enabled: Whether the shortcut is active
        platform: Platform-specific shortcut ID
        description: Short description of what the shortcut does
        metadata: Additional metadata
    """
    id: str = ""
    name: str = ""
    keys: str = ""
    action: ShortcutAction = ShortcutAction.CUSTOM
    action_fn: Optional[Callable] = None
    enabled: bool = True
    platform: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShortcutManager:
    """Manages global keyboard shortcut registration.

    Supports registering, unregistering, enabling, and disabling
    global shortcuts. Platform adapters handle OS-level registration.

    Usage:
        mgr = ShortcutManager()
        mgr.initialize()

        shortcut = GlobalShortcut(
            name="Toggle Voice",
            keys="Ctrl+Shift+V",
            action=ShortcutAction.TOGGLE_VOICE,
        )
        mgr.register(shortcut)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._shortcuts: Dict[str, GlobalShortcut] = {}
        self._platform_adapter: Optional[Callable] = None
        self._subscribers: Dict[ShortcutAction, List[Callable]] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the shortcut manager."""
        self._initialized = True
        logger.info("ShortcutManager: initialized")

    def set_platform_adapter(self, adapter: Callable) -> None:
        """Set a platform-specific shortcut registration adapter.

        The adapter receives commands: register(shortcut), unregister(id),
        enable(id), disable(id).

        Args:
            adapter: Platform shortcut handler
        """
        self._platform_adapter = adapter

    def register(self, shortcut: GlobalShortcut) -> bool:
        """Register a global shortcut.

        Args:
            shortcut: Shortcut configuration

        Returns:
            True if registered
        """
        if not shortcut.id:
            shortcut.id = uuid.uuid4().hex[:12]

        with self._lock:
            self._shortcuts[shortcut.id] = shortcut

        if self._platform_adapter:
            try:
                self._platform_adapter("register", shortcut)
            except Exception as exc:
                logger.warning("ShortcutManager: platform registration failed: %s", exc)
                return False

        logger.info("ShortcutManager: registered shortcut '%s' (%s)", shortcut.name, shortcut.keys)
        return True

    def unregister(self, shortcut_id: str) -> bool:
        """Unregister a global shortcut.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            True if unregistered
        """
        with self._lock:
            shortcut = self._shortcuts.pop(shortcut_id, None)
            if shortcut is None:
                return False

        if self._platform_adapter:
            try:
                self._platform_adapter("unregister", shortcut_id)
            except Exception as exc:
                logger.debug("ShortcutManager: platform unregister failed: %s", exc)

        logger.info("ShortcutManager: unregistered shortcut %s", shortcut_id[:8])
        return True

    def enable(self, shortcut_id: str) -> bool:
        """Enable a shortcut.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            True if enabled
        """
        with self._lock:
            shortcut = self._shortcuts.get(shortcut_id)
            if shortcut is None:
                return False
            shortcut.enabled = True

        if self._platform_adapter:
            try:
                self._platform_adapter("enable", shortcut_id)
            except Exception as exc:
                logger.debug("ShortcutManager: platform enable failed: %s", exc)
        return True

    def disable(self, shortcut_id: str) -> bool:
        """Disable a shortcut.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            True if disabled
        """
        with self._lock:
            shortcut = self._shortcuts.get(shortcut_id)
            if shortcut is None:
                return False
            shortcut.enabled = False

        if self._platform_adapter:
            try:
                self._platform_adapter("disable", shortcut_id)
            except Exception as exc:
                logger.debug("ShortcutManager: platform disable failed: %s", exc)
        return True

    def get_shortcut(self, shortcut_id: str) -> Optional[GlobalShortcut]:
        """Get a shortcut by ID.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            GlobalShortcut or None
        """
        with self._lock:
            return self._shortcuts.get(shortcut_id)

    def find_by_keys(self, keys: str) -> Optional[GlobalShortcut]:
        """Find a shortcut by key combination.

        Args:
            keys: Key combination (e.g. "Ctrl+Shift+A")

        Returns:
            Matching GlobalShortcut or None
        """
        with self._lock:
            for shortcut in self._shortcuts.values():
                if shortcut.keys.lower() == keys.lower():
                    return shortcut
        return None

    def subscribe(self, action: ShortcutAction, callback: Callable) -> Callable:
        """Subscribe to a shortcut action being triggered.

        Args:
            action: Action to subscribe to
            callback: Callable to invoke

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.setdefault(action, []).append(callback)

        def unsubscribe():
            with self._lock:
                cbs = self._subscribers.get(action, [])
                if callback in cbs:
                    cbs.remove(callback)

        return unsubscribe

    def trigger(self, shortcut_id: str) -> bool:
        """Trigger a shortcut's action.

        Args:
            shortcut_id: Shortcut to trigger

        Returns:
            True if triggered
        """
        with self._lock:
            shortcut = self._shortcuts.get(shortcut_id)
            if shortcut is None or not shortcut.enabled:
                return False
            action = shortcut.action
            subscribers = list(self._subscribers.get(action, []))
            action_fn = shortcut.action_fn

        # Invoke action function
        if action_fn:
            try:
                action_fn()
            except Exception as exc:
                logger.warning("ShortcutManager: action_fn failed: %s", exc)

        # Notify subscribers
        for cb in subscribers:
            try:
                cb(shortcut)
            except Exception as exc:
                logger.debug("ShortcutManager: subscriber failed: %s", exc)

        return True

    def list_shortcuts(self) -> List[GlobalShortcut]:
        """List all registered shortcuts.

        Returns:
            List of GlobalShortcut objects
        """
        with self._lock:
            return list(self._shortcuts.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get shortcut manager statistics."""
        with self._lock:
            return {
                "total": len(self._shortcuts),
                "enabled": sum(1 for s in self._shortcuts.values() if s.enabled),
                "platform_adapter": self._platform_adapter is not None,
            }
