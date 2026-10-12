"""
Summarizer — generates summaries from memory content.

Provides text summarization for memory consolidation, conversation
summaries, and context compression. Supports extractive and abstractive
summarization strategies.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Summarizer:
    """Generates summaries from text content.

    Supports extractive summarization (key sentence extraction) by
    default, and can be configured with a custom LLM-based summarizer
    for abstractive summaries.

    Usage:
        summarizer = Summarizer()
        summary = summarizer.summarize(long_text, max_chars=500)
        bullet = summarizer.bullet_points(long_text, max_points=5)
        key = summarizer.key_points(long_text)
    """

    def __init__(self, llm_summarizer: Optional[Callable] = None):
        self._llm_summarizer = llm_summarizer

    # ------------------------------------------------------------------
    # Main summarize
    # ------------------------------------------------------------------

    def summarize(self, text: str, max_chars: int = 500,
                  style: str = "paragraph") -> str:
        """Generate a summary of the text.

        Args:
            text: Text to summarize
            max_chars: Maximum length of the summary
            style: "paragraph", "bullet", "concise"

        Returns:
            Summarized text
        """
        if not text:
            return ""

        if self._llm_summarizer:
            return self._llm_summarize(text, max_chars, style)

        return self._extractive_summarize(text, max_chars)

    def bullet_points(self, text: str, max_points: int = 5) -> List[str]:
        """Extract key bullet points from text."""
        if not text:
            return []

        # Split into sentences
        sentences = self._split_sentences(text)

        # Score sentences by importance
        scored = [(self._score_sentence(s), s) for s in sentences if len(s) > 10]
        scored.sort(key=lambda x: -x[0])

        return [s for _, s in scored[:max_points]]

    def key_points(self, text: str, max_points: int = 3) -> List[str]:
        """Extract the most important points from text."""
        if not text:
            return []

        points = self.bullet_points(text, max_points * 2)
        return points[:max_points]

    def extractive_summarize(self, text: str,
                             max_chars: int = 500) -> str:
        """Extractive summarization — picks the most important sentences."""
        return self._extractive_summarize(text, max_chars)

    def format_memory_context(self, entries: List[Dict[str, Any]],
                              max_chars: int = 2000) -> str:
        """Format multiple memory entries into a readable context block."""
        if not entries:
            return ""

        parts = []
        total = 0
        for entry in entries:
            key = entry.get("key", "?")
            value = str(entry.get("value", ""))
            memory_type = entry.get("memory_type", "memory")

            text = f"[{memory_type}] {key}: {value}"
            if total + len(text) > max_chars:
                remaining = max_chars - total
                if remaining > 50:
                    parts.append(text[:remaining] + "...")
                break

            parts.append(text)
            total += len(text)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _extractive_summarize(self, text: str, max_chars: int) -> str:
        """Extractive summarization using sentence scoring."""
        if len(text) <= max_chars:
            return text

        sentences = self._split_sentences(text)
        if not sentences:
            return text[:max_chars]

        # Score and sort
        scored = [(self._score_sentence(s), s) for s in sentences]
        scored.sort(key=lambda x: -x[0])

        # Build summary
        summary = ""
        for _, sentence in scored:
            if len(summary) + len(sentence) <= max_chars:
                summary += sentence + " "
            else:
                break

        if not summary:
            return text[:max_chars]

        return summary.strip()

    def _llm_summarize(self, text: str, max_chars: int,
                       style: str) -> str:
        """Abstractive summarization using an LLM."""
        if not self._llm_summarizer:
            return self._extractive_summarize(text, max_chars)

        try:
            result = self._llm_summarizer(text, max_chars, style)
            return str(result)[:max_chars]
        except Exception as exc:
            logger.warning("LLM summarization failed: %s", exc)
            return self._extractive_summarize(text, max_chars)

    @staticmethod
    def _score_sentence(sentence: str) -> float:
        """Score a sentence by its likely importance."""
        score = 0.0
        lower = sentence.lower()

        # Length signal (medium sentences are often more informative)
        words = len(sentence.split())
        if 5 <= words <= 30:
            score += 0.3
        elif words > 30:
            score += 0.2
        elif words < 5:
            score -= 0.2

        # Keywords that indicate importance
        important_words = [
            "important", "critical", "key", "significant", "essential",
            "must", "should", "never", "always", "required",
            "conclusion", "summary", "result", "found", "discovered",
            "therefore", "however", "because", "recommend",
            "error", "warning", "failure", "success",
            "TODO", "FIXME", "HACK", "NOTE",
        ]
        for word in important_words:
            if word in lower:
                score += 0.1

        # Position bonus (first sentence of a paragraph)
        if sentence.strip().endswith("."):
            score += 0.1

        return min(score, 1.0)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
