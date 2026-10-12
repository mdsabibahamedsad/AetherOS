# AetherOS Retention Policy (§33-36, §95-96)

Retention: security audit 365d, debug 30d, temp traces 7d, durable events
180d, checkpoints 30d (never while leased), caches 7d, backups 90d.
`RetentionManager.apply()` is reference-aware: active tasks, memory, audit,
artifacts, backups, recovery state block collection.

Deletion types: SOFT_DELETE (flag), HARD_DELETE (row removal, audited),
RETENTION_DELETE (policy expiry, audited), CRYPTOGRAPHIC_ERASURE:
NOT_IMPLEMENTED (no per-record data-key scheme exists; not claimed).

Deletion audit (§96): who/what/why/when/scope/policy/result in
`deletion_log` + audit event. Secret values are never written to the audit;
the deletion event is logged, not the content.

No silent data loss (§111): destructive operations require explicit scope,
safety checks, backup where appropriate, and audit.
