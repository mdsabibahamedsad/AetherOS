"""
Ranking Engine — scores and ranks memory entries by relevance.

Provides configurable ranking strategies for memory retrieval results.
Supports importance-based, recency-based, frequency-based, and
hybrid scoring that combines multiple signals.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryEntry

logger = logging.getLogger(__name__)


class RankingEngine:
    """Configurable ranking engine for memory entries.

    Combines multiple signals (importance, recency, frequency, context)
    into a unified relevance score.

    Usage:
        ranker = RankingEngine()
        ranked = ranker.rank(entries, query="deployment")
        ranked = ranker.rank_weighted(entries, weights={
            "importance": 2.0, "recency": 1.0, "frequency": 0.5,
        })
    """

    def __init__(self):
        self._default_weights = {
            "importance": 1.5,
            "recency": 1.0,
            "frequency": 0.5,
            "tag_match": 0.8,
        }

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def rank(self, entries: List[MemoryEntry],
             query: str = "",
             weights: Dict[str, float] = None) -> List[MemoryEntry]:
        """Rank entries by relevance, returning scored entries.

        Args:
            entries: Memory entries to rank
            query: Optional query for context matching
            weights: Optional weight overrides

        Returns:
            Entries sorted by relevance (descending)
        """
        w = {**self._default_weights, **(weights or {})}
        scored = [(self._compute_score(e, query, w), e) for e in entries]
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored]

    def rank_with_scores(self, entries: List[MemoryEntry],
                         query: str = "",
                         weights: Dict[str, float] = None) -> List[tuple]:
        """Rank entries and return (score, entry) tuples."""
        w = {**self._default_weights, **(weights or {})}
        scored = [(self._compute_score(e, query, w), e) for e in entries]
        scored.sort(key=lambda x: -x[0])
        return scored

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _compute_score(self, entry: MemoryEntry, query: str,
                       weights: Dict[str, float]) -> float:
        """Compute a combined relevance score for an entry."""
        score = 0.0

        # Importance signal
        score += entry.importance * weights.get("importance", 1.0)

        # Recency signal (decays over 30 days)
        age_hours = (time.time() - entry.created_at) / 3600
        recency = max(0, 1.0 - age_hours / 720.0)
        score += recency * weights.get("recency", 1.0)

        # Frequency signal (from metadata)
        mention_count = entry.metadata.get("mention_count", 1)
        frequency = min(mention_count / 10.0, 1.0)  # Cap at 10 mentions
        score += frequency * weights.get("frequency", 0.5)

        # Tag match signal
        if query:
            query_lower = query.lower()
            tag_matches = sum(
                1 for tag in entry.tags if query_lower in tag.lower()
            )
            if tag_matches > 0:
                score += (tag_matches / len(entry.tags)) * weights.get("tag_match", 0.8)

        return score

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def boost_important(self, entries: List[MemoryEntry],
                        min_importance: float = 0.8) -> List[MemoryEntry]:
        """Boost important entries to the top."""
        important = [e for e in entries if e.importance >= min_importance]
        normal = [e for e in entries if e.importance < min_importance]
        return important + normal

    def boost_recent(self, entries: List[MemoryEntry],
                     hours: float = 24) -> List[MemoryEntry]:
        """Boost entries from the last N hours to the top."""
        cutoff = time.time() - (hours * 3600)
        recent = [e for e in entries if e.created_at >= cutoff]
        older = [e for e in entries if e.created_at < cutoff]
        return recent + older

    def filter_by_threshold(self, entries: List[MemoryEntry],
                            min_score: float = 0.3,
                            query: str = "") -> List[MemoryEntry]:
        """Filter entries below a minimum score threshold."""
        return [
            e for e in entries
            if self._compute_score(e, query, self._default_weights) >= min_score
        ]

    def get_config(self) -> Dict[str, Any]:
        """Return current ranking configuration."""
        return {
            "default_weights": dict(self._default_weights),
        }
