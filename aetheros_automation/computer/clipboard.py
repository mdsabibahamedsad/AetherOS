from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class ClipboardController:
    def __init__(self):
        self._pyperclip = None
        self._available = False
        self._init_backend()

    def _init_backend(self):
        try:
            import pyperclip
            self._pyperclip = pyperclip
            self._available = True
            log.debug("ClipboardController: using pyperclip")
        except ImportError:
            log.warning("ClipboardController: pyperclip not available")

    def get_text(self) -> str:
        if not self._available:
            raise RuntimeError("Clipboard backend not available (pyperclip required)")
        return self._pyperclip.paste()

    def set_text(self, text: str):
        if not self._available:
            raise RuntimeError("Clipboard backend not available (pyperclip required)")
        self._pyperclip.copy(text)

    def clear(self):
        self.set_text("")
