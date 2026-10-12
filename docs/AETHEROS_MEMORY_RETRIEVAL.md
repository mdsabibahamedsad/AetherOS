# AetherOS Memory 2.0 — Retrieval, Scoring, Budget (Master 41)

## Pipeline (`hybrid.py::HybridRetriever`)

Query → `parse_query` (temporal windows like "last 14 days", quoted entity
hints) → scope isolation pre-filter (deleted/expired never returned) →
channels: lexical, semantic (pluggable `embedding_fn`, Jaccard fallback so
offline works), graph (entity-hint expansion via `GraphStore.neighbors`),
project, episodic, research → fusion → `scoring.py` rerank → redundancy
penalty → top-k → usage counters touched.

Modes: `exact|semantic|temporal|project|entity|graph|research|episodic|
global|hybrid` (default `hybrid`).

## Scoring (`scoring.py`)

```
score = w_sem*semantic + w_lex*lexical + w_scope*scope + w_ent*entity
      + w_tmp*temporal + w_task*task + w_proj*project + w_imp*importance
      + w_conf*confidence + w_fresh*freshness + w_rec*recency
      - w_contra*contradiction - w_stale*stale - w_priv*privacy - w_red*redundancy
```

Defaults in `ScoringWeights` (all configurable, documented in code).
Sub-scores are pure functions (`lexical_relevance`, `bm25_lite`,
`scope_match`, `entity_match`, `temporal_relevance`, `freshness`,
`recency`) — unit-tested for determinism.

## Budget (`budget.py::MemoryBudgetManager`)

Priority: task constraints → explicit user instructions → project state →
decisions → recent events → validated research → stable preferences →
historical context. Token estimate = chars/4 (documented heuristic) + 24
framing overhead per record. Returns included/excluded + tokens used.

## Global questions

" Catch me up on the last two weeks" is served by `get_timeline` +
`get_project_memory` + graph neighbors — not naive top-k. See service API.
