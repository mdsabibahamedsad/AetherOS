# AetherOS Storage Threat Model (§115)

Threats and mitigations (all verified by tests where stated):

- Database theft → backups encrypted with caller-held Fernet keys; live DB
  inherits OS file permissions; secrets not in DB (only in `.env`, excluded
  from backups).
- Backup theft → encrypted backups opaque without key; content hash detects
  tampering; keys never beside backups.
- Corrupted backup → `verify()` (manifest + per-file hashes) gates restore.
- Ransomware → offline/local backups + hash verification + safety snapshot.
- Unauthorized restore → explicit confirmation required + audit; restores of
  authority revalidated.
- Malicious import → schema/integrity/policy gates; authority never imported;
  archives never executed.
- State rollback → generations + CAS reject stale writers; conflicts explicit.
- Stale authority restore → live revalidation; revoked/expired stay invalid.
- Sync poisoning / conflict poisoning → policy_check gate, non-syncable
  enforcement, APPEND_ONLY memory, MANUAL_REVIEW for automations.
- Memory poisoning → CANDIDATE default, quarantine/retract with provenance.
- Artifact tampering → sha256 re-verification on read and restore.
- Audit tampering → append-only API (no update/delete), hash-chained
  pre-existing memory-intelligence log mapped.
- Migration corruption → locked, intent-recorded, safety-snapshotted.
- Stale writer → CAS ConflictError.
- Replay → idempotency keys dedupe.

Out of scope: physical device seizure with unlocked disk; E2E sync encryption
(NOT_IMPLEMENTED, not claimed); PostgreSQL/remote threat surface (no such
provider).
