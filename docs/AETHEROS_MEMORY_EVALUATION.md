# AetherOS Memory 2.0 — Evaluation (Master 41)

## Synthetic fixtures (`tests/aetheros_memory_intelligence/test_memory2.py`)

| Fixture | Setup | Expected |
|---|---|---|
| Preference evolution | Prefer A (confirmed) → supersede with B | B active, A superseded |
| Project isolation | Secret in Alpha, query from Beta | Alpha memory not retrieved |
| Temporal reasoning | API-version facts | currently-valid prioritized |
| Contradiction | tabs vs spaces (both confirmed) | newest-wins supersede |
| Research reuse | fresh claim + evidence | reuse/revalidate decision |

## Benchmarks (`scripts/benchmark_memory2.py`, measured 2026-09-04)

Environment: Windows, CPython 3.12 (uv), temp-dir store.

| Metric | 1k records | 10k | 100k | 1M |
|---|---|---|---|---|
| Write throughput | 16.3/s (61.4s) | BLOCKED | NOT RUN | NOT RUN |
| Retrieval p50 (top-8, project-scoped) | 6.0ms | BLOCKED | NOT RUN | NOT RUN |
| Retrieval max | 7.5ms | BLOCKED | NOT RUN | NOT RUN |
| Graph write 200 nodes+edges | 1.7s | — | — | — |
| Graph traverse depth-3 | <0.1ms | — | — | — |
| Consolidate | 0.3s, 5 created | — | — | — |
| Health score | 0.996 | — | — | — |

10k: BLOCKED — full-file JSON rewrite per write is O(n²); the 10k run
exceeded the 15-minute command budget in this environment. Mitigation path:
SQLite/FTS-backed `RecordStore`. 100k/1M: NOT RUN (same blocker).

## Quality tracking

`MemoryService.quality()` reports duplicates, contradictions, stale,
unsupported, privacy violations, secret leaks, orphan relations, broken
provenance — all measured from live records. `health()` folds them into a
score starting at 1.0 with per-issue deductions (never a fake 99%).
