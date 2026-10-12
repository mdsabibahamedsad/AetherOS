from __future__ import annotations

import os
from aetheros_voice.models.models import TTSResult
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.tts import register_tts


class AzureTTS(TTSBackend):
    name = "azure"
    supports_offline = False

    async def synthesize(self, text: str, speed: float = 1.0, voice: str = "en-US-JennyNeural", **kwargs) -> TTSResult:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=os.getenv("AZURE_SPEECH_KEY"),
                region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            )
            speech_config.speech_synthesis_voice_name = voice
            import io
            audio_stream = io.BytesIO()
            audio_config = speechsdk.audio.AudioOutputConfig(stream=audio_stream)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="{voice}"><prosody rate="{int((speed-1)*100)}%">{text}</prosody></voice></speak>'
            result = synthesizer.speak_ssml(ssml)
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return TTSResult(audio_data=audio_stream.getvalue(), text=text, format="wav", sample_rate=24000)
            return TTSResult(error=f"Azure TTS: {result.reason}")
        except ImportError:
            return TTSResult(error="azure-cognitiveservices-speech not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        return bool(os.getenv("AZURE_SPEECH_KEY"))

    @property
    def voices(self) -> list[str]:
        return ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-SoniaNeural", "en-AU-NatashaNeural"]


class GoogleTTS(TTSBackend):
    name = "google"
    supports_offline = False

    async def synthesize(self, text: str, speed: float = 1.0, voice: str = "en-US-Standard-C", **kwargs) -> TTSResult:
        try:
            from google.cloud.texttospeech import TextToSpeechClient, SynthesisInput, VoiceSelectionParams, AudioConfig, AudioEncoding
            client = TextToSpeechClient()
            input_text = SynthesisInput(text=text)
            voice_params = VoiceSelectionParams(language_code=voice[:5] if len(voice) >= 5 else "en-US", name=voice)
            audio_config = AudioConfig(audio_encoding=AudioEncoding.LINEAR16, speaking_rate=speed)
            response = client.synthesize_speech(request={"input": input_text, "voice": voice_params, "audio_config": audio_config})
            return TTSResult(audio_data=response.audio_content, text=text, format="wav", sample_rate=24000)
        except ImportError:
            return TTSResult(error="google-cloud-texttospeech not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            from google.cloud.texttospeech import TextToSpeechClient
            return True
        except ImportError:
            return False

    @property
    def voices(self) -> list[str]:
        return ["en-US-Standard-C", "en-US-Standard-B", "en-US-Standard-D", "en-US-Standard-E", "en-US-Standard-A"]


register_tts("azure", AzureTTS)
register_tts("google", GoogleTTS)
