"""Jarvis Mode — emotion & tone adaptation.

Selects a response tone based on task type, conversation style, and user
preferences. The engine explicitly does NOT pretend to have emotions — it
selects an appropriate professional register from the allowed set. All output
stays factual and professional.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from aetheros_jarvis.models import VoiceTone

logger = logging.getLogger(__name__)

_TASK_TONE: Dict[str, VoiceTone] = {
    "error": VoiceTone.EMPATHETIC,
    "warning": VoiceTone.URGENT,
    "progress": VoiceTone.ENCOURAGING,
    "summary": VoiceTone.CONCISE,
    "greeting": VoiceTone.FRIENDLY,
    "confirmation": VoiceTone.CONCISE,
    "question": VoiceTone.PROFESSIONAL,
}

_ALLOWED = {tone.value for tone in VoiceTone}


class ToneEngine:
    """Deterministic tone selection — no simulated emotion.

    Usage::

        engine = ToneEngine()
        tone = engine.for_task("progress", style="friendly", prefs={"tone": "concise"})
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._user_tone: Optional[VoiceTone] = None
        self._default_tone = VoiceTone.PROFESSIONAL

    def set_user_tone(self, tone: Optional[VoiceTone]) -> None:
        with self._lock:
            self._user_tone = tone

    def set_default_tone(self, tone: VoiceTone) -> None:
        with self._lock:
            self._default_tone = tone

    def for_task(self, task_type: str = "general", style: str = "professional", prefs: Optional[Dict[str, Any]] = None) -> VoiceTone:
        """Pick the tone for a task.

        Resolution order: user preference > task-type mapping > style hint >
        default. The result is always one of the allowed professional tones.
        """
        if prefs and prefs.get("tone") in _ALLOWED:
            return VoiceTone(prefs["tone"])

        with self._lock:
            if self._user_tone is not None:
                return self._user_tone

        mapped = _TASK_TONE.get(task_type)
        if mapped is not None:
            return mapped

        style = (style or "professional").lower()
        if style in _ALLOWED:
            return VoiceTone(style)
        return self._default_tone

    def render(self, text: str, tone: VoiceTone, *, force_professional: bool = True) -> str:
        """Apply tone-appropriate framing without inventing emotion.

        Keeps the payload intact; only the framing marker is added, and it is
        stripped for professional/concise tones.
        """
        text = (text or "").strip()
        if not text:
            return text
        if force_professional and tone in (VoiceTone.PROFESSIONAL, VoiceTone.CONCISE):
            return text
        prefixes = {
            VoiceTone.FRIENDLY: "Sure thing: ",
            VoiceTone.ENCOURAGING: "You're making progress: ",
            VoiceTone.URGENT: "Heads up: ",
            VoiceTone.EMPATHETIC: "Understood. ",
        }
        return prefixes.get(tone, "") + text

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "default_tone": self._default_tone.value,
                "user_tone": self._user_tone.value if self._user_tone else None,
            }
