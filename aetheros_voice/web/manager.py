from __future__ import annotations

from typing import Any


class WebSettingsManager:
    def __init__(self):
        self._settings: dict = {
            "theme": "dark",
            "show_captions": False,
            "show_mic_indicator": True,
            "high_contrast": False,
            "font_size": 24,
            "language": "en",
        }

    def get_all(self) -> dict:
        return dict(self._settings)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        self._settings[key] = value
