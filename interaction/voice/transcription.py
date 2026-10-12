"""
Transcription Engine — Speech-to-text configuration and management.

Configures and manages transcription (STT) providers. Integrates
with the existing Aetheros transcription infrastructure (tools/transcription_tools.py).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionConfig:
    """Configuration for transcription.

    Attributes:
        provider: STT provider name
        model: Model name override
        language: Language code (auto-detect if empty)
        enabled: Whether transcription is enabled
        max_file_size: Maximum audio file size in bytes
        supported_formats: List of supported audio formats
        provider_config: Provider-specific configuration
    """
    provider: str = "local"
    model: str = ""
    language: str = ""
    enabled: bool = True
    max_file_size: int = 25 * 1024 * 1024
    supported_formats: List[str] = field(default_factory=lambda: [
        "mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "aac", "flac",
    ])
    provider_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptionResult:
    """Result of a transcription operation.

    Attributes:
        success: Whether successful
        text: Transcribed text
        confidence: Confidence score (0.0 - 1.0)
        language: Detected language
        duration_seconds: Audio duration
        provider: Provider used
        error: Error message if failed
    """
    success: bool = False
    text: str = ""
    confidence: float = 0.0
    language: str = ""
    duration_seconds: float = 0.0
    provider: str = ""
    error: str = ""


class TranscriptionEngine:
    """Manages transcription configuration and delegates to providers.

    Integrates with the existing Aetheros STT infrastructure and
    provides a unified interface for transcription operations.

    Usage:
        config = TranscriptionConfig(provider="local", model="base")
        engine = TranscriptionEngine(config)
        result = engine.transcribe("/tmp/audio.wav")
        print(result.text)
    """

    def __init__(self, config: Optional[TranscriptionConfig] = None):
        self.config = config or TranscriptionConfig()
        self._history: List[TranscriptionResult] = []
        self._max_history: int = 100

    def transcribe(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file.

        Delegates to tools.transcription_tools.transcribe_audio() when
        available, or uses a configured adapter.

        Args:
            audio_path: Path to audio file
            model: Model override
            language: Language override

        Returns:
            TranscriptionResult
        """
        try:
            from tools.transcription_tools import transcribe_audio

            effective_model = model or self.config.model or None
            result = transcribe_audio(audio_path, model=effective_model)

            tr = TranscriptionResult(
                success=result.get("success", False),
                text=result.get("transcript", ""),
                provider=result.get("provider", self.config.provider),
                error=result.get("error", ""),
            )
        except ImportError:
            tr = TranscriptionResult(
                success=False,
                error="Transcription tools not available. Install aetheros with STT support.",
            )
        except Exception as exc:
            tr = TranscriptionResult(
                success=False,
                error=f"Transcription failed: {exc}",
                provider=self.config.provider,
            )

        self._history.append(tr)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return tr

    def is_available(self) -> bool:
        """Check if transcription is available.

        Returns:
            True if at least one STT provider can work
        """
        try:
            from tools.transcription_tools import is_stt_enabled, _get_provider, _load_stt_config
            config = _load_stt_config()
            if not is_stt_enabled(config):
                return False
            provider = _get_provider(config)
            return provider != "none"
        except ImportError:
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get current transcription configuration.

        Returns:
            Transcription configuration dict
        """
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "language": self.config.language,
            "enabled": self.config.enabled,
            "supported_formats": self.config.supported_formats,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get transcription engine statistics."""
        recent = self._history[-10:] if self._history else []
        return {
            "provider": self.config.provider,
            "available": self.is_available(),
            "total_transcriptions": len(self._history),
            "recent_success_rate": (
                sum(1 for r in recent if r.success) / len(recent)
                if recent else 0
            ),
        }
