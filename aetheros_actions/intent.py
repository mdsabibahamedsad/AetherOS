"""Original-intent drift check (Step 95).

Checks whether a proposed plan still serves the user's stated goal, or has
drifted into unrelated territory. Pure + injectable: keyword extraction is a
simple tokenizer by default and can be swapped for an embedding/LLM-based
extractor. Drift alone never blocks execution in the default configuration —
the manager surfaces it as a warning (``block_on_intent_drift`` opt-in makes
it a hard stop for destructive steps).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set

from aetheros_actions.model import Action, ActionType, RiskLevel

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "for", "of", "on", "in", "to",
    "with", "please", "can", "you", "me", "my", "i", "is", "are", "do",
    "does", "be", "it", "this", "that", "at", "by", "from", "as", "into",
    "then", "now", "please", "want", "need", "help",
})

# Destructive action kinds where drift matters most.
_DRIFT_SENSITIVE = frozenset({
    ActionType.CLOSE, ActionType.APP_CLOSE, ActionType.UPLOAD,
    ActionType.DOWNLOAD, ActionType.FILE_SAVE, ActionType.NAVIGATE,
    ActionType.APP_LAUNCH,
})


def default_extract_tokens(text: str) -> Set[str]:
    """Lowercase, non-stopword tokens from ``text`` (pure, no deps)."""
    words = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
    return {w for w in words if w and w not in _STOPWORDS}


@dataclass
class IntentCheck:
    """Result of comparing a goal against a plan."""

    goal: str
    drifted: bool = False
    confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "drifted": self.drifted,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


class IntentVerifier:
    """Detects when plan actions stop serving the stated goal."""

    def __init__(
        self,
        *,
        extractor: Callable[[str], Set[str]] = default_extract_tokens,
        min_similarity: float = 0.0,
        drift_threshold: float = 0.5,
    ) -> None:
        self._extract = extractor
        self.min_similarity = min_similarity
        self.drift_threshold = drift_threshold

    def check(self, goal: str, actions: List[Action]) -> IntentCheck:
        """Return drift info comparing ``goal`` against ``actions``."""
        goal_tokens = self._extract(goal)
        if not goal_tokens:
            # No goal signal to compare against — cannot assert drift.
            return IntentCheck(goal=goal, drifted=False, confidence=0.0,
                               reasons=["goal has no extractable tokens"])

        unmatched: List[Action] = []
        for action in actions:
            haystack = self._extract(f"{action.target} {action.reason}")
            # Non-destructive navigation that shares a token is fine; a
            # destructive action with zero goal-token overlap is suspicious.
            if not (goal_tokens & haystack):
                if action.action_type in _DRIFT_SENSITIVE:
                    unmatched.append(action)
                elif action.risk_level >= RiskLevel.HIGH and not haystack:
                    unmatched.append(action)

        if not unmatched:
            return IntentCheck(goal=goal, drifted=False, confidence=0.0)

        overlap = len(unmatched) / max(1, len(actions))
        drifted = overlap >= self.drift_threshold
        reasons = [
            f"step targeting {a.target!r} shares no terms with the goal"
            for a in unmatched[:5]
        ]
        return IntentCheck(goal=goal, drifted=drifted,
                           confidence=min(1.0, overlap),
                           reasons=reasons)