"""Voice interaction package for AetherOS interaction layer."""

from interaction.voice.voice_manager import (
    VoiceManager,
    VoiceConfig,
    VoiceSession,
    VoiceEvent,
    VoiceState,
)
from interaction.voice.speech_input import (
    SpeechInputManager,
    SpeechInputAdapter,
    SpeechInputResult,
    SpeechInputEvent,
)
from interaction.voice.speech_output import (
    SpeechOutputManager,
    SpeechOutputAdapter,
    SpeechOutputResult,
    SpeechOutputEvent,
)
from interaction.voice.wake_word import (
    WakeWordEngine,
    WakeWordConfig,
    WakeWordEvent,
    WakeWordState,
)
from interaction.voice.audio_pipeline import (
    AudioPipeline,
    AudioConfig,
    AudioFormat,
    AudioSource,
    AudioSink,
)
from interaction.voice.transcription import (
    TranscriptionEngine,
    TranscriptionConfig,
    TranscriptionResult,
)

__all__ = [
    "VoiceManager",
    "VoiceConfig",
    "VoiceSession",
    "VoiceEvent",
    "VoiceState",
    "SpeechInputManager",
    "SpeechInputAdapter",
    "SpeechInputResult",
    "SpeechInputEvent",
    "SpeechOutputManager",
    "SpeechOutputAdapter",
    "SpeechOutputResult",
    "SpeechOutputEvent",
    "WakeWordEngine",
    "WakeWordConfig",
    "WakeWordEvent",
    "WakeWordState",
    "AudioPipeline",
    "AudioConfig",
    "AudioFormat",
    "AudioSource",
    "AudioSink",
    "TranscriptionEngine",
    "TranscriptionConfig",
    "TranscriptionResult",
]
