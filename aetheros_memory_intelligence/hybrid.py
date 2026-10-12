"""Hybrid memory retriever (Master 41 sections 8-9, 45, 48-49).

Pipeline: intent/scope/entity/temporal detection -> candidate retrieval
(lexical + semantic + graph + project + episodic + research) -> fusion ->
rerank (scoring.py) -> conflict flags -> freshness/confidence -> budgeting.

Semantic channel is pluggable via ``embedding_fn`` (defaults to token-Jaccard
so offline works; wire a real embedding engine when configured).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_memory_intelligence.graph_store import GraphStore
from aetheros_memory_intelligence.record import (
    MemoryRecord, RecordScope, RecordStatus, scope_visible,
)
from aetheros_memory_intelligence.scoring import (
    ScoringWeights, lexical_relevance, score_record, tokenize,
)

EmbeddingFn = Callable[[str], List[float]]


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@dataclass
class RetrievalQuery:
    text: str = ""
    scope: RecordScope = RecordScope.USER
    project_id: str = ""
    task_id: str = ""
    session_id: str = ""
    user_id: str = ""
    workspace_id: str = ""
    entity_names: List[str] = field(default_factory=list)
    record_types: List[str] = field(default_factory=list)
    start_ts: float = 0.0
    end_ts: float = 0.0
    mode: str = "hybrid"  # exact|semantic|temporal|project|entity|graph|research|episodic|global|hybrid
    top_k: int = 8


@dataclass
class RetrievedRecord:
    record: MemoryRecord
    score: float = 0.0
    channels: List[str] = field(default_factory=list)
    breakdown: Dict[str, Any] = field(default_factory=dict)
    conflicted: bool = False
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.record.id, "type": self.record.type.value,
                "scope": self.record.scope.value, "score": round(self.score, 4),
                "channels": self.channels, "confidence": self.record.confidence,
                "confidence_band": self.record.confidence_band.value,
                "status": self.record.status.value,
                "summary": self.record.summary, "content": self.record.content[:500],
                "project_id": self.record.project_id,
                "conflicted": self.conflicted, "explanation": self.explanation,
                "breakdown": self.breakdown}


_TEMP_RE = re.compile(r"(last|past)\s+(\d+)\s+(day|week|month|year)s?", re.I)


def parse_query(query: RetrievalQuery) -> RetrievalQuery:
    """Lightweight intent/temporal/entity detection over the query text."""
    m = _TEMP_RE.search(query.text)
    if m and not query.start_ts:
        n, unit = int(m.group(2)), m.group(3).lower()
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit] * n
        now = time.time()
        query.end_ts = now
        query.start_ts = now - days * 86400.0
    # Quoted spans are treated as entity hints.
    quoted = re.findall(r'"([^"]+)"', query.text)
    for q in quoted:
        if q not in query.entity_names:
            query.entity_names.append(q)
    return query


class HybridRetriever:
    def __init__(self, records: Callable[[], List[MemoryRecord]],
                 *, graph: Optional[GraphStore] = None,
                 weights: Optional[ScoringWeights] = None,
                 embedding_fn: Optional[EmbeddingFn] = None) -> None:
        self._records = records
        self._graph = graph
        self._weights = weights or ScoringWeights()
        self._embedding_fn = embedding_fn

    # -- channels -------------------------------------------------------
    def _semantic_sim(self, query: str, record: MemoryRecord) -> float:
        if self._embedding_fn is not None:
            try:
                qv, dv = self._embedding_fn(query), self._embedding_fn(record.content)
                if qv and dv and len(qv) == len(dv):
                    dot = sum(a * b for a, b in zip(qv, dv))
                    nq = sum(a * a for a in qv) ** 0.5
                    nd = sum(b * b for b in dv) ** 0.5
                    if nq and nd:
                        return max(0.0, dot / (nq * nd))
            except Exception:
                pass
        return _jaccard(query, f"{record.content} {record.summary}")

    def retrieve(self, query: RetrievalQuery) -> List[RetrievedRecord]:
        query = parse_query(query)
        now = time.time()
        all_records = self._records()
        # Global pre-filter: deleted never returned; scope isolation enforced.
        eligible = [r for r in all_records
                    if r.status not in (RecordStatus.DELETED, RecordStatus.EXPIRED)
                    and scope_visible(r.scope, query.scope,
                                      record_project=r.project_id,
                                      query_project=query.project_id)]
        if query.record_types:
            eligible = [r for r in eligible if r.type.value in query.record_types]
        if query.start_ts or query.end_ts:
            eligible = [r for r in eligible
                        if (not query.start_ts or (r.observed_at or r.created_at) >= query.start_ts)
                        and (not query.end_ts or (r.observed_at or r.created_at) <= query.end_ts)]

        # Graph channel: expand entity hints to related entity ids.
        graph_ids: set = set()
        if self._graph is not None and query.entity_names:
            for name in query.entity_names:
                ent = self._graph.find_entity(name)
                if ent is not None:
                    graph_ids.add(ent.id)
                    sub = self._graph.neighbors(ent.id, depth=1,
                                                project_id=query.project_id)
                    for e in sub["entities"]:
                        graph_ids.add(e["id"])

        scored: List[RetrievedRecord] = []
        for rec in eligible:
            channels: List[str] = []
            mode = query.mode
            want_lex = mode in ("hybrid", "exact", "global")
            want_sem = mode in ("hybrid", "semantic", "global")
            want_graph = mode in ("hybrid", "graph", "entity", "global")
            want_proj = mode in ("hybrid", "project", "global")
            want_epi = mode in ("hybrid", "episodic", "temporal", "global")
            want_res = mode in ("hybrid", "research", "global")

            lex = lexical_relevance(query.text, rec)
            if want_lex and lex > 0:
                channels.append("lexical")
            sem = self._semantic_sim(query.text, rec) if want_sem else 0.0
            if want_sem and sem > 0.05:
                channels.append("semantic")
            if want_graph and (set(rec.entity_ids) & graph_ids):
                channels.append("graph")
            if want_proj and query.project_id and rec.project_id == query.project_id:
                channels.append("project")
            if want_epi and rec.type.value == "episodic_event":
                channels.append("episodic")
            if want_res and rec.type.value in ("research_finding", "source_memory"):
                channels.append("research")
            if mode != "hybrid" and not channels:
                continue
            if mode == "hybrid" and not channels and lex == 0 and sem <= 0.05:
                continue
            bd = score_record(rec, query.text, weights=self._weights,
                              query_scope=query.scope,
                              query_entities=list(graph_ids),
                              query_task_id=query.task_id,
                              query_project_id=query.project_id,
                              semantic_sim=sem, now=now)
            scored.append(RetrievedRecord(
                record=rec, score=bd.total, channels=channels,
                breakdown=bd.to_dict(),
                explanation=f"channels={','.join(channels) or 'score-only'} "
                            f"conf={rec.confidence:.2f} status={rec.status.value}"))
        # Redundancy penalty: second record sharing long content prefix sinks.
        scored.sort(key=lambda r: r.score, reverse=True)
        seen_prefixes: List[str] = []
        for r in scored:
            prefix = r.record.content[:80].lower()
            r.conflicted = r.record.status == RecordStatus.CONFLICTED
            if any(prefix and prefix == p for p in seen_prefixes):
                r.score -= self._weights.redundancy
                r.explanation += " redundancy-penalty"
            elif prefix:
                seen_prefixes.append(prefix)
        scored.sort(key=lambda r: r.score, reverse=True)
        # Touch usage counters for returned records.
        for r in scored[:query.top_k]:
            r.record.mark_used(now)
        return scored[:query.top_k]
