from __future__ import annotations

import struct
import time


class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.02, min_speech_frames: int = 5, silence_timeout: float = 1.5):
        self._threshold = threshold
        self._min_speech_frames = min_speech_frames
        self._silence_timeout = silence_timeout
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speech = False
        self._speech_start = 0.0
        self._last_speech = 0.0

    def is_speech(self, audio_chunk: bytes) -> bool:
        rms = self._compute_rms(audio_chunk)
        if rms > self._threshold:
            self._speech_frames += 1
            self._silence_frames = 0
            self._last_speech = time.time()
            if self._speech_frames >= self._min_speech_frames:
                if not self._is_speech:
                    self._speech_start = time.time()
                self._is_speech = True
        else:
            self._silence_frames += 1
            self._speech_frames = 0
            if self._is_speech and (time.time() - self._last_speech) > self._silence_timeout:
                self._is_speech = False
        return self._is_speech

    @property
    def speech_duration(self) -> float:
        if not self._is_speech:
            return 0.0
        return time.time() - self._speech_start

    def reset(self):
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speech = False

    def _compute_rms(self, audio: bytes) -> float:
        if len(audio) < 2:
            return 0.0
        try:
            count = len(audio) // 2
            samples = struct.unpack(f"<{count}h", audio[:count * 2])
            rms = sum(s * s for s in samples) / len(samples)
            return (rms ** 0.5) / 32768.0
        except Exception:
            return 0.0
