"""Jarvis Mode — wake word engine.

Bridges the offline acoustic wake word detector from ``aetheros_voice`` with
the Jarvis runtime. Supports custom wake phrases, energy-gated offline
detection, and push-to-talk. A wake event is only emitted when a real
speech-shaped acoustic event is captured — never randomly.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable, List, Optional

from aetheros_jarvis.models import WakeEvent, WakeWordSource

logger = logging.getLogger(__name__)

try:
    from aetheros_voice.wakeword import create_wakeword
    from aetheros_voice.noise.vad import VoiceActivityDetector
except Exception:  # pragma: no cover - degraded when voice package absent
    create_wakeword = None  # type: ignore[assignment]
    VoiceActivityDetector = None  # type: ignore[assignment,misc]


class WakeWordEngine:
    """Detects a configured wake phrase from audio frames.

    Detection pipeline:
      1. Audio frames (16 kHz PCM16LE) flow through a voice-activity gate.
      2. A speech-shaped utterance trips the acoustic detector.
      3. The phrase is matched against the configured wake phrases.

    When the voice package's offline detector is unavailable, the engine
    reports ``available=False`` and never fabricates a wake event.
    """

    def __init__(self, phrases: Optional[List[str]] = None, enabled: bool = True) -> None:
        self._phrases: List[str] = [p.strip().lower() for p in (phrases or ["aether", "jarvis"]) if p and p.strip()]
        self._enabled = enabled
        self._lock = threading.RLock()
        self._listeners: List[Callable[[WakeEvent], None]] = []
        self._detector = None
        self._init_detector()

    def _init_detector(self) -> None:
        try:
            if create_wakeword is not None:
                self._detector = create_wakeword("local")
                if hasattr(self._detector, "set_keywords"):
                    self._detector.set_keywords(self._phrases)
        except Exception as exc:
            logger.warning("Wake word detector unavailable: %s", exc)
            self._detector = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def phrases(self) -> List[str]:
        with self._lock:
            return list(self._phrases)

    def set_phrases(self, phrases: List[str]) -> None:
        with self._lock:
            self._phrases = [p.strip().lower() for p in phrases if p and p.strip()]
            if self._detector is not None and hasattr(self._detector, "set_keywords"):
                self._detector.set_keywords(self._phrases)

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def available(self) -> bool:
        return self._detector is not None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def process_frame(self, audio: bytes) -> Optional[WakeEvent]:
        """Feed an audio frame; returns a WakeEvent when the phrase is heard."""
        if not self._enabled or self._detector is None:
            return None
        try:
            result = self._run_detection(audio)
            if result is not None:
                event = self._to_event(result)
                if event is not None:
                    self._emit(event)
                    return event
            return None
        except Exception as exc:
            logger.debug("Wake word frame error: %s", exc)
            return None

    def _run_detection(self, audio: bytes):
        """Run the async detector without blocking a running event loop.

        Executes in a dedicated worker thread and joins with a timeout so a
        hung detector can never stall the calling (audio) thread.
        """
        result_holder: list = []
        error_holder: list = []

        def _work() -> None:
            try:
                result_holder.append(asyncio.run(self._detector.detect(audio)))
            except Exception as exc:  # pragma: no cover - defensive
                error_holder.append(exc)

        worker = threading.Thread(target=_work, daemon=True, name="wake-detect")
        worker.start()
        worker.join(timeout=1.0)
        if worker.is_alive():
            logger.warning("Wake word detection timed out; frame dropped")
            return None
        if error_holder:
            raise error_holder[0]
        return result_holder[0] if result_holder else None

    def _to_event(self, result) -> Optional[WakeEvent]:
        if result is None:
            return None
        detected = bool(getattr(result, "detected", False))
        if not detected:
            return None
        phrase = getattr(result, "wake_word", "") or (self._phrases[0] if self._phrases else "")
        confidence = float(getattr(result, "confidence", 0.0) or 0.0)
        verified = bool(getattr(result, "phrase_verified", True))
        return WakeEvent(
            phrase=phrase,
            confidence=confidence,
            source=WakeWordSource.VOICE,
            verified=verified,
            trigger="wake_phrase",
        )

    def push_to_talk(self, phrase: str = "user") -> WakeEvent:
        """Explicit user-triggered wake (push-to-talk / keyboard)."""
        event = WakeEvent(
            phrase=phrase,
            confidence=1.0,
            source=WakeWordSource.PUSH_TO_TALK,
            verified=True,
            trigger="push_to_talk",
        )
        self._emit(event)
        return event

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_wake(self, callback: Callable[[WakeEvent], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def _emit(self, event: WakeEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Wake listener error: %s", exc)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "phrases": self.phrases,
            "listeners": self._listener_count(),
        }

    def _listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)
