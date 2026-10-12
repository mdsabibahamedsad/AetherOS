from __future__ import annotations

import os
from aetheros_voice.models.models import STTResult
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.stt import register_stt


class GoogleSTT(STTBackend):
    name = "google"
    supports_offline = False
    supports_streaming = True

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        try:
            from google.cloud.speech_v2 import SpeechClient
            from google.cloud.speech_v2.types import cloud_speech
            client = SpeechClient()
            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=[language or "en-US"],
                model="latest_short",
            )
            request = cloud_speech.RecognizeRequest(
                recognizer=f"projects/{os.getenv('GOOGLE_PROJECT_ID')}/locations/global/recognizers/_",
                config=config,
                content=audio,
            )
            response = client.recognize(request=request)
            text = " ".join(r.alternatives[0].transcript.strip() for r in response.results if r.alternatives)
            return STTResult(text=text, language=language or "en", is_final=True)
        except ImportError:
            return STTResult(error="google-cloud-speech not installed")
        except Exception as e:
            return STTResult(error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        try:
            from google.cloud.speech_v2 import SpeechClient
            from google.cloud.speech_v2.types import cloud_speech
            client = SpeechClient()
            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=[language or "en-US"],
                model="latest_short",
            )
            streaming_config = cloud_speech.StreamingRecognitionConfig(config=config)

            async def request_generator():
                yield cloud_speech.StreamingRecognizeRequest(streaming_config=streaming_config)
                async for chunk in audio_stream:
                    yield cloud_speech.StreamingRecognizeRequest(audio=chunk)

            responses = client.streaming_recognize(requests=request_generator())
            for response in responses:
                for result in response.results:
                    if result.alternatives:
                        yield STTResult(
                            text=result.alternatives[0].transcript.strip(),
                            confidence=result.alternatives[0].confidence if hasattr(result.alternatives[0], "confidence") else 1.0,
                            language=language or "en",
                            is_final=result.is_final,
                        )
        except ImportError:
            yield STTResult(error="google-cloud-speech not installed")
        except Exception as e:
            yield STTResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            from google.cloud.speech_v2 import SpeechClient
            return True
        except ImportError:
            return False


class AzureSTT(STTBackend):
    name = "azure"
    supports_offline = False
    supports_streaming = True

    async def transcribe(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=os.getenv("AZURE_SPEECH_KEY"),
                region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            )
            speech_config.speech_recognition_language = language or "en-US"
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            audio_config = speechsdk.AudioConfig(filename=tmp_path)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            result = recognizer.recognize_once()
            import os as _os
            _os.unlink(tmp_path)
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return STTResult(text=result.text.strip(), language=language or "en", is_final=True)
            return STTResult(error=f"Azure STT: {result.reason}")
        except ImportError:
            return STTResult(error="azure-cognitiveservices-speech not installed")
        except Exception as e:
            return STTResult(error=str(e))

    async def transcribe_stream(self, audio_stream, language: str | None = None, **kwargs):
        yield STTResult(error="Azure streaming TBD")

    @property
    def is_available(self) -> bool:
        return bool(os.getenv("AZURE_SPEECH_KEY"))


register_stt("google", GoogleSTT)
register_stt("azure", AzureSTT)
