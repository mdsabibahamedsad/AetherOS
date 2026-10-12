"""Deterministic hybrid relevance scoring (Master 41 section 10).

score = w_sem*semantic + w_lex*lexical + w_scope*scope + w_ent*entity
      + w_tmp*temporal + w_task*task + w_proj*project + w_imp*importance
      + w_conf*confidence + w_fresh*freshness + w_rec*recency
      - w_contra*contradiction - w_stale*stale - w_priv*privacy - w_red*redundancy

All weights configurable via ``ScoringWeights`` (documented defaults, no
magic numbers elsewhere).  Sub-scores are pure functions for testability.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.record import MemoryRecord, RecordScope


@dataclass
class ScoringWeights:
    semantic: float = 1.0
    lexical: float = 1.0
    scope: float = 0.8
    entity: float = 0.7
    temporal: float = 0.5
    task: float = 0.6
    project: float = 0.9
    importance: float = 0.5
    confidence: float = 0.7
    freshness: float = 0.5
    recency: float = 0.3
    contradiction: float = 2.0
    stale: float = 1.2
    privacy: float = 1.5
    redundancy: float = 0.8

    def to_dict(self) -> Dict[str, float]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "ScoringWeights":
        if not d:
            return cls()
        known = set(cls.__dataclass_fields__)
        return cls(**{k: float(v) for k, v in d.items() if k in known})


_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def lexical_relevance(query: str, record: MemoryRecord) -> float:
    qt = tokenize(query)
    if not qt:
        return 0.0
    hay = tokenize(f"{record.content} {record.summary}")
    if not hay:
        return 0.0
    hay_set = set(hay)
    hits = sum(1 for t in qt if t in hay_set)
    return hits / len(qt)


def bm25_lite(query: str, record: MemoryRecord) -> float:
    """Small BM25-ish lexical score (no corpus stats needed)."""
    qt = tokenize(query)
    if not qt:
        return 0.0
    toks = tokenize(f"{record.content} {record.summary}")
    if not toks:
        return 0.0
    n = len(toks)
    score = 0.0
    for t in set(qt):
        tf = toks.count(t)
        idf = 1.0  # single-doc mode: uniform idf
        score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * n / 100.0))
    return min(1.0, score / max(1, len(set(qt))))


def scope_match(record_scope: RecordScope, query_scope: RecordScope) -> float:
    if record_scope == query_scope:
        return 1.0
    if record_scope == RecordScope.GLOBAL:
        return 0.6
    return 0.3


def entity_match(record_entities: List[str], query_entities: List[str]) -> float:
    if not query_entities:
        return 0.0
    hit = len(set(record_entities) & set(query_entities))
    return min(1.0, hit / max(1, len(query_entities)))


def temporal_relevance(record: MemoryRecord, now: Optional[float] = None,
                       query_start: float = 0.0, query_end: float = 0.0) -> float:
    now = now if now is not None else time.time()
    if query_start or query_end:
        t = record.observed_at or record.created_at
        if query_start and t < query_start:
            return 0.0
        if query_end and t > query_end:
            return 0.0
        return 1.0
    if not record.is_currently_valid(now):
        return 0.0
    return 1.0


def freshness(record: MemoryRecord, now: Optional[float] = None,
              half_life_days: float = 90.0) -> float:
    now = now if now is not None else time.time()
    if record.last_confirmed:
        age_days = (now - record.last_confirmed) / 86400.0
    else:
        age_days = (now - record.updated_at) / 86400.0
    if age_days <= 0:
        return 1.0
    return math.exp(-age_days * math.log(2) / max(1.0, half_life_days))


def recency(record: MemoryRecord, now: Optional[float] = None) -> float:
    now = now if now is not None else time.time()
    age_days = (now - record.created_at) / 86400.0
    if age_days <= 1:
        return 1.0
    if age_days >= 365:
        return 0.0
    return 1.0 - (age_days / 365.0)


@dataclass
class ScoreBreakdown:
    total: float = 0.0
    parts: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"total": round(self.total, 4),
                "parts": {k: round(v, 4) for k, v in self.parts.items()}}


def score_record(record: MemoryRecord, query: str, *,
                 weights: Optional[ScoringWeights] = None,
                 query_scope: RecordScope = RecordScope.USER,
                 query_entities: Optional[List[str]] = None,
                 query_task_id: str = "", query_project_id: str = "",
                 semantic_sim: float = 0.0,
                 contradicted: bool = False,
                 redundant_with_selected: bool = False,
                 now: Optional[float] = None) -> ScoreBreakdown:
    w = weights or ScoringWeights()
    now = now if now is not None else time.time()
    lex = max(lexical_relevance(query, record), bm25_lite(query, record))
    parts: Dict[str, float] = {
        "semantic": w.semantic * semantic_sim,
        "lexical": w.lexical * lex,
        "scope": w.scope * scope_match(record.scope, query_scope),
        "entity": w.entity * entity_match(record.entity_ids, query_entities or []),
        "temporal": w.temporal * temporal_relevance(record, now),
        "task": w.task * (1.0 if query_task_id and record.task_id == query_task_id else 0.0),
        "project": w.project * (1.0 if query_project_id and record.project_id == query_project_id else 0.0),
        "importance": w.importance * record.importance,
        "confidence": w.confidence * record.confidence,
        "freshness": w.freshness * freshness(record, now),
        "recency": w.recency * recency(record, now),
    }
    penalties = 0.0
    pen_parts: Dict[str, float] = {}
    if contradicted or record.status.value == "conflicted":
        pen_parts["contradiction"] = w.contradiction * 1.0
    if record.status.value in ("stale", "expired") or not record.is_currently_valid(now):
        pen_parts["stale"] = w.stale * 1.0
    if record.privacy_class.value in ("sensitive", "secret"):
        pen_parts["privacy"] = w.privacy * record.sensitivity
    if redundant_with_selected:
        pen_parts["redundancy"] = w.redundancy * 1.0
    penalties = sum(pen_parts.values())
    total = sum(parts.values()) - penalties
    merged = {**parts, **{f"-{k}": v for k, v in pen_parts.items()}}
    return ScoreBreakdown(total=total, parts=merged)
