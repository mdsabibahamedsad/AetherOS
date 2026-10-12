from __future__ import annotations

from abc import ABC, abstractmethod
from aetheros_voice.models.models import TTSResult


class TTSBackend(ABC):
    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        ...

    async def synthesize_stream(self, text_stream, speed: float = 1.0, voice: str | None = None, **kwargs):
        async for text in text_stream:
            yield await self.synthesize(text, speed=speed, voice=voice, **kwargs)

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
    def supports_offline(self) -> bool:
        return False

    @property
    def voices(self) -> list[str]:
        return []
