from __future__ import annotations

import time
from abc import ABC, abstractmethod
from aetheros_voice.models.models import WakeWordResult


class WakeWordDetector(ABC):
    name: str = "base"

    @abstractmethod
    async def detect(self, audio: bytes) -> WakeWordResult:
        ...

    async def start(self):
        pass

    async def stop(self):
        pass

    async def close(self):
        pass

    @property
    def is_available(self) -> bool:
        return True

    @property
    def supports_custom(self) -> bool:
        return False
