"""Window management — window definitions, positioning, state."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class WindowDefinition:
    id: str
    title: str
    url: str = ""
    width: int = 1024
    height: int = 768
    min_width: int = 400
    min_height: int = 300
    x: Optional[int] = None
    y: Optional[int] = None
    resizable: bool = True
    maximized: bool = False
    fullscreen: bool = False
    frameless: bool = False
    transparent: bool = False
    always_on_top: bool = False
    show_in_taskbar: bool = True
    icon: str = ""
    devtools: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class WindowManager:
    def __init__(self):
        self._windows: dict[str, WindowDefinition] = {}
        self._active_window: Optional[str] = None

    def create(self, window: WindowDefinition):
        self._windows[window.id] = window
        self._active_window = window.id
        logger.info("Created window: %s", window.id)

    def get(self, window_id: str) -> Optional[WindowDefinition]:
        return self._windows.get(window_id)

    def list(self) -> list[WindowDefinition]:
        return list(self._windows.values())

    def update(self, window_id: str, updates: dict) -> bool:
        win = self._windows.get(window_id)
        if not win:
            return False
        for k, v in updates.items():
            if hasattr(win, k):
                setattr(win, k, v)
        return True

    def close(self, window_id: str) -> bool:
        result = self._windows.pop(window_id, None) is not None
        if result and self._active_window == window_id:
            self._active_window = next(iter(self._windows)) if self._windows else None
        return result

    def set_active(self, window_id: str) -> bool:
        if window_id in self._windows:
            self._active_window = window_id
            return True
        return False

    def get_active(self) -> Optional[WindowDefinition]:
        if self._active_window:
            return self._windows.get(self._active_window)
        return None

    def count(self) -> int:
        return len(self._windows)

    def close_all(self):
        self._windows.clear()
        self._active_window = None

    def to_dict(self) -> list[dict]:
        return [w.__dict__ for w in self._windows.values()]
