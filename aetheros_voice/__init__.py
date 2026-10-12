"""Aether Voice OS — a production-grade voice operating system inside AetherOS."""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Callable

from aetheros_voice.core.engine import VoiceEngine
from aetheros_voice.core.config import VoiceConfigManager
from aetheros_voice.core.state import VoiceStateManager
from aetheros_voice.models.models import (
    VoiceMode, VoiceState, VoiceConfig, STTResult, TTSResult,
)
from aetheros_voice.api.voice_api import UnifiedVoiceAPI
from aetheros_voice.web.api import VoiceWebAPI
from aetheros_voice.commands.registry import CommandRegistry
from aetheros_voice.commands.builtin import BuiltInCommands
from aetheros_voice.plugins.registry import VoicePluginRegistry


class VoiceOS:
    def __init__(self, config: VoiceConfig | None = None):
        self.engine = VoiceEngine(config)
        self.config_mgr = self.engine.config_mgr
        self.state = self.engine.state
        self.commands = self.engine.commands
        self.api = UnifiedVoiceAPI(self.engine)
        self.web = VoiceWebAPI(self.engine)

        BuiltInCommands(self.commands, self.engine.computer)

    async def start(self, mode: VoiceMode = VoiceMode.CONVERSATION):
        self.state.mode = mode
        await self.engine.start()
        await self.engine.plugins.initialize_all(self.engine)
        await self.engine._emit("voice.started", {"mode": mode.value})

    async def stop(self):
        await self.engine.plugins.shutdown_all()
        await self.engine.stop()

    async def listen_and_respond(self):
        text = await self.engine.listen()
        if text:
            response = await self._handle_input(text)
            await self.engine.speak(response)
            self.engine.history.add(text, response, self.state.mode.value)

    async def _handle_input(self, text: str) -> str:
        mode = self.state.mode
        if mode == VoiceMode.COMMAND:
            return await self.engine.process_voice_command(text) or f"Unknown command: {text}"
        elif mode == VoiceMode.DICTATION:
            return await self.engine.dictation.process(text)
        elif mode == VoiceMode.ASSISTANT:
            from aetheros_voice.modes.conversation import ConversationMode
            return await ConversationMode(self.engine).handle(text)
        else:
            cmd_result = await self.engine.process_voice_command(text)
            if cmd_result:
                return cmd_result
            return text

    async def listen_loop(self):
        while self.state.state != VoiceState.IDLE:
            await self.listen_and_respond()

    @property
    def is_running(self) -> bool:
        return self.state.state != VoiceState.IDLE

    def set_mode(self, mode: VoiceMode):
        self.state.mode = mode

    def register_plugin(self, plugin):
        self.engine.plugins.register(plugin)

    def on(self, event: str, callback: Callable):
        self.engine.on(event, callback)


__all__ = [
    "VoiceOS", "VoiceEngine", "VoiceConfigManager", "VoiceStateManager",
    "VoiceConfig", "VoiceMode", "VoiceState", "UnifiedVoiceAPI",
    "CommandRegistry", "VoicePluginRegistry",
]
