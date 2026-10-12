# AetherOS Crash Recovery (§18-21)

`CrashRecoveryManager.startup_scan()` on startup (§80 steps 1-10):
validates storage/schema/migrations/integrity, detects stale leases and
interrupted tasks, validates authority, recovers safe state, reports
unresolved issues without blocking startup for non-critical corruption.

Leases (§19): task_id/agent_id/worker_id/lease_id/generation/
acquired_at/expires_at; atomic CAS acquire; stale leases expire and are
reclaimable; stale generation rejected.

Side effects (§20): operation_id + idempotency key + receipt. Crash ⇒
`UNKNOWN_OUTCOME`; `reconcile(op, verify)` maps verify() → VERIFIED / FAILED /
stays UNKNOWN. `exception == did-not-happen` is never assumed.

Two-phase (§21): PREPARE → AUTHORIZE → COMMIT → VERIFY where supported;
otherwise record UNKNOWN_OUTCOME and require reconciliation. UNKNOWN is never
auto-converted to SUCCESS.

Restored tasks with uncertain effects enter RECOVERED_PENDING_RECONCILIATION
(§92); dangerous actions are never auto-continued.
