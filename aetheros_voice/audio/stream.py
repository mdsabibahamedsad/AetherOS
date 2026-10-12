from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator


class AudioStream:
    def __init__(self, chunk_size: int = 4096):
        self._chunk_size = chunk_size
        self._buffers: dict[str, asyncio.Queue] = {}

    async def stream_audio(self, audio: bytes, stream_id: str = "default") -> AsyncGenerator[bytes, None]:
        for i in range(0, len(audio), self._chunk_size):
            yield audio[i:i + self._chunk_size]
            await asyncio.sleep(0)

    async def buffer(self, stream_id: str, data: bytes):
        if stream_id not in self._buffers:
            self._buffers[stream_id] = asyncio.Queue()
        await self._buffers[stream_id].put(data)

    async def read(self, stream_id: str) -> bytes:
        if stream_id not in self._buffers:
            return b""
        try:
            return await asyncio.wait_for(self._buffers[stream_id].get(), timeout=0.1)
        except asyncio.TimeoutError:
            return b""

    async def iterate(self, stream_id: str) -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await self.read(stream_id)
            if not chunk:
                break
            yield chunk

    def close_stream(self, stream_id: str):
        self._buffers.pop(stream_id, None)
