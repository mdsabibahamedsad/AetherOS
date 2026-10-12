# AetherOS 1.0 Migration Guide

## Hermes legacy
No automated legacy destructive migration exists. If a legacy install is
present, the 1.0 installer (when built) will detect it, back it up, and ask
before importing. Never delete legacy data unless policy explicitly permits —
current policy does not.

## Database / memory / configuration / artifacts / credentials / automation / settings
- Migrations are versioned with precondition → execute → validate →
  rollback (see `update-health.ts` `applyMigrations`).
- Before any risky migration the updater creates a recovery point (Master 61).
- On validation failure the migration rolls back applied steps in reverse
  order; failure escalates to update ROLLBACK, never silent corruption.
- Credentials are never migrated into logs, bundles, or telemetry
  (redaction unit-tested).

This guide is PROCEDURE, validated in harness only; device runs pending.
