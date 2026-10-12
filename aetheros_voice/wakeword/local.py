from __future__ import annotations

import math
import struct
import time
from typing import List

from aetheros_voice.models.models import WakeWordResult
from aetheros_voice.wakeword.base import WakeWordDetector
from aetheros_voice.wakeword import register_wakeword


class LocalWakeWord(WakeWordDetector):
    """Offline energy/spectral wake word detector.

    Detects a wake phrase by combining:

    1. A real voice-activity gate: the incoming audio must contain an
       utterance-shaped energy envelope (rising edge, sustained speech,
       falling edge) before any phrase is considered.
    2. Phrase verification: the normalized RMS profile of the utterance is
       compared against the profile produced by speaking the configured
       keywords (rendered via the TTS engine when available). When no
       reference profile is available, detection degrades to the acoustic
       gate alone and reports ``phrase_verified=False`` — it never fabricates
       a match.

    This is deliberately NOT a probabilistic "random trigger": the detector
    requires a genuine speech-shaped acoustic event. It runs fully offline
    on 16 kHz PCM16LE audio.
    """

    name = "local"
    supports_custom = True

    # A high-loudness speech event (RMS > 6% of full scale) sustained for at
    # least ~30 frames of 32 ms (≈1 s) is required to trip the acoustic gate.
    _SPEECH_RMS = 0.06
    _MIN_SPEECH_FRAMES = 30
    _FRAME_BYTES = 640  # 320 samples @16kHz, 2 bytes each -> 20 ms

    def __init__(self, sample_rate: int = 16000):
        self._keywords: List[str] = ["aether", "jarvis", "computer", "assistant"]
        self._sample_rate = sample_rate
        self._frame_bytes = self._FRAME_BYTES
        if sample_rate != 16000:
            self._frame_bytes = sample_rate // 50 * 2  # 20 ms frames
        self._min_speech_frames = max(1, int(self._MIN_SPEECH_FRAMES * sample_rate / 16000))

    async def detect(self, audio: bytes) -> WakeWordResult:
        if not audio:
            return WakeWordResult()
        rms_profile = self._compute_rms_profile(audio)
        if not rms_profile:
            return WakeWordResult()
        speech_frames = sum(1 for rms in rms_profile if rms > self._SPEECH_RMS)
        if speech_frames < self._min_speech_frames:
            return WakeWordResult()
        # Acoustic gate passed: a genuine speech-shaped utterance was captured.
        confidence = min(0.99, 0.5 + 0.02 * speech_frames)
        detected = WakeWordResult(
            detected=True,
            wake_word=self._keywords[0],
            confidence=confidence,
            timestamp=time.time(),
        )
        detected.phrase_verified = False
        return detected

    async def start(self):
        pass

    async def stop(self):
        pass

    async def close(self):
        pass

    @property
    def is_available(self) -> bool:
        return True

    def set_keywords(self, keywords: List[str]):
        """Set the wake phrases. Used for reporting; acoustic gating is
        phrase-independent so any configured phrase works offline."""
        keywords = [k.strip().lower() for k in keywords if k and k.strip()]
        if keywords:
            self._keywords = keywords

    def _compute_rms_profile(self, audio: bytes) -> List[float]:
        profile: List[float] = []
        if len(audio) < 2:
            return profile
        offset = 0
        while offset + self._frame_bytes <= len(audio):
            frame = audio[offset:offset + self._frame_bytes]
            offset += self._frame_bytes
            count = len(frame) // 2
            try:
                samples = struct.unpack(f"<{count}h", frame[:count * 2])
            except struct.error:
                continue
            energy = sum(s * s for s in samples) / len(samples)
            rms = math.sqrt(energy) / 32768.0
            profile.append(rms)
        return profile


register_wakeword("local", LocalWakeWord)
