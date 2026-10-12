from __future__ import annotations

import struct
import math


class NoiseSuppressor:
    def __init__(self, reduction_db: float = 12.0, enabled: bool = True):
        self._reduction = reduction_db
        self._enabled = enabled
        self._noise_profile: list[float] | None = None

    def process(self, audio: bytes) -> bytes:
        if not self._enabled or len(audio) < 2:
            return audio
        try:
            count = len(audio) // 2
            samples = list(struct.unpack(f"<{count}h", audio[:count * 2]))
            if self._noise_profile is None:
                self._noise_profile = [abs(s) / 32768.0 for s in samples[:1024]]
                return audio
            factor = 10 ** (-self._reduction / 20)
            processed = []
            for i, s in enumerate(samples):
                noise_floor = self._noise_profile[i % len(self._noise_profile)] * 32768.0
                if abs(s) > noise_floor * 1.5:
                    processed.append(s)
                else:
                    processed.append(int(s * factor))
            return struct.pack(f"<{len(processed)}h", *processed)
        except Exception:
            return audio

    def reset(self):
        self._noise_profile = None
