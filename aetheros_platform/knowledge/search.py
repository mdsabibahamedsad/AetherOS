"""Semantic search — embedding-based similarity search for knowledge graph and memory."""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from typing import Any, Optional

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "her", "our", "their", "not", "no", "nor", "so", "if", "then",
    "than", "too", "very", "just", "about", "also", "more", "some", "any",
    "each", "every", "all", "both", "few", "most", "other", "such", "only",
    "own", "same", "what", "which", "who", "whom", "when", "where", "why",
    "how", "there", "here", "up", "down", "out", "off", "over", "under",
}


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{1,}\b', text)
    return [t for t in tokens if t not in STOP_WORDS]


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    tf = Counter(tokens)
    max_tf = max(tf.values())
    vec = {}
    for term, count in tf.items():
        tf_val = 0.5 + 0.5 * (count / max_tf)
        vec[term] = tf_val * idf.get(term, 1.0)
    return vec


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    terms = set(a) & set(b)
    if not terms:
        return 0.0
    dot = sum(a[t] * b[t] for t in terms)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticSearch:
    def __init__(self):
        self._documents: list[dict] = []
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._dirty = True

    def index(self, documents: list[dict],
               text_field: str = "content"):
        self._documents = documents
        all_tokens = []
        for doc in documents:
            text = doc.get(text_field, "")
            if isinstance(text, dict):
                text = json.dumps(text)
            tokens = _tokenize(str(text))
            doc["_tokens"] = tokens
            all_tokens.append(tokens)
        n = len(documents)
        term_doc_count: dict[str, int] = {}
        for tokens in all_tokens:
            for t in set(tokens):
                term_doc_count[t] = term_doc_count.get(t, 0) + 1
        self._idf = {
            t: math.log((n + 1) / (count + 1)) + 1
            for t, count in term_doc_count.items()
        }
        self._vectors = [
            _tfidf_vector(tokens, self._idf) for tokens in all_tokens
        ]
        self._dirty = False

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return self._documents[:top_k] if self._dirty else []
        if self._dirty:
            return [{"error": "No index built yet"}]
        query_vec = _tfidf_vector(query_tokens, self._idf)
        scored = []
        for i, doc_vec in enumerate(self._vectors):
            score = _cosine_similarity(query_vec, doc_vec)
            if score > 0:
                result = dict(self._documents[i])
                result["_score"] = round(score, 4)
                result.pop("_tokens", None)
                scored.append(result)
        scored.sort(key=lambda x: -x["_score"])
        return scored[:top_k]

    def hybrid_search(self, query: str, kg: Any,
                       top_k: int = 10) -> list[dict]:
        results = []
        semantic_results = self.search(query, top_k)
        for r in semantic_results:
            results.append({"source": "semantic", **r, "score": r.pop("_score", 0.0)})
        kg_results = kg.search_entities(query, top_k)
        for r in kg_results:
            for existing in results:
                if existing.get("id") == r.get("id"):
                    break
            else:
                tokens = _tokenize(query) + _tokenize(r.get("name", ""))
                score = len(set(tokens)) / max(len(tokens), 1)
                results.append({"source": "knowledge_graph", **r, "score": score})
        results.sort(key=lambda x: -x.get("score", 0))
        return results[:top_k]

    def similarity(self, text_a: str, text_b: str) -> float:
        tokens_a = _tokenize(text_a)
        tokens_b = _tokenize(text_b)
        if not tokens_a or not tokens_b:
            return 0.0
        temp_docs = [{"_tokens": tokens_a}, {"_tokens": tokens_b}]
        n = 2
        term_doc_count = {}
        for tokens in [tokens_a, tokens_b]:
            for t in set(tokens):
                term_doc_count[t] = term_doc_count.get(t, 0) + 1
        idf = {t: math.log((n + 1) / (count + 1)) + 1
               for t, count in term_doc_count.items()}
        vec_a = _tfidf_vector(tokens_a, idf)
        vec_b = _tfidf_vector(tokens_b, idf)
        return _cosine_similarity(vec_a, vec_b)

    def extract_keywords(self, text: str, top_k: int = 10) -> list[str]:
        tokens = _tokenize(text)
        if not tokens:
            return []
        tf = Counter(tokens)
        scored = [(t, f * self._idf.get(t, 1.0)) for t, f in tf.most_common(20)]
        scored.sort(key=lambda x: -x[1])
        return [t for t, s in scored[:top_k]]
