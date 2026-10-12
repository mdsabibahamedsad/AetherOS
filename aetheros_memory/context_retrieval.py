"""Context Retrieval — automatically retrieves relevant context before every AI request.

Before every AI request, this module retrieves:
- Relevant memories (via RAG pipeline)
- Relevant code
- Relevant files
- Recent decisions
- Pinned notes
- Workspace context

All retrieval is bounded by token limits to avoid exceeding model context windows.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory.memory_manager import MemoryManager, MemoryCategory, MemoryRecord
from aetheros_memory.rag_pipeline import RAGPipeline, RAGConfig, RetrievedContext
from aetheros_memory.knowledge_graph import KnowledgeGraph

logger = logging.getLogger("aetheros_memory.context_retrieval")


@dataclass
class RetrievalConfig:
    max_total_tokens: int = 8000
    max_memory_tokens: int = 3000
    max_code_tokens: int = 2000
    max_decision_tokens: int = 1000
    max_pinned_tokens: int = 1000
    max_workspace_tokens: int = 1000
    enable_recent_decisions: bool = True
    enable_pinned: bool = True
    enable_workspace_context: bool = True
    enable_relevant_code: bool = True
    enable_semantic_search: bool = True
    recency_hours: float = 24.0
    min_relevance_score: float = 0.3


@dataclass
class RetrievalBundle:
    contexts: List[RetrievedContext] = field(default_factory=list)
    total_tokens: int = 0
    memory_count: int = 0
    code_count: int = 0
    decision_count: int = 0
    pinned_count: int = 0
    workspace_count: int = 0
    retrieval_time_ms: float = 0.0
    formatted_context: str = ""


class ContextRetrieval:
    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        rag_pipeline: Optional[RAGPipeline] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        config: Optional[RetrievalConfig] = None,
    ) -> None:
        self._memory_manager = memory_manager
        self._rag_pipeline = rag_pipeline
        self._knowledge_graph = knowledge_graph
        self._config = config or RetrievalConfig()
        self._lock = threading.RLock()

    @property
    def config(self) -> RetrievalConfig:
        return self._config

    @config.setter
    def config(self, value: RetrievalConfig) -> None:
        with self._lock:
            self._config = value

    def retrieve(
        self,
        query: str,
        workspace_id: str = "",
        project_id: str = "",
        conversation_id: str = "",
        max_tokens: Optional[int] = None,
    ) -> RetrievalBundle:
        with self._lock:
            start = time.perf_counter()
            cfg = self._config
            limit = min(max_tokens or cfg.max_total_tokens, cfg.max_total_tokens)
            budget = _TokenBudget(limit)

            all_contexts: List[RetrievedContext] = []

            memories = self.get_relevant_memories(
                query=query,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=20,
                max_tokens=min(cfg.max_memory_tokens, budget.remaining),
            )
            token_count = sum(_count_ctx_tokens(c) for c in memories)
            all_contexts.extend(memories)
            budget.spend(token_count)

            if cfg.enable_relevant_code:
                code = self.get_relevant_code(
                    query=query,
                    project_id=project_id,
                    max_tokens=min(cfg.max_code_tokens, budget.remaining),
                )
                token_count = sum(_count_ctx_tokens(c) for c in code)
                all_contexts.extend(code)
                budget.spend(token_count)

            if cfg.enable_recent_decisions:
                decisions = self.get_recent_decisions(
                    workspace_id=workspace_id,
                    hours=cfg.recency_hours,
                    max_tokens=min(cfg.max_decision_tokens, budget.remaining),
                )
                token_count = sum(_count_ctx_tokens(c) for c in decisions)
                all_contexts.extend(decisions)
                budget.spend(token_count)

            if cfg.enable_pinned:
                pinned = self.get_pinned_notes(
                    workspace_id=workspace_id,
                    max_tokens=min(cfg.max_pinned_tokens, budget.remaining),
                )
                token_count = sum(_count_ctx_tokens(c) for c in pinned)
                all_contexts.extend(pinned)
                budget.spend(token_count)

            if cfg.enable_workspace_context:
                workspace = self.get_workspace_context(
                    workspace_id=workspace_id,
                    max_tokens=min(cfg.max_workspace_tokens, budget.remaining),
                )
                token_count = sum(_count_ctx_tokens(c) for c in workspace)
                all_contexts.extend(workspace)
                budget.spend(token_count)

            formatted = self.format_context(all_contexts, limit)

            elapsed = (time.perf_counter() - start) * 1000.0

            return RetrievalBundle(
                contexts=all_contexts,
                total_tokens=budget.spent,
                memory_count=len(memories),
                code_count=len([c for c in memories if c.metadata.get("category") == "code"]),
                decision_count=len(decisions),
                pinned_count=len(pinned),
                workspace_count=len(workspace),
                retrieval_time_ms=round(elapsed, 2),
                formatted_context=formatted,
            )

    def get_relevant_memories(
        self,
        query: str,
        workspace_id: str = "",
        project_id: str = "",
        top_k: int = 10,
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedContext]:
        if not query.strip():
            return []
        try:
            rag_config = RAGConfig(
                top_k=top_k,
                min_score=self._config.min_relevance_score,
                workspace_id=workspace_id,
                project_id=project_id,
            )
            result = self._rag_pipeline.retrieve(query, config=rag_config)
            contexts = result.contexts if result.contexts else []
        except Exception as exc:
            logger.warning("RAG pipeline retrieval failed: %s", exc)
            contexts = []

        return self._truncate_by_tokens(contexts, max_tokens)

    def get_recent_decisions(
        self,
        workspace_id: str = "",
        hours: float = 24.0,
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedContext]:
        cutoff = time.time() - (hours * 3600.0)
        results: List[RetrievedContext] = []
        try:
            memories = self._memory_manager.get_by_workspace(workspace_id) if workspace_id else []
            for mem in memories:
                if mem.created_at < cutoff:
                    continue
                if mem.category != MemoryCategory.AGENT and "decision" not in mem.tags:
                    continue
                results.append(_record_to_context(mem, source="recent_decision"))
        except Exception as exc:
            logger.warning("Failed to retrieve recent decisions: %s", exc)

        results.sort(key=lambda c: c.score, reverse=True)
        return self._truncate_by_tokens(results, max_tokens)

    def get_pinned_notes(
        self,
        workspace_id: str = "",
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedContext]:
        results: List[RetrievedContext] = []
        try:
            pinned = self._memory_manager.list_pinned()
            if workspace_id:
                pinned = [p for p in pinned if p.workspace_id == workspace_id]
            for mem in pinned:
                results.append(_record_to_context(mem, source="pinned_note"))
        except Exception as exc:
            logger.warning("Failed to retrieve pinned notes: %s", exc)

        return self._truncate_by_tokens(results, max_tokens)

    def get_workspace_context(
        self,
        workspace_id: str = "",
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedContext]:
        results: List[RetrievedContext] = []
        if not workspace_id:
            return results
        try:
            memories = self._memory_manager.get_by_workspace(workspace_id)
            for mem in memories:
                if mem.category in (MemoryCategory.WORKSPACE, MemoryCategory.PROJECT):
                    results.append(_record_to_context(mem, source="workspace_context"))
        except Exception as exc:
            logger.warning("Failed to retrieve workspace context: %s", exc)

        return self._truncate_by_tokens(results, max_tokens)

    def get_relevant_code(
        self,
        query: str,
        project_id: str = "",
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedContext]:
        results: List[RetrievedContext] = []
        try:
            if project_id:
                memories = self._memory_manager.get_by_project(project_id)
            else:
                memories = []
                for cat in (MemoryCategory.CODE,):
                    with self._lock:
                        pass
                memories = []

            code_memories = [m for m in memories if m.category == MemoryCategory.CODE]

            if query.strip():
                query_lower = query.lower()
                scored: List[tuple[float, MemoryRecord]] = []
                for mem in code_memories:
                    score = 0.0
                    if query_lower in mem.content.lower():
                        score += 5.0
                    if query_lower in mem.key.lower():
                        score += 10.0
                    for tag in mem.tags:
                        if query_lower in tag.lower():
                            score += 3.0
                    if score > 0:
                        score *= mem.importance
                        scored.append((score, mem))
                scored.sort(key=lambda x: x[0], reverse=True)
                code_memories = [m for _, m in scored]

            for mem in code_memories:
                results.append(_record_to_context(mem, source="relevant_code"))
        except Exception as exc:
            logger.warning("Failed to retrieve relevant code: %s", exc)

        return self._truncate_by_tokens(results, max_tokens)

    def format_context(
        self,
        contexts: List[RetrievedContext],
        max_tokens: Optional[int] = None,
    ) -> str:
        if not contexts:
            return ""

        sections: Dict[str, List[str]] = {}

        for ctx in contexts:
            source = ctx.metadata.get("source", "unknown") if ctx.metadata else "unknown"
            if source not in sections:
                sections[source] = []

            label_map = {
                "recent_decision": "Recent Decision",
                "pinned_note": "Pinned Note",
                "workspace_context": "Workspace Context",
                "relevant_code": "Code Snippet",
                "memory": "Memory",
            }
            label = label_map.get(source, source.replace("_", " ").title())

            header = f"[{label}]"
            if ctx.metadata and ctx.metadata.get("key"):
                header += f" (key: {ctx.metadata['key']})"
            if ctx.score > 0:
                header += f" [relevance: {ctx.score:.2f}]"

            sections[source].append(f"{header}\n{ctx.text}")

        parts: List[str] = []
        source_order = [
            "pinned_note",
            "workspace_context",
            "recent_decision",
            "memory",
            "relevant_code",
        ]
        seen = set()
        for source in source_order:
            if source in sections:
                parts.extend(sections[source])
                seen.add(source)
        for source in sections:
            if source not in seen:
                parts.extend(sections[source])

        combined = "\n\n---\n\n".join(parts)

        if max_tokens is not None:
            combined = self._truncate_text(combined, max_tokens)

        return combined

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _truncate_by_tokens(
        self,
        contexts: List[RetrievedContext],
        max_tokens: Optional[int],
    ) -> List[RetrievedContext]:
        if max_tokens is None:
            return contexts
        result: List[RetrievedContext] = []
        running = 0
        for ctx in contexts:
            tokens = self.estimate_tokens(ctx.text)
            if running + tokens > max_tokens:
                remaining = max_tokens - running
                if remaining > 16:
                    truncated = ctx.text[:remaining * 4]
                    result.append(_replace_text(ctx, truncated))
                break
            result.append(ctx)
            running += tokens
        return result

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        estimated = self.estimate_tokens(text)
        if estimated <= max_tokens:
            return text
        ratio = max_tokens / estimated
        target_chars = max(1, int(len(text) * ratio))
        return text[:target_chars]


class _TokenBudget:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._spent = 0

    @property
    def remaining(self) -> int:
        return max(0, self._limit - self._spent)

    @property
    def spent(self) -> int:
        return self._spent

    def spend(self, tokens: int) -> None:
        self._spent += tokens


def _record_to_context(record: MemoryRecord, source: str = "memory") -> RetrievedContext:
    return RetrievedContext(
        text=record.content,
        source=source,
        score=record.importance,
        metadata={
            "id": record.id,
            "key": record.key,
            "category": record.category.value if record.category else "",
            "source": source,
            "created_at": record.created_at,
            "tags": list(record.tags),
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
        },
    )


def _replace_text(ctx: RetrievedContext, new_text: str) -> RetrievedContext:
    return RetrievedContext(
        text=new_text,
        source=ctx.source,
        score=ctx.score,
        metadata=ctx.metadata,
    )


def _count_ctx_tokens(ctx: RetrievedContext) -> int:
    return max(1, len(ctx.text) // 4)
