"""Desktop resource locks (Step 75).

Guards shared input/automation resources so two agents (or two sessions) can
never drive the same surface simultaneously — keyboard, mouse, clipboard,
terminal, workspace, display. A lock is a named, held-by-holder contract;
acquisition returns False when another holder already owns it (the caller
should defer or deny, not queue forever).

Pure in-memory; the manager consults it before executing actions that touch
a governed resource.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

# Stable resource names. Every resource an action can touch maps to one of
# these keys; ungoverned actions (e.g. pure observation) touch none.
KEYBOARD = "keyboard"
MOUSE = "mouse"
CLIPBOARD = "clipboard"
TERMINAL = "terminal"
WORKSPACE = "workspace"
DISPLAY = "display"

DESKTOP_RESOURCES = (KEYBOARD, MOUSE, CLIPBOARD, TERMINAL, WORKSPACE, DISPLAY)

# Action type → the resource it governs (used by manager lock-checking).
ACTION_RESOURCES = {
    "TYPE": KEYBOARD,
    "KEY_PRESS": KEYBOARD,
    "CLICK": MOUSE,
    "DOUBLE_CLICK": MOUSE,
    "DRAG": MOUSE,
    "MOVE": MOUSE,
    "SCROLL": MOUSE,
    "COPY": CLIPBOARD,
    "PASTE": KEYBOARD,
    "SCREENSHOT": DISPLAY,
    "APP_LAUNCH": WORKSPACE,
    "APP_CLOSE": WORKSPACE,
}


class ResourceLockManager:
    """Named exclusive locks keyed by resource."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._holders: Dict[str, str] = {}

    def acquire(self, resource: str, holder: str) -> bool:
        """Try to take ``resource`` for ``holder``. False if already held."""
        if not holder:
            return True  # anonymous holders cannot conflict
        with self._lock:
            current = self._holders.get(resource)
            if current is not None and current != holder:
                return False
            self._holders[resource] = holder
            return True

    def release(self, resource: str, holder: str) -> bool:
        """Release ``resource`` if held by ``holder``."""
        with self._lock:
            if self._holders.get(resource) != holder:
                return False
            del self._holders[resource]
            return True

    def held_by(self, resource: str) -> Optional[str]:
        with self._lock:
            return self._holders.get(resource)

    def held(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._holders)

    def release_all(self, holder: str) -> int:
        """Release every resource held by ``holder``; returns count released."""
        with self._lock:
            dropped = [r for r, h in self._holders.items() if h == holder]
            for r in dropped:
                del self._holders[r]
            return len(dropped)

    def reset(self) -> None:
        with self._lock:
            self._holders.clear()