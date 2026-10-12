"""Multimodal Memory Consolidation & Pruning (Phase 57).

Advanced memory management with:
- Automatic consolidation of similar memories
- Intelligent pruning based on relevance/access patterns
- Memory compression with semantic preservation
- Long-term vs short-term memory separation
- Importance scoring and decay functions
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

import numpy as np

from agent.multimodal.memory import MultimodalMemoryStore, MultimodalMemoryEntry
from agent.multimodal.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    """Memory storage tiers."""
    HOT = "hot"           # Frequently accessed, high priority
    WARM = "warm"         # Occasionally accessed
    COLD = "cold"         # Rarely accessed, compressed
    ARCHIVE = "archive"   # Long-term storage


class ConsolidationStrategy(Enum):
    """Memory consolidation strategies."""
    SIMILARITY_MERGE = "similarity_merge"      # Merge similar memories
    TEMPORAL_CLUSTER = "temporal_cluster"      # Group by time
    TOPIC_CLUSTER = "topic_cluster"            # Group by topic
    IMPORTANCE_BASED = "importance_based"      # Keep important, merge others
    SEMANTIC_DEDUP = "semantic_dedup"          # Remove semantic duplicates


@dataclass
class MemoryImportance:
    """Importance scoring for memory entries."""
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    relevance_score: float = 0.5
    user_rating: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    tier: MemoryTier = MemoryTier.WARM

    def compute_importance(self, current_time: Optional[float] = None) -> float:
        """Compute overall importance score (0-1)."""
        now = current_time or time.time()
        age_hours = (now - self.creation_time) / 3600
        recency_hours = (now - self.last_access) / 3600

        # Recency factor (exponential decay)
        recency_factor = np.exp(-recency_hours / 168)  # Half-life ~1 week

        # Access frequency factor (logarithmic)
        frequency_factor = np.log1p(self.access_count) / np.log1p(100)

        # Explicit rating factor
        rating_factor = self.user_rating if self.user_rating is not None else 0.5

        # Tier bonus
        tier_bonus = {
            MemoryTier.HOT: 0.3,
            MemoryTier.WARM: 0.1,
            MemoryTier.COLD: -0.1,
            MemoryTier.ARCHIVE: -0.2,
        }.get(self.tier, 0.0)

        score = (
            0.3 * recency_factor +
            0.2 * frequency_factor +
            0.2 * rating_factor +
            0.1 * self.relevance_score +
            0.2 * (0.5 + tier_bonus)
        )
        return max(0.0, min(1.0, score))


@dataclass
class ConsolidationResult:
    """Result of consolidation operation."""
    merged_count: int
    pruned_count: int
    compressed_bytes: int
    new_entries: int
    strategy_used: str
    duration_ms: float


class MemoryConsolidator:
    """Advanced memory consolidation and pruning (Phase 57)."""

    def __init__(
        self,
        store: "MultimodalMemoryStore",
        tracker: Optional[Any] = None,
        similarity_threshold: float = 0.85,
        max_memory_entries: int = 10000,
        consolidation_interval_hours: int = 6,
    ):
        self.store = store
        self.tracker = tracker
        self.similarity_threshold = similarity_threshold
        self.max_memory_entries = max_memory_entries
        self.consolidation_interval = consolidation_interval_hours * 3600
        self._importance_scores: Dict[str, MemoryImportance] = {}
        self._last_consolidation = time.time()
        self._lock = threading.Lock()
        self._consolidation_thread: Optional[threading.Thread] = None
        self._running = False

    def start_background_consolidation(self) -> None:
        """Start background consolidation thread."""
        if self._running:
            return
        self._running = True
        self._consolidation_thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self._consolidation_thread.start()

    def stop_background_consolidation(self) -> None:
        self._running = False
        if self._consolidation_thread:
            self._consolidation_thread.join(timeout=5.0)

    def _consolidation_loop(self) -> None:
        while self._running:
            time.sleep(60)  # Check every minute
            if time.time() - self._last_consolidation >= self.consolidation_interval:
                self.consolidate()

    def update_access(self, entry_id: str, increment: bool = True) -> None:
        """Update access statistics for an entry."""
        with self._lock:
            if entry_id not in self._importance_scores:
                self._importance_scores[entry_id] = MemoryImportance()
            imp = self._importance_scores[entry_id]
            imp.last_access = time.time()
            if increment:
                imp.access_count += 1

    def set_rating(self, entry_id: str, rating: float) -> None:
        """Set explicit user rating for an entry (0-1)."""
        with self._lock:
            if entry_id not in self._importance_scores:
                self._importance_scores[entry_id] = MemoryImportance()
            self._importance_scores[entry_id].user_rating = max(0.0, min(1.0, rating))

    def set_tier(self, entry_id: str, tier: MemoryTier) -> None:
        """Set memory tier for an entry."""
        with self._lock:
            if entry_id not in self._importance_scores:
                self._importance_scores[entry_id] = MemoryImportance()
            self._importance_scores[entry_id].tier = tier

    def add_tags(self, entry_id: str, tags: Set[str]) -> None:
        """Add tags to an entry."""
        with self._lock:
            if entry_id not in self._importance_scores:
                self._importance_scores[entry_id] = MemoryImportance()
            self._importance_scores[entry_id].tags.update(tags)

    def consolidate(
        self,
        strategy: ConsolidationStrategy = ConsolidationStrategy.SIMILARITY_MERGE,
        dry_run: bool = False,
    ) -> ConsolidationResult:
        """Run memory consolidation."""
        start = time.time()
        with self._lock:
            # Get all entries
            entries = self.store._entries  # Access internal list

            if not entries:
                return ConsolidationResult(0, 0, 0, 0, strategy.value, 0)

            # Update importance scores
            self._update_importance_scores()

            # Apply consolidation strategy
            if strategy == ConsolidationStrategy.SIMILARITY_MERGE:
                merged, pruned = self._merge_similar()
            elif strategy == ConsolidationStrategy.TEMPORAL_CLUSTER:
                merged, pruned = self._cluster_temporal()
            elif strategy == ConsolidationStrategy.TOPIC_CLUSTER:
                merged, pruned = self._cluster_by_topic()
            elif strategy == ConsolidationStrategy.IMPORTANCE_BASED:
                merged, pruned = self._prune_by_importance()
            elif strategy == ConsolidationStrategy.SEMANTIC_DEDUP:
                merged, pruned = self._semantic_dedup()
            else:
                merged, pruned = 0, 0

            # Enforce max entries limit
            pruned += self._enforce_max_entries()

            # Update tier assignments
            self._reassign_tiers()

            duration_ms = (time.time() - start) * 1000
            self._last_consolidation = time.time()

            return ConsolidationResult(
                merged_count=merged,
                pruned_count=pruned,
                compressed_bytes=0,  # Would calculate actual savings
                new_entries=0,
                strategy_used=strategy.value,
                duration_ms=duration_ms,
            )

    def _update_importance_scores(self) -> None:
        """Recalculate importance scores for all entries."""
        for entry in self.store._entries:
            if entry.entry_id not in self._importance_scores:
                self._importance_scores[entry.entry_id] = MemoryImportance(
                    creation_time=entry.timestamp,
                )
            imp = self._importance_scores[entry.entry_id]
            imp.relevance_score = self._compute_relevance(entry)

    def _compute_relevance(self, entry: MultimodalMemoryEntry) -> float:
        """Compute relevance score based on content and metadata."""
        # Base relevance on content length and metadata
        content_len = len(entry.content)
        length_score = min(1.0, content_len / 10000)

        # Tag relevance
        tag_score = min(1.0, len(self._importance_scores.get(entry.entry_id, MemoryImportance()).tags) / 10)

        return (length_score + tag_score) / 2

    def _merge_similar(self) -> Tuple[int, int]:
        """Merge semantically similar entries."""
        merged = 0
        pruned = 0
        entries = self.store._entries
        processed = set()

        for i, entry_a in enumerate(entries):
            if entry_a.entry_id in processed:
                continue

            for entry_b in entries[i+1:]:
                if entry_b.entry_id in processed:
                    continue

                similarity = self._compute_similarity(entry_a, entry_b)
                if similarity >= self.similarity_threshold:
                    # Merge b into a
                    merged_entry = self._merge_entries(entry_a, entry_b)
                    # Replace a with merged
                    idx_a = self.store._entries.index(entry_a)
                    self.store._entries[idx_a] = merged_entry
                    # Remove b
                    self.store._entries.remove(entry_b)
                    processed.add(entry_b.entry_id)
                    merged += 1
                    pruned += 1

            processed.add(entry_a.entry_id)

        return merged, pruned

    def _compute_similarity(self, a: MultimodalMemoryEntry, b: MultimodalMemoryEntry) -> float:
        """Compute semantic similarity between two entries."""
        # Text similarity (Jaccard on words)
        words_a = set(a.content.lower().split())
        words_b = set(b.content.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        text_sim = intersection / union if union > 0 else 0

        # Tag similarity
        tags_a = set(self._importance_scores.get(a.entry_id, MemoryImportance()).tags)
        tags_b = set(self._importance_scores.get(b.entry_id, MemoryImportance()).tags)
        tag_sim = len(tags_a & tags_b) / len(tags_a | tags_b) if tags_a or tags_b else 0

        # Type similarity
        type_sim = 1.0 if a.kind == b.kind else 0.5

        return 0.5 * text_sim + 0.3 * tag_sim + 0.2 * type_sim

    def _merge_entries(self, a: MultimodalMemoryEntry, b: MultimodalMemoryEntry) -> "MultimodalMemoryEntry":
        """Merge two entries into one."""
        from agent.multimodal.memory import MultimodalMemoryEntry
        merged_content = a.content + "\n\n[MERGED]\n\n" + b.content
        merged_tags = set(self._importance_scores.get(a.entry_id, MemoryImportance()).tags) | \
                      set(self._importance_scores.get(b.entry_id, MemoryImportance()).tags)

        merged = MultimodalMemoryEntry(
            entry_id=a.entry_id,  # Keep a's ID
            kind=a.kind,
            content=merged_content,
            media_id=a.media_id or b.media_id,
            source=a.source,
            mime_type=a.mime_type,
            timestamp=a.timestamp,
            sensitivity=a.sensitivity,
            tags=list(set(a.tags + b.tags)),
            metadata={**a.metadata, **b.metadata, "merged_from": [a.entry_id, b.entry_id]},
        )
        # Merge importance
        imp_a = self._importance_scores.get(a.entry_id, MemoryImportance())
        imp_b = self._importance_scores.get(b.entry_id, MemoryImportance())
        self._importance_scores[a.entry_id] = MemoryImportance(
            access_count=imp_a.access_count + imp_b.access_count,
            last_access=max(imp_a.last_access, imp_b.last_access),
            creation_time=min(imp_a.creation_time, imp_b.creation_time),
            relevance_score=max(imp_a.relevance_score, imp_b.relevance_score),
            user_rating=max(imp_a.user_rating or 0, imp_b.user_rating or 0),
            tags=merged_tags,
            tier=max(imp_a.tier, imp_b.tier, key=lambda t: t.value),
        )
        # Remove b's importance
        if b.entry_id in self._importance_scores:
            del self._importance_scores[b.entry_id]
        return merged

    def _cluster_temporal(self) -> Tuple[int, int]:
        """Cluster entries by time and merge within time windows."""
        # Group by day
        from collections import defaultdict
        daily = defaultdict(list)
        for entry in self.store._entries:
            day = datetime.fromtimestamp(entry.timestamp).date()
            daily[day].append(entry)

        merged = 0
        pruned = 0
        for day, entries in daily.items():
            if len(entries) > 5:  # Many entries in one day
                # Merge into daily summary
                summary_content = f"Daily summary for {day}:\n"
                for e in entries:
                    summary_content += f"- {e.content[:200]}\n"

                from agent.multimodal.memory import MultimodalMemoryEntry
                summary = MultimodalMemoryEntry(
                    entry_id=str(uuid.uuid4()),
                    kind="summary",
                    content=summary_content,
                    media_id="",
                    source=f"daily_summary_{day}",
                    mime_type="text/plain",
                    timestamp=time.time(),
                    sensitivity="private",
                    tags=["daily_summary", str(day)],
                    metadata={"original_count": len(entries), "date": str(day)},
                )
                self.store._entries.append(summary)
                # Remove originals
                for e in entries:
                    self.store._entries.remove(e)
                merged += 1
                pruned += len(entries) - 1

        return merged, pruned

    def _cluster_by_topic(self) -> Tuple[int, int]:
        """Cluster by topic/tags and merge."""
        # Group by primary tag
        tag_groups = defaultdict(list)
        for entry in self.store._entries:
            tags = self._importance_scores.get(entry.entry_id, MemoryImportance()).tags
            if tags:
                primary = sorted(tags)[0]
                tag_groups[primary].append(entry)

        merged = 0
        pruned = 0
        for tag, entries in tag_groups.items():
            if len(entries) > 3:
                # Create topic summary
                summary_content = f"Topic: {tag}\n"
                for e in entries:
                    summary_content += f"- {e.content[:200]}\n"

                from agent.multimodal.memory import MultimodalMemoryEntry
                summary = MultimodalMemoryEntry(
                    entry_id=str(uuid.uuid4()),
                    kind="topic_summary",
                    content=summary_content,
                    media_id="",
                    source=f"topic_{tag}",
                    mime_type="text/plain",
                    timestamp=time.time(),
                    sensitivity="private",
                    tags=[tag, "topic_summary"],
                    metadata={"original_count": len(entries), "topic": tag},
                )
                self.store._entries.append(summary)
                for e in entries:
                    self.store._entries.remove(e)
                merged += 1
                pruned += len(entries) - 1

        return merged, pruned

    def _prune_by_importance(self) -> Tuple[int, int]:
        """Prune least important entries."""
        # Score all entries
        scored = []
        for entry in self.store._entries:
            imp = self._importance_scores.get(entry.entry_id, MemoryImportance())
            score = imp.compute_importance()
            scored.append((score, entry))

        # Sort by importance (ascending - least important first)
        scored.sort(key=lambda x: x[0])

        # Prune bottom 10% if over capacity
        target_prune = max(1, len(scored) // 10)
        pruned = 0
        for i in range(min(target_prune, len(scored))):
            entry = scored[i][1]
            self.store._entries.remove(entry)
            if entry.entry_id in self._importance_scores:
                del self._importance_scores[entry.entry_id]
            pruned += 1

        return 0, pruned

    def _semantic_dedup(self) -> Tuple[int, int]:
        """Remove semantic duplicates."""
        # More aggressive similarity threshold
        original_threshold = self.similarity_threshold
        self.similarity_threshold = 0.95
        merged, pruned = self._merge_similar()
        self.similarity_threshold = original_threshold
        return merged, pruned

    def _enforce_max_entries(self) -> int:
        """Enforce maximum entry limit by pruning least important."""
        if len(self.store._entries) <= self.max_memory_entries:
            return 0

        # Score and prune
        scored = []
        for entry in self.store._entries:
            imp = self._importance_scores.get(entry.entry_id, MemoryImportance())
            score = imp.compute_importance()
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0])
        to_prune = len(scored) - self.max_memory_entries
        pruned = 0
        for i in range(min(to_prune, len(scored))):
            entry = scored[i][1]
            self.store._entries.remove(entry)
            if entry.entry_id in self._importance_scores:
                del self._importance_scores[entry.entry_id]
            pruned += 1

        return pruned

    def _reassign_tiers(self) -> None:
        """Reassign memory tiers based on importance."""
        scored = []
        for entry in self.store._entries:
            imp = self._importance_scores.get(entry.entry_id, MemoryImportance())
            score = imp.compute_importance()
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        total = len(scored)
        hot_cutoff = int(total * 0.1)
        warm_cutoff = int(total * 0.4)
        cold_cutoff = int(total * 0.8)

        for i, (_, entry) in enumerate(scored):
            imp = self._importance_scores.get(entry.entry_id)
            if imp:
                if i < hot_cutoff:
                    imp.tier = MemoryTier.HOT
                elif i < warm_cutoff:
                    imp.tier = MemoryTier.WARM
                elif i < cold_cutoff:
                    imp.tier = MemoryTier.COLD
                else:
                    imp.tier = MemoryTier.ARCHIVE

    def get_stats(self) -> Dict[str, Any]:
        """Get consolidation statistics."""
        with self._lock:
            tiers = defaultdict(int)
            for imp in self._importance_scores.values():
                tiers[imp.tier.value] += 1

            total_importance = sum(imp.compute_importance() for imp in self._importance_scores.values())
            avg_importance = total_importance / len(self._importance_scores) if self._importance_scores else 0

            return {
                "total_entries": len(self.store._entries),
                "tracked_entries": len(self._importance_scores),
                "tiers": dict(tiers),
                "avg_importance": avg_importance,
                "last_consolidation": self._last_consolidation,
                "next_consolidation_in": max(0, self.consolidation_interval - (time.time() - self._last_consolidation)),
            }

    def export_importance(self) -> Dict[str, Dict]:
        """Export importance scores for backup."""
        with self._lock:
            return {
                eid: {
                    "access_count": imp.access_count,
                    "last_access": imp.last_access,
                    "creation_time": imp.creation_time,
                    "relevance_score": imp.relevance_score,
                    "user_rating": imp.user_rating,
                    "tags": list(imp.tags),
                    "tier": imp.tier.value,
                }
                for eid, imp in self._importance_scores.items()
            }

    def import_importance(self, data: Dict[str, Dict]) -> None:
        """Import importance scores from backup."""
        with self._lock:
            for eid, imp_data in data.items():
                self._importance_scores[eid] = MemoryImportance(
                    access_count=imp_data.get("access_count", 0),
                    last_access=imp_data.get("last_access", time.time()),
                    creation_time=imp_data.get("creation_time", time.time()),
                    relevance_score=imp_data.get("relevance_score", 0.5),
                    user_rating=imp_data.get("user_rating"),
                    tags=set(imp_data.get("tags", [])),
                    tier=MemoryTier(imp_data.get("tier", "warm")),
                )


def create_consolidator(
    store: "MultimodalMemoryStore",
    similarity_threshold: float = 0.85,
    max_entries: int = 10000,
) -> MemoryConsolidator:
    """Factory for creating a memory consolidator."""
    return MemoryConsolidator(
        store=store,
        similarity_threshold=similarity_threshold,
        max_memory_entries=max_entries,
    )