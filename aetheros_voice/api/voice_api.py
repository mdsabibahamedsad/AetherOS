"""Unified Voice API — speech_to_text, text_to_speech, wake_word, stream_audio, voice_command."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from aetheros_voice.core.engine import VoiceEngine
from aetheros_voice.models.models import STTResult, TTSResult, WakeWordResult


class UnifiedVoiceAPI:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    async def speech_to_text(self, audio: bytes, language: str | None = None, **kwargs) -> STTResult:
        if language:
            self._engine.config_mgr.set("language", language)
        return await self._engine._transcribe(audio)

    async def speech_to_text_stream(self, audio_stream, language: str | None = None, **kwargs):
        if language:
            self._engine.config_mgr.set("language", language)
        async for chunk in audio_stream:
            yield await self._engine._transcribe(chunk)

    async def text_to_speech(self, text: str, voice: str | None = None, speed: float = 1.0, **kwargs) -> TTSResult:
        return await self._engine._synthesize(text, speed=speed)

    async def text_to_speech_stream(self, text_stream, voice: str | None = None, speed: float = 1.0, **kwargs):
        async for text in text_stream:
            yield await self._engine._synthesize(text, speed=speed)

    async def wake_word(self, audio: bytes) -> WakeWordResult:
        return await self._engine.detect_wake_word(audio)

    async def stream_audio(self, audio_stream):
        async for chunk in audio_stream:
            yield chunk

    async def voice_command(self, text: str) -> str:
        return await self._engine.process_voice_command(text)

    async def listen(self, timeout: float | None = None) -> str:
        return await self._engine.listen(timeout=timeout)

    async def speak(self, text: str):
        await self._engine.speak(text)

    def set_config(self, **kwargs):
        self._engine.config_mgr.update(**kwargs)

    def get_status(self) -> dict:
        return self._engine.state.summary()
