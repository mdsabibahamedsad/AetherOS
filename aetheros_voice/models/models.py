from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VoiceMode(Enum):
    CONVERSATION = "conversation"
    COMMAND = "command"
    DICTATION = "dictation"
    ASSISTANT = "assistant"
    CONTINUOUS = "continuous"
    PUSH_TO_TALK = "push_to_talk"
    OFF = "off"


class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"


class WakeWord(Enum):
    HEY_AETHER = "hey aether"
    AETHER = "aether"
    HELLO_AETHER = "hello aether"
    CUSTOM = "custom"


class STTProvider(Enum):
    WHISPER = "whisper"
    WHISPER_CPP = "whisper_cpp"
    FASTER_WHISPER = "faster_whisper"
    DEEPGRAM = "deepgram"
    ASSEMBLYAI = "assemblyai"
    GOOGLE = "google"
    AZURE = "azure"
    LOCAL = "local"


class TTSProvider(Enum):
    PIPER = "piper"
    KOKORO = "kokoro"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE = "google"
    COQUI = "coqui"
    EDGE_TTS = "edge_tts"
    LOCAL = "local"


class Personality(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    MINIMAL = "minimal"
    TECHNICAL = "technical"
    CUSTOM = "custom"


class DictationMode(Enum):
    PLAIN = "plain"
    MARKDOWN = "markdown"
    CODE = "code"
    EMAIL = "email"


@dataclass
class VoiceConfig:
    mode: VoiceMode = VoiceMode.CONVERSATION
    stt_provider: STTProvider = STTProvider.WHISPER
    tts_provider: TTSProvider = TTSProvider.EDGE_TTS
    wake_word: WakeWord | None = WakeWord.HEY_AETHER
    wake_word_enabled: bool = True
    wake_word_custom: str = ""
    personality: Personality = Personality.FRIENDLY
    language: str = "en"
    auto_language_detect: bool = True
    noise_suppression: bool = True
    echo_cancellation: bool = True
    silence_timeout: float = 1.5
    push_to_talk_key: str = "space"
    streaming_enabled: bool = True
    interrupt_enabled: bool = True
    dictation_mode: DictationMode = DictationMode.PLAIN
    auto_punctuation: bool = True
    grammar_correction: bool = True
    voice_speed: float = 1.0
    voice_volume: float = 1.0
    captions_enabled: bool = False
    high_contrast: bool = False
    voice_only_mode: bool = False
    mic_device: str = ""
    speaker_device: str = ""
    mic_gain: float = 1.0
    sample_rate: int = 16000
    buffer_size: int = 1024
    offline_mode: bool = False
    history_enabled: bool = True
    show_mic_indicator: bool = True
    confirm_destructive: bool = True
    memory_enabled: bool = True

    @classmethod
    def defaults(cls) -> VoiceConfig:
        return cls()


@dataclass
class VoiceProfile:
    id: str = ""
    name: str = "Default"
    config: VoiceConfig = field(default_factory=VoiceConfig.defaults)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class VoiceCommand:
    id: str = ""
    phrase: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    enabled: bool = True
    category: str = "general"
    requires_confirm: bool = False
    created_at: float = 0.0


@dataclass
class VoiceShortcut:
    id: str = ""
    name: str = ""
    phrase: str = ""
    commands: list[VoiceCommand] = field(default_factory=list)
    enabled: bool = True


@dataclass
class VoiceMacro:
    id: str = ""
    name: str = ""
    steps: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class VoiceWorkflow:
    id: str = ""
    name: str = ""
    trigger: str = ""
    actions: list[dict] = field(default_factory=list)
    enabled: bool = True


@dataclass
class STTResult:
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    is_final: bool = True
    duration: float = 0.0
    segments: list[dict] = field(default_factory=list)
    error: str = ""


@dataclass
class TTSResult:
    audio_data: bytes = b""
    text: str = ""
    duration: float = 0.0
    format: str = "wav"
    sample_rate: int = 24000
    error: str = ""


@dataclass
class WakeWordResult:
    detected: bool = False
    wake_word: str = ""
    confidence: float = 0.0
    timestamp: float = 0.0
    phrase_verified: bool = True


@dataclass
class VoiceHistoryEntry:
    id: str = ""
    timestamp: float = 0.0
    text: str = ""
    response: str = ""
    mode: str = ""
    duration: float = 0.0
    source: str = "mic"


@dataclass
class ScreenContext:
    text: str = ""
    elements: list[dict] = field(default_factory=list)
    screenshot: bytes = b""
    active_window: str = ""
    url: str = ""
    dimensions: tuple = (0, 0)


@dataclass
class MultimodalInput:
    voice: str = ""
    text: str = ""
    image: bytes = b""
    screenshot: bytes = b""
    clipboard: str = ""
    file_paths: list[str] = field(default_factory=list)
    camera_frame: bytes = b""
    screen_context: ScreenContext | None = None


@dataclass
class VoiceMemoryEntry:
    key: str = ""
    value: Any = None
    category: str = "preference"
    timestamp: float = 0.0
    consented: bool = False
