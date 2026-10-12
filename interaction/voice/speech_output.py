"""
Speech Output Manager — Text-to-speech adapter management.

Manages speech output adapters (TTS providers) with pluggable backends.
Wraps the existing Aetheros TTS infrastructure.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpeechOutputEvent(enum.Enum):
    """Events from speech output."""
    ADAPTER_REGISTERED = "speech_output.adapter_registered"
    SPEAKING_STARTED = "speech_output.speaking_started"
    SPEAKING_STOPPED = "speech_output.speaking_stopped"
    SPEAKING_INTERRUPTED = "speech_output.speaking_interrupted"
    SPEAKING_FAILED = "speech_output.speaking_failed"


@dataclass
class SpeechOutputResult:
    """Result of a speech output operation.

    Attributes:
        success: Whether successful
        audio_path: Path to generated audio file
        duration_seconds: Duration of generated audio
        provider: Which provider was used
        format: Audio format
        text: The original text that was synthesized
        error: Error message if failed
    """
    success: bool = False
    audio_path: str = ""
    duration_seconds: float = 0.0
    provider: str = ""
    format: str = "mp3"
    text: str = ""
    error: str = ""


class SpeechOutputAdapter:
    """Base class for speech output adapters.

    Subclasses implement the actual TTS provider integration.
    """

    def __init__(self, name: str = "", config: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__
        self.config = config or {}

    def synthesize(self, text: str, **kwargs) -> SpeechOutputResult:
        """Synthesize speech from text.

        Args:
            text: Text to convert to speech
            **kwargs: Additional provider-specific options

        Returns:
            SpeechOutputResult
        """
        raise NotImplementedError(f"{self.name} must implement synthesize()")

    def is_available(self) -> bool:
        """Check if this adapter is available.

        Returns:
            True if ready for use
        """
        return True


class SpeechOutputManager:
    """Manages speech output (TTS) adapters.

    Provides a unified interface for text-to-speech synthesis that
    delegates to configured adapters.

    Usage:
        mgr = SpeechOutputManager()
        mgr.register_adapter("edge", EdgeTTSAdapter())
        result = mgr.synthesize("Hello world", adapter_name="edge")
        print(result.audio_path)
    """

    def __init__(self):
        self._adapters: Dict[str, SpeechOutputAdapter] = {}
        self._default_adapter: Optional[str] = None
        self._history: List[SpeechOutputResult] = []
        self._max_history: int = 50

    def register_adapter(self, name: str, adapter: SpeechOutputAdapter) -> None:
        """Register a speech output adapter.

        Args:
            name: Unique adapter name
            adapter: SpeechOutputAdapter instance
        """
        self._adapters[name] = adapter
        if self._default_adapter is None:
            self._default_adapter = name
        logger.debug("SpeechOutputManager: registered adapter '%s'", name)

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

    def synthesize(
        self,
        text: str,
        adapter_name: Optional[str] = None,
        **kwargs,
    ) -> SpeechOutputResult:
        """Synthesize speech from text.

        Args:
            text: Text to convert
            adapter_name: Adapter to use (uses default if not specified)
            **kwargs: Additional provider-specific options

        Returns:
            SpeechOutputResult
        """
        name = adapter_name or self._default_adapter
        if not name or name not in self._adapters:
            return SpeechOutputResult(
                success=False,
                error=f"No adapter available: {name}",
            )

        adapter = self._adapters[name]
        try:
            result = adapter.synthesize(text, **kwargs)
        except Exception as exc:
            result = SpeechOutputResult(
                success=False,
                error=f"Synthesis failed: {exc}",
                provider=name,
            )

        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return result

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
        """Get speech output manager statistics."""
        return {
            "adapters": len(self._adapters),
            "default": self._default_adapter,
            "history_size": len(self._history),
        }
