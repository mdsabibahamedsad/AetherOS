from __future__ import annotations

import time


class MicrophoneIndicator:
    def __init__(self):
        self._active = False
        self._style = "default"
        self._start_time = 0.0

    def show(self, style: str = "default"):
        self._active = True
        self._style = style
        self._start_time = time.time()

    def hide(self):
        self._active = False

    @property
    def is_visible(self) -> bool:
        return self._active

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_time if self._active else 0.0

    def render_terminal(self) -> str:
        if not self._active:
            return ""
        elapsed = self.elapsed
        pulse = "|/-\\"[int(elapsed * 4) % 4]
        if self._style == "minimal":
            return f"\r🎤 {pulse}"
        return f"\r🎤 Listening {pulse} ({elapsed:.1f}s)"

    def render_html(self) -> str:
        if not self._active:
            return ""
        return '<div class="mic-indicator active"><span class="mic-pulse"></span> Listening...</div>'
