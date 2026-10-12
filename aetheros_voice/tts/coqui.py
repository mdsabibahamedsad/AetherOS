from __future__ import annotations

import os
from aetheros_voice.models.models import TTSResult
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.tts import register_tts


class CoquiTTS(TTSBackend):
    name = "coqui"
    supports_offline = True

    def __init__(self):
        self._model = None

    async def load_model(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        try:
            from TTS.api import TTS
            self._model = TTS(model_name=model_name)
        except ImportError:
            pass

    async def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None, **kwargs) -> TTSResult:
        if self._model is None:
            await self.load_model()
        if self._model is None:
            return TTSResult(error="Coqui TTS not available")
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            self._model.tts_to_file(text=text, file_path=tmp_path, speed=speed)
            with open(tmp_path, "rb") as f:
                audio = f.read()
            import os as _os
            _os.unlink(tmp_path)
            return TTSResult(audio_data=audio, text=text, format="wav", sample_rate=24000)
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            from TTS.api import TTS
            return True
        except ImportError:
            return False


class EdgeTTS(TTSBackend):
    name = "edge_tts"
    supports_offline = False

    async def synthesize(self, text: str, speed: float = 1.0, voice: str = "en-US-JennyNeural", **kwargs) -> TTSResult:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice=voice, rate=f"+{int((speed-1)*100)}%" if speed >= 1 else f"{int((speed-1)*100)}%")
            audio = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
            return TTSResult(audio_data=audio, text=text, format="mp3", sample_rate=24000)
        except ImportError:
            return TTSResult(error="edge-tts not installed")
        except Exception as e:
            return TTSResult(error=str(e))

    @property
    def is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    @property
    def voices(self) -> list[str]:
        try:
            import edge_tts
            import asyncio
            voices = asyncio.run(edge_tts.list_voices())
            return [v["Name"] for v in voices]
        except Exception:
            return ["en-US-JennyNeural"]


register_tts("coqui", CoquiTTS)
register_tts("edge_tts", EdgeTTS)
