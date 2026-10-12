"""Jarvis Mode — voice engine.

Wraps the ``aetheros_voice`` engine and adapters into the Jarvis runtime.
Provides speech-to-text, text-to-speech, streaming synthesis, interruption,
microphone/speaker selection, and honest capability reporting. No fake audio:
if no STT/TTS backend is usable, ``available`` is False and calls return
honest errors instead of pretending.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

try:
    from aetheros_voice.core.engine import VoiceEngine
    from aetheros_voice.models.models import VoiceConfig, VoiceMode, VoiceState
except Exception:  # pragma: no cover - degraded when voice package absent
    VoiceEngine = None  # type: ignore[assignment,misc]
    VoiceConfig = None  # type: ignore[assignment,misc]
    VoiceMode = None  # type: ignore[assignment,misc]
    VoiceState = None  # type: ignore[assignment,misc]

try:
    from aetheros_jarvis import models as jmodels
except Exception:  # pragma: no cover
    jmodels = None  # type: ignore[assignment]


class VoiceEngineWrapper:
    """Jarvis-facing facade over the AetherOS voice engine.

    The wrapper is backend-agnostic: STT/TTS adapters are created by the
    voice package and report ``is_available`` truthfully. Streaming and
    interruption are only enabled when the backend supports them.
    """

    def __init__(
        self,
        *,
        stt_provider: str = "local",
        tts_provider: str = "local",
        mic_device: str = "",
        speaker_device: str = "",
        streaming_enabled: bool = True,
        interruption_enabled: bool = True,
    ) -> None:
        self._stt_provider = stt_provider
        self._tts_provider = tts_provider
        self._mic_device = mic_device
        self._speaker_device = speaker_device
        self._streaming_enabled = streaming_enabled
        self._interruption_enabled = interruption_enabled
        self._engine = None
        self._init_engine()

    def _init_engine(self) -> None:
        if VoiceEngine is None:
            return
        try:
            config = VoiceConfig()
            config.stt_provider = self._stt_provider
            config.tts_provider = self._tts_provider
            config.mic_device = self._mic_device
            config.speaker_device = self._speaker_device
            config.streaming_enabled = self._streaming_enabled
            config.interrupt_enabled = self._interruption_enabled
            self._engine = VoiceEngine(config)
        except Exception as exc:
            logger.warning("Voice engine initialization failed: %s", exc)
            self._engine = None

    # ------------------------------------------------------------------
    # Capability reporting
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._engine is not None

    def stt_available(self) -> bool:
        if self._engine is None:
            return False
        stt = getattr(self._engine, "_stt", None)
        return stt is not None and bool(getattr(stt, "is_available", False))

    def tts_available(self) -> bool:
        if self._engine is None:
            return False
        tts = getattr(self._engine, "_tts", None)
        return tts is not None and bool(getattr(tts, "is_available", False))

    def list_microphones(self) -> List[Dict[str, Any]]:
        if self._engine is None:
            return []
        capture = getattr(self._engine, "capture", None)
        if capture is None or not hasattr(capture, "list_devices"):
            return []
        try:
            return capture.list_devices()
        except Exception as exc:
            logger.debug("Could not list microphones: %s", exc)
            return []

    def list_speakers(self) -> List[str]:
        if self._engine is None:
            return []
        tts = getattr(self._engine, "_tts", None)
        if tts is None or not hasattr(tts, "voices"):
            return []
        try:
            return list(tts.voices)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    async def transcribe(self, audio: bytes, language: str = "en") -> "jmodels.Transcript":
        if self._engine is None:
            return jmodels.Transcript(text="", language=language, is_final=False)
        try:
            result = await self._engine._transcribe(audio)
            if result is None:
                return jmodels.Transcript(text="", language=language, is_final=False)
            error = getattr(result, "error", "")
            text = getattr(result, "text", "")
            if error and not text:
                logger.warning("STT error: %s", error)
                return jmodels.Transcript(text="", language=language, is_final=False, confidence=0.0)
            return jmodels.Transcript(
                text=text,
                language=getattr(result, "language", language) or language,
                confidence=float(getattr(result, "confidence", 0.0) or 0.0),
                is_final=bool(getattr(result, "is_final", True)),
            )
        except Exception as exc:
            logger.warning("STT failed: %s", exc)
            return jmodels.Transcript(text="", language=language, is_final=False)

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    async def speak(self, text: str) -> bool:
        """Synthesize and (when a backend + playback exist) play text."""
        if self._engine is None:
            logger.warning("No voice engine; cannot speak: %s", text[:80])
            return False
        try:
            result = await self._engine.speak(text)
            return result is not None and not getattr(result, "error", "")
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
            return False

    async def speak_stream(self, chunks: Any) -> bool:
        """Stream a sequence of text chunks as speech."""
        if self._engine is None:
            return False
        try:
            await self._engine.speak_stream(chunks)
            return True
        except Exception as exc:
            logger.warning("Streaming TTS failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Interruption
    # ------------------------------------------------------------------

    def interrupt(self) -> None:
        """Stop current speech/processing immediately."""
        if self._engine is None:
            return
        try:
            self._engine.interrupt()
        except Exception as exc:
            logger.debug("Interrupt failed: %s", exc)

    @property
    def interruption_enabled(self) -> bool:
        return self._interruption_enabled

    def set_interruption(self, enabled: bool) -> None:
        self._interruption_enabled = enabled
        if self._engine is not None:
            try:
                self._engine.config_mgr.update(interrupt_enabled=enabled)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Confirmation routing (mission-critical safety)
    # ------------------------------------------------------------------

    def set_confirmation_resolver(self, resolver: Callable[[str], bool]) -> None:
        """Route destructive voice-command confirmations to the permission layer."""
        if self._engine is None:
            return
        try:
            self._engine.set_confirmation_resolver(resolver)
        except Exception as exc:
            logger.warning("Could not install confirmation resolver: %s", exc)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        engine_state = ""
        if self._engine is not None:
            state = getattr(self._engine, "state", None)
            if state is not None:
                engine_state = getattr(state, "state", "").value if hasattr(state, "state") else ""
        return {
            "available": self.available,
            "stt_provider": self._stt_provider,
            "tts_provider": self._tts_provider,
            "stt_available": self.stt_available(),
            "tts_available": self.tts_available(),
            "streaming_enabled": self._streaming_enabled,
            "interruption_enabled": self._interruption_enabled,
            "mic_device": self._mic_device,
            "speaker_device": self._speaker_device,
            "state": engine_state,
        }
