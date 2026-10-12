"""Memory Ranking — scores and ranks memories by multiple weighted factors."""

from __future__ import annotations

import enum
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory.memory_manager import MemoryRecord

logger = logging.getLogger("aetheros_memory.ranking")


class ScoringFactor(str, enum.Enum):
    IMPORTANCE = "importance"
    RECENCY = "recency"
    FREQUENCY = "frequency"
    PIN_STATUS = "pin_status"
    PROJECT_RELEVANCE = "project_relevance"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    SOURCE_CREDIBILITY = "source_credibility"
    CATEGORY_MATCH = "category_match"


_DEFAULT_FACTOR_WEIGHTS: Dict[ScoringFactor, float] = {
    ScoringFactor.IMPORTANCE: 1.0,
    ScoringFactor.RECENCY: 1.0,
    ScoringFactor.FREQUENCY: 0.5,
    ScoringFactor.PIN_STATUS: 2.0,
    ScoringFactor.PROJECT_RELEVANCE: 1.5,
    ScoringFactor.SEMANTIC_SIMILARITY: 2.0,
    ScoringFactor.SOURCE_CREDIBILITY: 0.3,
    ScoringFactor.CATEGORY_MATCH: 0.8,
}


@dataclass
class RankingConfig:
    factor_weights: Dict[ScoringFactor, float] = field(default_factory=lambda: dict(_DEFAULT_FACTOR_WEIGHTS))
    recency_decay_hours: float = 24.0
    frequency_boost_cap: int = 100
    importance_weight: float = 1.0
    recency_weight: float = 1.0
    frequency_weight: float = 0.5
    pin_weight: float = 2.0
    relevance_weight: float = 1.5
    semantic_weight: float = 2.0

    def __post_init__(self) -> None:
        if not self.factor_weights:
            self.factor_weights = dict(_DEFAULT_FACTOR_WEIGHTS)
        self.factor_weights[ScoringFactor.IMPORTANCE] = self.importance_weight
        self.factor_weights[ScoringFactor.RECENCY] = self.recency_weight
        self.factor_weights[ScoringFactor.FREQUENCY] = self.frequency_weight
        self.factor_weights[ScoringFactor.PIN_STATUS] = self.pin_weight
        self.factor_weights[ScoringFactor.PROJECT_RELEVANCE] = self.relevance_weight
        self.factor_weights[ScoringFactor.SEMANTIC_SIMILARITY] = self.semantic_weight


@dataclass
class RankedMemory:
    record: MemoryRecord
    score: float = 0.0
    factor_scores: Dict[ScoringFactor, float] = field(default_factory=dict)
    rank: int = 0


