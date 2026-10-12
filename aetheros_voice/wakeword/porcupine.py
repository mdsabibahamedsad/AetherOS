from __future__ import annotations

import os, time
from aetheros_voice.models.models import WakeWordResult
from aetheros_voice.wakeword.base import WakeWordDetector
from aetheros_voice.wakeword import register_wakeword


class PorcupineWakeWord(WakeWordDetector):
    name = "porcupine"
    supports_custom = True

    def __init__(self, keywords: list[str] | None = None):
        self._access_key = os.getenv("PICOVOICE_ACCESS_KEY", "")
        self._keywords = keywords or ["hey aether"]
        self._porcupine = None
        self._audio_stream = None

    async def start(self):
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(
                access_key=self._access_key,
                keywords=self._keywords,
            )
        except ImportError:
            pass

    async def detect(self, audio: bytes) -> WakeWordResult:
        if self._porcupine is None:
            await self.start()
        if self._porcupine is None:
            return WakeWordResult()

        try:
            import struct
            frame_width = self._porcupine.frame_length
            frames = [audio[i:i+frame_width*2] for i in range(0, len(audio), frame_width*2)]
            for frame in frames:
                if len(frame) < frame_width * 2:
                    continue
                pcm = struct.unpack_from("h" * frame_width, frame)
                result = self._porcupine.process(pcm)
                if result >= 0:
                    return WakeWordResult(
                        detected=True,
                        wake_word=self._keywords[result] if result < len(self._keywords) else "",
                        confidence=1.0,
                        timestamp=time.time(),
                    )
            return WakeWordResult()
        except Exception:
            return WakeWordResult()

    async def stop(self):
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

    async def close(self):
        await self.stop()

    @property
    def is_available(self) -> bool:
        return bool(self._access_key)


register_wakeword("porcupine", PorcupineWakeWord)
