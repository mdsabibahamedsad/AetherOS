from __future__ import annotations

import time
from typing import Any


class CaptionSystem:
    def __init__(self):
        self._enabled = False
        self._current_text = ""
        self._history: list[str] = []
        self._max_history = 100
        self._font_size = 24
        self._high_contrast = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def show(self, text: str):
        self._current_text = text
        self._history.append(text)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def clear(self):
        self._current_text = ""

    @property
    def current(self) -> str:
        return self._current_text

    @property
    def history(self) -> list[str]:
        return list(self._history)

    def render(self) -> str:
        if not self._enabled:
            return ""
        if self._high_contrast:
            return f"\033[1;37;47m {self._current_text} \033[0m"
        return f"\033[3;36m🎤 {self._current_text}\033[0m"
