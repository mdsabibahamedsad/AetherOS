from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationTurn:
    id: str = ""
    text: str = ""
    response: str = ""
    timestamp: float = 0.0
    duration: float = 0.0
    interrupted: bool = False
    context: dict = field(default_factory=dict)


class ConversationManager:
    def __init__(self, max_history: int = 50):
        self._history: list[ConversationTurn] = []
        self._max_history = max_history
        self._current_turn: ConversationTurn | None = None
        self._interrupted = False
        self._listeners: list = []

    def start_turn(self, text: str, context: dict | None = None) -> str:
        turn_id = str(uuid.uuid4())[:8]
        self._current_turn = ConversationTurn(
            id=turn_id, text=text, timestamp=time.time(), context=context or {},
        )
        return turn_id

    def complete_turn(self, response: str):
        if self._current_turn:
            self._current_turn.response = response
            self._current_turn.duration = time.time() - self._current_turn.timestamp
            self._current_turn.interrupted = self._interrupted
            self._history.append(self._current_turn)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            self._notify(self._current_turn)
        self._current_turn = None
        self._interrupted = False

    def interrupt(self):
        self._interrupted = True

    @property
    def current_turn(self) -> ConversationTurn | None:
        return self._current_turn

    @property
    def history(self) -> list[ConversationTurn]:
        return list(self._history)

    @property
    def last_response(self) -> str:
        return self._history[-1].response if self._history else ""

    @property
    def turn_count(self) -> int:
        return len(self._history)

    def get_context(self, turns: int = 5) -> list[dict]:
        recent = self._history[-turns:] if self._history else []
        return [{"role": "user" if i % 2 == 0 else "assistant", "text": t.text if i % 2 == 0 else t.response}
                for i, t in enumerate(recent) if t.response or t.text]

    def on_turn_complete(self, callback):
        self._listeners.append(callback)

    def clear(self):
        self._history.clear()
        self._current_turn = None

    def _notify(self, turn: ConversationTurn):
        for cb in self._listeners:
            try:
                cb(turn)
            except Exception:
                pass
