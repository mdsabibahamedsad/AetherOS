# AetherOS Data Storage Audit (Master 61 §2)

Audit date: 2026-09-09. Scope: repository working tree + profile-aware
`get_aetheros_home()` runtime layout. Method: code inspection of store
modules, schema inspection of SQLite users, config inspection.

## Canonical new store (Master 61)

| Path | Technology | Domains |
|---|---|---|
| `<HOME>/data/aetheros_data.db` | SQLite WAL, FK ON, busy_timeout 5000, migrations v1-3 | task, agent, automation, checkpoint, event, memory, knowledge graph, authority, audit, config, device, sync ops, conflicts, backups, exports |
| `<HOME>/data/artifacts/` | Filesystem, content-hash keyed, SQLite metadata | artifact bytes |
| `<HOME>/data/device.json` | JSON | device identity |
| `<HOME>/backups/` | zip (+optional Fernet `.zip.enc`), manifest | backup registry in DB |

## Pre-existing stores (unchanged, mapped)

| Location | Technology | Content | Master 61 treatment |
|---|---|---|---|
| `<HOME>/state.db` | SQLite WAL + FTS5 (`aetheros_state.py`, schema v15) | sessions, messages | left authoritative; new layer does not duplicate sessions |
| `<HOME>/knowledge/*.db` | SQLite WAL (`aetheros_knowledge/store.py`) | knowledge base | mapped as KNOWLEDGE source; canonical graph in new DB |
| `<HOME>/research/research.db` | SQLite WAL (`agent/research/store.py`) | research tasks/claims/evidence | mapped to task/event domains |
| `<HOME>/memory_os/memory_os.db` | SQLite WAL (`agent/memory_os/store.py`) | memory OS | mapped; canonical memory in new DB |
| `<HOME>/memory_intelligence/store` | SQLite + HMAC chain | memory intelligence | mapped |
| `<HOME>/observability/*.db` | SQLite (`aetheros_observability/storage.py`) | metrics/traces | mapped to observability, not duplicated |
| `<HOME>/cron/jobs.json` + `.tick.lock` | JSON + file lock | schedules | mapped to automation domain |
| `<HOME>/reliability/checkpoints/` | JSON atomic writes (`aetheros_reliability/checkpoint.py`) | component checkpoints | mapped; canonical checkpoints in new DB |
| `<HOME>/checkpoints/store/` | bare git | trajectory caches | excluded from backup (machine-local) |
| `<HOME>/skills/.usage.json` | JSON sidecar (`tools/skill_usage.py`) | skill telemetry | mapped, backed up in FULL |
| `<HOME>/audit.jsonl` | JSONL append | comms audit | mapped; canonical audit in new DB |
| `<HOME>/config.yaml` | YAML | settings | layered config source |
| `<HOME>/.env` | env file, secrets | API keys | NEVER in backups by default |
| `<HOME>/mcp-tokens/` | JSON 0600 | MCP OAuth | NEVER in backups by default |
| `<HOME>/comms/signing.key` | key 0600 | comms signing | NEVER in backups by default |
| `<HOME>/cache/` | files | embeddings/browser/HTTP/model caches | disposable; retention purges >7d |
| `<HOME>/extensions/`, `<HOME>/plugins/` | dirs | extension state | extension domain |
| `<HOME>/cloud/{workspaces,teams,sync,storage,audit,knowledge,remote}/` | JSON/dirs | cloud features | integration domain |
| `localStorage/IndexedDB` (desktop), Electron storage | browser | UI prefs | NOT implemented server-side (BLOCKED: needs Electron harness) |
| PostgreSQL / ObjectStorage / RemoteDatabase | — | — | NOT supported (provider matrix documents SQLite-only) |

## Legacy paths (section 110)

`HERMES_HOME` env fallback (deprecated), `~/.hermes`-era names, `MESSAGING_CWD`/
`TERMINAL_CWD` in `.env` (removed; canonical is `terminal.cwd` in config.yaml).
Migration preserves legacy state; nothing is deleted until verified.

## Key findings driving design

1. Session/memory/research/knowledge each own a SQLite DB — correct locally;
   unifying them into one DB would be a risky rewrite with no evidence of
   benefit. Master 61 adds ONE canonical DB for the domains that had NO
   transactional home (tasks, checkpoints, leases, side effects, authority,
   sync, backups) and maps the rest.
2. Existing backup (`aetheros_cli/backup.py`) zips `$HOME` with sqlite-backup
   snapshots and secret exclusions — reused as the pattern for the new
   `BackupManager`, extended with manifest hashes, verify, encryption, registry.
3. Sync (`aetheros_cli/sync_engine.py`) already has offline queue/conflicts for
   cloud scopes; the new `SyncEngine` covers the canonical domains with
   explicit non-syncable enforcement and policy gating.
