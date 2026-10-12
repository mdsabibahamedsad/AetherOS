from __future__ import annotations

import asyncio
import io
from typing import Any


class AudioPlayback:
    def __init__(self, device: str | None = None):
        self._device = device
        self._stream = None
        self._playing = False

    async def play(self, audio: bytes, volume: float = 1.0):
        if not audio:
            return
        try:
            import pyaudio
            import wave
            p = pyaudio.PyAudio()
            try:
                wf = wave.open(io.BytesIO(audio), "rb")
                sample_width = wf.getsampwidth()
                channels = wf.getnchannels()
                rate = wf.getframerate()
                fmt = p.get_format_from_width(sample_width)
                data = wf.readframes(wf.getnframes())
                if volume != 1.0:
                    import struct
                    import math
                    samples = struct.unpack(f"<{len(data)//sample_width}h" if sample_width == 2 else f"<{len(data)}b", data)
                    samples = [max(-32768, min(32767, int(s * volume))) for s in samples]
                    data = struct.pack(f"<{len(samples)}h", *samples)
                self._playing = True
                stream = p.open(format=fmt, channels=channels, rate=rate, output=True)
                stream.write(data)
                stream.stop_stream()
                stream.close()
            except wave.Error:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
                stream.write(audio)
                stream.stop_stream()
                stream.close()
            finally:
                p.terminate()
                self._playing = False
        except ImportError:
            pass

    def stop(self):
        self._playing = False

    def close(self):
        self.stop()

    @property
    def is_playing(self) -> bool:
        return self._playing
