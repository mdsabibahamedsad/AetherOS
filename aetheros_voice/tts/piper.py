from __future__ import annotations

import os, tempfile, subprocess
from aetheros_voice.models.models import TTSResult
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.tts import register_tts


class PiperTTS(TTSBackend):
    name = "piper"
    supports_offline = True

    def __init__(self, model_path: str | None = None):
        self._model_path = model_path or os.getenv("PIPER_MODEL_PATH", "")

    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        try:
            import piper_tts
            if not self._model_path:
                return TTSResult(error="Piper model path not set")
            tts = piper_tts.PiperTTS(self._model_path)
            audio = tts.synthesize(text)
            return TTSResult(audio_data=audio, text=text, format="wav", sample_rate=22050)
        except ImportError:
            return TTSResult(error="piper-tts not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            import piper_tts
            return True
        except ImportError:
            return False


class KokoroTTS(TTSBackend):
    name = "kokoro"
    supports_offline = True

    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        try:
            from kokoro import KPipeline
            import numpy as np
            pipeline = KPipeline(lang_code='a')
            generator = pipeline(text, voice=voice or 'af_heart', speed=speed)
            audio_parts = []
            for result in generator:
                audio_parts.append(result.audio)
            if audio_parts:
                import numpy as np
                audio = np.concatenate(audio_parts) if len(audio_parts) > 1 else audio_parts[0]
                import soundfile as sf
                import io
                buf = io.BytesIO()
                sf.write(buf, audio, 24000, format='wav')
                return TTSResult(audio_data=buf.getvalue(), text=text, format="wav", sample_rate=24000)
        except ImportError:
            return TTSResult(error="kokoro not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            from kokoro import KPipeline
            return True
        except ImportError:
            return False


register_tts("piper", PiperTTS)
register_tts("kokoro", KokoroTTS)
