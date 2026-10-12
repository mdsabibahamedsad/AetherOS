from __future__ import annotations

import re
from typing import Any

from aetheros_voice.models.models import DictationMode
from aetheros_voice.dictation.autocorrect import AutoCorrect
from aetheros_voice.dictation.modes import DictationModeHandler


class DictationEngine:
    def __init__(self):
        self._autocorrect = AutoCorrect()
        self._mode_handler = DictationModeHandler()
        self._buffer: list[str] = []
        self._mode: DictationMode = DictationMode.PLAIN

    @property
    def mode(self) -> DictationMode:
        return self._mode

    @mode.setter
    def mode(self, value: DictationMode):
        self._mode = value

    async def process(self, text: str, mode: DictationMode | None = None, auto_punctuate: bool = True,
                      grammar_correct: bool = True) -> str:
        m = mode or self._mode
        result = text.strip()
        if auto_punctuate:
            result = self._autocorrect.add_punctuation(result)
        if grammar_correct:
            result = self._autocorrect.correct_grammar(result)

        output = self._mode_handler.apply(result, m)
        return output

    async def process_stream(self, text_stream):
        async for chunk in text_stream:
            yield await self.process(chunk)

    def add_to_buffer(self, text: str):
        self._buffer.append(text)

    def flush_buffer(self) -> str:
        result = " ".join(self._buffer)
        self._buffer.clear()
        return result

    def reset(self):
        self._buffer.clear()
