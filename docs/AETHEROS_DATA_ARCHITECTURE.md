# AetherOS Data Architecture (Master 61)

## State is not memory (§3)

Seven independent lifecycles: execution state (ends with the task),
memory (versioned knowledge), authority (revalidated), audit (append-only),
artifacts (content-addressed), configuration (layered), cache (disposable).
`aetheros_data/domains.py` is the canonical map.

## Logical domains (§4)

17 domains in `STORAGE_DOMAINS`. One physical SQLite DB
(`data/aetheros_data.db`) + filesystem artifact bytes. Physical separation
was chosen because the workload is single-writer local-first; 16 databases
would add failure modes with no measured benefit.

## Storage abstraction (§5)

`StorageEngine`: transaction, read/write/update/delete, CAS, batch (via
explicit transactions), query, snapshot (backup API), checkpoint (via
`CheckpointManager`), migration, integrity-check, backup/restore (via
managers). Domain boundaries: `records.py` repos, `checkpoints.py`,
`recovery.py`, `artifacts.py`, `backup.py`, `restore.py`, `sync.py`,
`portability.py`, `services.py`. Subsystems never touch SQLite internals
except through these classes.

## Providers (§6)

| Provider | Txn | Durability | Concurrent writers | Snapshots | Backup | Encryption | Remote | Offline | Sync |
|---|---|---|---|---|---|---|---|---|---|
| LocalSQLite | yes | crash-safe* | 1 writer + N readers (WAL) | backup API | yes | at-rest via backup Fernet | no | yes | via envelopes |
| PostgreSQL | — | — | — | — | — | — | — | — | NOT_IMPLEMENTED |
| ObjectStorage | — | — | — | — | — | — | — | — | NOT_IMPLEMENTED |

* durability = OS fsync guarantees; physical power-loss protection NOT
claimed (would need hardware testing; §87 BLOCKED).

## Local-first (§7)

`LOCAL_ONLY` is the default and only mode. Core execution never touches the
network for storage. State survives restart/sleep/crash via WAL + atomic
writes + startup recovery scan.

## Transactions (§9), events (§10-11), idempotency (§12), CAS (§13-14)

`mutate_with_event()`: BEGIN IMMEDIATE → validate → mutate → write event →
COMMIT; event visible only after commit. Durable vs ephemeral kinds in
`events.py`. Envelope: event_id/seq/timestamp/aggregate_id/aggregate_type/
actor/task_id/agent_id/correlation_id/causation_id/schema_version/payload.
Order = AUTOINCREMENT seq; timestamps informational. Idempotency keys on
records + side effects. `record.version` CAS + monotonic `generation`;
stale writers get `ConflictError`.
