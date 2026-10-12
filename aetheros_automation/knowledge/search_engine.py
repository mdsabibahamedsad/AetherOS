from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class SearchType(str, Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    NATURAL_LANGUAGE = "natural_language"
    METADATA = "metadata"


class SearchSource(str, Enum):
    FILES = "files"
    MESSAGES = "messages"
    EMAILS = "emails"
    PROJECTS = "projects"
    NOTES = "notes"
    RESEARCH = "research"
    CODE = "code"
    DOCUMENTS = "documents"
    CONVERSATIONS = "conversations"
    MEMORIES = "memories"
    ALL = "all"


@dataclass
class SearchQuery:
    text: str
    type: SearchType = SearchType.HYBRID
    sources: list[SearchSource] = field(default_factory=lambda: [SearchSource.ALL])
    tags: list[str] = field(default_factory=list)
    date_from: str = ""
    date_to: str = ""
    person: str = ""
    project: str = ""
    conversation_id: str = ""
    space_id: str = ""
    max_results: int = 50
    min_score: float = 0.0
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    id: str
    title: str
    snippet: str
    source: SearchSource
    source_path: str = ""
    score: float = 0.0
    date: str = ""
    author: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    match_highlights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source.value,
            "source_path": self.source_path,
            "score": self.score,
            "date": self.date,
            "author": self.author,
            "url": self.url,
            "tags": self.tags,
            "metadata": self.metadata,
            "match_highlights": self.match_highlights,
        }


