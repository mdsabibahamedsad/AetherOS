# AETHEROS MASTER 19 — Orchestration Architecture

Date: 2026-08-24 · Companions: `AETHEROS_MASTER19_ORCHESTRATION_AUDIT.md`,
`AETHEROS_MASTER19_AGENT_CATALOG.md`, `AETHEROS_MASTER19_FINAL_REPORT.md`,
`aetheros_master19_final_status.json`.

## 1. Stance

Extend, don't duplicate. The prior `agent/orchestration` package (registry,
router, decomposition, task graph, handoffs, verification, approvals, budgets,
queues, recovery, state, planner, observability — audit §1.1) remains the
backbone. Master 19 adds the missing swarm-execution layer and security
guards as additive modules, then binds everything into one deterministic,
synchronous orchestrator suitable for offline verification.

## 2. New modules (all additive)

| Module | Provides | Phases |
|---|---|---|
| `swarm_guards.py` | Capability constants (14), `GrantedCapabilities.grant()` least-privilege intersection, `risk_from_capabilities()`, injection-marker scanner on messages/handoffs, `check_handoff_payload()` exfiltration+secret screening with topic authorization, `ExecutionIdentity` chain w/ impersonation+depth guard | P4-7, P18, P60-61, P73-79 |
| `blackboard.py` | `TaskBlackboard` (verified facts / approved decisions / warnings), `ArtifactStore` with version chains (`parent_artifact`, sha256 hash, provenance), cross-task share grants enforced at read time | P19-22, P71-72 |
| `consensus.py` | Deterministic `critique()` critic reports (assumptions/missing evidence/edge cases), `compare_results()` → AGREEMENT/DISAGREEMENT/PARTIAL_AGREEMENT/INSUFFICIENT_EVIDENCE (never forced), `DisagreementPlan`, `LayeredConfidence` (result/evidence/verification/conclusion) | P25, P28-30 |
| `synthesis.py` | `synthesize()` over verified contributions preserving conflicts/citations/provenance; `validate_completion()` measurable P89 checklist; final status COMPUTED — unverified required work ⇒ PARTIAL/FAILED, never SUCCESS | P88-90 |
| `circuit_breaker.py` | CLOSED→OPEN→HALF_OPEN breaker with bounded growing cooldown, fail-fast while open | P46 |
| `catalog.py` | 15 named specialist manifests (planner/research/browser/computer-use/coding/testing/documentation/data/analysis/verifier/critic/security/monitoring/recovery/synthesis) bound to real roles+capabilities; capability-based `select_team()`; reputation stats as routing-only signals | P3, P63-67 |
| `swarm.py` | `SwarmOrchestrator`: DAG-ready scheduling with thread fan-out of independent nodes, sequential ordering via dependencies, per-node budgets + global pool (orchestrator-only rebalancing), spawn guard (explicit permission, depth cap, swarm cap), side-effect→approval board (fail-closed, expiring grants, single-use scope), failure classification incl. raw-exception mapping, bounded retry w/ exponential backoff, circuit breaking per agent key, atomic checkpoints + resume skipping completed nodes, idempotency keys, emergency stop freezing consequential actions, graceful cancellation, event log + trace, consensus collection, computed final status | P8-14, P43-62, P84-91 |
| `chaos.py` | Seeded fault-injection harness (planned per-attempt faults + random storm mode) | P94 |

Additive `types.py` extensions: FailureType += USER_ERROR/PLANNING_ERROR/
AGENT_ERROR/POLICY_ERROR/SECURITY_ERROR/VERIFICATION_FAILURE; RiskLevel +=
READ_ONLY; AgentRole += VERIFICATION/CRITIC/MONITORING/RECOVERY/SYNTHESIS/
ANALYSIS; TaskResult += summary/evidence_ids/confidence/verification_needed
(defaulted — backward compatible, contract-test enforced).

## 3. Security model (non-negotiables → enforcement)

1. **Least privilege is an intersection**: granted = requested ∩ manifest;
   there is no API for an agent to widen its grant; every use is checked
   against the grant (`CapabilityViolation`).
2. **Risk from capabilities**, never names (`risk_from_capabilities`).
3. **Messages/handoffs/tool outputs are DATA**: injection markers flagged;
   nothing scanned ever mutates policy; malicious output stored verbatim but
   detectable and non-authoritative.
4. **Exfiltration boundary**: sensitive payloads carry topics; transfer
   requires the target's authorization set; secrets are refused outright
   (reuses M18 secret scanner).
5. **Approvals fail closed**: consequential side effects require a prior
   human-approved, scoped, expiring grant; agents cannot decide their own
   requests; emergency stop freezes all consequential authorization.
6. **Spawn protection**: children require explicit identity linkage to the
   spawning execution, stay inside the parent task, respect depth caps and
   swarm size caps.
7. **Budgets**: node budgets raise on overrun (RESOURCE_EXHAUSTED); global
   pool allocations release unused budget only via the orchestrator.
8. **No false completion**: two-phase WORK_COMPLETE→VERIFIED; required
   unverified contributions force PARTIAL/FAILED in synthesis; validation
   checklist is built from measured facts only.

## 4. Execution flow

submit → plan/decompose (nodes w/ success criteria) → ready-set by dependency
topology + priority → parallel fan-out (bounded) → per-node: identity check,
budget consume, approval gate, circuit-broken executor call, deadline check,
contract validation → VERIFYING phase for high-risk nodes via independent
`swarm.verifier` executor → retry classification/backoff for transient
classes → checkpoint after each wave → synthesize + validate →
SUCCESS/PARTIAL/FAILED.

## 5. Test map (137 orchestration tests total)

`tests/orchestration/`: pre-existing basics (26), guards (11),
budget/spawn/approvals/breaker (9), verification+consensus (10),
blackboard/artifacts (7), recovery/checkpoint/resume/timeouts (11),
golden scenarios SC01-SC30 (30), red team (12), chaos (5), performance (3),
api contract (13).
