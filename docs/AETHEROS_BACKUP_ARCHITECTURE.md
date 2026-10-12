# AetherOS Backup Architecture (§37-44)

Types: FULL (curated set) and SNAPSHOT (critical files). INCREMENTAL /
DIFFERENTIAL / POINT_IN_TIME-as-mode: NOT_IMPLEMENTED (a point in time is
recovered by choosing the backup with the wanted `created_at`).

Manifest (§38): backup_id, created_at, source, scope, schema_version,
encryption, compression, content_hash, size, retention, tool_version, file
hashes. Integrity (§39): `verify()` re-hashes archive + each file, checks
manifest, schema sanity, zip validity. Uncertified until restore-tested (§88).

Encryption (§40-41): Fernet (`cryptography`), caller-supplied key, never
stored beside the backup. Generation: `Fernet.generate_key()`; rotation:
re-encrypt latest FULL with the new key and revoke the old; recovery:
documented key custody is the operator's responsibility (loss ⇒ backup
unrecoverable; stated, not hidden).

Destinations (§42): LOCAL (`<HOME>/backups`), EXTERNAL_DRIVE /
USER_SELECTED_FOLDER via `BackupManager(engine, backup_dir=...)`.
OBJECT_STORAGE/REMOTE: NOT_IMPLEMENTED (no fake cloud).

Scheduler (§43): configurable by the operator (cron `backup create` daily/
weekly/manual/before-migration/before-upgrade); backups use consistent
snapshots and never block active execution beyond the write lock.

Locking (§44): SQLite files via `sqlite3.backup()`; never raw-copy live DBs.
