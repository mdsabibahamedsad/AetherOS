# AETHEROS MASTER 20 — EVALUATION SYSTEM AUDIT (Phase 0)

Date: 2026-08-24 · Read-only; no code modified in this phase.

---

## 1. Existing systems

### 1.1 Test infrastructure
- pytest 9.0.2 + pytest-timeout (30s/thread) + pytest-asyncio; hermetic
  `tests/conftest.py` (env blanking, per-test `AETHEROS_HOME` tmpdir,
  TZ/LANG/hashseed pinning).
- Canonical runner `scripts/run_tests.sh` → `scripts/run_tests_parallel.py`:
  per-file subprocess isolation, bounded workers, duration cache
  (`test_durations.json`), summary lines `=== Summary: N files, X passed,
  Y failed (P% complete) …`, per-failure classification buckets
  (failures / nonzero-exit / no-tests-ran).
- Suite inventory: ~1,600 test files across ~50 dirs; ~31k tests; documented
  pre-existing failure clusters (see §1.7).
- Special suites: `tests/stress/` (opt-in `--run-stress`; kanban kernel
  benchmarks/concurrency/property-fuzzing/subprocess-e2e), e2e + integration
  excluded by default (dedicated CI jobs).

### 1.2 Benchmarks
- `tests/stress/test_benchmarks.py` (kanban task_runs latency at scale),
  `scripts/benchmark_browser_eval.py`, `aetheros_master15_baseline.json` +
  `AETHEROS_MASTER15_BASELINE.md` (recorded baseline artifact pattern from
  Master 15). No general-purpose benchmark engine with baseline comparison —
  gap M20 fills.

### 1.3 CI / release pipelines (.github/workflows — 21 files)
- `tests.yml` (suite + e2e job, 30-min cap), `security-testing.yml`
  (tests/security + tests/production, --timeout=60), `lint.yml`,
  `typecheck.yml`, `supply-chain-audit.yml`, `osv-scanner.yml`,
  `uv-lockfile-check.yml`, `history-check.yml`, `contributor-check.yml`,
  `docker-lint/publish.yml`, `build-windows-installer.yml`,
  `nix.yml`/`nix-lockfile-fix.yml`, `deploy-site.yml`/`docs-site-checks.yml`,
  `skills-index*.yml`, `upload_to_pypi.yml` (release path).
- Coverage tooling: NOT configured (no pytest-cov) — documented gap; M20 adds
  targeted-coverage reporting hooks, not percentage chasing (P85).

### 1.4 Observability platform — `aetheros_observability/` (15 modules)
- `metrics.py` `UnifiedMetrics` (increment/gauge/observe/snapshot/prometheus,
  record_request/error/retry).
- `evaluation.py` `TaskOutcome` taxonomy + `TaskEvaluation` records +
  success-score semantics (subjective quality never treated as objective).
- `incidents.py`, `diagnostics.py`, `health.py`, `cost.py`, `tracing.py`,
  `errors.py`, `recovery.py`, `service.py`, `storage.py` (persistence),
  `redaction.py` (secret-safe telemetry), `context.py`, `config.py`.

### 1.5 Reliability platform — `aetheros_reliability/` (23 modules)
- `rca.py` — evidence-disciplined root-cause analysis: RCAConfidence
  CONFIRMED/LIKELY/POSSIBLE/UNKNOWN, FailureAnalysis chains; "NEVER asserts
  root cause without evidence".
- `slas.py` — RecoverySLAMetrics (mttr/success_rate), MetricSample windows.
- `watchdog.py`, `heartbeat.py`, `checkpoint.py`, `backup.py`, `restore.py`,
  `journal.py`, `modes.py`, `shutdown.py`, `startup.py`, `states.py`,
  `queue.py`, `ipc.py`, `mission.py`, `config_recovery.py`, `database.py`,
  `diagnostics.py`, `events.py`, `service.py`.

### 1.6 Orchestration/agent evaluation hooks (M19)
- `agent/orchestration/observability.py` (event store/emitter/timeline),
  `catalog.ReputationStore` (routing-only performance signals),
  `chaos.ChaosHarness` (seeded fault injection), `circuit_breaker`,
  recovery classification (`FailureType`), synthesis computed-final-status.
