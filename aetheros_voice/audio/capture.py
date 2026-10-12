from __future__ import annotations

import asyncio
import queue
import struct
import time
from typing import Any, Callable


class AudioCapture:
    def __init__(self, device: str | None = None, sample_rate: int = 16000, buffer_size: int = 1024):
        self._device = device
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._stream = None
        self._running = False

    async def record(self, timeout: float | None = None) -> bytes:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            device_idx = self._resolve_device(p)
            stream = p.open(
                format=pyaudio.paInt16, channels=1, rate=self._sample_rate,
                input=True, input_device_index=device_idx,
                frames_per_buffer=self._buffer_size,
            )
            frames = []
            end_time = time.time() + (timeout or 5.0)
            while time.time() < end_time:
                data = stream.read(self._buffer_size, exception_on_overflow=False)
                frames.append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()
            return b"".join(frames)
        except ImportError:
            return b""

    async def record_stream(self, callback: Callable):
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            device_idx = self._resolve_device(p)

            def _callback(in_data, frame_count, time_info, status):
                if self._running:
                    asyncio.run_coroutine_threadsafe(callback(in_data), asyncio.get_event_loop())
                return (None, pyaudio.paContinue)

            self._stream = p.open(
                format=pyaudio.paInt16, channels=1, rate=self._sample_rate,
                input=True, input_device_index=device_idx,
                frames_per_buffer=self._buffer_size,
                stream_callback=_callback,
            )
            self._running = True
            self._stream.start_stream()
            while self._running:
                await asyncio.sleep(0.1)
            self._stream.stop_stream()
            self._stream.close()
            p.terminate()
        except ImportError:
            pass

    def stop(self):
        self._running = False

    def close(self):
        self.stop()

    def _resolve_device(self, p) -> int | None:
        if self._device:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if self._device in info["name"]:
                    return i
        return None

    def list_devices(self) -> list[dict]:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append({"index": i, "name": info["name"], "channels": info["maxInputChannels"], "rate": info["defaultSampleRate"]})
            p.terminate()
            return devices
        except ImportError:
            return []
