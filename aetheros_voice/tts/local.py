from __future__ import annotations

from aetheros_voice.models.models import TTSResult
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.tts import register_tts


class LocalTTS(TTSBackend):
    name = "local"
    supports_offline = True

    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            rate = engine.getProperty("rate")
            engine.setProperty("rate", int(rate * speed))
            if voice:
                voices = engine.getProperty("voices")
                for v in voices:
                    if voice.lower() in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, "rb") as f:
                audio = f.read()
            import os
            os.unlink(tmp_path)
            return TTSResult(audio_data=audio, text=text, format="wav", sample_rate=22050)
        except ImportError:
            return TTSResult(error="pyttsx3 not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            import pyttsx3
            return True
        except ImportError:
            return False

    @property
    def voices(self) -> list[str]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            return [v.name for v in engine.getProperty("voices")]
        except Exception:
            return ["default"]


class FallbackTTS(TTSBackend):
    name = "fallback"

    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        print(f"[Voice TTS] {text}")
        return TTSResult(text=text, format="text", error="No TTS backend configured. Install edge-tts, piper-tts, or set ELEVENLABS_API_KEY.")


register_tts("local", LocalTTS)