- M18 `agent/memory_os` retriever (precision/recall eval-able), secret
  scanner; M17 `agent/research/reports.py` `citation_coverage`/
  `quality_metric`; M15 `aetheros_computer` pattern/task checkpoints.

### 1.7 Known failures (documented baseline)
- Pre-existing clusters (M17/M18/M19 reports): Windows
  PTY/setup/update/display-string suites; nous-credits stale imports
  (`_subscription_from_payload`); `aetheros_memory_intelligence` fabric
  tests (62); multimodal/mem-intel clusters; 2 kanban stress scripts
  (atypical_scenarios `Task.spawn_failures` attr; subprocess_e2e dangling
  `current_run_id`).
- Latest full sweep (M19): 31,379 passed / 904 failed / 1,604 files,
  0 new failures.

### 1.8 Release gates today
- Per-master certification JSONs with `ready_blockers` + `final_certification`
  (M15-M19 pattern); CI as de-facto gates. No unified release-gate engine —
  gap M20 fills.

## 2. Missing infrastructure (M20 scope)
1. Unified **EvaluationRun / Baseline / Candidate / ChangeProposal /
   Experiment** objects with persisted, reproducible runs (P2-4, P11-12, P90).
2. **BenchmarkEngine** with baseline comparison + regression-threshold
   blocking (P13, P45-47) and anti-fabrication (results only from executed
   checks; P17-18).
3. **Regression classification** NEW/FIXED/PRE_EXISTING/FLAKY/ENVIRONMENTAL/
   EXPECTED_CHANGE + flaky tracking + explicit-reason quarantine +
   prioritization (P23-27).
4. **Golden datasets** with versioning/integrity (P30-31) and golden suite
   SC01-SC30 (P95) with honest per-platform verification status (P39).
5. **Diagnostics/RCA composition** with change-correlation that never
   auto-blames the latest commit (P55-60).
6. **Improvement proposals** with evidence, SAFE_AUTO_FIX allowlist,
   CRITICAL-requires-review, mandatory rollback plan (P61-66).
7. **Rollout/rollback controller** (canary stages, threshold-triggered auto
   rollback + post-rollback validation) over config-driven flags (P9, P68-71).
8. **Release gates + scorecard** (FUNCTIONAL/SECURITY/PERFORMANCE/
   RELIABILITY/COMPATIBILITY/INSTALLER/DOCUMENTATION; PASS/WARN/BLOCK) (P82-84).
9. **Knowledge base + known-issues DB** seeded from §1.7 (P80-81).
10. **Trend tracking + alert events** (P93-94).

## 3. Duplicate infrastructure (must NOT duplicate)
- Do not rebuild metrics (use `UnifiedMetrics`), task-outcome taxonomy
  (`TaskOutcome`), RCA (use `rca.py`), SLA math (`slas.py`), test runner
  (use `run_tests_parallel.py`), CI (extend workflows only if needed),
  stress/property suites (reuse `tests/stress`), chaos (reuse M19
  `ChaosHarness`).

## 4. Integration points
`aetheros_observability.{metrics,evaluation,incidents}` ← quality metrics;
`aetheros_reliability.{rca,slas}` ← diagnostics/recovery score;
`scripts/run_tests_parallel.py` ← regression engine execution;
`agent/orchestration.{types.FailureType, chaos, catalog.ReputationStore}` ←
classification/chaos/agent eval; `agent/memory_os` ← memory eval probes;
`agent/research/reports` ← research quality metrics; master certification
JSONs + documented failure clusters ← known-issues seed; config.yaml ←
feature-flag/rollout policy source.

## 5. Build decision
New unifying package `agent/quality/` (pure-stdlib, offline-deterministic,
profile-safe persistence under `get_aetheros_home()/quality/`), composing the
platforms above. CLI `aetheros quality {status,gate,scorecard,known-issues,
baselines}` (Footprint Ladder rung 2). No production behavior changes; the
layer observes, evaluates, proposes, gates — it never silently modifies
product code (safe-autofix allowlist only, everything else human-approved).
