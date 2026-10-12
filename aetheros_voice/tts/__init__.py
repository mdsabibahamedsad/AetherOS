"""Text-to-speech backends."""

from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.models.models import TTSResult, TTSProvider

_TTS_REGISTRY: dict[str, type[TTSBackend]] = {}


def register_tts(name: str, cls: type[TTSBackend]):
    _TTS_REGISTRY[name] = cls


from aetheros_voice.tts import piper, elevenlabs, azure, coqui, local


def create_tts(provider: TTSProvider | str) -> TTSBackend:
    name = provider.value if hasattr(provider, "value") else str(provider)
    cls = _TTS_REGISTRY.get(name)
    if cls is None:
        from aetheros_voice.tts.local import FallbackTTS
        return FallbackTTS()
    return cls()


__all__ = ["TTSBackend", "TTSResult", "register_tts", "create_tts"]
