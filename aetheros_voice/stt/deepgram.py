from __future__ import annotations

import os, time
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class DeepgramSTT(STTBackend):
    name = "deepgram"
    supports_offline = False
    supports_streaming = True

    def __init__(self):
        self._client = None
        self._api_key = os.getenv("DEEPGRAM_API_KEY", "")

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        try:
            from deepgram import DeepgramClient, PrerecordedOptions
            if self._client is None:
                self._client = DeepgramClient(self._api_key)
            opts = PrerecordedOptions(model="nova-2", language=language or "en", smart_format=True)
            source = {"buffer": audio, "mimetype": "audio/wav"}
            response = self._client.listen.prerecorded.v("1").transcribe(source, opts)
            results = response.results
            channels = results.channels
            if channels:
                words = channels[0].alternatives[0]
                return STTResult(
                    text=words.transcript.strip(),
                    confidence=words.confidence if hasattr(words, "confidence") else 1.0,
                    language=language or "en",
                    is_final=True,
                )
        except ImportError:
            return STTResult(error="deepgram not installed")
        except Exception as e:
            return STTResult(error=str(e))
        return STTResult()

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        try:
            from deepgram import DeepgramClient, LiveOptions
            if self._client is None:
                self._client = DeepgramClient(self._api_key)
            conn = self._client.listen.live.v("1")
            opts = LiveOptions(model="nova-2", language=language or "en", smart_format=True, encoding="linear16", sample_rate=16000)
            conn.start(opts)
            async for chunk in audio_stream:
                conn.send(chunk)
                for response in conn:
                    if response.get("is_final"):
                        yield STTResult(
                            text=response["channel"]["alternatives"][0]["transcript"].strip(),
                            confidence=response["channel"]["alternatives"][0].get("confidence", 1.0),
                            language=language or "en",
                            is_final=True,
                        )
            conn.finish()
        except ImportError:
            yield STTResult(error="deepgram not installed")
        except Exception as e:
            yield STTResult(error=str(e))

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)


register_stt("deepgram", DeepgramSTT)
