"""Wake word detection."""

from aetheros_voice.wakeword.base import WakeWordDetector, WakeWordResult
from aetheros_voice.models.models import WakeWord

_WW_REGISTRY: dict[str, type[WakeWordDetector]] = {}


def register_wakeword(name: str, cls: type[WakeWordDetector]):
    _WW_REGISTRY[name] = cls


from aetheros_voice.wakeword import porcupine, local


def create_wakeword(name: str = "porcupine") -> WakeWordDetector:
    cls = _WW_REGISTRY.get(name)
    if cls is None:
        from aetheros_voice.wakeword.local import LocalWakeWord
        return LocalWakeWord()
    return cls()


__all__ = ["WakeWordDetector", "WakeWordResult", "register_wakeword", "create_wakeword"]
