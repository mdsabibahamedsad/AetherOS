# Payment Architecture

Status: IMPLEMENTED (abstraction + 3 local providers) / PLANNED
(external rails, escrow, taxes/fees beyond recorded fields).

## Interface

`PaymentProvider`: quote / authorize / capture / refund / void /
get_transaction / reconcile. All amounts minor units; all mutating
calls take idempotency keys; replays return originals; settled
transactions refuse re-capture/re-void; refunds never exceed captured.

## Escrow

Abstraction only: the ORDER authorize→verify→capture is enforced, and
`supports_escrow` exists on the interface, but no shipped provider
implements conditional settlement. Claiming otherwise would be
fabrication — so we don't.

## Replay / double-spend / duplicate billing

- Same authorize key → same transaction (balance moved once).
- Same capture key → same result (no movement).
- New capture on settled tx → refused.
- Ledger appends dedupe on (event, idempotency key).
- Refund-before-status-flip ordering in disputes.

## API security

Versioned `MarketplaceAPI` (v1): pagination capped, ids validated,
tenant filters explicit, economics server-derived. Rate/size/replay
protection at transport + gateway layers (reused, not duplicated).
