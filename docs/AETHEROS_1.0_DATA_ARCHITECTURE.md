# AetherOS 1.0 Data Architecture (as implemented)

Stores: SQLite session store (FTS5), memory-provider backends (ABC +
orchestrator), artifact store, config YAML, skills/usage sidecars. Migrations:
versioned precondition→execute→validate→rollback with pre-run recovery points;
expand/contract preferred for server schema; destructive auto-rollback of
durable data is FORBIDDEN (operator procedure only). UNKNOWN_OUTCOME semantics
preserved for uncertain external effects (reconcile, never blind-retry).
Backup/restore/retention paths exist (Master 61); live restore drill BLOCKED.
Sync: device identity, conflict resolution, offline/reconnect, revocation —
implemented in tree, multi-device live validation UNVERIFIED. Retention:
current + previous + security fallback; vulnerable releases revocable.
