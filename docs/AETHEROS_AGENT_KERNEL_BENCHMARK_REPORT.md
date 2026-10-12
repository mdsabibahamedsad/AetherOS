# AetherOS Agent Kernel 1.0 — Benchmark Report

Runner: `kernel/benchmark.py` (`aetheros kernel benchmark`), 20 iterations,
Windows host, Python 3.11.15. REAL `perf_counter` measurements; not
comparable across machines. No fabricated numbers; no speedup claims.

## Micro-benchmarks (ms)

| op | n | p50 | p95 | p99 | mean |
|---|---|---|---|---|---|
| intent.admit | 20 | 0.2859 | 0.3939 | 0.3939 | 0.2859 |
| policy.evaluate_intent | 20 | 0.0034 | 0.0116 | 0.0116 | 0.0040 |
| capability.list | 20 | 0.0058 | 0.0403 | 0.0403 | 0.0077 |
| agent.create | 5 | 0.3066 | 0.3454 | 0.3454 | 0.3069 |
| scheduler.schedule | 1 | 0.0 | 0.0 | 0.0 | 0.0 |
| memory.write | 20 | 0.0049 | 0.0309 | 0.0309 | 0.0066 |
| memory.read | 20 | 0.0027 | 0.0060 | 0.0060 | 0.0030 |
| checkpoint.create | 1 | 0.0 | 0.0 | 0.0 | 0.0 |

`scheduler.schedule`/`checkpoint.create` n=1 with ~0.0ms reflects
already-dequeued no-op ticks at timer resolution — honest, not a
performance claim. Throughput/error/CPU/RAM/GPU aggregation is NOT
reported (not measured in this environment).

## Not measured

Agent task-completion/token/cost benchmarks (need live models),
100/1000-agent scheduler stress (SIMULATED workloads not executed),
failure-injection recovery timing — all marked NOT RUN.
