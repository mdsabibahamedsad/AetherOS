# Self-Improvement Threat Model (§119) + Long-Horizon Tests

## Threats → mitigations → residual
- Prompt injection into traces/lessons: redaction + untrusted-data
  boundary; residual: paraphrased injections → human review gate.
- Reward hacking / metric gaming: multi-dimensional promotion,
  MetricIntegrityCheck; residual: novel gaming → calibration sampling.
- Eval gaming / grader gaming: multi-graders, hidden holdouts, outcome
  verification, rotation; residual: adaptive gaming → red-team refresh.
- Data/memory poisoning: tenant isolation, provenance, scoped lessons,
  global-promotion gate; residual: slow-drip poisoning → drift alerts.
- Candidate poisoning: versioned registry, review, sandbox eval;
  residual: supply-chain signer → Master 50 key rotation.
- Malicious benchmark/grader: grader versioning + calibration +
  evaluator-failure detection; residual: colluding grader → human audit.
- Cross-tenant leakage: store-level isolation (tested); residual:
  aggregation leaks → minimum-n reporting (future).
- Improvement engine privilege abuse: Master 50 gating, I-levels,
  emergency stop, audit; residual: none accepted silently — flagged.

## Long-horizon tests (`docs/testing/AETHEROS_LONG_HORIZON_TESTS.md`)
Status: harness ready (multi-trial engine, budgets, pause/resume/
cancel, checkpoints via experiment status), 20+/50+/100+ step suites
NOT yet authored — tracked as follow-up. Interruption/failure-
injection (tool timeout, model timeout, network failure, browser
crash, MCP/A2A disconnect, malformed output, scope escalation,
malicious tool/page) supported via executor fault-injection pattern:
executors raise / return errors; recovery measured by retry success,
recovery latency, recurrence. Per-step vs overall failure compounding
reported by aggregate(). Simulation ("digital twin") claim: NOT
claimed — temp-dir sandbox only, documented as such.
