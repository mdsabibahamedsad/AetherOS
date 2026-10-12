from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES = {
    "en": "English", "bn": "Bangla", "hi": "Hindi", "ar": "Arabic",
    "ja": "Japanese", "zh": "Chinese", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "ru": "Russian", "ko": "Korean",
    "it": "Italian", "nl": "Dutch", "tr": "Turkish", "vi": "Vietnamese",
    "th": "Thai", "pl": "Polish", "uk": "Ukrainian", "ro": "Romanian",
}


class LanguageDetector:
    def __init__(self):
        self._last_language = "en"
        self._confidence = 0.0

    async def detect(self, text: str) -> str:
        if not text or len(text) < 3:
            return self._last_language
        import re
        scripts = {
            "bn": re.compile(r'[\u0980-\u09FF]'),
            "hi": re.compile(r'[\u0900-\u097F]'),
            "ar": re.compile(r'[\u0600-\u06FF]'),
            "ja": re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'),
            "zh": re.compile(r'[\u4E00-\u9FFF]'),
            "ko": re.compile(r'[\uAC00-\uD7AF]'),
            "th": re.compile(r'[\u0E00-\u0E7F]'),
            "ru": re.compile(r'[\u0400-\u04FF]'),
            "el": re.compile(r'[\u0370-\u03FF]'),
        }
        for lang, pattern in scripts.items():
            if pattern.search(text):
                self._last_language = lang
                self._confidence = 0.9
                return lang
        self._last_language = "en"
        self._confidence = 0.8
        return "en"

    @property
    def last_language(self) -> str:
        return self._last_language

    @property
    def last_confidence(self) -> float:
        return self._confidence

    def list_languages(self) -> dict[str, str]:
        return dict(SUPPORTED_LANGUAGES)
