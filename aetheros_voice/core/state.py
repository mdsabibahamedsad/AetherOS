from __future__ import annotations

import time
from typing import Any

from aetheros_voice.models.models import VoiceMode, VoiceState


class VoiceStateManager:
    def __init__(self):
        self._state: VoiceState = VoiceState.IDLE
        self._mode: VoiceMode = VoiceMode.CONVERSATION
        self._listening: bool = False
        self._speaking: bool = False
        self._processing: bool = False
        self._paused: bool = False
        self._error: str = ""
        self._started_at: float = 0.0
        self._listeners: list = []

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def mode(self) -> VoiceMode:
        return self._mode

    @mode.setter
    def mode(self, value: VoiceMode):
        self._mode = value

    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    @property
    def is_processing(self) -> bool:
        return self._processing

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_idle(self) -> bool:
        return self._state == VoiceState.IDLE

    @property
    def has_error(self) -> bool:
        return self._state == VoiceState.ERROR

    @property
    def error(self) -> str:
        return self._error

    def set_state(self, state: VoiceState):
        old = self._state
        self._state = state
        if state == VoiceState.LISTENING:
            self._listening = True
            self._speaking = False
            self._processing = False
        elif state == VoiceState.PROCESSING:
            self._listening = False
            self._processing = True
        elif state == VoiceState.SPEAKING:
            self._speaking = True
            self._listening = False
            self._processing = False
        elif state == VoiceState.IDLE:
            self._listening = False
            self._speaking = False
            self._processing = False
            self._paused = False
            self._error = ""
        elif state == VoiceState.PAUSED:
            self._paused = True
        self._notify(old)

    def set_error(self, error: str):
        self._error = error
        self.set_state(VoiceState.ERROR)

    def start(self):
        self._started_at = time.time()
        self.set_state(VoiceState.IDLE)

    def stop(self):
        self.set_state(VoiceState.IDLE)

    def pause(self):
        self.set_state(VoiceState.PAUSED)

    def resume(self):
        self.set_state(VoiceState.IDLE)

    def summary(self) -> dict:
        return {
            "state": self._state.value,
            "mode": self._mode.value,
            "listening": self._listening,
            "speaking": self._speaking,
            "processing": self._processing,
            "paused": self._paused,
            "error": self._error,
            "uptime": time.time() - self._started_at if self._started_at else 0,
        }

    def on_state_change(self, callback):
        self._listeners.append(callback)

    def _notify(self, old_state: VoiceState):
        for cb in self._listeners:
            try:
                cb(old_state, self._state)
            except Exception:
                pass
