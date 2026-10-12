"""Hybrid retrieval with budget + explanations (P41-47, P64) and working
memory slots (P3)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agent.memory_os.models import (
    CONFIDENCE_ORDER,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
)
from agent.memory_os.security import AccessContext, check_read_access


SemanticFn = Callable[[str, str], float]   # (query, content) -> 0..1


@dataclass
class RetrievalHit:
    item: MemoryItem
    score: float
    why: List[str] = field(default_factory=list)

    def explanation(self) -> str:
        """P64 — why retrieved / where from / when stored / why relevant."""
        p = self.item.provenance
        bits = [f"score={self.score:.2f}"] + self.why
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.item.created_at))
        actor = p.actor or "unknown"
        return (
            f"[{', '.join(bits)}] source={self.item.source_type.value}"
            f" via {actor} at {when}"
            f" confidence={self.item.confidence.value}"
        )


@dataclass
class RetrievalResult:
    hits: List[RetrievalHit]
    query: str
    total_candidates: int = 0

    def context_block(self, max_chars: int = 4000) -> str:
        lines = []
        used = 0
        for h in self.hits:
            line = f"- ({h.item.type.value}) {h.item.summary or h.item.content}"
            if used + len(line) > max_chars:
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(lines)


class Retriever:
    def __init__(self, store):
        self._store = store
        self._semantic: Optional[SemanticFn] = None

    # P71 — abstract embedding provider injection point.
    def set_semantic_scorer(self, fn: Optional[SemanticFn]) -> None:
        self._semantic = fn

    # ------------------------------------------------------------------ search

    def search(
        self,
        query: str,
        ctx: AccessContext,
        *,
        top_k: int = 8,
        types: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        include_stale: bool = False,
        min_score: float = 0.05,
        now: Optional[float] = None,
    ) -> RetrievalResult:
        now = now or time.time()
        candidates = self._gather(query, types=types, scopes=scopes,
                                  project_id=project_id)
        hits: List[RetrievalHit] = []
        for item in candidates:
            if not item.temporally_valid(now):
                continue  # P28 validity windows honored at retrieval time
            if not check_read_access(item, ctx):
                continue
            score, why = self._score(item, query, now)
            if not include_stale and item.needs_revalidation(now):
                why.append("stale-flag")
                score -= 0.15
            if score >= min_score:
                item.touch_access()
                hits.append(RetrievalHit(item=item, score=round(score, 4), why=why))
        hits.sort(key=lambda h: h.score, reverse=True)
        top = hits[:top_k]
        # P26 last-used tracking: one batched write for the returned page.
        self._store.touch_items([h.item.memory_id for h in top], at=now)
        self._store.bump_counter("retrievals", delta=len(top))
        self._store.bump_counter("queries")
        return RetrievalResult(top, query, len(candidates))

    def _gather(self, query: str, *, types=None, scopes=None,
                project_id=None) -> List[MemoryItem]:
        active = [MemoryStatus.ACTIVE, MemoryStatus.CANDIDATE]
        pool = {}
        for it in self._store.query_items(statuses=active, types=types,
                                          scopes=scopes, limit=2000):
            pool[it.memory_id] = it
        lex_ids = {mid for mid, _ in self._store.fts_search(query, limit=200)}
        out = []
        seen = set()
        # FTS matches first (they are pre-scored), then rest of active pool.
        for mid in lex_ids:
            it = pool.get(mid) or self._store.get_item(mid)
            if it is None or mid in seen:
                continue
            if it.status not in (MemoryStatus.ACTIVE, MemoryStatus.CANDIDATE):
                continue  # never resurrect superseded/quarantined rows via FTS
            if project_id is not None and it.project_id != project_id:
                continue
            seen.add(mid)
            out.append(it)
        for it in pool.values():
            if it.memory_id in seen:
                continue
            if project_id is not None and it.project_id != project_id:
                continue
            out.append(it)
        return out

    # ------------------------------------------------------------------ scoring

    def _lex_score(self, item: MemoryItem, query: str) -> float:
        q_tokens = {t.lower() for t in query.split() if len(t) > 2}
        if not q_tokens:
            return 0.0
        text = f"{item.content} {item.summary} {' '.join(item.tags)}".lower()
        overlap = sum(1 for t in q_tokens if t in text)
        base = overlap / len(q_tokens)
        # exact phrase bonus
        if query.strip().lower() and query.strip().lower() in text:
            base = min(1.0, base + 0.25)
        return base

    def _recency(self, item: MemoryItem, now: float) -> float:
        age_days = max(0.0, (now - item.updated_at)) / 86400.0
        return math.exp(-age_days / 45.0)  # ~half-life feel without decay writes

    def _graph_boost(self, item: MemoryItem) -> float:
        if not item.entity_ids:
            return 0.0
        return min(0.15, 0.05 * len({e for e in item.entity_ids}))

    def _score(self, item: MemoryItem, query: str, now: float):
        why: List[str] = []
        score = 0.0
        lex = self._lex_score(item, query)
        if lex > 0:
            score += 0.45 * lex
            why.append(f"keyword:{lex:.2f}")
        sem = 0.0
        if self._semantic is not None:
            sem = max(0.0, min(1.0, float(self._semantic(query, item.content))))
            score += 0.30 * sem
            why.append(f"semantic:{sem:.2f}")
        key_match = bool(item.semantic_key and item.semantic_key in query.lower())
        if not (lex > 0 or sem > 0 or key_match):
            # P82 precision guard: no relevance signal -> no retrieval.
            return 0.0, []
        rec = self._recency(item, now)
        score += 0.10 * rec
        conf = CONFIDENCE_ORDER[item.confidence]
        score += 0.08 * conf
        score += 0.07 * max(0.0, min(1.0, item.importance))
        gb = self._graph_boost(item)
        if gb > 0:
            score += gb
            why.append("entity-link")
        if key_match:
            score += 0.2
            why.append("key-match")
        if item.scope == MemoryScope.PROJECT and item.project_id:
            why.append(f"project:{item.project_id}")
        if item.status == MemoryStatus.CANDIDATE:
            why.append("candidate")
            score -= 0.05
        return score, why


# ---------------------------------------------------------------------------
# Working memory (P3) — session-scoped structured slots.
# ---------------------------------------------------------------------------

WORKING_SLOTS = (
    "objective", "entities", "constraints", "files",
    "tools", "decisions", "pending", "task_state",
)


class WorkingMemory:
    def __init__(self, store, session_id: str):
        self._store = store
        self.session_id = session_id

    def set(self, slot: str, payload: Any) -> None:
        if slot not in WORKING_SLOTS:
            raise ValueError(f"unknown working slot '{slot}'")
        self._store.set_slot(self.session_id, slot, {"value": payload})

    def get(self, slot: str) -> Any:
        d = self._store.get_slot(self.session_id, slot) or {}
        return d.get("value")

    def all(self) -> Dict[str, Any]:
        return {
            slot: self.get(slot)
            for slot in WORKING_SLOTS
            if self.get(slot) is not None
        }

    def snapshot_as_episodic(self, *, owner: str = "default") -> MemoryItem:
        state = self.all()
        lines = [f"{k}: {v}" for k, v in state.items()]
        item = MemoryItem(
            type=MemoryType.EPISODIC,
            content="working-session snapshot\n" + "\n".join(lines),
            summary=f"working snapshot session={self.session_id}",
            scope=MemoryScope.TASK,
            owner=owner,
            status=MemoryStatus.ACTIVE,
            metadata={"session_id": self.session_id},
        )
        item.provenance.origin_event = "working-snapshot"
        item.provenance.actor = "system"
        self._store.upsert_item(item, actor="working-memory", note="snapshot")
        return item

    def clear(self) -> None:
        self._store.clear_slots(self.session_id)