class CrossSourceSearch:
    def __init__(self):
        self._index: dict[str, dict] = {}

    def _tokenize(self, text: str) -> set[str]:
        text = text.lower()
        tokens = set(re.findall(r"[a-z0-9]+", text))
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "has", "have", "had", "do", "does", "did", "will", "would",
                     "could", "should", "may", "might", "shall", "can", "need",
                     "i", "you", "he", "she", "it", "we", "they", "this", "that",
                     "these", "those", "am", "to", "of", "in", "for", "on", "with",
                     "at", "by", "from", "as", "into", "through", "during", "before",
                     "after", "above", "below", "between", "out", "off", "over", "under",
                     "again", "then", "once", "here", "there", "and", "but", "or",
                     "because", "if", "than", "so", "about", "up", "down", "some",
                     "any", "each", "every", "all", "both", "few", "more", "most",
                     "other", "no", "nor", "not", "only", "own", "same", "very",
                     "just", "also", "now", "how", "what", "which", "who", "whom"}
        return tokens - stopwords

    def index_item(self, item_id: str, title: str, content: str, source: SearchSource,
                   source_path: str = "", date: str = "", author: str = "",
                   tags: list[str] | None = None, metadata: dict | None = None):
        tokens = self._tokenize(f"{title} {content}")
        self._index[item_id] = {
            "id": item_id,
            "title": title,
            "content": content,
            "source": source.value,
            "source_path": source_path,
            "date": date,
            "author": author,
            "tags": tags or [],
            "metadata": metadata or {},
            "tokens": tokens,
        }

    def remove_index(self, item_id: str):
        self._index.pop(item_id, None)

    def clear_index(self):
        self._index.clear()

    def _keyword_search(self, query: str, sources: set[str],
                        max_results: int) -> list[SearchResult]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        scored = []
        for item_id, data in self._index.items():
            if "all" not in sources and data["source"] not in sources:
                continue
            content_tokens = data["tokens"]
            matches = q_tokens & content_tokens
            if not matches:
                continue
            score = len(matches) / len(q_tokens)
            title_tokens = self._tokenize(data["title"])
            title_matches = q_tokens & title_tokens
            score += len(title_matches) * 0.2
            if score <= 0:
                continue
            snippet = data["content"][:200] if len(data["content"]) > 200 else data["content"]
            result = SearchResult(
                id=item_id,
                title=data["title"],
                snippet=snippet,
                source=SearchSource(data["source"]),
                source_path=data["source_path"],
                score=score,
                date=data["date"],
                author=data["author"],
                tags=list(data["tags"]),
                metadata=dict(data["metadata"]),
                match_highlights=list(matches),
            )
            scored.append((score, result))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:max_results]]

    def _semantic_search(self, query: str, sources: set[str],
                         max_results: int) -> list[SearchResult]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        scored = []
        for item_id, data in self._index.items():
            if "all" not in sources and data["source"] not in sources:
                continue
            content_tokens = data["tokens"]
            overlap = q_tokens & content_tokens
            if not overlap:
                continue
            jaccard = len(overlap) / len(q_tokens | content_tokens) if (q_tokens | content_tokens) else 0
            if jaccard <= 0:
                continue
            snippet = data["content"][:200] if len(data["content"]) > 200 else data["content"]
            result = SearchResult(
                id=item_id,
                title=data["title"],
                snippet=snippet,
                source=SearchSource(data["source"]),
                source_path=data["source_path"],
                score=jaccard,
                date=data["date"],
                author=data["author"],
                tags=list(data["tags"]),
                metadata=dict(data["metadata"]),
                match_highlights=list(overlap),
            )
            scored.append((jaccard, result))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:max_results]]

    def _nl_search(self, query: str, sources: set[str],
                   max_results: int) -> list[SearchResult]:
        nl_tokens = self._tokenize(query)
        stopwords = {"find", "show", "get", "list", "search", "where", "what",
                     "when", "who", "how", "tell", "give", "all", "related",
                     "about", "from", "with", "for", "me", "my", "the"}
        q_tokens = {t for t in nl_tokens if t not in stopwords}
        if not q_tokens:
            q_tokens = nl_tokens
        return self._keyword_search(" ".join(q_tokens), sources, max_results)

    def _apply_filters(self, results: list[SearchResult], query: SearchQuery) -> list[SearchResult]:
        filtered = results
        if query.tags:
            filtered = [r for r in filtered if any(t in r.tags for t in query.tags)]
        if query.date_from:
            try:
                df = datetime.fromisoformat(query.date_from)
                filtered = [r for r in filtered if r.date and datetime.fromisoformat(r.date) >= df]
            except (ValueError, TypeError):
                pass
        if query.date_to:
            try:
                dt = datetime.fromisoformat(query.date_to)
                filtered = [r for r in filtered if r.date and datetime.fromisoformat(r.date) <= dt]
            except (ValueError, TypeError):
                pass
        if query.person:
            pl = query.person.lower()
            filtered = [r for r in filtered if pl in r.author.lower()]
        if query.project:
            pl = query.project.lower()
            filtered = [r for r in filtered if pl in r.title.lower() or pl in r.snippet.lower()
                        or any(pl in str(v).lower() for v in r.metadata.values())]
        if query.min_score > 0:
            filtered = [r for r in filtered if r.score >= query.min_score]
        return filtered

    def search(self, query: SearchQuery) -> list[SearchResult]:
        sources = set(s.value for s in query.sources)
        if query.type == SearchType.KEYWORD:
            results = self._keyword_search(query.text, sources, query.max_results)
        elif query.type == SearchType.SEMANTIC:
            results = self._semantic_search(query.text, sources, query.max_results)
        elif query.type == SearchType.NATURAL_LANGUAGE:
            results = self._nl_search(query.text, sources, query.max_results)
        else:
            kw_results = self._keyword_search(query.text, sources, query.max_results)
            sm_results = self._semantic_search(query.text, sources, query.max_results)
            seen = set()
            combined = []
            for r in kw_results + sm_results:
                if r.id not in seen:
                    seen.add(r.id)
                    combined.append(r)
            combined.sort(key=lambda x: x.score, reverse=True)
            results = combined[:query.max_results]
        return self._apply_filters(results, query)

    def get_index_stats(self) -> dict:
        source_counts: dict[str, int] = {}
        for data in self._index.values():
            s = data["source"]
            source_counts[s] = source_counts.get(s, 0) + 1
        return {
            "total_items": len(self._index),
            "items_by_source": source_counts,
        }