class MemoryRanking:
    def __init__(self, config: Optional[RankingConfig] = None) -> None:
        self._config = config or RankingConfig()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rank_memories(
        self,
        records: List[MemoryRecord],
        query: str = "",
        workspace_id: str = "",
        project_id: str = "",
    ) -> List[RankedMemory]:
        if not records:
            return []
        with self._lock:
            ranked: List[RankedMemory] = []
            for record in records:
                rm = self.compute_score(record, query, workspace_id, project_id)
                ranked.append(rm)
            ranked.sort(key=lambda x: x.score, reverse=True)
            for i, rm in enumerate(ranked):
                rm.rank = i + 1
            return ranked

    def rank_semantically(
        self,
        records: List[MemoryRecord],
        query_vector: List[float],
    ) -> List[RankedMemory]:
        if not records or not query_vector:
            return []
        with self._lock:
            ranked: List[RankedMemory] = []
            for record in records:
                semantic = self.compute_semantic_score(record, query_vector)
                factor_scores: Dict[ScoringFactor, float] = {
                    ScoringFactor.SEMANTIC_SIMILARITY: semantic,
                }
                total = semantic * self.factor_weight(ScoringFactor.SEMANTIC_SIMILARITY)
                ranked.append(RankedMemory(
                    record=record,
                    score=total,
                    factor_scores=factor_scores,
                ))
            ranked.sort(key=lambda x: x.score, reverse=True)
            for i, rm in enumerate(ranked):
                rm.rank = i + 1
            return ranked

    def compute_score(
        self,
        record: MemoryRecord,
        query: str = "",
        workspace_id: str = "",
        project_id: str = "",
    ) -> RankedMemory:
        importance = self.compute_importance_score(record)
        recency = self.compute_recency_score(record)
        frequency = self.compute_frequency_score(record)
        pin = 1.0 if record.pinned else 0.0
        relevance = self.compute_relevance_score(record, query) if query else 0.0
        project_relevance = 1.0 if project_id and record.project_id == project_id else 0.0
        category_match = 1.0 if workspace_id and record.workspace_id == workspace_id else 0.0
        source_credibility = record.importance * 0.5

        factor_scores: Dict[ScoringFactor, float] = {
            ScoringFactor.IMPORTANCE: importance,
            ScoringFactor.RECENCY: recency,
            ScoringFactor.FREQUENCY: frequency,
            ScoringFactor.PIN_STATUS: pin,
            ScoringFactor.PROJECT_RELEVANCE: project_relevance,
            ScoringFactor.SEMANTIC_SIMILARITY: 0.0,
            ScoringFactor.SOURCE_CREDIBILITY: source_credibility,
            ScoringFactor.CATEGORY_MATCH: category_match,
        }

        total = (
            importance * self.factor_weight(ScoringFactor.IMPORTANCE)
            + recency * self.factor_weight(ScoringFactor.RECENCY)
            + frequency * self.factor_weight(ScoringFactor.FREQUENCY)
            + pin * self.factor_weight(ScoringFactor.PIN_STATUS)
            + relevance * self.factor_weight(ScoringFactor.PROJECT_RELEVANCE)
            + project_relevance * self.factor_weight(ScoringFactor.PROJECT_RELEVANCE)
            + category_match * self.factor_weight(ScoringFactor.CATEGORY_MATCH)
            + source_credibility * self.factor_weight(ScoringFactor.SOURCE_CREDIBILITY)
        )

        return RankedMemory(record=record, score=total, factor_scores=factor_scores)

    # ------------------------------------------------------------------
    # Per-factor scoring
    # ------------------------------------------------------------------

    def compute_recency_score(self, record: MemoryRecord) -> float:
        elapsed = time.time() - record.accessed_at
        decay_hours = self._config.recency_decay_hours
        if decay_hours <= 0:
            return 1.0
        return math.exp(-elapsed / (decay_hours * 3600.0))

    def compute_frequency_score(self, record: MemoryRecord) -> float:
        cap = max(self._config.frequency_boost_cap, 1)
        return min(record.access_count / cap, 1.0)

    def compute_importance_score(self, record: MemoryRecord) -> float:
        return max(min(record.importance, 10.0), 0.0) / 10.0

    def compute_relevance_score(self, record: MemoryRecord, query: str) -> float:
        if not query:
            return 0.0
        q = query.lower()
        score = 0.0
        if q in record.content.lower():
            score += 0.5
        if q in record.key.lower():
            score += 0.3
        if q in record.summary.lower():
            score += 0.2
        for tag in record.tags:
            if q in tag.lower():
                score += 0.1
        return min(score, 1.0)

    def compute_semantic_score(
        self,
        record: MemoryRecord,
        query_vector: List[float],
    ) -> float:
        if not record.embedding or not query_vector:
            return 0.0
        if len(record.embedding) != len(query_vector):
            return 0.0
        dot = sum(a * b for a, b in zip(record.embedding, query_vector))
        norm_a = math.sqrt(sum(a * a for a in record.embedding))
        norm_b = math.sqrt(sum(b * b for b in query_vector))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return max(dot / (norm_a * norm_b), 0.0)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def factor_weight(self, factor: ScoringFactor) -> float:
        return self._config.factor_weights.get(factor, 1.0)

    def configure(self, weights: Dict[ScoringFactor, float]) -> None:
        with self._lock:
            self._config.factor_weights.update(weights)

    @property
    def config(self) -> RankingConfig:
        return self._config
