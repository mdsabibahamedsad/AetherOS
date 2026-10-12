# Eval Architecture / Methodology / Regression / Benchmarks / Grading

## Architecture (`docs/evals/AETHEROS_EVAL_ARCHITECTURE.md`)
EvalTask (inputs, criteria, graders, budget, security reqs, golden,
holdout, platform tags) → EvalTrial (seed, config, trace, outcome,
grader verdicts, cost/latency/tokens) → EvalDataset (versioned,
fingerprinted) → EvaluationEngine (multi-trial runs, aggregation) →
ExperimentRunner (baseline vs candidate, same dataset/constraints).

## Methodology (`AETHEROS_EVAL_METHODOLOGY.md`)
Complete trajectories, multiple trials (seeds), outcome-based graders
first; capability suites must NOT saturate (retire ≥98% to regression);
regression answers "did we break it?"; golden tasks use objective
verification, never NLG similarity alone; holdouts hidden from
optimizers; contamination checks flag train-on-test; report sample
size, agreement, variance, CI — never present small-n wins as certain.

## Regression strategy (`AETHEROS_REGRESSION_STRATEGY.md`)
Every production capability gains regression tasks; production failures
→ anonymize → minimize → EvalTask; security incidents → security eval +
regression test; saturated capability tasks promoted to regression;
eval rotation retires stale tasks.

## Benchmarks (`AETHEROS_BENCHMARKS.md`)
Measured on Windows 11 / Python 3.11 (2026-09-07):
trace_record p50 0.48ms; capability 6/6 in ~5ms; regression 4/4;
security 2/4 pass with 2 hard-gate FAILs (proves gates bite);
experiment_compare p50 0.007ms; drift_observe ~0ms.
Run: `$env:PYTHONPATH='.../aetheros'; python benchmark/eval_bench.py`.

## Grading model (`AETHEROS_GRADING_MODEL.md`)
Deterministic / Outcome / StaticAnalysis / Model / Human graders with
id, version, weight, confidence, evidence. Ensemble: hard gates
(security, unauthorized action, missing artifact, test/state fail)
decide FAIL and no soft score overrides them. ModelGrader without a
provider reports NOT AVAILABLE — never a fake score; it is advisory
only, never certifying (§0.3).
