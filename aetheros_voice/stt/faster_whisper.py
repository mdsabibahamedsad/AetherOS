from __future__ import annotations

import time
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class FasterWhisperSTT(STTBackend):
    name = "faster_whisper"
    supports_offline = True
    supports_streaming = False

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self._model_size = model_size
        self._device = device
        self._model = None

    async def load_model(self):
        try:
            from faster_whisper import WhisperModel
            device = self._device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            self._model = WhisperModel(self._model_size, device=device, compute_type=compute_type)
        except ImportError:
            pass

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        import io
        import tempfile
        if self._model is None:
            await self.load_model()
        if self._model is None:
            return STTResult(error="faster-whisper not available")

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            segments, info = self._model.transcribe(tmp_path, language=language or None)
            text = " ".join(seg.text for seg in segments)
            import os
            os.unlink(tmp_path)
            return STTResult(
                text=text.strip(),
                confidence=info.average_logprob if info else 1.0,
                language=info.language if info else (language or "en"),
                is_final=True,
                segments=[{"text": s.text, "start": s.start, "end": s.end} for s in segments] if segments else [],
            )
        except Exception as e:
            return STTResult(error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        yield STTResult(error="faster-whisper does not support streaming yet")

    async def close(self):
        self._model = None

    @property
    def is_available(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False


register_stt("faster_whisper", FasterWhisperSTT)
