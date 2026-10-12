# AetherOS Master 76 Performance Validation (host-local, labeled)

Production benchmarks: UNVERIFIED (no prod build until this phase, no lab).
Real measured durations on win32-x64 / Node v25.5.0 (evidence in logs):
tsc full typecheck ~2–3 min; vite renderer build 14.53s; electron download
138MB in 1m55s; vitest full 811 tests ~47–54s; wrapper CLI suites as logged;
artifacts 178–188MB. Micro-timings (perf-micro.json, clearly NOT prod
benchmarks): canonicalize ~11.5µs, RSA-2048 sign ~4.7ms, verify ~0.13ms.
Update overhead/startup/CPU/memory/agent latencies on prod bits: UNMEASURED.
comparePerf() gates remain fail-closed on missing data.
