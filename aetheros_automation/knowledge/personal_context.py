from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from aetheros_automation.knowledge.context_engine import ContextEngine, RelevantItem, ContextSource, ContextRelevance
from aetheros_automation.knowledge.memory_manager import UnifiedMemoryManager, MemoryType, MemoryConfidence
from aetheros_automation.knowledge.search_engine import CrossSourceSearch, SearchQuery, SearchSource, SearchType


@dataclass
class PersonalContextResult:
    query: str
    answer: str = ""
    sources: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    items_found: int = 0


class PersonalContextEngine:
    def __init__(self, memory_manager: UnifiedMemoryManager | None = None,
                 search_engine: CrossSourceSearch | None = None,
                 context_engine: ContextEngine | None = None):
        self._memory = memory_manager or UnifiedMemoryManager()
        self._search = search_engine or CrossSourceSearch()
        self._context = context_engine or ContextEngine()

    def answer_personal_query(self, query: str, space_id: str = "") -> PersonalContextResult:
        query_lower = query.lower()
        result = PersonalContextResult(query=query)
        sources = []

        if "yesterday" in query_lower:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            sq = SearchQuery(text=yesterday, type=SearchType.KEYWORD, max_results=20, space_id=space_id)
            date_results = self._search.search(sq)
            for r in date_results:
                sources.append({"title": r.title, "snippet": r.snippet, "source": r.source.value,
                                "date": r.date, "score": r.score})
            memories = self._memory.search(query=yesterday, space_id=space_id)
            for m in memories:
                sources.append({"title": m.key, "snippet": m.summary, "source": "memory",
                                "date": m.created_at, "score": m.importance})

        if "unfinished" in query_lower or "incomplete" in query_lower or "pending" in query_lower:
            tasks = self._memory.search(query="task", type=MemoryType.TASK, space_id=space_id)
            for t in tasks:
                sources.append({"title": t.key, "snippet": t.summary, "source": "task",
                                "date": t.created_at, "score": t.importance})

        if "project" in query_lower or "working on" in query_lower:
            projects = self._memory.search(query="project", type=MemoryType.PROJECT, space_id=space_id)
            for p in projects:
                sources.append({"title": p.key, "snippet": p.summary, "source": "project",
                                "date": p.created_at, "score": p.importance})

        if "document" in query_lower or "file" in query_lower or "save" in query_lower:
            docs = self._memory.search(query=query, type=MemoryType.DOCUMENT, space_id=space_id)
            for d in docs:
                sources.append({"title": d.key, "snippet": d.summary, "source": "document",
                                "date": d.created_at, "score": d.importance})
            sq = SearchQuery(text=query, type=SearchType.NATURAL_LANGUAGE,
                             sources=[SearchSource.FILES, SearchSource.DOCUMENTS],
                             max_results=10, space_id=space_id)
            file_results = self._search.search(sq)
            for r in file_results:
                sources.append({"title": r.title, "snippet": r.snippet, "source": r.source.value,
                                "date": r.date, "score": r.score})

        general_sq = SearchQuery(text=query, type=SearchType.NATURAL_LANGUAGE, max_results=10, space_id=space_id)
        general_results = self._search.search(general_sq)
        for r in general_results:
            if not any(s.get("title") == r.title for s in sources):
                sources.append({"title": r.title, "snippet": r.snippet, "source": r.source.value,
                                "date": r.date, "score": r.score})

        general_memories = self._memory.search(query=query, space_id=space_id, min_importance=0.3)
        for m in general_memories:
            if not any(s.get("title") == m.key for s in sources):
                sources.append({"title": m.key, "snippet": m.summary, "source": m.type.value,
                                "date": m.created_at, "score": m.importance})

        sources.sort(key=lambda x: x.get("score", 0), reverse=True)
        result.sources = sources[:20]
        result.items_found = len(sources)
        result.confidence = min(1.0, len(sources) * 0.1)
        if sources:
            result.answer = f"Found {len(sources)} relevant items"
        else:
            result.answer = "No relevant information found in permitted knowledge sources"
        return result
