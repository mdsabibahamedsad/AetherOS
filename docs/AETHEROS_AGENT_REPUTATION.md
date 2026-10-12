# AetherOS Agent Reputation

Status: IMPLEMENTED.

## Multidimensional, never a single number

13 metrics: reliability, task_success, verified_success, evidence_quality,
latency, cost_efficiency, security, policy_compliance, cancellation_rate,
sla_adherence, interoperability, user_satisfaction,
verification_confidence. Each exposes value/confidence/sample_count/
time_window/provenance.

## Evidence weighting

verified (1.0, ×1.25 with transaction ref) > observed (0.7) >
attestation (0.5) > user_feedback (0.35); security signals weight 1.0.
Temporal decay (45-day half-life). Confidence blends sample depth,
reviewer diversity, and recency mass. Below minimum samples: flag
`insufficient_evidence`, value 0 — the UI shows that string, never a
percentage.

## Attack defense (all tested)

- Review burst (≥10 feedback/hour) → `suspected_review_burst`
- Single-org dominance (>80%, n≥5) → `single_org_dominance`
- Perfect-score single-reviewer histories → `suspected_reciprocal_ratings`
- Sybil/collusion: identity weighting via verified-transaction boost +
  org-correlation flags; minimum samples before confidence
- Selective reporting: unverified claims stay low-confidence; only
  verified outcomes move `verified_success`
- Flags are informational; nothing auto-blacklists on one noisy signal

## Trust (companion engine)

7 dimensions (identity, security, execution, economic, evidence,
behavioral, organizational), signals with source/type/value/confidence/
timestamp/evidence/decay. Incidents carry strong penalties with slow
(180-day) decay. Batched `summaries()`/`ranks()` use identical math to
single-agent `profile()` (660x scale fix, measured).

## Drift

Reputation/price/capability drift is surfaced via re-verification
flags on listing update, price-deviation flags on quotes, and metric
histories. Sudden changes show previous/current/cause/evidence in the
detail views.
