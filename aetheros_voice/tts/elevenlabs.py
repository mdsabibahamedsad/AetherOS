from __future__ import annotations

import os
from aetheros_voice.models.models import TTSResult
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.tts import register_tts


class ElevenLabsTTS(TTSBackend):
    name = "elevenlabs"
    supports_offline = False

    def __init__(self):
        self._api_key = os.getenv("ELEVENLABS_API_KEY", "")

    async def synthesize(self, text: str, speed: float = 1.0, voice: str = "21m00Tcm4TlvDq8ikWAM", **kwargs) -> TTSResult:
        try:
            from elevenlabs import Voice, VoiceSettings, generate
            audio = generate(
                text=text,
                voice=voice,
                model="eleven_multilingual_v2",
                api_key=self._api_key,
            )
            return TTSResult(audio_data=audio if isinstance(audio, bytes) else b"", text=text, format="mp3", sample_rate=44100)
        except ImportError:
            return TTSResult(error="elevenlabs not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    @property
    def voices(self) -> list[str]:
        if not self._api_key:
            return []
        try:
            from elevenlabs import voices as get_voices
            return [v.voice_id for v in get_voices()]
        except Exception:
            return []


class OpenAITTS(TTSBackend):
    name = "openai"
    supports_offline = False

    def __init__(self):
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    async def synthesize(self, text: str, speed: float = 1.0, voice: str = "alloy", **kwargs) -> TTSResult:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key)
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=text,
                speed=speed,
                response_format="wav",
            )
            return TTSResult(audio_data=response.content, text=text, format="wav", sample_rate=24000)
        except ImportError:
            return TTSResult(error="openai not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    @property
    def voices(self) -> list[str]:
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


register_tts("elevenlabs", ElevenLabsTTS)
register_tts("openai", OpenAITTS)
