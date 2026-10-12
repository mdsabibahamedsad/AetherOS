from __future__ import annotations

import re
import time
import uuid
from typing import Any, Callable

from aetheros_voice.models.models import VoiceCommand


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, VoiceCommand] = {}
        self._handlers: dict[str, Callable] = {}
        self._builtins: BuiltInCommands | None = None

    def register(self, phrase: str, action: str, handler: Callable, category: str = "general",
                 requires_confirm: bool = False, params: dict | None = None):
        cmd = VoiceCommand(
            id=str(uuid.uuid4())[:8], phrase=phrase, action=action,
            params=params or {}, category=category, requires_confirm=requires_confirm,
            created_at=time.time(),
        )
        key = phrase.lower().strip()
        self._commands[key] = cmd
        self._handlers[key] = handler

    def match(self, text: str) -> VoiceCommand | None:
        lower = text.lower().strip()
        for phrase, cmd in self._commands.items():
            if phrase in lower or lower.startswith(phrase) or lower == phrase:
                return cmd
        for phrase, cmd in self._commands.items():
            words = phrase.split()
            matches = sum(1 for w in words if w in lower)
            if matches >= len(words) * 0.7:
                return cmd
        return None

    async def execute(self, command: VoiceCommand) -> str:
        handler = self._handlers.get(command.phrase.lower())
        if handler is None:
            return f"No handler for: {command.phrase}"
        try:
            result = handler(**command.params)
            if hasattr(result, "__await__"):
                return await result
            return result if result is not None else f"Executed: {command.phrase}"
        except Exception as e:
            return f"Error executing {command.phrase}: {e}"

    def list_commands(self, category: str | None = None) -> list[VoiceCommand]:
        if category:
            return [c for c in self._commands.values() if c.category == category]
        return list(self._commands.values())

    def remove(self, phrase: str):
        key = phrase.lower().strip()
        self._commands.pop(key, None)
        self._handlers.pop(key, None)
