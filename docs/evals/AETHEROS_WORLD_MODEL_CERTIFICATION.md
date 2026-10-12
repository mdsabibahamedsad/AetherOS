# World-Model Certification (§204) — measured, 2026-09-07, Win11/Py3.11

- Model: HybridWorldModel vhybrid-v1 = RuleBased rules-v1 +
  (StateTransition trans-v1, GraphDynamics graph-v1 available).
  LLM/Neural/External: NOT AVAILABLE (no provider wired).
- Datasets/trials: scripted transition checks (write/delete → 2/2
  correct); pytest suites: tests/cognitive 35 passed; full
  tests/cognitive+self_improvement+control_plane = 99 passed.
- Prediction metrics: scripted accuracy 2/2; long-horizon confidence
  0.90(h1) → 0.045(h50) via horizon penalty (monotone, §88).
- Calibration: scripted 8/10 @0.9 → Brier 0.17, "calibrated within
  observed range" (small-n caveat surfaced, §61-style honesty).
- Foresight: deliberative/simulative decision ~0.4ms vs reactive
  ~0.13ms; planner expand p50 0.015ms. Selection: VoI-gated
  (negative → skip); ablation fast→reactive … max→deliberative.
- Counterfactual/causal: compare/rank/explain exercised; observation
  cannot validate causality (tested); do() contrast tested.
- Latency/cost: sub-ms throughout; budgets enforced (truncation
  tested); Max mode budget-constrained.
- Security: firewall blocks undeclared tools (attempts counted);
  policy pruning pre-execution; TOCTOU recheck; poisoning seams
  documented. No AGI/human-level claims.
- Known limitations: scripted scenarios, not production; twins are
  sketches; no live browser/computer/DB/API integration; no renderer
  UI; calibration needs production data before trust.
