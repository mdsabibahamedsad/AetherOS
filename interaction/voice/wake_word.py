"""
Wake Word Engine — Optional wake word detection module.

Provides a modular wake word detection system that supports
different wake word engines through pluggable adapters.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WakeWordEvent(enum.Enum):
    """Events from wake word detection."""
    ENGINE_LOADED = "wake_word.engine_loaded"
    ENGINE_UNLOADED = "wake_word.engine_unloaded"
    WAKE_WORD_DETECTED = "wake_word.detected"
    FALSE_POSITIVE = "wake_word.false_positive"
    LISTENING_STARTED = "wake_word.listening_started"
    LISTENING_STOPPED = "wake_word.listening_stopped"
    ERROR = "wake_word.error"


class WakeWordState(enum.Enum):
    """Wake word engine states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LISTENING = "listening"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection.

    Attributes:
        wake_word: Primary wake word phrase
        alternate_words: Alternative wake words
        sensitivity: Detection sensitivity (0.0 - 1.0)
        cooldown_seconds: Minimum time between detections
        engine: Detection engine to use (porcupine, snowboy, etc.)
        model_path: Path to custom wake word model
        continuous_listening: Listen continuously vs on-demand
    """
    wake_word: str = "aetheros"
    alternate_words: List[str] = field(default_factory=list)
    sensitivity: float = 0.5
    cooldown_seconds: float = 2.0
    engine: str = ""
    model_path: str = ""
    continuous_listening: bool = False


class WakeWordEngine:
    """Wake word detection engine with pluggable backends.

    Supports different wake word engines through adapter functions.
    Manages the listening lifecycle and emits detection events.

    Usage:
        config = WakeWordConfig(wake_word="aetheros", sensitivity=0.5)
        engine = WakeWordEngine(config)
        engine.set_detection_adapter(my_detector)

        engine.start_listening()
        # ... engine notifies subscribers on wake word detected ...
        engine.stop_listening()
    """

    def __init__(self, config: Optional[WakeWordConfig] = None):
        self.config = config or WakeWordConfig()
        self._lock = threading.RLock()
        self._state = WakeWordState.UNLOADED
        self._last_detection: float = 0.0
        self._detection_count: int = 0
        self._false_positive_count: int = 0
        self._subscribers: List[Callable[[WakeWordEvent, Dict[str, Any]], None]] = []
        self._detection_adapter: Optional[Callable] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """Load the wake word engine.

        Returns:
            True if loaded successfully
        """
        with self._lock:
            if self._state != WakeWordState.UNLOADED:
                return False
            self._state = WakeWordState.LOADING

        logger.info("WakeWordEngine: loading (wake_word=%s, engine=%s)",
                     self.config.wake_word, self.config.engine)

        with self._lock:
            self._state = WakeWordState.PAUSED

        self._notify(WakeWordEvent.ENGINE_LOADED, {
            "wake_word": self.config.wake_word,
            "engine": self.config.engine,
        })
        return True

    def unload(self) -> None:
        """Unload the wake word engine."""
        self.stop_listening()
        with self._lock:
            self._state = WakeWordState.UNLOADED
        self._notify(WakeWordEvent.ENGINE_UNLOADED, {})
        logger.info("WakeWordEngine: unloaded")

    # ------------------------------------------------------------------
    # Listening control
    # ------------------------------------------------------------------

    def start_listening(self) -> bool:
        """Start listening for the wake word.

        Returns:
            True if started
        """
        with self._lock:
            if self._state in (WakeWordState.UNLOADED, WakeWordState.ERROR):
                return False
            self._state = WakeWordState.LISTENING
            self._running = True

        if self.config.continuous_listening and self._detection_adapter:
            self._listen_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name="wake-word-listener",
            )
            self._listen_thread.start()

        self._notify(WakeWordEvent.LISTENING_STARTED, {
            "wake_word": self.config.wake_word,
        })
        logger.info("WakeWordEngine: listening started")
        return True

    def stop_listening(self) -> None:
        """Stop listening for the wake word."""
        self._running = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2)
            self._listen_thread = None

        with self._lock:
            self._state = WakeWordState.PAUSED

        self._notify(WakeWordEvent.LISTENING_STOPPED, {})
        logger.info("WakeWordEngine: listening stopped")

    def _listen_loop(self) -> None:
        """Continuous listening loop."""
        while self._running:
            if self._detection_adapter:
                try:
                    detected = self._detection_adapter()
                    if detected:
                        self._on_detection()
                except Exception as exc:
                    logger.debug("WakeWordEngine: detection loop error: %s", exc)
            time.sleep(0.1)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def set_detection_adapter(self, adapter: Callable[[], bool]) -> None:
        """Set the wake word detection adapter.

        Args:
            adapter: Callable returning True if wake word detected
        """
        self._detection_adapter = adapter

    def detect(self) -> bool:
        """Manually check for wake word (one-shot).

        Returns:
            True if wake word detected
        """
        if self._detection_adapter:
            try:
                if self._detection_adapter():
                    self._on_detection()
                    return True
            except Exception as exc:
                logger.debug("WakeWordEngine: detection failed: %s", exc)
        return False

    def _on_detection(self) -> None:
        """Handle a wake word detection."""
        now = time.time()
        if now - self._last_detection < self.config.cooldown_seconds:
            return

        self._last_detection = now
        self._detection_count += 1

        self._notify(WakeWordEvent.WAKE_WORD_DETECTED, {
            "wake_word": self.config.wake_word,
            "timestamp": now,
        })
        logger.info("WakeWordEngine: wake word detected (#%d)", self._detection_count)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[WakeWordEvent, Dict[str, Any]], None]) -> Callable:
        """Subscribe to wake word events.

        Args:
            callback: Receives (event, data)

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self, event: WakeWordEvent, data: Dict[str, Any]) -> None:
        """Notify subscribers of an event.

        Args:
            event: Event type
            data: Event data
        """
        with self._lock:
            subscribers = list(self._subscribers)
        for cb in subscribers:
            try:
                cb(event, data)
            except Exception as exc:
                logger.debug("WakeWordEngine: subscriber failed: %s", exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            return {
                "state": self._state.value,
                "wake_word": self.config.wake_word,
                "detection_count": self._detection_count,
                "false_positives": self._false_positive_count,
                "listening": self._running,
                "last_detection": self._last_detection,
            }
