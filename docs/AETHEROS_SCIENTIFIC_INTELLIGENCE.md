# AetherOS Scientific Intelligence (Master 53) — Documentation Index

- `docs/AETHEROS_SCIENTIFIC_INTELLIGENCE.md` — this file: overview,
  principles, lifecycle, module map, honesty contract.
- `docs/AETHEROS_SCIENCE_ARCHITECTURE.md` — component architecture.
- `docs/AETHEROS_EXPERIMENT_ENGINE.md` — runtime, sandbox, manifests.
- `docs/AETHEROS_HYPOTHESIS_ENGINE.md` — generation → validation.
- `docs/AETHEROS_SCIENTIFIC_SAFETY.md` — safety + threat model (§238).
- `docs/AETHEROS_SCIENTIFIC_BENCHMARKS.md` — benchmark design + results.
- `docs/AETHEROS_DISCOVERY_PROVENANCE.md` — provenance + audit design.
- `docs/AETHEROS_MASTER_53_SCIENTIFIC_INTELLIGENCE_REPORT.md` — final
  report (§249).

## Highest invariant

**AetherOS may autonomously search for truth, but it must never
manufacture truth.** Plausibility ≠ truth. Discovery is a gated
process, not a text event. Failed experiments are knowledge. UNKNOWN
is valid. Prediction ≠ observation. Evidence > consensus.
Reproducibility > impressiveness. Autonomy stays bounded.

## Lifecycle

Question → Research → Hypotheses → Critique/Causal → Experiment/
Simulate → Observe/Measure → Analyze → Falsify/Validate → Update
World Model → New Hypotheses → Synthesize Discovery → Provenance.

## Module map (`aetheros_science/`)

| Module | Responsibility |
|---|---|
| models | Typed contracts + status enums |
| research | Decomposition, landscape, gaps, independence, contradictions |
| hypotheses | Generation, diversity, novelty, critique, falsification, exploration |
| experiments | Designer, sandboxed runtime, M52 simulation bridge, active selection |
| statistics | Real stdlib stats, documented assumptions |
| evidence | Chain, E0–E6, Bayes (Beta-Binomial), reproducibility, negative memory |
| knowledge | Provenance-required graph, chronological memory |
| discovery | Gated state machine, quality gate, replication plans, red-team, reports, guards |
| safety | Classification, protocol/doc scanning, confidentiality, lab connector |
| engine | Lifecycle facade, autonomy L0–L5, budgets, checkpoints, audit |
| benchmarks | Categories, golden + adversarial fixtures |

## Honesty contract (enforced by tests)

- Unvalidated hypotheses labeled PROPOSED/UNVALIDATED.
- Simulations labeled SIMULATION; unavailable backends say UNAVAILABLE.
- Novelty verdicts describe corpus search, never declare discovery.
- p-values never reported without effect size + CI + n.
- Raw observations immutable; exclusions logged.
- Secrets/injections in documents → quarantine, never authority.
