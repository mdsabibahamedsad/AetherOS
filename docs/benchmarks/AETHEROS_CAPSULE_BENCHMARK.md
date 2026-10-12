# AetherOS Capsule Benchmark

Runner: `kernel/core/hypervisor/benchmark.py::run_capsule_benchmarks`
(also `aetheros capsule benchmark`). Real `perf_counter` measurements on
the executing host; never compared across machines, never invented.

## Results — reference host (Windows, Python 3.11.15, 20 iterations)

| op | n | p50 (ms) | p95 (ms) | p99 (ms) | mean (ms) |
|---|---|---|---|---|---|
| capsule.create | 5 | 61.306 | 136.255 | 136.255 | 75.602 |
| capsule.mediate | 20 | 0.008 | 0.033 | 0.033 | 0.010 |
| capsule.policy_evaluate | 20 | 0.010 | 0.050 | 0.050 | 0.013 |
| capsule.checkpoint | 5 | 2.941 | 4.268 | 4.268 | 3.165 |
| capsule.restore | 5 | 0.060 | 0.083 | 0.083 | 0.060 |
| capsule.replay_observe | 5 | 0.001 | 0.003 | 0.003 | 0.002 |

`capsule.create` includes kernel admission + FS provisioning + manifest
seal + risk scoring. Mediation overhead (manifest + budgets + receipt) is
~8µs p50 — policy checks are cheap enough for per-call enforcement.

## Isolation probes (§109)

- filesystem_escape: 6/6 denied — PASS
- network_escape: 4/4 blocked — PASS

## Not measured (honestly unmeasured)

Crash/restart recovery timing, checkpoint-transfer migration timing
(remote), 10/100/1000-agent scheduler stress, GPU quotas (NOT_SUPPORTED),
long-run leak drift (§116 — procedure documented in the test plan, no
multi-hour run executed here). No claim is made for these beyond the
functional tests.
