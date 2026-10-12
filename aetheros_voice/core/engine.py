from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

from aetheros_voice.models.models import (
    VoiceState, VoiceConfig, STTResult, TTSResult,
    WakeWordResult,
)
from aetheros_voice.core.config import VoiceConfigManager
from aetheros_voice.core.state import VoiceStateManager
from aetheros_voice.audio.capture import AudioCapture
from aetheros_voice.audio.playback import AudioPlayback
from aetheros_voice.audio.stream import AudioStream
from aetheros_voice.stt.base import STTBackend
from aetheros_voice.tts.base import TTSBackend
from aetheros_voice.wakeword.base import WakeWordDetector
from aetheros_voice.commands.registry import CommandRegistry
from aetheros_voice.chat.conversation import ConversationManager
from aetheros_voice.dictation.engine import DictationEngine
from aetheros_voice.computer.controller import ComputerController
from aetheros_voice.personality.base import PersonalityEngine
from aetheros_voice.memory.store import VoiceMemoryStore
from aetheros_voice.history.store import VoiceHistoryStore
from aetheros_voice.security.consent import ConsentManager
from aetheros_voice.noise.vad import VoiceActivityDetector
from aetheros_voice.plugins.registry import VoicePluginRegistry


class VoiceEngine:
    def __init__(self, config: VoiceConfig | None = None):
        self.config_mgr = VoiceConfigManager()
        if config:
            self.config_mgr.config = config
        self.state = VoiceStateManager()
        self.capture = AudioCapture()
        self.playback = AudioPlayback()
        self.stream = AudioStream()
        self.vad = VoiceActivityDetector()
        self.commands = CommandRegistry()
        self.conversation = ConversationManager()
        self.dictation = DictationEngine()
        self.computer = ComputerController()
        self.personality = PersonalityEngine()
        self.memory = VoiceMemoryStore()
        self.history = VoiceHistoryStore()
        self.consent = ConsentManager()
        self.plugins = VoicePluginRegistry()
        self._confirmation_resolver: Callable[[str], bool] | None = None

        self._stt: STTBackend | None = None
        self._tts: TTSBackend | None = None
        self._wakeword: WakeWordDetector | None = None
        self._running = False
        self._listeners: dict[str, list[Callable]] = {}
        self._interrupt_event = asyncio.Event()

    async def start(self):
        self.state.start()
        self._running = True
        self._interrupt_event.clear()
        await self._init_backends()
        await self._emit("engine.started")

    async def stop(self):
        self._running = False
        await self._stop_backends()
        self.state.stop()
        self.capture.close()
        self.playback.close()
        await self._emit("engine.stopped")

    async def listen(self, timeout: float | None = None) -> str:
        self.state.set_state(VoiceState.LISTENING)
        await self._emit("listening.started")
        audio = await self.capture.record(timeout=timeout)
        if audio is None or len(audio) == 0:
            self.state.set_state(VoiceState.IDLE)
            return ""
        self.state.set_state(VoiceState.PROCESSING)
        await self._emit("processing.started")
        result = await self._transcribe(audio)
        self.state.set_state(VoiceState.IDLE)
        await self._emit("listening.finished", {"text": result.text})
        return result.text

    async def listen_stream(self, callback: Callable):
        self.state.set_state(VoiceState.LISTENING)
        await self._emit("listening.started")

        async def _on_chunk(audio_chunk):
            if self._interrupt_event.is_set():
                return
            result = await self._transcribe(audio_chunk)
            if result.text:
                await callback(result)

        await self.capture.record_stream(_on_chunk)

    async def speak(self, text: str) -> TTSResult:
        self.state.set_state(VoiceState.SPEAKING)
        await self._emit("speaking.started", {"text": text})
        result = await self._synthesize(text, self.config_mgr.get("voice_speed"))
        if result.audio_data:
            await self.playback.play(result.audio_data, self.config_mgr.get("voice_volume"))
        self.state.set_state(VoiceState.IDLE)
        await self._emit("speaking.finished")
        return result

    async def speak_stream(self, text_stream):
        self.state.set_state(VoiceState.SPEAKING)
        async for chunk in text_stream:
            if self._interrupt_event.is_set():
                break
            result = await self._synthesize(chunk)
            if result.audio_data:
                await self.playback.play(result.audio_data)
        self.state.set_state(VoiceState.IDLE)

    def interrupt(self):
        self._interrupt_event.set()
        self.playback.stop()
        self.state.set_state(VoiceState.IDLE)

    async def process_voice_command(self, text: str) -> str:
        text = text.strip().lower()
        command = self.commands.match(text)
        if command:
            await self._emit("command.executed", {"command": command.phrase, "action": command.action})
            if command.requires_confirm and self.config_mgr.get("confirm_destructive"):
                confirmed = await self._request_confirmation(f"Execute {command.phrase}?")
                if not confirmed:
                    return "Command cancelled."
            result = await self.commands.execute(command)
            return result
        return ""

    async def detect_wake_word(self, audio: bytes) -> WakeWordResult:
        if self._wakeword is None or not self.config_mgr.get("wake_word_enabled"):
            return WakeWordResult()
        return await self._wakeword.detect(audio)

    def on(self, event: str, callback: Callable):
        self._listeners.setdefault(event, []).append(callback)

    async def get_status(self) -> dict:
        return {
            "state": self.state.summary(),
            "config": self.config_mgr.export_config(),
            "stt": self._stt.__class__.__name__ if self._stt else None,
            "tts": self._tts.__class__.__name__ if self._tts else None,
            "wakeword": self._wakeword.__class__.__name__ if self._wakeword else None,
            "running": self._running,
        }

    async def _init_backends(self):
        from aetheros_voice.stt import create_stt
        from aetheros_voice.tts import create_tts
        from aetheros_voice.wakeword import create_wakeword
        self._stt = create_stt(self.config_mgr.get("stt_provider"))
        self._tts = create_tts(self.config_mgr.get("tts_provider"))
        self._wakeword = create_wakeword()

    async def _stop_backends(self):
        if self._stt:
            await self._stt.close()
        if self._tts:
            await self._tts.close()
        if self._wakeword:
            await self._wakeword.close()

    async def _transcribe(self, audio: bytes) -> STTResult:
        if self._stt is None:
            return STTResult(error="No STT backend")
        return await self._stt.transcribe(audio, language=self.config_mgr.get("language") if not self.config_mgr.get("auto_language_detect") else None)

    async def _synthesize(self, text: str, speed: float = 1.0) -> TTSResult:
        if self._tts is None:
            return TTSResult(error="No TTS backend")
        return await self._tts.synthesize(text, speed=speed)

    def set_confirmation_resolver(self, resolver: Callable[[str], bool]):
        """Set the callback used to approve destructive actions.

        The resolver receives the confirmation prompt and must return a
        boolean decision. By default no resolver is installed and destructive
        commands are DENIED, never auto-approved.
        """
        self._confirmation_resolver = resolver

    async def _request_confirmation(self, prompt: str) -> bool:
        await self._emit("confirmation.requested", {"prompt": prompt})
        if self._confirmation_resolver is None:
            logger.warning("Destructive command requested (%s) but no confirmation resolver is set; denying.", prompt)
            return False
        try:
            result = self._confirmation_resolver(prompt)
            if asyncio.iscoroutine(result):
                result = await result
            return bool(result)
        except Exception as exc:
            logger.warning("Confirmation resolver failed (%s); denying: %s", prompt, exc)
            return False

    async def _emit(self, event: str, data: Any = None):
        for cb in self._listeners.get(event, []):
            try:
                result = cb(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
