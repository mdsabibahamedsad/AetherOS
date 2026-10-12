"""
Audio Pipeline — Streaming audio capture, processing, and playback.

Provides a modular audio pipeline that supports streaming capture,
format conversion, level monitoring, and playback. Handles both
push-to-talk and continuous modes.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AudioFormat(enum.Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    OGG_OPUS = "ogg"
    FLAC = "flac"
    PCM_16 = "pcm_16"
    PCM_32 = "pcm_32"


class AudioSource(enum.Enum):
    """Audio source types."""
    MICROPHONE = "microphone"
    SYSTEM_AUDIO = "system_audio"
    FILE = "file"
    STREAM = "stream"
    PHONE_CALL = "phone_call"


class AudioSink(enum.Enum):
    """Audio output sink types."""
    SPEAKER = "speaker"
    HEADSET = "headset"
    FILE = "file"
    STREAM = "stream"


@dataclass
class AudioConfig:
    """Configuration for the audio pipeline.

    Attributes:
        sample_rate: Audio sample rate (Hz)
        channels: Number of audio channels (1 = mono, 2 = stereo)
        chunk_size: Audio chunk size in frames
        dtype: Audio data type (int16, float32, etc.)
        input_device: Input device index or name
        output_device: Output device index or name
        silence_threshold: RMS threshold for silence detection
        silence_duration: Seconds of silence before auto-stop
        auto_gain_control: Enable automatic gain control
        noise_suppression: Enable noise suppression
    """
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    dtype: str = "int16"
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    silence_threshold: int = 200
    silence_duration: float = 2.0
    auto_gain_control: bool = False
    noise_suppression: bool = False


class AudioPipeline:
    """Streaming audio pipeline for capture and playback.

    Handles audio input capture, format conversion, level monitoring,
    and audio output. Supports both push-to-talk and continuous modes.

    Usage:
        config = AudioConfig(sample_rate=16000, channels=1)
        pipeline = AudioPipeline(config)

        pipeline.start_capture()
        # ... audio is being captured ...
        wav_path = pipeline.stop_capture()

        pipeline.play_audio(wav_path)
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._lock = threading.RLock()
        self._capturing = False
        self._playing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frames: List[bytes] = []
        self._level_callback: Optional[Callable[[float], None]] = None
        self._capture_start_time: float = 0.0
        self._peak_level: float = 0.0

        # Platform audio adapter
        self._capture_adapter: Optional[Callable] = None
        self._playback_adapter: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Adapter registration
    # ------------------------------------------------------------------

    def set_capture_adapter(self, adapter: Callable) -> None:
        """Set the audio capture adapter.

        Args:
            adapter: Callable for capture operations
        """
        self._capture_adapter = adapter

    def set_playback_adapter(self, adapter: Callable) -> None:
        """Set the audio playback adapter.

        Args:
            adapter: Callable for playback operations
        """
        self._playback_adapter = adapter

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def start_capture(self) -> bool:
        """Start audio capture.

        Returns:
            True if capture started
        """
        with self._lock:
            if self._capturing:
                return False
            self._capturing = True
            self._frames = []
            self._capture_start_time = time.time()
            self._peak_level = 0.0

        logger.info("AudioPipeline: capture started (rate=%d, channels=%d)",
                     self.config.sample_rate, self.config.channels)
        return True

    def stop_capture(self) -> Optional[str]:
        """Stop audio capture and optionally save to file.

        Returns:
            Path to captured audio file, or None
        """
        with self._lock:
            if not self._capturing:
                return None
            self._capturing = False

        duration = time.time() - self._capture_start_time
        logger.info("AudioPipeline: capture stopped (duration=%.1fs, frames=%d, peak=%.2f)",
                     duration, len(self._frames), self._peak_level)

        if self._capture_adapter:
            try:
                return self._capture_adapter("stop")
            except Exception as exc:
                logger.debug("AudioPipeline: capture adapter stop failed: %s", exc)
        return None

    def cancel_capture(self) -> None:
        """Cancel audio capture and discard data."""
        with self._lock:
            self._capturing = False
            self._frames = []
        logger.info("AudioPipeline: capture cancelled")

    @property
    def is_capturing(self) -> bool:
        """Whether capture is active."""
        return self._capturing

    @property
    def capture_elapsed(self) -> float:
        """Elapsed capture time in seconds."""
        if not self._capturing:
            return 0.0
        return time.time() - self._capture_start_time

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play_audio(self, audio_path: str) -> bool:
        """Play an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            True if playback started
        """
        if self._playback_adapter:
            try:
                result = self._playback_adapter("play", audio_path)
                if result:
                    logger.info("AudioPipeline: playing %s", audio_path)
                    return True
            except Exception as exc:
                logger.debug("AudioPipeline: playback failed: %s", exc)
        return False

    def stop_playback(self) -> None:
        """Stop current audio playback."""
        if self._playback_adapter:
            try:
                self._playback_adapter("stop")
            except Exception as exc:
                logger.debug("AudioPipeline: stop playback failed: %s", exc)
        logger.info("AudioPipeline: playback stopped")

    # ------------------------------------------------------------------
    # Level monitoring
    # ------------------------------------------------------------------

    def set_level_callback(self, callback: Callable[[float], None]) -> None:
        """Set a callback for audio level updates.

        The callback receives RMS level as a float (0.0 - 1.0).

        Args:
            callback: Level callback
        """
        self._level_callback = callback

    def get_current_level(self) -> float:
        """Get the current audio input level.

        Returns:
            RMS level (0.0 - 1.0)
        """
        return self._peak_level

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        with self._lock:
            return {
                "capturing": self._capturing,
                "playing": self._playing,
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "frames_captured": len(self._frames),
                "peak_level": self._peak_level,
                "capture_duration": self.capture_elapsed,
            }
