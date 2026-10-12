# AetherOS Self-Improvement — Architecture (Master 51)

Package `aetheros_self_improvement/` implements the controlled loop:

```
Production Experience → Telemetry → TraceStore → FailureAnalyzer →
EvalTask → ExperimentRunner → Candidate → Offline/Shadow eval →
Regression + Security gates → Human Approval → Canary → Monitor →
Promote / Rollback
```

Modules: `models.py` (all types) · `traces.py` (TraceStore,
RedactionEngine, retention, private mode) · `graders_eval.py`
(5 graders + hard-gate ensemble + EvaluationEngine + datasets) ·
`failures.py` (classification, root cause, counterfactuals, clusters) ·
`lessons.py` (scoped lessons, conflicts, expiry, global gate) ·
`experiments.py` (baseline control, isolation, budgets, shadow) ·
`improvements.py` (planner + versioned CandidateRegistry — proposals
only, never production mutation) · `deploy.py` (promotion ladder,
auto-rollback, config rollback) · `monitoring.py` (drift, eval health,
metric integrity, scorecards) · `engine.py` (SelfImprovementEngine
facade, autonomy I0–I5, Master 50 gating) · `suites.py` (built-in
offline suites) · CLI `aetheros_cli/evolution_cmd.py`
(`aetheros evolution …`, `aetheros eval …`).

Governance: every privileged op passes `plane.check()`; no plane →
fail closed. Emergency stop halts experiments/canaries. All actions
emit ImprovementAuditEvents. Default autonomy I2 (propose).
Status vocabulary: Observed / Inferred / Proposed / Experimented /
Validated / Deployed — never interchanged (§156).
