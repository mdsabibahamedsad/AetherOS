# AetherOS Agent Economy (money movement)

Status: IMPLEMENTED (providers none/credits/org_budget, ledger,
accounting, budgets) / PLANNED (external rails, escrow, taxes).

## Providers

| Provider | Real? | Notes |
|---|---|---|
| `none` | Yes | Free tasks; zero-amount idempotent transactions, ledger-audited |
| `credits` | Yes (local) | Integer pool with authorize-hold semantics; NOT real money |
| `org_budget` | Yes (records) | Envelope transactions; enforcement via BudgetManager |
| `external:*` | BLOCKED | Refused until a `PaymentProvider` is configured |

## Quoting

Provider quotes verified deterministically: schema, expiry, currency
match, budget fit, offer binding, free→paid flip refused, >10x price
deviation flagged for review. Quotes carry idempotency keys; replays
return the original.

## Authorization policy

Risk classes by amount (minor units): FREE=0, LOW≤500, MEDIUM≤5000,
HIGH≤50000, CRITICAL above. Tiers: NO (free only), AUTO (≤
auto_approve_limit), CONDITIONAL (≤ approval_threshold — still needs an
approver unless policy auto-allows), HUMAN (above, or no budget
configured, or CRITICAL always). No LLM anywhere in this path.

Autonomous purchase additionally requires: `automatic_payment` flag +
per-user `payment_limit_minor` covering the amount. Otherwise refused.

## Ledger

Append-only JSONL, sha256 hash-chained (`prev_hash`/`entry_hash`).
Event set: QUOTE_CREATED … ADJUSTED. Corrections are compensating
ADJUSTED entries, never edits. `verify_chain()` detects tampering;
failure puts the marketplace in safe mode. Idempotency keys prevent
duplicate settlement entries.

## Accounting

Estimated (quoted breakdown) vs actual (settled ledger only). Variance
is null until settlement — actual cost is never claimed early.
Dashboard summary: spent/refunded/net/captures/refunds.

## Abuse controls

Per-task/per-agent caps, daily/weekly/monthly limits, spend-velocity
guard, quote-flood guard, recursion ceilings, payment-loop (chain
re-entry) refusal, double-capture refusal, replay-safe captures.
