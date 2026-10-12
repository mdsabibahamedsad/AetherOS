"""
Episodic Memory — stores and retrieves experiences and events.

Episodic memory records 'episodes' — sequences of events with temporal
context. Each episode captures what happened, when it happened, the
context, and the outcome. Supports timeline-based retrieval and
experience replay for learning.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.memory_constants import ConfidenceLevel, PrivacyLevel, ProvenanceSource, DEFAULT_CONFIDENCE_LEVEL, DEFAULT_PRIVACY_LEVEL

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    """A recorded episode/experience.

    Attributes:
        id: Unique episode ID
        summary: Brief summary of the episode
        description: Detailed description
        context: The context in which the episode occurred
        action: The action taken
        outcome: The outcome/result
        duration_seconds: How long the episode lasted
        tags: Categorization tags
        importance: Importance score (0.0 - 1.0)
        timestamp: When the episode occurred
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    summary: str = ""
    description: str = ""
    context: str = ""
    action: str = ""
    outcome: str = ""
    duration_seconds: float = 0.0
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodicMemory:
    """Stores experiences as episodes for retrieval and learning.

    Episodes capture temporal sequences with context, action, and outcome.
    Supports timeline queries, similarity search, and importance-based ranking.

    Usage:
        ep = EpisodicMemory(store)
        ep.record(Episode(summary="Fixed auth bug", outcome="success"))
        recent = ep.get_recent(limit=5)
        similar = ep.find_similar("authentication issue")
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"episodic:{id(self)}"
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, episode: Episode) -> MemoryEntry:
    def record(self, episode: Episode) -> MemoryEntry:
        """Record an episode in memory."""
        return self._store.save(
            key=f"episode:{episode.id}",
            value=episode,
            memory_type="episodic",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=episode.tags + ["episode"],
            metadata={
                "summary": episode.summary,
                "outcome": episode.outcome,
                "duration": episode.duration_seconds,
                **episode.metadata,
            },
            importance=episode.importance,
            confidence_level=DEFAULT_CONFIDENCE_LEVEL,
            privacy_level=DEFAULT_PRIVACY_LEVEL,
            provenance_source=ProvenanceSource.EPISODIC,
            provenance_agent="episodic",
            importance_override=None,
        )
    def record_event(self, summary: str, outcome: str = "",
                     context: str = "", action: str = "",
                     importance: float = 0.5,
                     tags: List[str] = None) -> Episode:
        """Convenience method to record an episode with minimal fields."""
        episode = Episode(
            summary=summary,
            outcome=outcome,
            context=context,
            action=action,
            importance=importance,
            tags=tags or [],
        )
        self.record(episode)
        return episode

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by its ID."""
        entry = self._store.get_by_key(
            f"episode:{episode_id}",
            scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        return entry.value if entry else None

    def get_recent(self, limit: int = 20) -> List[Episode]:
        """Get the most recent episodes."""
        entries = self._store.search(
            memory_type="episodic",
            namespace=self._namespace,
            limit=limit,
        )
        episodes = []
        for e in entries:
            if isinstance(e.value, Episode):
                episodes.append(e.value)
        return episodes

    def get_timeline(self, start_time: float = 0.0,
                     end_time: Optional[float] = None,
                     limit: int = 50) -> List[Episode]:
        """Get episodes within a time range, ordered chronologically."""
        end_time = end_time or time.time()
        entries = self._store.search(
            memory_type="episodic",
            namespace=self._namespace,
            limit=100,
        )
        episodes = []
        for e in entries:
            ep = e.value
            if isinstance(ep, Episode) and start_time <= ep.timestamp <= end_time:
                episodes.append(ep)
        episodes.sort(key=lambda ep: ep.timestamp, reverse=True)
        return episodes[:limit]

    def find_similar(self, query: str, limit: int = 10) -> List[Episode]:
        """Find episodes with similar descriptions."""
        entries = self._store.search(
            query=query,
            memory_type="episodic",
            namespace=self._namespace,
            limit=limit,
        )
        return [e.value for e in entries if isinstance(e.value, Episode)]

    def search_by_outcome(self, outcome: str,
                          limit: int = 20) -> List[Episode]:
        """Find episodes by outcome (success, failure, etc.)."""
        entries = self._store.search(
            memory_type="episodic",
            namespace=self._namespace,
            limit=100,
        )
        outcome_lower = outcome.lower()
        episodes = []
        for e in entries:
            ep = e.value
            if isinstance(ep, Episode) and outcome_lower in ep.outcome.lower():
                episodes.append(ep)
        return episodes[:limit]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        """Clear all episodic memories. Returns count removed."""
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        """Count recorded episodes."""
        return self._store.count(namespace=self._namespace)

    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        episodes = self.get_recent(limit=10000)
        successes = sum(1 for e in episodes if "success" in e.outcome.lower())
        failures = sum(1 for e in episodes if "fail" in e.outcome.lower())
        return {
            "total_episodes": len(episodes),
            "successes": successes,
            "failures": failures,
            "avg_importance": (
                sum(e.importance for e in episodes) / len(episodes)
                if episodes else 0.0
            ),
        }
