"""Jarvis Mode — natural conversation (dialogue).

Handles multi-turn dialogue with context carry-over, follow-up questions,
clarification requests, and corrections. Dialogue state (recent turns,
pending clarifications, corrections) is stored in memory so a turn can
reference the previous one. This is the "remember the conversation" layer.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from aetheros_jarvis.models import DialogueTurn

logger = logging.getLogger(__name__)

_CLARIFICATION_PATTERNS = ("?", "what do you mean", "clarify", "i mean", "actually", "correction")


class DialogueManager:
    """Maintains multi-turn conversation context and clarifies ambiguous input.

    Each accepted utterance is appended to a bounded turn buffer. Follow-up
    utterances (detected heuristically) carry the previous turn's topic
    forward, so "and the second one?" resolves against the prior context.
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._lock = threading.RLock()
        self._max_turns = max_turns
        self._turns: List[DialogueTurn] = []
        self._pending_clarification: Optional[str] = None
        self._corrections: List[str] = []

    # ------------------------------------------------------------------
    # Turn recording
    # ------------------------------------------------------------------

    def add_turn(self, role: str, text: str) -> DialogueTurn:
        turn = DialogueTurn(role=role, text=text)
        with self._lock:
            self._turns.append(turn)
            if len(self._turns) > self._max_turns:
                self._turns = self._turns[-self._max_turns:]
        return turn

    def user(self, text: str) -> DialogueTurn:
        return self.add_turn("user", text)

    def assistant(self, text: str) -> DialogueTurn:
        return self.add_turn("assistant", text)

    # ------------------------------------------------------------------
    # Context carry-over
    # ------------------------------------------------------------------

    def recent(self, limit: int = 5) -> List[DialogueTurn]:
        with self._lock:
            return list(self._turns[-limit:])

    def last_user_text(self) -> str:
        with self._lock:
            for turn in reversed(self._turns):
                if turn.role == "user":
                    return turn.text
            return ""

    def last_topic(self) -> str:
        """Best-effort topic of the most recent user turn."""
        with self._lock:
            for turn in reversed(self._turns):
                if turn.role == "user":
                    return turn.text[:120]
            return ""

    def is_follow_up(self, text: str) -> bool:
        """Heuristic: a short utterance that references prior context."""
        t = (text or "").strip().lower()
        if not t:
            return False
        follow_markers = ("and", "the second", "next", "that one", "this one", "again", "what about", "so then")
        short = len(t.split()) <= 6
        return short and any(m in t for m in follow_markers)

    # ------------------------------------------------------------------
    # Clarification
    # ------------------------------------------------------------------

    def request_clarification(self, question: str) -> None:
        with self._lock:
            self._pending_clarification = question

    @property
    def pending_clarification(self) -> Optional[str]:
        with self._lock:
            return self._pending_clarification

    def resolve_clarification(self) -> None:
        with self._lock:
            self._pending_clarification = None

    # ------------------------------------------------------------------
    # Corrections
    # ------------------------------------------------------------------

    def record_correction(self, previous: str, corrected: str) -> None:
        with self._lock:
            self._corrections.append(f"{previous} -> {corrected}")
            self._corrections = self._corrections[-10:]

    @property
    def corrections(self) -> List[str]:
        with self._lock:
            return list(self._corrections)

    def needs_clarification(self, text: str) -> bool:
        """Return True when the utterance is ambiguous enough to ask."""
        t = (text or "").strip().lower()
        if not t:
            return True
        ambiguous = ("it", "that", "this", "them", "do it", "yes", "no", "go ahead")
        return len(t.split()) <= 3 and t in ambiguous

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "turn_count": len(self._turns),
                "last_topic": self.last_topic(),
                "pending_clarification": self._pending_clarification,
                "corrections": len(self._corrections),
                "follow_up_detected": self.is_follow_up(self.last_user_text()),
            }
