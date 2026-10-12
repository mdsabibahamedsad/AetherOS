# AetherOS Automation — Evaluation (Master 43)

Harness: `scripts/benchmark_autonomy.py` (virtual clock, no real waiting).
Raw: `aetheros_autonomy/bench_results.json`. Env: Windows, CPython 3.12,
2026-09-04. No LLM judge; oracles are asserts on state.

## Scheduler scale (measured)

| Defs | Create | Tick (all due) | Runs started | Trigger match | RSS |
|---|---|---|---|---|---|
| 100 | 0.44s | 0.07s | 100 | 0.0ms | 29MB |
| 1,000 | 31.7s | 0.63s | 1,000 | 1.0ms | 35MB |
| 10,000 | BLOCKED | — | — | — | — |

10k BLOCKED: definition create path is O(n²) (full-file rewrite per
save); projected >30 min. Tick path itself scales (batched persist:
1000-run tick 409s → 0.63s after fix). Mitigation: SQLite backend
(same path as Master 41/42 stores).

## Concurrency (measured)

| Runs | Completed | Wall |
|---|---|---|
| 10 | 10 | 0.02s |
| 50 | 50 | 0.04s |
| 100 | 100 | 0.08s |

500: NOT RUN (environment time box; pool supports it).

## Quality signals (from test suite, 35 tests)

Trigger accuracy (match/mismatch), idempotent delivery (no double-fire),
missed-policy matrix, recursion block counter, retry/backoff values,
recovery→resume→verify path, notification precision (auth denials),
dry-run purity (zero sends), version diff/rollback round-trip.
