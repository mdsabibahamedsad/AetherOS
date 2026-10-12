"""Jarvis Mode — accessibility.

Exposes accessibility features: keyboard shortcuts, screen-reader support,
captions, high contrast, reduced motion, and voice alternatives. The manager
reports current state and persists user choices so assistive preferences
survive restarts.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    import os

    def get_aetheros_home() -> Path:
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class AccessibilityManager:
    """Stateful accessibility preferences for the Jarvis runtime.

    These settings are consumed by presentation layers (CLI, TUI, voice).
    The manager stores them in ``<home>/jarvis/accessibility.json``.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._path = self._home / "jarvis" / "accessibility.json"
        self._lock = threading.RLock()
        self._keyboard_shortcuts = True
        self._screen_reader = False
        self._captions = False
        self._high_contrast = False
        self._reduced_motion = False
        self._voice_alternative = True
        self._load()

    # ------------------------------------------------------------------
    # Toggles
    # ------------------------------------------------------------------

    def set(self, **kwargs: bool) -> None:
        with self._lock:
            for key, value in kwargs.items():
                attr = f"_{key}"
                if hasattr(self, attr):
                    setattr(self, attr, bool(value))
            self._save()

    @property
    def keyboard_shortcuts(self) -> bool:
        with self._lock:
            return self._keyboard_shortcuts

    @property
    def screen_reader(self) -> bool:
        with self._lock:
            return self._screen_reader

    @property
    def captions(self) -> bool:
        with self._lock:
            return self._captions

    @property
    def high_contrast(self) -> bool:
        with self._lock:
            return self._high_contrast

    @property
    def reduced_motion(self) -> bool:
        with self._lock:
            return self._reduced_motion

    @property
    def voice_alternative(self) -> bool:
        with self._lock:
            return self._voice_alternative

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    SHORTCUTS = {
        "wake": "Ctrl+Alt+A",
        "push_to_talk": "Ctrl+Alt+V",
        "interrupt": "Esc",
        "toggle_captions": "Ctrl+Alt+C",
        "toggle_voice": "Ctrl+Alt+M",
        "briefing": "Ctrl+Alt+B",
        "help": "Ctrl+/",
    }

    def shortcut(self, action: str) -> str:
        return self.SHORTCUTS.get(action, "")

    def describe(self) -> str:
        with self._lock:
            parts = []
            if self._keyboard_shortcuts:
                parts.append("Keyboard shortcuts: on")
            if self._screen_reader:
                parts.append("Screen reader: on")
            if self._captions:
                parts.append("Captions: on")
            if self._high_contrast:
                parts.append("High contrast: on")
            if self._reduced_motion:
                parts.append("Reduced motion: on")
            if self._voice_alternative:
                parts.append("Voice alternatives: on")
            return "; ".join(parts) if parts else "Accessibility: default"

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "keyboard_shortcuts": self._keyboard_shortcuts,
                "screen_reader": self._screen_reader,
                "captions": self._captions,
                "high_contrast": self._high_contrast,
                "reduced_motion": self._reduced_motion,
                "voice_alternative": self._voice_alternative,
                "shortcuts": dict(self.SHORTCUTS),
            }

    def _load(self) -> None:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key in ("keyboard_shortcuts", "screen_reader", "captions", "high_contrast", "reduced_motion", "voice_alternative"):
                    if key in data:
                        setattr(self, f"_{key}", bool(data[key]))
        except Exception as exc:
            logger.debug("Could not load accessibility settings: %s", exc)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = self.snapshot()
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.debug("Could not save accessibility settings: %s", exc)
