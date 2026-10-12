"""
Speech Input Manager — Speech-to-text adapter management.

Manages speech input adapters (STT providers) with pluggable backends.
Wraps the existing Aetheros transcription infrastructure.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpeechInputEvent(enum.Enum):
    """Events from speech input."""
    ADAPTER_REGISTERED = "speech_input.adapter_registered"
    RECORDING_STARTED = "speech_input.recording_started"
    RECORDING_STOPPED = "speech_input.recording_stopped"
    TRANSCRIPTION_STARTED = "speech_input.transcription_started"
    TRANSCRIPTION_COMPLETED = "speech_input.transcription_completed"
    TRANSCRIPTION_FAILED = "speech_input.transcription_failed"


@dataclass
class SpeechInputResult:
    """Result of a speech input operation.

    Attributes:
        success: Whether successful
        text: Transcribed text
        audio_duration: Audio duration in seconds
        confidence: Confidence score (0.0 - 1.0)
        language: Detected language
        provider: Which provider was used
        error: Error message if failed
    """
    success: bool = False
    text: str = ""
    audio_duration: float = 0.0
    confidence: float = 0.0
    language: str = ""
    provider: str = ""
    error: str = ""


class SpeechInputAdapter:
    """Base class for speech input adapters.

    Subclasses implement the actual STT provider integration.
    """

    def __init__(self, name: str = "", config: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__
        self.config = config or {}

    def transcribe(self, audio_path: str, **kwargs) -> SpeechInputResult:
        """Transcribe audio to text.

        Args:
            audio_path: Path to audio file
            **kwargs: Additional provider-specific options

        Returns:
            SpeechInputResult
        """
        raise NotImplementedError(f"{self.name} must implement transcribe()")

    def is_available(self) -> bool:
        """Check if this adapter is available.

        Returns:
            True if ready for use
        """
        return True


class SpeechInputManager:
    """Manages speech input (STT) adapters.

    Provides a unified interface for transcribing audio that delegates
    to configured adapters.

    Usage:
        mgr = SpeechInputManager()
        mgr.register_adapter("local", LocalSTTAdapter())
        result = mgr.transcribe("/tmp/audio.wav", adapter_name="local")
        print(result.text)
    """

    def __init__(self):
        self._adapters: Dict[str, SpeechInputAdapter] = {}
        self._default_adapter: Optional[str] = None
        self._history: List[SpeechInputResult] = []
        self._max_history: int = 100

    def register_adapter(self, name: str, adapter: SpeechInputAdapter) -> None:
        """Register a speech input adapter.

        Args:
            name: Unique adapter name
            adapter: SpeechInputAdapter instance
        """
        self._adapters[name] = adapter
        if self._default_adapter is None:
            self._default_adapter = name
        logger.debug("SpeechInputManager: registered adapter '%s'", name)

    def set_default_adapter(self, name: str) -> bool:
        """Set the default adapter.

        Args:
            name: Adapter name

        Returns:
            True if set
        """
        if name in self._adapters:
            self._default_adapter = name
            return True
        return False

    def transcribe(
        self,
        audio_path: str,
        adapter_name: Optional[str] = None,
        **kwargs,
    ) -> SpeechInputResult:
        """Transcribe audio using the specified adapter.

        Args:
            audio_path: Path to audio file
            adapter_name: Adapter to use (uses default if not specified)
            **kwargs: Additional provider-specific options

        Returns:
            SpeechInputResult
        """
        name = adapter_name or self._default_adapter
        if not name or name not in self._adapters:
            return SpeechInputResult(
                success=False,
                error=f"No adapter available: {name}",
            )

        adapter = self._adapters[name]
        try:
            result = adapter.transcribe(audio_path, **kwargs)
        except Exception as exc:
            result = SpeechInputResult(
                success=False,
                error=f"Transcription failed: {exc}",
                provider=name,
            )

        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return result

    def get_transcribe_fn(self, adapter_name: Optional[str] = None) -> Callable:
        """Get a callable that wraps the adapter's transcribe method.

        Args:
            adapter_name: Adapter to wrap

        Returns:
            Callable suitable as a tool handler
        """
        name = adapter_name or self._default_adapter

        def _transcribe(audio_path: str, **kwargs) -> SpeechInputResult:
            return self.transcribe(audio_path, adapter_name=name, **kwargs)

        return _transcribe

    def list_adapters(self) -> Dict[str, bool]:
        """List registered adapters and their availability.

        Returns:
            Dict of {name: is_available}
        """
        return {
            name: adapter.is_available()
            for name, adapter in self._adapters.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get speech input manager statistics."""
        return {
            "adapters": len(self._adapters),
            "default": self._default_adapter,
            "history_size": len(self._history),
        }
