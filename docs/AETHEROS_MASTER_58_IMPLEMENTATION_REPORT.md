# AetherOS Master 58 — Agent Hypervisor 1.0: Implementation Report

## Architecture

New `kernel/core/hypervisor/` package (types, profiles, guards,
isolation, filesystem, secrets, risk, hypervisor, api, benchmark)
integrated into `AgentKernel` as a first-class subsystem (service
registration, init, shutdown-first ordering, `status()` surface,
`KernelSDK.capsules`). No second desktop, no replaced architecture, no
fake VM: the hypervisor layers over the strongest *detected* host
primitive and labels the rest honestly. CLI: `aetheros capsule …`
(22 verbs) via `security_integration.py`, reusing the sandbox-command
pattern; dangerous verbs require `--force`; cross-process `list/inspect`
read a persisted registry snapshot explicitly marked non-live.

## Capsule Runtime

Implemented: 15-state lifecycle with validated transitions + Kernel
events + audit; admission pipeline (intent→authority→policy→risk→
resources→isolation); 14 profiles (defaults, never bypasses); sealed
capability manifests (deny-by-default, live revocation with reseal);
per-capsule virtual FS (7 logical dirs, 6 mount types, COW,
artifact discipline); explicit network policy; capability-mediated
SecretBroker (scoped/bound/TTL/rotated/revoked/audited, plaintext only
to provider callbacks); deterministic risk + 8-scope blast radius;
quotas/budgets, circuit breakers, rate buckets, recursion/depth/child/
capacity guards, swarm collective quotas, automation budgets; mediated
`invoke()` (operability→manifest→breaker→rate→budget→net/screen/secret
policy→kernel→chained receipt+egress); quarantine→forensic→recover/
destroy pipeline; versioned integrity-sealed snapshots, restore,
local migration with rollback; 4-mode replay (OBSERVE_ONLY default,
external effects never auto-executed); handoff with revalidation;
takeover with suspension; policy re-evaluation (5 verdicts);
placement decisions; receipts chained per capsule; tamper-evident audit
via kernel AuditEngine; GC + leak scan; health states; registry
persistence; CapsuleAPI (`capsules.*`); preview/simulate/diff.

## Isolation

Detected, never assumed: LEVEL_0 native process (SUPPORTED everywhere),
LEVEL_1 via Windows Job Objects where the probe succeeds / firejail /
Windows Sandbox / containers only when present (else
REQUIRES_CONFIGURATION), LEVEL_2 containers only with reachable daemon,
LEVEL_3 VM and LEVEL_4 host UNAVAILABLE in 1.0. Profile floors enforced
(refuse, never silently downgrade). Reference host: strongest =
level_1_sandboxed_process.

## Resource Enforcement

Admission denial naming the limit; lean profile slices (sessions only
where semantically needed); agent allocation scoped to the slice;
admission-reservation leak fixed (released post-allocation); per-call
tool/network/spawn budgets; GPU honestly NOT_SUPPORTED
(accounting-only).

## Security

See `docs/security/AETHEROS_CAPSULE_THREAT_MODEL.md` (+ escape-test doc):
§111 invariants ×11, §112 path/SSRF/symlink/env probes,
§113 injection payloads, §114 malicious-agent containment,
§115 chaos subset — all executable in
`tests/kernel/test_agent_capsule_security.py`.

## Tests

Exact commands (repo convention, per-file hermetic):
`scripts/run_tests.sh tests/kernel/test_agent_capsule.py`,
`scripts/run_tests.sh tests/kernel/test_agent_capsule_security.py`
(Windows direct: `<venv>\Scripts\python.exe -m pytest
tests/kernel/test_agent_capsule*.py -q`).

## Results

`tests/kernel/`: **283 passed** (202 pre-existing + 26 capsule + 55
capsule-security), 0 failed. Pre-existing suites green after the two
narrow kernel fixes below.

## Benchmarks

Real measurements (reference host table in
`docs/benchmarks/AETHEROS_CAPSULE_BENCHMARK.md`): create p50 61.3ms,
mediate p50 0.008ms, policy p50 0.010ms, checkpoint p50 2.94ms, restore
p50 0.060ms, replay p50 0.001ms; isolation probes 6/6 + 4/4 PASS.
Unmeasured items explicitly listed (recovery timing, remote migration,
scheduler stress, GPU, long-run drift).

## Platform Matrix

Windows: LEVEL_0 + Job Objects path TESTED (reference host).
Linux (namespaces/cgroups/firejail/containers): detection code present,
NOT_TESTED (REQUIRES_ENVIRONMENT). macOS: detection present,
NOT_TESTED. VM/GPU/remote-node: UNAVAILABLE/NOT_SUPPORTED in 1.0.

## Migration

Local migration: TESTED (pause→snapshot→verify→restore→resume +
rollback path). Remote: REQUIRES_CONFIGURATION (honest, moves nothing).

## Known Limitations

Capsule Center desktop UI not built (data API ready; UI deferred);
`aetheros capsule` live control is per-process (registry snapshots for
visibility); remote capsules/pairing/mTLS, VM/container execution
backends, GPU enforcement, long-run test, and full chaos matrix are NOT
in 1.0. Two narrow pre-existing kernel fixes were required (documented
below) — no refactors, no API changes.

### Incidental kernel fixes (evidence-backed, minimal)

1. `kernel/core/scheduler.py` — `heapq` over unordered `ScheduledAgent`
   raised `TypeError` for any two same-priority agents (proven by
   traceback); added monotonic `seq` + `__lt__` on
   `(priority_key, seq)`. No behavior change otherwise.
2. `kernel/core/kernel.py` — admission `reserve()` ids never matched the
   agent-keyed release in `allocate()`, leaking one reservation per agent
   (proven: reservation count grew, sessions exhausted); the reservation
   is now released after allocation.

## Release Readiness

**PRODUCTION_READY_WITH_WARNINGS** — capsule runtime complete, tested,
measured, and honestly scoped; warnings: desktop Capsule Center,
remote/VM/GPU backends, and long-run validation remain future work.
