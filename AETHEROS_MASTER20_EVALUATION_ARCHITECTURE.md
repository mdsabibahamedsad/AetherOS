# AETHEROS MASTER 20 — EVALUATION ARCHITECTURE

Date: 2026-08-24. Layer: controlled continuous-improvement pipeline
(OBSERVE → MEASURE → EVALUATE → DIAGNOSE → PROPOSE → EXPERIMENT → TEST →
VERIFY → APPROVE → RELEASE → MONITOR → ROLLBACK) over the existing AetherOS
stack. Not unrestricted self-modification: the layer evaluates, gates and
proposes; it never silently rewrites product behavior.

## 1. Design constraints honored

- **Reuse, don't duplicate**: composes `aetheros_observability`
  (UnifiedMetrics, TaskOutcome taxonomy, incidents/recovery/redaction),
  `aetheros_reliability` (rca/slas/checkpoint/watchdog), the canonical test
  runner (`scripts/run_tests.sh` → `run_tests_parallel.py`), M19 chaos
  harness + ReputationStore, M17 research quality metrics, existing CI.
- **Narrow waist**: zero new model tools; CLI-only surface
  (`aetheros quality …`, Footprint Ladder rung 2).
- **Profiles**: persistent state under `get_aetheros_home()/quality/`.
- **Pure-stdlib core** (plus aetheros_observability import in metrics):
  offline-deterministic, no network, no model calls.

## 2. Module map (phases covered)

| Module | Covers |
|---|---|
| `agent/quality/models.py` | P2 EvaluationRun, P3 Baseline, P4 Candidate, P5 ChangeProposal (+P7 risk classification, P8 approval semantics), P11 Experiment, P12 Hypothesis, P24 FailureClassification, P26 QuarantineEntry, P80/P81 KB rows, P83 scorecard, P55 Diagnosis, P68 rollout state |
| `benchmarks.py` | P13 engine, P3/P45 baseline store, P46-47 comparison+blocking, P90 reproducibility, P91 artifact hashes, P17-19 anti-fabrication publish gate |
| `metrics.py` | P15 verified-only success, P16 quality dimensions, P19-20 rates/availability, P21 budgets, P22 SLOs, P54 recovery score, P18 cost summary (secret-free) |
| `regression.py` | P23 before/after classification, P25 flaky detection, P26 explicit-reason quarantine, P27 prioritization |
| `datasets.py` | P30-31 versioned immutable datasets with integrity hashes |
| `diagnostics.py` | P55 self-diagnostics, P56 evidence-gated RCA, P57-58 correlation/traceability, P59 no-auto-blame change correlation, P60 report rendering |
| `improvement.py` | P61 signal→proposal derivation, P62 no unsupervised changes, P63 SAFE_AUTO_FIX allowlist enforcement (`UnsafeAutoApply`), P66 mandatory why/what/where/benefit/risk/tests/rollback |
| `rollout.py` | P9 config-driven flags, P67 same-criteria comparison, P68-69 staged rollout, P70 threshold auto-rollback, P71 post-rollback validation |
| `trends.py` | P93 trend series/deterioration detection, P94 alert events |
| `knowledge.py` | P80 regression KB, P81 known-issues DB seeded from documented clusters |
| `gates.py` | P82 seven release gates, P84 PASS/WARN/BLOCK semantics, missing-eval=BLOCK, P98 verdict composition |

## 3. Safety model

1. Risk classification is upgrade-only from touched components;
   CRITICAL_COMPONENTS (security/auth/installer/credentials/migration/
   sandbox/permission_policy/release) force human approval.
2. Autonomous application exists ONLY for SAFE_AUTO_FIX_KINDS
   (formatting, regenerate_derived_index, restart_failed_worker,
   clear_safe_cache) executed through registered action callables;
   everything else raises `UnsafeAutoApply`.
3. Proposals are constructed-invalid without evidence and without a
   rollback plan (P26-27 enforced at the dataclass boundary).
4. Publishing requires an actually-executed EvaluationRun (P17/P18).
5. Rollout monitors breach ⇒ stop + rollback + validation checklist (P70-71).

## 4. Data flow

```
task records ──► QualityMetrics ──► ReliabilitySnapshot ─┐
checks ────────► BenchmarkEngine ─► EvaluationRun ────────┼─► ReleaseGateEngine ─► Scorecard (ready?)
before/after ──► classify_regressions ─► classifications ─┘            │
signals ───────► ProposalEngine ─► ChangeProposals ─► (approval)       │
series ────────► TrendTracker ─► alerts          │                     │
failures ──────► DiagnosticEngine ─► Diagnosis ◄──┘        RolloutController ─► advance/rollback
```

Persistence: baselines under `<AETHEROS_HOME>/quality/baselines.json`;
everything else is value-type state owned by callers (composable, no hidden
singletons).

## 5. CLI surface (`aetheros_cli/quality.py`, wired in `main.py`)

```
aetheros quality status                    # subsystem overview
aetheros quality gate [inputs.json]        # PASS/WARN/BLOCK table; exit 1 on BLOCK
aetheros quality scorecard [inputs.json]   # full scorecard JSON
aetheros quality baselines                 # recorded evaluation baselines
aetheros quality known-issues              # seeded pre-existing clusters
```

Gate inputs are measured facts supplied by the caller (CI job outputs,
benchmark runs); absent input = gate never evaluated = BLOCK — the CLI can
never invent a pass.

## 6. What was intentionally NOT built

No new metrics stack, no new test framework, no new CI pipelines, no
feature-flag subsystem (config mapping suffices), no autonomous code
mutation path beyond the allowlist registry, no dashboard redesign (data is
JSON-ready for the existing observability surfaces).
