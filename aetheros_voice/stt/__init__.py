"""Speech-to-text backends."""

from aetheros_voice.stt.base import STTBackend
from aetheros_voice.models.models import STTResult, STTProvider

_STT_REGISTRY: dict[str, type[STTBackend]] = {}


def register_stt(name: str, cls: type[STTBackend]):
    _STT_REGISTRY[name] = cls


# Import all backends so they register themselves (after register_stt is defined)
from aetheros_voice.stt import whisper, deepgram, assemblyai, google, local, faster_whisper


def create_stt(provider: STTProvider | str) -> STTBackend:
    name = provider.value if hasattr(provider, "value") else str(provider)
    cls = _STT_REGISTRY.get(name)
    if cls is None:
        from aetheros_voice.stt.local import FallbackSTT
        return FallbackSTT()
    return cls()


__all__ = ["STTBackend", "STTResult", "register_stt", "create_stt"]
