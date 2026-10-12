# AetherOS Data Migration (§53-55, §109-110)

Each migration: version, description, preconditions (backup verified,
integrity clean, lock acquired, intent recorded), changes (DDL), postconditions
(schema version row, critical-record validation, index check), rollback
(restore safety snapshot). Migrations run inside `acquire_migration_lock`;
only one owner.

Failure (§55): preserve failed state, record failure event, restore safety
backup, report exact error. Never delete/recreate blindly or silently
downgrade.

Legacy (§109-110): old Hermes paths/names/env (`HERMES_HOME`, `MESSAGING_CWD`,
`TERMINAL_CWD`) detected and bridged; legacy data migrated with provenance
preserved and migration recorded; legacy sources kept until verified.
`aetheros data migrate` reports current schema (migrations auto-apply on
engine init).
