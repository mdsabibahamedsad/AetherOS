from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aetheros_voice.models.models import STTResult


class STTBackend(ABC):
    name: str = "base"

    @abstractmethod
    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        ...

    @abstractmethod
    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        ...

    async def load_model(self):
        pass

    async def unload_model(self):
        pass

    async def close(self):
        pass

    @property
    def is_available(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_offline(self) -> bool:
        return False

    @property
    def languages(self) -> list[str]:
        return ["en"]
