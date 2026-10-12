# AetherOS Storage Architecture

Companion to AETHEROS_DATA_ARCHITECTURE.md; physical details.

## Database selection (§8)

SQLite retained (no evidence to replace). Correct usage:
WAL (fallback DELETE on NFS/SMB/FUSE), `foreign_keys=ON`,
`busy_timeout=5000`, `synchronous=NORMAL`, explicit `BEGIN IMMEDIATE`,
`sqlite3.backup()` snapshots, `PRAGMA integrity_check` +
`foreign_key_check`, versioned migrations with lock, atomic artifact writes
(temp + `os.replace`).

PostgreSQL: not used; no PostgreSQL code paths exist, so no claims.

## Schema

`aetheros_data/engine.py::_MIGRATIONS` v1 (16 tables) → v2 (deletion_log) →
v3 (export_registry). `schema_migrations` table records applied versions.
Migration lock: `migration_lock` row, 5-min stale expiry, single owner.

## Concurrency (§56-57)

Writers: main process, gateway workers, CLI, cron, kanban dispatcher share
one DB via WAL single-writer + busy timeout. Writer ownership = whoever holds
the `BEGIN IMMEDIATE` reservation; transaction boundaries = one state
transition + its event; conflicts surface as `ConflictError`, never silent
last-write-wins for versioned domains.

## Caches/indexes/embeddings (§75-78)

Caches disposable (`<HOME>/cache`, 7-day retention). Indexes rebuildable:
`index_meta` registry tracks kind/source_version/model/dimension/status.
Embeddings are derived data with source object + version + model recorded;
re-index supported; embeddings never the sole copy of memory.

## Observability/quotas/backpressure (§81-83)

`StorageMetrics` counters + latency averages + db/artifact sizes.
`check_quotas()` returns WARNING/BLOCK/CLEANUP/USER_ACTION_REQUIRED, never
silent deletion. Backpressure: bounded sync retry queue, idempotent dedupe,
retention compaction; event storms degrade to queued-not-lost.

## Performance (§84-85)

Measured on this machine; see completion report §Performance Measurements.
Benchmarks: `tests/aetheros_data/test_sync_benchmark.py` (1/100/1000 tasks,
memory R/W, event ingestion, checkpoint, backup/restore, sync apply).
