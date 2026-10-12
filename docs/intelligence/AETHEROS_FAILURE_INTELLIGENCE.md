# Experience / Learning / Failure Intelligence / Improvement Lifecycle

## Experience model (`AETHEROS_EXPERIENCE_MODEL.md`)
ExperienceRecord {task, context, approach, actions, outcome,
verification, failure, lesson, confidence, provenance, tenant}.
Evidence, NOT truth. Pipeline: raw traces → episodes → failure
patterns → lessons → validated knowledge → long-term memory (Memory
2.0 integration point: lessons carry scope/provenance/confidence;
memory writes stay user-controlled — never silent deletion of
permanent memory §37). Tenant boundaries enforced at store level.

## Learning model (`AETHEROS_LEARNING_MODEL.md`)
No online training required (§81): improvement via memory, retrieval,
prompts, tool/workflow policies, routing, verification, planning.
Fine-tuning seam exists as honest stub: TrainingCandidate /
DatasetVersion / TrainingRun / ModelArtifact report
STATUS: NOT AVAILABLE when infra is absent (§82 — not implemented,
no fake training). Dataset versioning {id, version, provenance,
license, privacy, hash}; holdouts hidden; leakage patterns
(memorized answer, fixture reproduction, env fingerprinting) flagged.

## Failure intelligence (`AETHEROS_FAILURE_INTELLIGENCE.md`)
17 classes (§7), severity F0–F5 by impact signals (§8). RootCause:
what/expected/divergence step/deciding action/earlier detection/
model-planner-memory-verification alternatives, with confidence +
evidence. Counterfactuals are real re-runs. Clusters + hotspots
identify systemic issues. "Why did it fail?" chains Task→Plan→
Decision→Tool→Observation→Error→Recovery→Outcome.

## Improvement lifecycle (`AETHEROS_IMPROVEMENT_LIFECYCLE.md`)
Failure → Evidence → Hypothesis → Candidate → Offline test →
Regression → Security → Human/policy gate → Canary → Monitoring →
Promotion (ladder OFFLINE→…→GENERAL, no skips without justification,
auto-demotion on degradation) → Outcome. Proposal states
DRAFT…ROLLED_BACK. Every deployment answers why/evidence/experiment/
eval version/approver/timing/aftermath (§107); rollbacks record
reason/trigger/metrics/target/operator (§108). User controls: Teach
(converts to scoped candidate lesson with visible scope/retention),
Forget (removes lesson/experience where policy permits), opt-out,
private mode, local-only eval, retention 7/30/90d/custom.
