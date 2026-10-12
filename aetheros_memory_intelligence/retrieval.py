"""Secure retrieval for the memory fabric.

Retrieval is the flip side of the write pipeline: entries are filtered by
boundary authorization, grounded by trust/confidence, and never returned as
instructions.  A ``RetrievalResult`` carries the evidence (the entry + its
provenance) alongside the text so consumers can cite sources rather than
blindly trusting content.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.boundaries import AccessContext, MemoryBoundaries
from aetheros_memory_intelligence.provenance import ProvenanceRecord
from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.store import MemoryStore
from aetheros_memory_intelligence.trust import TrustModel
from aetheros_memory_intelligence.types import MemoryState


@dataclass
class RetrievedMemory:
    entry: MemoryEntry
    score: float = 0.0
    trust: float = 0.0
    confidence: float = 0.0
    provenance: Optional[ProvenanceRecord] = None

    @property
    def id(self) -> str:
        return self.entry.id

    @property
    def text(self) -> str:
        return self.entry.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.entry.id,
            "memory_type": self.entry.memory_type.value,
            "boundary": self.entry.boundary.value,
            "score": round(self.score, 4),
            "trust": round(self.trust, 4),
            "confidence": round(self.confidence, 4),
            "content": self.entry.content,
            "source": self.entry.source,
            "source_uri": self.entry.source_uri,
            "verification": self.entry.verification,
        }


@dataclass
class RetrievalResult:
    query: str
    memories: List[RetrievedMemory] = field(default_factory=list)
    total_found: int = 0
    total_eligible: int = 0
    total_filtered_by_boundary: int = 0
    duration_ms: float = 0.0
    used_cache: bool = False
    loop_guard_reason: str = ""


class SecureRetriever:
    """Retrieves entries after boundary + trust + state filtering."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        boundaries: Optional[MemoryBoundaries] = None,
        trust: Optional[TrustModel] = None,
        top_k: int = 8,
        min_score: float = 0.25,
        keyword_weight: float = 0.7,
        semantic_score_fn: Optional[Callable[[str, MemoryEntry], float]] = None,
    ) -> None:
        self._store = store
        self._boundaries = boundaries or MemoryBoundaries()
        self._trust = trust or TrustModel()
        self.top_k = top_k
        self.min_score = min_score
        self.keyword_weight = keyword_weight
        self._semantic_score_fn = semantic_score_fn

    # ------------------------------------------------------------------

    def retrieve(self, query: str, actor: AccessContext, *, top_k: Optional[int] = None) -> RetrievalResult:
        start = time.time()
        k = top_k or self.top_k
        eligible = [e for e in self._store.all() if e.state == MemoryState.ACTIVE]
        total_eligible = len(eligible)

        # Boundary filter (security gate).
        readable = self._boundaries.filter_readable(eligible, actor)
        total_filtered = total_eligible - len(readable)

        # Score.
        scored: List[RetrievedMemory] = []
        for entry in readable:
            score = self._score(query, entry)
            trust = self._trust.trust_for(entry)
            confidence = self._trust.confidence(entry)
            # Blend trust into score so low-trust entries sink.
            blended = score * (0.5 + 0.5 * trust)
            rm = RetrievedMemory(
                entry=entry,
                score=round(blended, 4),
                trust=round(trust, 4),
                confidence=round(confidence, 4),
                provenance=self._provenance_for(entry),
            )
            scored.append(rm)

        scored.sort(key=lambda r: r.score, reverse=True)
        top = [r for r in scored if r.score >= self.min_score][:k]

        return RetrievalResult(
            query=query,
            memories=top,
            total_found=len(scored),
            total_eligible=total_eligible,
            total_filtered_by_boundary=total_filtered,
            duration_ms=round((time.time() - start) * 1000.0, 2),
        )

    def _score(self, query: str, entry: MemoryEntry) -> float:
        kw = self._keyword_score(query, entry)
        sem = 0.0
        if self._semantic_score_fn is not None:
            sem = self._semantic_score_fn(query, entry)
        return self.keyword_weight * kw + (1.0 - self.keyword_weight) * sem

    def _keyword_score(self, query: str, entry: MemoryEntry) -> float:
        q = query.lower().strip()
        if not q:
            return 0.0
        haystack = f"{entry.content} {entry.summary} {' '.join(entry.tags)}".lower()
        if q in haystack:
            return 1.0
        tokens = q.split()
        if not tokens:
            return 0.0
        hits = sum(1 for t in tokens if t in haystack)
        return hits / len(tokens)

    def _provenance_for(self, entry: MemoryEntry) -> Optional[ProvenanceRecord]:
        raw = entry.metadata.get("provenance")
        if not raw:
            return None
        try:
            return ProvenanceRecord.from_dict(raw)
        except (ValueError, KeyError):
            return None