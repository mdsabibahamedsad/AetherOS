from __future__ import annotations

import time
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class LocalSTT(STTBackend):
    name = "local"
    supports_offline = True
    supports_streaming = False

    def __init__(self, model_type: str = "transformers"):
        self._model_type = model_type
        self._model = None
        self._processor = None

    async def load_model(self):
        try:
            if self._model_type == "transformers":
                from transformers import WhisperProcessor, WhisperForConditionalGeneration
                self._processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")
                self._model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")
                self._model.config.forced_decoder_ids = None
            else:
                import torch
                import torchaudio
        except ImportError:
            pass

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        if self._model is None:
            await self.load_model()
        if self._model is None:
            return STTResult(error="No local model available")
        try:
            import io
            import torch
            import torchaudio
            import numpy as np
            buffer = io.BytesIO(audio)
            waveform, sr = torchaudio.load(buffer)
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                waveform = resampler(waveform)
            input_features = self._processor(waveform.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_features
            predicted_ids = self._model.generate(input_features)
            text = self._processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            return STTResult(text=text.strip(), language=language or "en", is_final=True)
        except ImportError:
            return STTResult(error="transformers/torch not installed")
        except Exception as e:
            return STTResult(error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        yield STTResult(error="Local streaming not supported")

    @property
    def is_available(self) -> bool:
        try:
            import transformers, torch, torchaudio
            return True
        except ImportError:
            return False


class FallbackSTT(STTBackend):
    name = "fallback"

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        return STTResult(error="No STT backend configured. Install whisper, set DEEPGRAM_API_KEY, or configure a provider.")

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        yield STTResult(error="No STT backend configured.")


register_stt("local", LocalSTT)
