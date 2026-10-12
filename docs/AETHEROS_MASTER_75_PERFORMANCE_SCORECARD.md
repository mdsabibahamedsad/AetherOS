# AetherOS Master 75 Performance Scorecard — 1.0.0

No production measurements exist (no packaged build, no perf lab run in this
phase). This scorecard records the gate state honestly rather than numbers.

| Metric | Baseline | 1.0.0 measured | Threshold source | Status |
|---|---|---|---|---|
| startup | prior benchmark report* | UNMEASURED | project thresholds | UNVERIFIED |
| memory | prior benchmark report* | UNMEASURED | project thresholds | UNVERIFIED |
| CPU | prior benchmark report* | UNMEASURED | project thresholds | UNVERIFIED |
| IPC | — | UNMEASURED | comparePerf() default 10% | UNVERIFIED |
| agent execution | — | UNMEASURED | explicit per-run | UNVERIFIED |
| browser / computer-use | — | UNMEASURED | explicit per-run | UNVERIFIED |
| update (check/dl/install) | harness timings only | no prod timing | update gates | UNVERIFIED |

\* `AETHEROS_BENCHMARK_REPORT.md` (dev-environment, pre-existing — NOT
production evidence). Gate fails closed: `comparePerf()` returns UNVERIFIED on
missing data and the release pipeline must not promote on UNVERIFIED perf.
