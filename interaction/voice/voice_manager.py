"""
Voice Manager — Coordinates voice interaction sessions.

Manages voice session lifecycle, coordinates between speech input,
speech output, wake word detection, and transcription. Voice providers
are replaceable through plugins.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class VoiceEvent(enum.Enum):
    """Events emitted by the voice manager."""
    VOICE_INITIALIZED = "voice.initialized"
    VOICE_SHUTDOWN = "voice.shutdown"
    SESSION_STARTED = "voice.session_started"
    SESSION_ENDED = "voice.session_ended"
    LISTENING_STARTED = "voice.listening_started"
    LISTENING_STOPPED = "voice.listening_stopped"
    SPEECH_DETECTED = "voice.speech_detected"
    TRANSCRIPTION_READY = "voice.transcription_ready"
    SPEAKING_STARTED = "voice.speaking_started"
    SPEAKING_STOPPED = "voice.speaking_stopped"
    WAKE_WORD_DETECTED = "voice.wake_word_detected"
    ERROR = "voice.error"


class VoiceState(enum.Enum):
    """Voice manager states."""
    STOPPED = "stopped"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceSessionType(enum.Enum):
    """Types of voice sessions."""
    PUSH_TO_TALK = "push_to_talk"
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"
    VOICE_COMMAND = "voice_command"


@dataclass
class VoiceConfig:
    """Configuration for voice interaction.

    Attributes:
        enable_continuous: Enable continuous listening
        enable_wake_word: Enable wake word detection
        wake_word: Wake word phrase
        push_to_talk_key: Key binding for push-to-talk
        speech_timeout: Silence timeout for auto-stop (seconds)
        max_session_duration: Maximum session duration (seconds)
        stt_provider: Speech-to-text provider name
        tts_provider: Text-to-speech provider name
        auto_stop_on_silence: Auto-stop recording on silence
        interruption_enabled: Allow voice to interrupt speaking
        voice_activity_timeout: Voice activity timeout (seconds)
    """
    enable_continuous: bool = False
    enable_wake_word: bool = False
    wake_word: str = "aetheros"
    push_to_talk_key: str = "Ctrl+Space"
    speech_timeout: float = 3.0
    max_session_duration: float = 300.0
    stt_provider: str = ""
    tts_provider: str = ""
    auto_stop_on_silence: bool = True
    interruption_enabled: bool = True
    voice_activity_timeout: float = 60.0


@dataclass
class VoiceSession:
    """An active voice interaction session.

    Attributes:
        id: Unique session identifier
        type: Session type
        state: Current session state
        started_at: When the session started
        last_activity: Last audio activity timestamp
        transcribed_text: Accumulated transcription text
        audio_duration: Total audio duration in seconds
        metadata: Additional session metadata
    """
    id: str = ""
    type: VoiceSessionType = VoiceSessionType.PUSH_TO_TALK
    state: VoiceState = VoiceState.IDLE
    started_at: float = 0.0
    last_activity: float = 0.0
    transcribed_text: str = ""
    audio_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoiceManager:
    """Coordinates all voice interaction features.

    Manages voice session lifecycle, integrates with speech input/output
    adapters, wake word detection, and transcription. Providers are
    pluggable via register_provider().

    Usage:
        config = VoiceConfig(enable_wake_word=True, wake_word="aetheros")
        vm = VoiceManager(event_bus, config)
        vm.initialize()

        session = vm.start_session(VoiceSessionType.PUSH_TO_TALK)
        vm.start_listening(session.id)

        vm.shutdown()
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[VoiceConfig] = None,
    ):
        self._event_bus = event_bus
        self.config = config or VoiceConfig()
        self._lock = threading.RLock()
        self._state = VoiceState.STOPPED
        self._sessions: Dict[str, VoiceSession] = {}
        self._speech_input_adapters: Dict[str, Callable] = {}
        self._speech_output_adapters: Dict[str, Callable] = {}
        self._wake_word_adapters: Dict[str, Callable] = {}
        self._transcription_adapters: Dict[str, Callable] = {}
        self._subscribers: Dict[str, List[Callable]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the voice manager."""
        with self._lock:
            self._state = VoiceState.IDLE

        if self._event_bus:
            self._event_bus.emit(VoiceEvent.VOICE_INITIALIZED.value, {
                "config": {
                    "continuous": self.config.enable_continuous,
                    "wake_word": self.config.enable_wake_word,
                    "push_to_talk": self.config.push_to_talk_key,
                },
            })

        logger.info("VoiceManager: initialized")

    def shutdown(self) -> None:
        """Shut down the voice manager, ending all sessions."""
        with self._lock:
            session_ids = list(self._sessions.keys())
            self._state = VoiceState.STOPPED

        for sid in session_ids:
            self.end_session(sid)

        if self._event_bus:
            self._event_bus.emit(VoiceEvent.VOICE_SHUTDOWN.value, {})

        logger.info("VoiceManager: shut down")

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(
        self,
        session_type: VoiceSessionType = VoiceSessionType.PUSH_TO_TALK,
    ) -> VoiceSession:
        """Start a new voice session.

        Args:
            session_type: Type of voice session

        Returns:
            The created VoiceSession
        """
        session = VoiceSession(
            id=uuid.uuid4().hex[:12],
            type=session_type,
            state=VoiceState.IDLE,
            started_at=time.time(),
            last_activity=time.time(),
        )

        with self._lock:
            self._sessions[session.id] = session

        if self._event_bus:
            self._event_bus.emit_async(VoiceEvent.SESSION_STARTED.value, {
                "session_id": session.id,
                "type": session_type.value,
            })

        logger.info("VoiceManager: session %s started (%s)", session.id[:8], session_type.value)
        return session

    def end_session(self, session_id: str) -> bool:
        """End a voice session.

        Args:
            session_id: Session to end

        Returns:
            True if ended
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False
            session.state = VoiceState.STOPPED

        if self._event_bus:
            self._event_bus.emit_async(VoiceEvent.SESSION_ENDED.value, {
                "session_id": session_id,
                "duration": time.time() - session.started_at,
            })

        logger.info("VoiceManager: session %s ended", session_id[:8])
        return True

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            VoiceSession or None
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[VoiceSession]:
        """List all active sessions.

        Returns:
            List of active VoiceSession objects
        """
        with self._lock:
            return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Listening control
    # ------------------------------------------------------------------

    def start_listening(self, session_id: str) -> bool:
        """Start listening for audio input in a session.

        Args:
            session_id: Session to start listening

        Returns:
            True if started
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.state = VoiceState.LISTENING
            session.last_activity = time.time()

        if self._event_bus:
            self._event_bus.emit_async(VoiceEvent.LISTENING_STARTED.value, {
                "session_id": session_id,
            })

        logger.debug("VoiceManager: listening started (session=%s)", session_id[:8])
        return True

    def stop_listening(self, session_id: str) -> bool:
        """Stop listening for audio input.

        Args:
            session_id: Session to stop

        Returns:
            True if stopped
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.state = VoiceState.IDLE

        if self._event_bus:
            self._event_bus.emit_async(VoiceEvent.LISTENING_STOPPED.value, {
                "session_id": session_id,
            })

        logger.debug("VoiceManager: listening stopped (session=%s)", session_id[:8])
        return True

    # ------------------------------------------------------------------
    # Transcription notification
    # ------------------------------------------------------------------

    def notify_transcription(
        self, session_id: str, text: str, is_final: bool = True,
    ) -> None:
        """Notify that transcription is available for a session.

        Args:
            session_id: Session identifier
            text: Transcribed text
            is_final: Whether this is the final transcription
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.transcribed_text = text
                session.last_activity = time.time()

        if self._event_bus and is_final:
            self._event_bus.emit_async(VoiceEvent.TRANSCRIPTION_READY.value, {
                "session_id": session_id,
                "text": text,
            })

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, event: VoiceEvent, callback: Callable) -> Callable:
        """Subscribe to a voice event.

        Args:
            event: Event to subscribe to
            callback: Callable receiving event data

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.setdefault(event.value, []).append(callback)

        def unsubscribe():
            with self._lock:
                cbs = self._subscribers.get(event.value, [])
                if callback in cbs:
                    cbs.remove(callback)

        return unsubscribe

    # ------------------------------------------------------------------
    # Plugin provider registration
    # ------------------------------------------------------------------

    def register_speech_input(self, name: str, adapter: Callable) -> None:
        """Register a speech input provider.

        Args:
            name: Provider name
            adapter: Speech input adapter function
        """
        with self._lock:
            self._speech_input_adapters[name] = adapter
        logger.debug("VoiceManager: registered speech input '%s'", name)

    def register_speech_output(self, name: str, adapter: Callable) -> None:
        """Register a speech output provider.

        Args:
            name: Provider name
            adapter: Speech output adapter function
        """
        with self._lock:
            self._speech_output_adapters[name] = adapter
        logger.debug("VoiceManager: registered speech output '%s'", name)

    def register_wake_word(self, name: str, adapter: Callable) -> None:
        """Register a wake word detection provider.

        Args:
            name: Provider name
            adapter: Wake word adapter function
        """
        with self._lock:
            self._wake_word_adapters[name] = adapter
        logger.debug("VoiceManager: registered wake word '%s'", name)

    def register_transcription(self, name: str, adapter: Callable) -> None:
        """Register a transcription provider.

        Args:
            name: Provider name
            adapter: Transcription adapter function
        """
        with self._lock:
            self._transcription_adapters[name] = adapter
        logger.debug("VoiceManager: registered transcription '%s'", name)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get voice manager statistics."""
        with self._lock:
            return {
                "state": self._state.value,
                "sessions": {
                    "active": len(self._sessions),
                    "ids": list(self._sessions.keys()),
                },
                "adapters": {
                    "speech_input": list(self._speech_input_adapters.keys()),
                    "speech_output": list(self._speech_output_adapters.keys()),
                    "wake_word": list(self._wake_word_adapters.keys()),
                    "transcription": list(self._transcription_adapters.keys()),
                },
                "config": {
                    "wake_word": self.config.enable_wake_word,
                    "continuous": self.config.enable_continuous,
                    "interruption": self.config.interruption_enabled,
                },
            }
