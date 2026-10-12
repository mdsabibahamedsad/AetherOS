"""Search engine — full-text, semantic, hybrid with filters."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.vectordb import VectorDB, SearchResult, get_vectordb
from aetheros_knowledge.indexing.embedders import get_embedder, BaseEmbedder
from aetheros_knowledge.models import SourceType

logger = logging.getLogger(__name__)

STOP_WORDS = {"the","a","an","and","or","but","in","on","at","to","for","of",
              "with","by","from","as","is","was","are","were","be","been","it",
              "its","this","that","these","those","i","you","he","she","we","they"}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{1,}\b', text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def _bm25_score(query_tokens: list[str], doc_tokens: list[str],
                 avg_dl: float, N: int, df: dict[str, int],
                 k1: float = 1.5, b: float = 0.75) -> float:
    dl = len(doc_tokens)
    score = 0.0
    for qt in set(query_tokens):
        if qt not in df:
            continue
        tf = doc_tokens.count(qt)
        idf = math.log((N - df[qt] + 0.5) / (df[qt] + 0.5) + 1)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
    return score


class SearchEngine:
    def __init__(self, store: KnowledgeStore,
                 vectordb: VectorDB = None,
                 embedder: BaseEmbedder = None,
                 reranking: bool = False):
        self.store = store
        self.vectordb = vectordb or get_vectordb("sqlite")
        self.embedder = embedder or get_embedder("sentence-transformers")
        self.reranking = reranking

    def fulltext_search(self, query: str, collection_id: str = None,
                         limit: int = 20) -> list[dict]:
        documents = self.store.list_documents(collection_id, limit=1000)
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        all_tokens = []
        doc_tokens_list = []
        for doc in documents:
            tokens = _tokenize(doc.title + " " + " ".join(doc.tags))
            doc_tokens_list.append(tokens)
            all_tokens.extend(tokens)
        if not all_tokens:
            return []
        N = len(documents)
        avg_dl = sum(len(t) for t in doc_tokens_list) / max(N, 1)
        df = Counter()
        for tokens in doc_tokens_list:
            for t in set(tokens):
                df[t] += 1
        scored = []
        for i, doc in enumerate(documents):
            score = _bm25_score(q_tokens, doc_tokens_list[i], avg_dl, N, df)
            if score > 0:
                scored.append({"id": doc.id, "title": doc.title,
                                "source_type": doc.source_type.value,
                                "collection_id": doc.collection_id,
                                "score": round(score, 4)})
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

def semantic_search(self, query: str, top_k: int = 10,
                     filters: dict = None) -> list[SearchResult]:
        embedding = self.embedder.embed(query)
        results = self.vectordb.search(embedding, top_k, filters)
        # Apply reranking if enabled
        if self.reranking and results:
            # Convert SearchResult objects to dictionaries for reranking
            result_dicts = [{
                "id": r.id,
                "score": r.score,
                "content": r.content,
                "metadata": r.metadata,
                "document_id": r.document_id,
                "chunk_index": r.chunk_index
            } for r in results]
            
            # Rerank the results
            reranked_dicts = self.rerank(query, result_dicts, top_k)
            
            # Convert back to SearchResult objects
            results = [
                SearchResult(
                    id=r["id"],
                    score=r["score"],
                    content=r["content"],
                    metadata=r.get("metadata", {}),
                    document_id=r.get("document_id", ""),
                    chunk_index=r.get("chunk_index", 0)
                )
                for r in reranked_dicts
            ]
        return results

    def hybrid_search(self, query: str, top_k: int = 10,
                       collection_id: str = None,
                       filters: dict = None,
                       alpha: float = 0.5) -> list[dict]:
        semantic_results = self.semantic_search(query, top_k * 2, filters)
        semantic_map = {r.id: r for r in semantic_results}
        fulltext_results = self.fulltext_search(query, collection_id, top_k * 2)
        fulltext_map = {r["id"]: r for r in fulltext_results}
        combined: dict[str, dict] = {}
        max_sem_score = max((r.score for r in semantic_results), default=1.0)
        max_ft_score = max((r["score"] for r in fulltext_results), default=1.0)
        for r in semantic_results:
            norm = r.score / max_sem_score if max_sem_score > 0 else 0
            combined[r.id] = {
                "id": r.id, "content": r.content, "score": alpha * norm,
                "semantic_score": r.score, "fulltext_score": 0,
                "metadata": r.metadata, "source": "semantic",
            }
        for r in fulltext_results:
            norm = r["score"] / max_ft_score if max_ft_score > 0 else 0
            if r["id"] in combined:
                combined[r["id"]]["score"] += (1 - alpha) * norm
                combined[r["id"]]["fulltext_score"] = r["score"]
                combined[r["id"]]["source"] = "hybrid"
            else:
                combined[r["id"]] = {
                    "id": r["id"], "content": "", "score": (1 - alpha) * norm,
                    "semantic_score": 0, "fulltext_score": r["score"],
                    "metadata": {}, "source": "fulltext",
                    "title": r["title"],
                }
        results = sorted(combined.values(), key=lambda x: -x["score"])
        results = results[:top_k]
        # Apply reranking if enabled
        return self.rerank(query, results, top_k)

    def rerank(self, query: str, results: list[dict], top_k: int = None) -> list[dict]:
        """
        Rerank search results based on additional relevance signals.
        
        Args:
            query: The original query
            results: List of search result dictionaries
            top_k: Number of top results to return (if None, returns all)
            
        Returns:
            Reranked list of search results
        """
        if not results or not self.reranking:
            return results[:top_k] if top_k is not None else results
        
        # Simple reranking implementation:
        # For now, we'll just boost scores based on query term frequency in content
        # and quality scores
        # In a more sophisticated implementation, we might use cross-encoders or ML models
        
        query_terms = set(query.lower().split())
        reranked_results = []
        
        for result in results:
            # Start with the original score
            score = result.get("score", 0.0)
            
            # Get content to analyze
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            
            # Calculate query term frequency in content and title
            content_terms = set(content.split())
            title_terms = set(title.split())
            
            # Boost score based on term overlap
            content_overlap = len(query_terms.intersection(content_terms))
            title_overlap = len(query_terms.intersection(title_terms))
            
            # Apply boost (title matches are weighted higher)
            boost = (content_overlap * 0.1) + (title_overlap * 0.2)
            score += boost
            
            # Boost score based on quality score if available
            quality_score = result.get("metadata", {}).get("quality_score")
            if quality_score is not None:
                # Quality score is between 0.0 and 1.0, so we can directly add a portion of it
                quality_boost = quality_score * 0.3  # Weight quality at 30%
                score += quality_boost
            
            # Create a copy of the result with updated score
            reranked_result = result.copy()
            reranked_result["score"] = score
            reranked_result["rerank_boost"] = boost
            if quality_score is not None:
                reranked_result["quality_boost"] = quality_score * 0.3
            reranked_results.append(reranked_result)
        
        # Sort by the new score
        reranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top k results if specified
        if top_k is not None:
            return reranked_results[:top_k]
        return reranked_results

    def search_with_filters(self, query: str, top_k: int = 10,
                             collection_id: str = None,
                             tags: list[str] = None,
                             source_type: str = None,
                             language: str = None,
                             date_from: str = None,
                             date_to: str = None,
                             hybrid: bool = True) -> list[dict]:
        filters = {}
        if collection_id:
            filters["collection_id"] = collection_id
        if source_type:
            filters["source_type"] = source_type
        if language:
            filters["language"] = language
        if hybrid:
            results = self.hybrid_search(query, top_k, collection_id, filters)
        else:
            results = self.semantic_search(query, top_k, filters)
            results = [{"id": r.id, "content": r.content,
                         "score": r.score, "metadata": r.metadata,
                         "source": "semantic"}
                       for r in results]
        if tags:
            filtered = []
            for r in results:
                meta = r.get("metadata", {})
                doc_tags = meta.get("tags", [])
                if isinstance(doc_tags, str):
                    try:
                        import json
                        doc_tags = json.loads(doc_tags)
                    except Exception:
                        doc_tags = []
                if any(t in doc_tags for t in tags):
                    filtered.append(r)
            results = filtered
        return results[:top_k]
