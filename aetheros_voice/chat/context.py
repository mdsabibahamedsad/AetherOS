from __future__ import annotations

import time
from typing import Any


class VoiceContext:
    def __init__(self):
        self._data: dict[str, Any] = {
            "screen": "",
            "active_app": "",
            "location": "",
            "time": "",
            "user_name": "",
            "preferences": {},
        }

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def update_from_screen(self, text: str, active_window: str = ""):
        self._data["screen"] = text
        if active_window:
            self._data["active_app"] = active_window

    def snapshot(self) -> dict:
        return dict(self._data)

    def clear(self):
        self._data.clear()
