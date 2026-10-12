"""
Retrieval Engine — hybrid retrieval combining keyword, semantic, and graph search.

Provides a unified retrieval interface that combines:
  - Keyword search (substring matching in memory store)
  - Semantic search (embedding-based similarity)
  - Graph traversal (knowledge graph relationships)
  - Metadata filtering
  - Recency boosting
  - Importance weighting

Results are ranked and returned with relevance scores.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.embeddings import EmbeddingProvider
from memory.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single result from the retrieval engine.

    Attributes:
        entry: The memory entry
        score: Relevance score (0.0 - 1.0)
        method: Which retrieval method found this (keyword, semantic, graph)
        match_explanation: Why this result matches
    """
    entry: MemoryEntry
    score: float
    method: str = "keyword"
    match_explanation: str = ""


class RetrievalEngine:
    """Hybrid retrieval engine combining multiple search strategies.

    Usage:
        engine = RetrievalEngine(store, embedder, knowledge_graph)
        results = engine.search("How to deploy the app?")
        results = engine.search_with_filters(
            query="authentication",
            memory_type="long_term",
            tags=["security"],
            limit=10,
        )
    """

    def __init__(self, store: MemoryStore,
                 embedder: Optional[EmbeddingProvider] = None,
                 knowledge_graph: Optional[KnowledgeGraph] = None):
        self._store = store
        self._embedder = embedder
        self._kg = knowledge_graph
        self._lock = threading.RLock()

        # Configurable weights
        self._keyword_weight = 1.0
        self._semantic_weight = 1.5
        self._graph_weight = 1.2
        self._recency_weight = 1.0
        self._importance_weight = 1.5

    # ------------------------------------------------------------------
    # Main search
    # ------------------------------------------------------------------

    def search(self, query: str,
               memory_type: Optional[str] = None,
               scope: Optional[MemoryScope] = None,
               namespace: str = "",
               tags: List[str] = None,
               limit: int = 20,
               include_semantic: bool = True,
               include_graph: bool = True) -> List[RetrievalResult]:
        """Hybrid search combining multiple retrieval strategies.

        Args:
            query: The search query
            memory_type: Filter by memory type
            scope: Filter by scope
            namespace: Filter by namespace
            tags: Filter by tags (ANY match)
            limit: Max results
            include_semantic: Whether to include semantic (embedding) search
            include_graph: Whether to include graph traversal

        Returns:
            Ranked list of RetrievalResult
        """
        # 1. Keyword search
        keyword_results = self._keyword_search(
            query, memory_type, scope, namespace, tags, limit * 2,
        )

        # 2. Semantic search (if embedder available)
        semantic_results: List[RetrievalResult] = []
        if include_semantic and self._embedder:
            semantic_results = self._semantic_search(
                query, memory_type, scope, namespace, tags, limit,
            )

        # 3. Graph search (if kg available)
        graph_results: List[RetrievalResult] = []
        if include_graph and self._kg:
            graph_results = self._graph_search(
                query, memory_type, scope, namespace, limit,
            )

        # Merge and rank
        combined = self._merge_results(
            keyword_results, semantic_results, graph_results,
        )

        # Apply recency boost
        combined = self._apply_recency_boost(combined)

        # Deduplicate by entry ID
        seen: set = set()
        deduped = []
        for r in combined:
            if r.entry.id not in seen:
                seen.add(r.entry.id)
                deduped.append(r)

        return deduped[:limit]

    def search_with_filters(self, query: str, **filters) -> List[RetrievalResult]:
        """Search with arbitrary metadata filters.

        Accepts keyword arguments that are passed as metadata filters.
        """
        # Base search
        results = self.search(query, **{
            k: v for k, v in filters.items()
            if k in ("memory_type", "scope", "namespace", "tags", "limit",
                    "include_semantic", "include_graph")
        })

        # Apply metadata filters
        meta_filters = {
            k: v for k, v in filters.items()
            if k not in ("memory_type", "scope", "namespace", "tags", "limit",
                        "include_semantic", "include_graph")
        }

        if meta_filters:
            filtered = []
            for result in results:
                entry = result.entry
                matches = True
                for mkey, mval in meta_filters.items():
                    if entry.metadata.get(mkey) != mval:
                        matches = False
                        break
                if matches:
                    filtered.append(result)
            return filtered

        return results

    # ------------------------------------------------------------------
    # Search strategies
    # ------------------------------------------------------------------

    def _keyword_search(self, query: str, memory_type: Optional[str],
                        scope: Optional[MemoryScope], namespace: str,
                        tags: List[str], limit: int) -> List[RetrievalResult]:
        """Keyword-based search using substring matching."""
        entries = self._store.search(
            query=query, memory_type=memory_type, scope=scope,
            namespace=namespace, tags=tags, limit=limit,
        )
        results = []
        for entry in entries:
            score = self._compute_keyword_score(query, entry)
            results.append(RetrievalResult(
                entry=entry,
                score=score,
                method="keyword",
                match_explanation=f"Keyword match (score={score:.2f})",
            ))
        return results

    def _semantic_search(self, query: str, memory_type: Optional[str],
                         scope: Optional[MemoryScope], namespace: str,
                         tags: List[str], limit: int) -> List[RetrievalResult]:
        """Semantic search using embedding similarity."""
        if not self._embedder:
            return []

        query_vec = self._embedder.embed(query)

        # Get candidates
        entries = self._store.search(
            memory_type=memory_type, scope=scope,
            namespace=namespace, tags=tags, limit=100,
        )

        # Score by similarity
        scored = []
        for entry in entries:
            entry_text = f"{entry.key} {entry.value}"
            entry_vec = self._embedder.embed(entry_text[:1000])
            similarity = EmbeddingProvider.cosine_similarity(query_vec, entry_vec)
            if similarity > 0.3:  # Minimum similarity threshold
                scored.append((similarity, entry))

        scored.sort(key=lambda x: -x[0])
        return [
            RetrievalResult(
                entry=entry,
                score=sim,
                method="semantic",
                match_explanation=f"Semantic similarity (score={sim:.2f})",
            )
            for sim, entry in scored[:limit]
        ]

    def _graph_search(self, query: str, memory_type: Optional[str],
                      scope: Optional[MemoryScope], namespace: str,
                      limit: int) -> List[RetrievalResult]:
        """Graph-based search using knowledge graph traversal."""
        if not self._kg:
            return []

        # Search for matching nodes in the graph
        nodes = self._kg.search_nodes(query, limit=10)
        if not nodes:
            return []

        results = []
        for node in nodes:
            # Get related nodes
            neighbors = self._kg.get_neighbors(node.id)
            for neighbor in neighbors:
                # Find corresponding memory entries
                entries = self._store.search(
                    query=neighbor.name, limit=3,
                )
                for entry in entries:
                    score = 0.5  # Base score for graph-based matches
                    results.append(RetrievalResult(
                        entry=entry,
                        score=score,
                        method="graph",
                        match_explanation=(
                            f"Related via '{node.name}' → '{neighbor.name}'"
                        ),
                    ))

        return results[:limit]

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_keyword_score(query: str, entry: MemoryEntry) -> float:
        """Compute keyword match score for an entry."""
        query_lower = query.lower()
        score = 0.0

        # Exact key match
        if entry.key.lower() == query_lower:
            score += 0.8
        # Key contains query
        elif query_lower in entry.key.lower():
            score += 0.5

        # Value contains query
        value_str = str(entry.value).lower()
        if query_lower in value_str:
            score += 0.4

        # Tag match
        for tag in entry.tags:
            if query_lower in tag.lower():
                score += 0.2

        # Namespace match
        if query_lower in entry.namespace.lower():
            score += 0.1

        return min(score, 1.0)

    def _merge_results(self, *result_lists: List[RetrievalResult]) -> List[RetrievalResult]:
        """Merge and score results from multiple retrieval strategies."""
        # Group by entry ID
        merged: Dict[str, RetrievalResult] = {}

        for results in result_lists:
            for result in results:
                if result.entry.id in merged:
                    existing = merged[result.entry.id]
                    # Average score with method bonuses
                    existing.score = (existing.score + result.score) / 2
                    existing.method = f"{existing.method}+{result.method}"
                else:
                    merged[result.entry.id] = result

        # Sort by score
        results = sorted(
            merged.values(),
            key=lambda r: r.score * self._importance_weight,
            reverse=True,
        )
        return results

    def _apply_recency_boost(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Boost scores for more recent entries."""
        now = time.time()
        boosted = []
        for result in results:
            age_hours = (now - result.entry.created_at) / 3600
            recency_boost = max(0, 1.0 - (age_hours / 720))  # 30 day half-life
            result.score = result.score * (1 + recency_boost * self._recency_weight)
            boosted.append(result)
        return boosted

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_weights(self, keyword: float = None, semantic: float = None,
                    graph: float = None, recency: float = None,
                    importance: float = None) -> None:
        """Adjust retrieval strategy weights."""
        if keyword is not None:
            self._keyword_weight = keyword
        if semantic is not None:
            self._semantic_weight = semantic
        if graph is not None:
            self._graph_weight = graph
        if recency is not None:
            self._recency_weight = recency
        if importance is not None:
            self._importance_weight = importance

    def stats(self) -> Dict[str, Any]:
        """Return retrieval engine configuration."""
        return {
            "weights": {
                "keyword": self._keyword_weight,
                "semantic": self._semantic_weight,
                "graph": self._graph_weight,
                "recency": self._recency_weight,
                "importance": self._importance_weight,
            },
            "semantic_available": self._embedder is not None,
            "graph_available": self._kg is not None,
        }
