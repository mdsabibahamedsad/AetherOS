"""Jarvis Mode — conversation manager.

Implements the conversation modes (voice-only, text-only, mixed, continuous,
push-to-talk, hands-free) and the dialogue rules that govern when Jarvis
listens, speaks, and yields. Conversation state is fully explicit and
thread-safe so the runtime can pause/resume without losing the turn.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from aetheros_jarvis.models import ConversationMode, Utterance

logger = logging.getLogger(__name__)


class ConversationManager:
    """Owns the current conversation mode and turn lifecycle."""

    def __init__(self, mode: ConversationMode = ConversationMode.MIXED) -> None:
        self._lock = threading.RLock()
        self._mode = mode
        self._listening = False
        self._speaking = False
        self._waiting_reply = False
        self._turn_count = 0
        self._current_utterance: Optional[Utterance] = None

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    @property
    def mode(self) -> ConversationMode:
        with self._lock:
            return self._mode

    def set_mode(self, mode: ConversationMode) -> None:
        with self._lock:
            self._mode = mode
            logger.info("Conversation mode set to %s", mode.value)

    # ------------------------------------------------------------------
    # Turn lifecycle
    # ------------------------------------------------------------------

    def start_turn(self, utterance: Utterance) -> None:
        with self._lock:
            self._current_utterance = utterance
            self._turn_count += 1
            self._listening = True
            self._speaking = False
            self._waiting_reply = False

    def finish_turn(self) -> None:
        with self._lock:
            self._current_utterance = None
            self._listening = False
            self._speaking = False
            self._waiting_reply = False

    def mark_speaking(self, speaking: bool) -> None:
        with self._lock:
            self._speaking = speaking
            if speaking:
                self._listening = False

    def mark_listening(self, listening: bool) -> None:
        with self._lock:
            self._listening = listening
            if listening:
                self._speaking = False

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def should_listen(self) -> bool:
        """Whether Jarvis should be listening right now for this mode."""
        with self._lock:
            if self._mode == ConversationMode.OFF or self._mode == ConversationMode.TEXT_ONLY:
                return False
            if self._speaking:
                return False
            if self._mode == ConversationMode.PUSH_TO_TALK:
                return False  # only after explicit push-to-talk
            return True

    def should_speak(self) -> bool:
        with self._lock:
            if self._mode == ConversationMode.TEXT_ONLY or self._mode == ConversationMode.OFF:
                return False
            return True

    def hands_free(self) -> bool:
        return self._mode == ConversationMode.HANDS_FREE

    def continuous(self) -> bool:
        return self._mode == ConversationMode.CONTINUOUS

    def listens_for_follow_up(self) -> bool:
        """Continuous/hands-free modes keep the channel open after a turn."""
        return self._mode in (ConversationMode.CONTINUOUS, ConversationMode.HANDS_FREE)

    def can_interrupt(self) -> bool:
        return self._mode in (ConversationMode.CONTINUOUS, ConversationMode.HANDS_FREE, ConversationMode.MIXED)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def turn_count(self) -> int:
        with self._lock:
            return self._turn_count

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "mode": self._mode.value,
                "listening": self._listening,
                "speaking": self._speaking,
                "turn_count": self._turn_count,
                "should_listen": self._mode not in (ConversationMode.OFF, ConversationMode.TEXT_ONLY) and not self._speaking,
            }
