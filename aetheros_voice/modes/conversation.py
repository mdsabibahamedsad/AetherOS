from __future__ import annotations

from aetheros_voice.core.engine import VoiceEngine


class ConversationMode:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    async def handle(self, text: str) -> str:
        return f"You said: {text}"

    @property
    def name(self) -> str:
        return "conversation"


class CommandMode:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    async def handle(self, text: str) -> str:
        result = await self._engine.process_voice_command(text)
        if result:
            return result
        return f"Command not recognized: {text}"

    @property
    def name(self) -> str:
        return "command"


class DictationMode:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    async def handle(self, text: str) -> str:
        processed = await self._engine.dictation.process(text, auto_punctuate=True, grammar_correct=True)
        return processed

    @property
    def name(self) -> str:
        return "dictation"


class AssistantMode:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    async def handle(self, text: str) -> str:
        return f"[Assistant] {text}"

    @property
    def name(self) -> str:
        return "assistant"


class ContinuousListening:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine
        self._running = False

    async def start(self, callback):
        self._running = True
        while self._running:
            text = await self._engine.listen(timeout=1.0)
            if text:
                await callback(text)

    def stop(self):
        self._running = False

    @property
    def name(self) -> str:
        return "continuous"


class PushToTalk:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine
        self._key = "space"

    async def wait_for_trigger(self) -> bool:
        return True

    async def handle(self, text: str) -> str:
        return await self._engine.process_voice_command(text) or text

    @property
    def name(self) -> str:
        return "push_to_talk"
