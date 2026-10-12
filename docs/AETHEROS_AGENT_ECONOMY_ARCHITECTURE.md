# AetherOS Agent Economy Architecture

Status: IMPLEMENTED (local engines) / PLANNED (external rails, escrow).

## Component diagram

```
Intent/Task -> CapabilityIndex -> Selection -> Contract -> Budget gate
   -> Approval? -> authorize -> A2A execute -> verify -> capture/void
   -> reputation update -> provenance chain
                                    |-> Ledger (hash-chained, append-only)
                                    |-> Events (typed, correlated, deduped)
                                    |-> Evidence (content-hashed, DLP-gated)
```

## Data flow

Quote (verified, never free→paid) → DelegationContract (immutable once
active; amendments are new versions) → BudgetManager reserve →
PaymentProvider.authorize → AgentGateway.delegate → poll/monitor →
ResultVerificationEngine → capture/refund/void → ledger entries →
reputation/trust updates → explanation record.

## Trust model

Identity (A2A-bound) + 7 trust dimensions + 13 reputation metrics +
listing verification + scan level. Trust ≠ capability ≠ authorization.

## Economic flow

Integer minor units. Risk tiers FREE/LOW/MEDIUM/HIGH/CRITICAL map to
NO/AUTO/CONDITIONAL/HUMAN approval deterministically; CRITICAL always
human. Budgets scope global→contract with daily/weekly/monthly +
per-task/per-agent caps + velocity guards.

## Lifecycles

- Contract: draft→proposed→negotiating→approved→active→completed/
  cancelled (+disputed). Locked once active.
- Transaction: quoted→authorized→captured/refunded/voided (+disputed).
- Dispute: open→under_review→evidence_requested→resolved/refunded/
  rejected/escalated. Refunds execute before the status flips.
- Delegation: created→delegated→running→evidence_received→verified→
  completed (+failed/cancelled/refunded/disputed).

## Security boundaries

Renderer holds no credentials (typed IPC). Remote content is DATA.
Secrets never cross (DLP + redaction + minimization). Artifacts are
quarantined (network layer) and hash-verified. Recursion depth/chain
ceilings enforced. Tenant isolation in org registries.

## Failure recovery

Retry/fallback (contract-gated, budget re-checked, never silent
upgrades), resume via idempotency, cancel→void, verify-fail→void/refund,
dispute→evidence→resolve, ledger tamper→safe mode.
