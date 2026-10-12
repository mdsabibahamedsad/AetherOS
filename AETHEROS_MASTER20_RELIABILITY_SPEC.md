# AETHEROS MASTER 20 — RELIABILITY SPEC

Scope: quality metrics, error budgets/SLOs, regression handling, rollout
safety, diagnostics discipline and the knowledge base
(`agent/quality/{metrics,regression,rollout,trends,diagnostics,knowledge}.py`).

## 1. Task success semantics (P15)

`TaskOutcome.COMPLETED` counts as **verified** success only when the record
carries `verified=True`; `USER_ACCEPTED` and `VALIDATION_SUCCESS` are
inherently verified. Unverified completions inflate neither
`verified_success_rate` nor SLO attainment. All rates are plain fractions of
`total` with no hidden weighting.

## 2. Reliability metrics (P19-20) & availability

Snapshot per evaluation window: success/failure/timeout/crash/retry rates,
recovery rate (recoveries over distinct troubled tasks — failures ∪ crashes,
no double counting), availability `(total − crashed)/total`.

## 3. Error budgets & SLOs (P21-22)

Both are constructor arguments — thresholds are never hard-coded doctrine:
- `ErrorBudget(metric, max_value)` — consumed from measured
  failure/timeout/crash rates; `exhausted` when consumption exceeds budget.
- `SLO(name, kind ∈ {availability, latency, task_success, security},
  target, higher_is_better)`; security SLO fails if any POLICY_VIOLATION
  occurred; latency is lower-is-better by declaration.

## 4. Recovery score (P54)

Deterministic deductions: detection latency (≤0.4 by 60 s), recovery time
(≤0.4 by 5 min), data loss (0.15 each), task loss (0.1 each), duplicate side
effects (0.2 each); floor at 0. Pure function — same inputs, same score.

## 5. Regression engine (P23-27)

- `classify_regressions(before, after)` precedence:
  EXPECTED_CHANGE > ENVIRONMENTAL > FLAKY > NEW_FAILURE / FIXED_FAILURE /
  PRE_EXISTING_FAILURE. Consistently-passing tests are not classified.
- `FlakyTracker`: intermittent outcome within a trailing window ⇒ FLAKY;
  consistently-failing tests are NOT flaky (they're broken).
- `QuarantineRegistry`: explicit non-empty reason mandatory; entries remain
  enumerable (`visible_entries`) — quarantine is bookkeeping, never hiding.
- `prioritize()`: changed-module → critical-security → critical-regression →
  golden → broad suite.

## 6. Rollout & rollback (P9, P68-71)

`RolloutPolicy` stages canary→medium→full with configurable monitors
(error_rate, latency_p95_ms, task_success_rate, security_events). Breaching
any monitor halts and auto-rolls back; post-rollback validation checks
service health, data integrity, task recovery and security state, recorded
on `RolloutState.validation`. Feature flags read a plain config mapping with
fraction-or-percent shares bucketed by `percent_env`.

## 7. Diagnostics & RCA discipline (P55-60, P59)

`DiagnosticEngine` composes `aetheros_reliability.rca` confidence levels.
Without evidence the cause is literally "undetermined" at confidence UNKNOWN.
Change correlation ranks only component-overlapping commits inside the
window, newest-first, each labeled "touches failed component …" — the latest
commit is one candidate among many, never an automatic culprit (P59).
Reports always include what/where/when/impact/cause/confidence/action.

## 8. Knowledge base & known issues (P80-81)

`RegressionKnowledgeBase` rows: failure, cause, fix, test, version,
component. `KnownIssuesDatabase` seeds the six documented pre-existing
clusters (KI-WINDOWS-PTY, KI-DISPLAY-STRINGS, KI-NOUS-IMPORTS,
KI-MEMINTEL-FABRIC, KI-MULTIMODAL, KI-KANBAN-STRESS) so the regression
engine classifies them PRE_EXISTING instead of NEW.

Observed during M20 validation: `tests/reliability/
test_journal_heartbeat_checkpoint.py::test_recent_orders_newest_first`
flips between runs under direct pytest invocation (hash-order sensitivity;
stable under the canonical `scripts/run_tests.sh` hermetic wrapper which
pins PYTHONHASHSEED=0). Classified FLAKY/ENVIRONMENTAL — tracked here, not
deleted, not skipped (P25/P26).

## 9. Trends & alerting (P93-94)

`TrendTracker` keeps append-only series; deterioration = recent-half mean
worse than prior-half mean beyond threshold (direction-aware per metric).
Alerts are returned on record and retained in `alerts` for existing
notification surfaces to consume.

## 10. Release gates (P82-84, P98)

Seven gates (FUNCTIONAL, SECURITY, PERFORMANCE, RELIABILITY,
COMPATIBILITY, INSTALLER, DOCUMENTATION) evaluate `GateInput` facts:
critical failure or all-checks-failed ⇒ BLOCK; partial failure ⇒ WARN; a
gate never evaluated ⇒ BLOCK (missing evidence is not a pass). Security
findings force SECURITY=BLOCK. Unavailable rollback downgrades PASS→WARN
and is recorded verbatim on the scorecard. Any BLOCK ⇒ `scorecard.ready`
False ⇒ release blocked.
