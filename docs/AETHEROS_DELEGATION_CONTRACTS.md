# Delegation Contracts

Status: IMPLEMENTED.

## Model

`DelegationContract`: requester, provider, service/offer/quote refs,
task, minimized-input ref, allowed/prohibited data, data class, expected
output, success criteria, SLA, timeout, budget, price, payment/
cancellation/refund conditions, verification + artifact requirements,
security constraints, retention, jurisdiction, expiry, fallback flag,
max depth, signatures, idempotency key, version + supersedes link.

## Immutability

Draft → proposed → (negotiating) → approved → active → terminal.
`is_locked` once active. Amendments create version N+1; the old record
is untouched and linked via `supersedes`. Locked records reject
mutation (tested).

## Negotiation

Only `NEGOTIABLE_FIELDS` (price, deadline, output format, scope, SLA,
retry policy, evidence requirements, delivery format) may change, and
only while proposed/negotiating. Security constraints, data class,
allowed/prohibited data, verification/artifact requirements, and depth
ceilings are a FLOOR: proposals touching them are rejected. Forbidden
asks (unrestricted filesystem, disable security, raw secrets/keys,
bypass approval) reject the whole proposal regardless of price.
Accepted changes produce an amended version for re-approval.

## Binding

`quote.contract_id` is stamped after contract creation
(`bind_contract`), so transactions trace quote→contract→delegation→
ledger. Client-supplied prices/trust/settlement/verdicts are never
trusted; all are server-derived or deterministically verified.
