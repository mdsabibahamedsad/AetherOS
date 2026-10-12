from __future__ import annotations

import os
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class AssemblyAISTT(STTBackend):
    name = "assemblyai"
    supports_offline = False
    supports_streaming = True

    def __init__(self):
        self._api_key = os.getenv("ASSEMBLYAI_API_KEY", "")

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        try:
            import assemblyai as aai
            aai.settings.api_key = self._api_key
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            config = aai.TranscriptionConfig(language_code=language or "en", speech_model=aai.SpeechModel.nano)
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(tmp_path, config=config)
            import os as _os
            _os.unlink(tmp_path)
            if transcript.status == aai.TranscriptStatus.error:
                return STTResult(error=transcript.error)
            return STTResult(
                text=transcript.text.strip(),
                confidence=transcript.confidence,
                language=transcript.language or language or "en",
                is_final=True,
            )
        except ImportError:
            return STTResult(error="assemblyai not installed")
        except Exception as e:
            return STTResult(error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        try:
            import assemblyai as aai
            aai.settings.api_key = self._api_key
            transcriber = aai.Transcriber()
            config = aai.TranscriptionConfig(language_code=language or "en")

            async def _feed():
                async for chunk in audio_stream:
                    yield chunk

            stream = transcriber.stream(_feed(), config=config)
            for result in stream:
                if result.text.strip():
                    yield STTResult(text=result.text.strip(), confidence=result.confidence, language=language or "en", is_final=result.is_final)
        except ImportError:
            yield STTResult(error="assemblyai not installed")
        except Exception as e:
            yield STTResult(error=str(e))

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)


register_stt("assemblyai", AssemblyAISTT)
