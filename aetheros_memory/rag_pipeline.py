"""RAG Pipeline — multi-stage retrieval-augmented generation pipeline.

User Query -> Query Expansion -> Semantic Search -> Knowledge Graph
Traversal -> Ranking -> Compression -> Prompt Builder -> Provider
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aetheros_memory.embedding_engine import (
    EmbeddingEngine,
    EmbeddingConfig,
    cosine_similarity,
)
from aetheros_memory.knowledge_graph import (
    GraphEntity,
    GraphQuery,
    KnowledgeGraph,
    EntityType,
)
from aetheros_memory.memory_manager import (
    MemoryCategory,
    MemoryManager,
    MemoryRecord,
)
from aetheros_memory.vector_database import (
    SearchResult,
    VectorDatabase,
)

logger = logging.getLogger("aetheros_memory.rag")


@dataclass
class RAGConfig:
    max_tokens: int = 4096
    min_score: float = 0.3
    top_k: int = 10
    enable_expansion: bool = True
    enable_graph: bool = True
    enable_compression: bool = True
    enable_ranking: bool = True
    max_context_length: int = 8192
    dedup_enabled: bool = True
    expansion_count: int = 3
    graph_max_depth: int = 2
    recency_weight: float = 0.15
    importance_weight: float = 0.15
    similarity_weight: float = 0.5
    credibility_weight: float = 0.1
    category_weight: float = 0.1
    cache_ttl: float = 300.0
    workspace_id: str = ""
    project_id: str = ""


@dataclass
class QueryExpansion:
    original_query: str
    expansions: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)


@dataclass
class RetrievedContext:
    text: str
    score: float
    source: str
    category: str
    record_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_from_graph: bool = False


@dataclass
class RAGResult:
    query: str
    contexts: List[RetrievedContext] = field(default_factory=list)
    expanded_queries: List[str] = field(default_factory=list)
    total_tokens: int = 0
    search_time_ms: float = 0.0
    graph_time_ms: float = 0.0
    rank_time_ms: float = 0.0
    compress_time_ms: float = 0.0
    total_time_ms: float = 0.0
    compressed_context: str = ""


class RAGPipeline:
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        vector_db: Optional[VectorDatabase] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        self._config = config or RAGConfig()
        self._embedding_engine = embedding_engine
        self._vector_db = vector_db
        self._knowledge_graph = knowledge_graph
        self._memory_manager = memory_manager
        self._lock = threading.RLock()
        self._expansion_cache: Dict[str, Tuple[QueryExpansion, float]] = {}
        self._embedding_cache: Dict[str, Tuple[List[float], float]] = {}
        self._stats: Dict[str, Any] = {
            "total_requests": 0,
            "total_search_time_ms": 0.0,
            "total_graph_time_ms": 0.0,
            "total_rank_time_ms": 0.0,
            "total_compress_time_ms": 0.0,
            "total_contexts_retrieved": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def retrieve(
        self,
        query: str,
        workspace_id: str = "",
        project_id: str = "",
        max_tokens: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        start_total = time.monotonic()
        result = RAGResult(query=query)
        effective_max_tokens = max_tokens or self._config.max_tokens
        effective_top_k = top_k or self._config.top_k

        with self._lock:
            self._stats["total_requests"] += 1

        expanded_queries: List[str] = []

        if self._config.enable_expansion:
            start_expand = time.monotonic()
            expansion = self.expand_query(query)
            expanded_queries = [expansion.original_query] + expansion.expansions
            result.expanded_queries = expanded_queries
            logger.debug(
                "Query expanded: %d variants for '%s'",
                len(expanded_queries),
                query[:60],
            )

        queries_to_search = expanded_queries if expanded_queries else [query]

        start_search = time.monotonic()
        contexts = self.semantic_search(
            queries_to_search,
            effective_top_k,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        result.search_time_ms = (time.monotonic() - start_search) * 1000

        with self._lock:
            self._stats["total_search_time_ms"] += result.search_time_ms

        if self._config.enable_graph and self._knowledge_graph is not None:
            start_graph = time.monotonic()
            graph_contexts = self.graph_traversal(contexts, query)
            result.graph_time_ms = (time.monotonic() - start_graph) * 1000

            with self._lock:
                self._stats["total_graph_time_ms"] += result.graph_time_ms

            existing_ids = {c.record_id for c in contexts}
            for gc in graph_contexts:
                if gc.record_id not in existing_ids:
                    contexts.append(gc)
                    existing_ids.add(gc.record_id)

        if self._config.enable_ranking:
            start_rank = time.monotonic()
            contexts = self.rank(contexts, query)
            result.rank_time_ms = (time.monotonic() - start_rank) * 1000

            with self._lock:
                self._stats["total_rank_time_ms"] += result.rank_time_ms

        contexts.sort(key=lambda c: c.score, reverse=True)
        contexts = contexts[:effective_top_k]

        with self._lock:
            self._stats["total_contexts_retrieved"] += len(contexts)

        result.contexts = contexts

        if self._config.enable_compression:
            start_compress = time.monotonic()
            compressed = self.compress(contexts, effective_max_tokens)
            result.compress_time_ms = (time.monotonic() - start_compress) * 1000

            with self._lock:
                self._stats["total_compress_time_ms"] += result.compress_time_ms

            result.compressed_context = compressed
            result.total_tokens = self._estimate_tokens(compressed)
        else:
            joined = "\n\n".join(
                f"[{c.source}](score={c.score:.3f}): {c.text}" for c in contexts
            )
            result.compressed_context = joined
            result.total_tokens = self._estimate_tokens(joined)

        result.total_time_ms = (time.monotonic() - start_total) * 1000

        return result

    def expand_query(self, query: str) -> QueryExpansion:
        with self._lock:
            cached = self._expansion_cache.get(query)
            if cached is not None:
                cached_result, cached_time = cached
                if time.time() - cached_time < self._config.cache_ttl:
                    self._stats["cache_hits"] += 1
                    return cached_result
            self._stats["cache_misses"] += 1

        expansion = QueryExpansion(original_query=query)

        keywords = self._extract_keywords(query)

        synonyms = self._generate_synonyms(keywords)
        expansion.synonyms = list(set(synonyms))

        for synonym_query in synonyms[: self._config.expansion_count]:
            combined = f"{query} {synonym_query}"
            expansion.expansions.append(combined)

        rephrased = self._rephrase_query(query)
        expansion.expansions.extend(rephrased)

        sub_questions = self._generate_sub_questions(query)
        expansion.expansions.extend(sub_questions)

        keyword_variants = self._keyword_variants(keywords)
        expansion.expansions.extend(keyword_variants)

        expansion.expansions = list(dict.fromkeys(expansion.expansions))
        expansion.expansions = expansion.expansions[: self._config.expansion_count * 3]

        with self._lock:
            self._expansion_cache[query] = (expansion, time.time())
            if len(self._expansion_cache) > 1000:
                oldest = min(
                    self._expansion_cache.keys(),
                    key=lambda k: self._expansion_cache[k][1],
                )
                del self._expansion_cache[oldest]

        return expansion

    def semantic_search(
        self,
        queries: List[str],
        top_k: int = 10,
        workspace_id: str = "",
        project_id: str = "",
    ) -> List[RetrievedContext]:
        all_results: Dict[str, RetrievedContext] = {}

        for query in queries:
            query_vector = self._get_embedding(query)
            if query_vector is not None and self._vector_db is not None:
                try:
                    vector_results = self._vector_db.search(
                        query_vector, top_k=top_k * 2
                    )
                except Exception as exc:
                    logger.warning("Vector search failed for query '%s': %s", query[:40], exc)
                    vector_results = []
            else:
                vector_results = []

            for vr in vector_results:
                category = vr.metadata.get("category", "unknown")
                source = vr.metadata.get("source", "vector_db")
                ctx = RetrievedContext(
                    text=vr.text,
                    score=vr.score,
                    source=source,
                    category=category,
                    record_id=vr.id,
                    metadata=vr.metadata,
                    is_from_graph=False,
                )
                dedup_key = ctx.record_id
                if dedup_key not in all_results or ctx.score > all_results[dedup_key].score:
                    all_results[dedup_key] = ctx

        if self._memory_manager is not None:
            for query in queries:
                try:
                    keyword_results = self._memory_manager.search(
                        query,
                        workspace_id=workspace_id,
                        limit=top_k,
                    )
                except Exception as exc:
                    logger.warning("Keyword search failed for '%s': %s", query[:40], exc)
                    keyword_results = []

                for record in keyword_results:
                    ctx = RetrievedContext(
                        text=record.content,
                        score=record.importance * 10.0,
                        source=record.source or "memory_manager",
                        category=record.category.value if isinstance(record.category, MemoryCategory) else str(record.category),
                        record_id=record.id,
                        metadata={
                            "key": record.key,
                            "tags": record.tags,
                            "importance": record.importance,
                            "created_at": record.created_at,
                            "accessed_at": record.accessed_at,
                            "access_count": record.access_count,
                        },
                        is_from_graph=False,
                    )
                    dedup_key = ctx.record_id
                    if dedup_key not in all_results or ctx.score > all_results[dedup_key].score:
                        all_results[dedup_key] = ctx

        results = sorted(all_results.values(), key=lambda c: c.score, reverse=True)

        deduped: List[RetrievedContext] = []
        seen_texts: set = set()
        for ctx in results:
            if self._config.dedup_enabled:
                text_key = re.sub(r'\s+', ' ', ctx.text[:200].lower().strip())
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)
            deduped.append(ctx)

        return deduped[:top_k]

    def graph_traversal(
        self,
        contexts: List[RetrievedContext],
        query: str,
    ) -> List[RetrievedContext]:
        if self._knowledge_graph is None:
            return []

        graph_contexts: List[RetrievedContext] = []
        matched_entity_ids: set = set()
        seen_names: set = set()

        for ctx in contexts:
            entity = self._knowledge_graph.get_entity(ctx.record_id)
            if entity is not None:
                matched_entity_ids.add(entity.id)
                seen_names.add(entity.name.lower())
                continue

            gq = GraphQuery(
                name_pattern=re.escape(self._extract_entity_name(ctx.text)),
                min_importance=0.3,
                max_depth=1,
                limit=5,
            )
            found = self._knowledge_graph.query(gq)
            for entity in found:
                matched_entity_ids.add(entity.id)
                seen_names.add(entity.name.lower())

        kg_search_results = self._knowledge_graph.search(query)
        for entity, score in kg_search_results:
            if entity.id not in matched_entity_ids:
                matched_entity_ids.add(entity.id)
                seen_names.add(entity.name.lower())

        for entity_id in matched_entity_ids:
            try:
                related = self._knowledge_graph.get_related_entities(
                    entity_id,
                    max_depth=self._config.graph_max_depth,
                    min_importance=0.2,
                )
            except Exception as exc:
                logger.warning("Graph traversal failed for entity %s: %s", entity_id, exc)
                continue

            for related_entity, rel, depth in related:
                name_lower = related_entity.name.lower()
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)

                description = related_entity.description or f"{related_entity.type.value}: {related_entity.name}"
                score = related_entity.importance * (1.0 / (1.0 + depth))
                ctx = RetrievedContext(
                    text=description,
                    score=score,
                    source=f"knowledge_graph.{related_entity.type.value}",
                    category=related_entity.type.value,
                    record_id=related_entity.id,
                    metadata={
                        "entity_type": related_entity.type.value,
                        "entity_name": related_entity.name,
                        "relationship_type": rel.type.value,
                        "relationship_weight": rel.weight,
                        "depth": depth,
                        "importance": related_entity.importance,
                    },
                    is_from_graph=True,
                )
                graph_contexts.append(ctx)

        graph_contexts.sort(key=lambda c: c.score, reverse=True)
        return graph_contexts[:self._config.top_k]

    def rank(
        self,
        contexts: List[RetrievedContext],
        query: str,
    ) -> List[RetrievedContext]:
        if not contexts:
            return []

        query_embedding = self._get_embedding(query)
        now = time.time()

        for ctx in contexts:
            similarity = ctx.score

            if query_embedding is not None and ctx.text:
                ctx_embedding = self._get_embedding(ctx.text[:1000])
                if ctx_embedding is not None:
                    similarity = cosine_similarity(query_embedding, ctx_embedding)

            created_at = ctx.metadata.get("created_at", now)
            if isinstance(created_at, (int, float)):
                age_hours = (now - created_at) / 3600.0
                recency = math.exp(-age_hours / 168.0)
            else:
                recency = 0.5

            importance = float(ctx.metadata.get("importance", 1.0))
            importance_boost = min(importance / 5.0, 1.0)

            credibility = self._source_credibility(ctx.source)

            category_relevance = self._category_relevance(ctx.category, query)

            combined = (
                self._config.similarity_weight * max(similarity, ctx.score) +
                self._config.recency_weight * recency +
                self._config.importance_weight * importance_boost +
                self._config.credibility_weight * credibility +
                self._config.category_weight * category_relevance
            )

            ctx.score = combined

        return contexts

    def compress(
        self,
        contexts: List[RetrievedContext],
        max_tokens: int,
    ) -> str:
        if not contexts:
            return ""

        sorted_contexts = sorted(contexts, key=lambda c: c.score, reverse=True)
        sections: List[str] = []
        total_tokens = 0
        token_overhead = 15

        for ctx in sorted_contexts:
            if ctx.score < self._config.min_score:
                continue

            ctx_text = ctx.text
            ctx_tokens = self._estimate_tokens(ctx_text)

            if ctx_tokens > max_tokens // 2:
                max_chars = int(max_tokens * 0.5 * 3.5)
                ctx_text = ctx_text[:max_chars]
                ctx_tokens = self._estimate_tokens(ctx_text)

            formatted = f"[Source: {ctx.source} | Score: {ctx.score:.3f}]\n{ctx_text}"
            formatted_tokens = self._estimate_tokens(formatted) + token_overhead

            if total_tokens + formatted_tokens > max_tokens:
                remaining = max_tokens - total_tokens
                if remaining > 50:
                    allowed_chars = int(remaining * 3.5)
                    truncated = ctx_text[:allowed_chars]
                    formatted = f"[Source: {ctx.source} | Score: {ctx.score:.3f}]\n{truncated}"
                    formatted_tokens = self._estimate_tokens(formatted)
                    if total_tokens + formatted_tokens <= max_tokens:
                        sections.append(formatted)
                        total_tokens += formatted_tokens
                break

            sections.append(formatted)
            total_tokens += formatted_tokens

        return "\n\n".join(sections)

    def build_prompt(self, query: str, compressed_context: str) -> str:
        if not compressed_context:
            return query

        sections: List[str] = []

        sections.append("Retrieved context from memory and knowledge:")
        sections.append("")
        sections.append(compressed_context)
        sections.append("")
        sections.append(f"User query: {query}")
        sections.append("")
        sections.append(
            "Answer the user's query based on the retrieved context above. "
            "If the context is insufficient, state what is missing."
        )

        return "\n".join(sections)

    def clear_cache(self) -> int:
        with self._lock:
            expansion_count = len(self._expansion_cache)
            embedding_count = len(self._embedding_cache)
            self._expansion_cache.clear()
            self._embedding_cache.clear()
            total = expansion_count + embedding_count
            logger.debug("Cleared RAG cache: %d entries", total)
            return total

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self._lock:
            cached = self._embedding_cache.get(text_hash)
            if cached is not None:
                vec, cache_time = cached
                if time.time() - cache_time < self._config.cache_ttl:
                    return vec

        if self._embedding_engine is not None:
            try:
                result = self._embedding_engine.embed(text)
                vec = result.vector
                with self._lock:
                    self._embedding_cache[text_hash] = (vec, time.time())
                    if len(self._embedding_cache) > 5000:
                        oldest = min(
                            self._embedding_cache.keys(),
                            key=lambda k: self._embedding_cache[k][1],
                        )
                        del self._embedding_cache[oldest]
                return vec
            except Exception as exc:
                logger.warning("Embedding failed: %s", exc)

        return None

    def _extract_keywords(self, query: str) -> List[str]:
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "about", "between", "under", "over", "out", "off", "up", "down",
            "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more", "most",
            "other", "some", "such", "no", "only", "own", "same", "than",
            "too", "very", "just", "because", "as", "if", "then", "else",
            "when", "where", "why", "how", "what", "which", "who", "whom",
            "this", "that", "these", "those", "it", "its", "i", "me", "my",
            "we", "us", "our", "you", "your", "he", "him", "his", "she",
            "her", "they", "them", "their", "please", "tell", "give", "show",
        }
        words = re.findall(r'[a-zA-Z]+', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _generate_synonyms(self, keywords: List[str]) -> List[str]:
        synonym_map: Dict[str, List[str]] = {
            "create": ["build", "make", "develop", "generate", "construct"],
            "find": ["search", "locate", "discover", "retrieve", "get"],
            "update": ["modify", "change", "edit", "revise", "alter"],
            "delete": ["remove", "erase", "clear", "destroy", "eliminate"],
            "show": ["display", "reveal", "present", "demonstrate", "exhibit"],
            "explain": ["describe", "clarify", "elaborate", "illustrate", "define"],
            "analyze": ["examine", "study", "inspect", "evaluate", "review"],
            "implement": ["execute", "apply", "perform", "realize", "deploy"],
            "test": ["verify", "validate", "check", "assess", "examine"],
            "optimize": ["improve", "enhance", "refine", "tune", "upgrade"],
            "config": ["configuration", "setup", "settings", "parameters"],
            "memory": ["context", "history", "state", "knowledge", "information"],
            "agent": ["assistant", "bot", "worker", "actor", "ai"],
            "query": ["question", "request", "inquiry", "search", "lookup"],
            "result": ["output", "response", "outcome", "answer", "return"],
            "error": ["bug", "issue", "problem", "fault", "exception"],
            "document": ["file", "record", "report", "paper", "doc"],
            "function": ["method", "operation", "routine", "procedure", "handler"],
            "data": ["information", "content", "details", "facts", "dataset"],
        }
        results: List[str] = []
        for kw in keywords:
            if kw in synonym_map:
                results.extend(synonym_map[kw])
        return results[:8]

    def _rephrase_query(self, query: str) -> List[str]:
        rephrased: List[str] = []

        prefixes = [
            "Tell me about",
            "What is",
            "I want to know about",
            "Describe",
            "Find information about",
        ]
        words = query.strip().rstrip("?.")
        for prefix in prefixes[:2]:
            rephrased.append(f"{prefix} {words}")

        if " and " in words:
            parts = re.split(r'\s+(?:and|or|but)\s+', words, maxsplit=1)
            if len(parts) == 2:
                rephrased.append(f"{parts[0]}. Also {parts[1]}")
                rephrased.append(f"What is the relationship between {parts[0]} and {parts[1]}")

        return rephrased[:3]

    def _generate_sub_questions(self, query: str) -> List[str]:
        sub_questions: List[str] = []

        topic_match = re.search(r'(?:about|of|for|in|on)\s+(.+?)$', query, re.IGNORECASE)
        if topic_match:
            topic = topic_match.group(1).strip().rstrip("?.")
            sub_questions.append(f"What are the key details of {topic}?")
            sub_questions.append(f"Who is involved with {topic}?")
            sub_questions.append(f"When did {topic} happen?")

        if "how" in query.lower():
            sub_questions.append(f"What are the steps for {query.lower().replace('how', '').strip()}?")

        if "why" in query.lower():
            sub_questions.append(f"What is the reason for {query.lower().replace('why', '').strip()}?")

        return [sq for sq in sub_questions if sq][:3]

    def _keyword_variants(self, keywords: List[str]) -> List[str]:
        if not keywords:
            return []

        variants: List[str] = []
        root = keywords[0] if keywords else ""

        if len(keywords) >= 2:
            variants.append(f"{keywords[0]} {keywords[1]}")
            variants.append(f"{keywords[0]} related to {keywords[1]}")

        if root.endswith("ion"):
            base = root[:-3]
            variants.append(f"{base}ing {root}")
        elif root.endswith("ing"):
            variants.append(root[:-3] + "e")
        elif root.endswith("ed"):
            variants.append(root[:-2])
            variants.append(root[:-2] + "ing")

        return variants[:3]

    def _extract_entity_name(self, text: str) -> str:
        words = text.split()[:5]
        return " ".join(words) if words else text[:50]

    def _source_credibility(self, source: str) -> float:
        credibility_map: Dict[str, float] = {
            "pinned": 1.0,
            "knowledge_graph.concept": 0.9,
            "knowledge_graph.decision": 0.95,
            "knowledge_graph.goal": 0.85,
            "knowledge_graph.task": 0.8,
            "knowledge_graph.person": 0.9,
            "knowledge_graph.code_snippet": 0.85,
            "knowledge_graph.document": 0.85,
            "knowledge_graph.project": 0.8,
            "conversation": 0.7,
            "user_preferences": 0.9,
            "agent": 0.85,
            "tool": 0.8,
            "research": 0.85,
            "code": 0.8,
            "long_term": 0.9,
            "workspace": 0.75,
            "project": 0.8,
        }
        return credibility_map.get(source, 0.6)

    def _category_relevance(self, category: str, query: str) -> float:
        query_lower = query.lower()
        category_variants = {
            "conversation": ["chat", "talk", "said", "message", "conversation", "discuss"],
            "code": ["code", "function", "class", "program", "script", "develop", "implement"],
            "research": ["research", "study", "paper", "find", "learn", "discover"],
            "task": ["task", "todo", "track", "progress", "job", "work"],
            "project": ["project", "plan", "milestone", "goal", "objective"],
            "user_preferences": ["prefer", "like", "want", "need", "setting", "config"],
            "agent": ["agent", "assistant", "ai", "bot", "automation"],
            "tool": ["tool", "command", "utility", "function", "script"],
            "pinned": ["important", "pinned", "favorite", "key", "critical"],
        }
        if category.lower() in category_variants:
            keywords = category_variants[category.lower()]
            for kw in keywords:
                if kw in query_lower:
                    return 1.0 / math.sqrt(len(keywords))
        return 0.0

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        char_count = len(text)
        word_count = len(text.split())
        approx_tokens = int(word_count * 1.3 + char_count * 0.04)
        return max(approx_tokens, 1)
