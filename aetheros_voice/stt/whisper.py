from __future__ import annotations

import time
import uuid
from typing import Any
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class WhisperSTT(STTBackend):
    name = "whisper"
    supports_offline = True
    supports_streaming = False

    def __init__(self, model_size: str = "base"):
        self._model_size = model_size
        self._model = None

    async def load_model(self):
        try:
            import whisper
            self._model = whisper.load_model(self._model_size)
        except ImportError:
            pass

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        import io
        import tempfile
        if self._model is None:
            await self.load_model()
        if self._model is None:
            return STTResult(error="Whisper not available")
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            opts = {"language": language} if language else {}
            result = self._model.transcribe(tmp_path, **opts)
            import os
            os.unlink(tmp_path)
            return STTResult(
                text=result.get("text", "").strip(),
                confidence=1.0,
                language=result.get("language", language or "en"),
                is_final=True,
                duration=result.get("duration", 0),
                segments=result.get("segments", []),
            )
        except Exception as e:
            return STTResult(text="", error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        yield STTResult(error="Whisper does not support streaming")

    async def close(self):
        self._model = None

    @property
    def is_available(self) -> bool:
        try:
            import whisper
            return True
        except ImportError:
            return False


class WhisperCPPSTT(WhisperSTT):
    name = "whisper_cpp"

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        try:
            import whisper_cpp_py as whisper_cpp
            result = whisper_cpp.transcribe(audio, language=language or "auto")
            return STTResult(
                text=result.get("text", "").strip(),
                confidence=result.get("confidence", 1.0),
                language=language or "en",
                is_final=True,
            )
        except ImportError:
            return STTResult(error="whisper-cpp not installed")
        except Exception as e:
            return STTResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            import whisper_cpp_py
            return True
        except ImportError:
            return False


register_stt("whisper", WhisperSTT)
register_stt("whisper_cpp", WhisperCPPSTT)
