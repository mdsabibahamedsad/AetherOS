# AetherOS Swarm — Benchmarks (Master 42)

Harness: `scripts/benchmark_swarm.py`. Deterministic oracle tasks, no LLM
judge, model/task/tools held constant (LocalFunctionExecutor, 20ms
simulated step latency). Raw JSON: `aetheros_swarm/bench_results.json`.
Env: Windows, CPython 3.12 (uv), 2026-09-04.

## Head-to-head (single vs multi, same goal)

| Task | Single (lat/tok/cost) | Multi (topo, agents, lat/tok/cost) | Verified |
|---|---|---|---|
| simple | 0.024s / 300 / $0.00090 | single chosen (no force effect) | no (no verifier) |
| parallel | 0.022s / 300 / $0.00090 | hierarchical, 2 agents, 0.045s / 270 / $0.00050 | no |
| dependency | 0.023s / 300 / $0.00090 | supervisor, 3 agents, 0.065s / 530 / $0.00140 | YES |
| research | 0.026s / 300 / $0.00090 | supervisor, 3 agents, 0.044s / 530 / $0.00140, 2/3 ok | no |
| coding | 0.022s / 300 / $0.00090 | single chosen | no |
| conflict | 0.021s / 300 / $0.00090 | single chosen | no |
| budget | 0.023s / 300 / $0.00090 | supervisor, 2 agents, 0.048s / 450 / $0.00120 | no |
| research[parallel] | — | parallel, 3 agents, 0.026s / 390 / $0.00070, 3/3 | no |
| research[review_loop] | — | review_loop, 3 agents, 0.068s / 480 / $0.00150, 3/3 | YES |

16/16 runs completed. Partial credit visible (research multi: 2/3
subtasks ok). `verified=True` only when a verifier agent actually ran —
synthesis never upgrades (`mixed` otherwise).

## Reading

- Decision engine correctly keeps simple/coding/conflict tasks single.
- Parallelism pays latency dividends only with real parallel work; with
  20ms simulated steps the coordination overhead dominates — honest
  small-scale numbers, not a scaling claim.
- research[parallel] (0.026s) vs research[review_loop] (0.068s) shows the
  verification cost explicitly.

## Not claimed

No LLM-backed runs, no cross-provider comparison, no large-scale
speedup claim. Production LLM evaluation (DelegateExecutor) is NOT RUN
here — it requires provider credentials and budget.
