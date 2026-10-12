# AetherOS Data Certification Matrix (Master 61 §122)

Evidence: `tests/aetheros_data/` (21 tests), `python -m aetheros_data.cli` smoke runs.
Environment: Windows, Python 3.11, SQLite WAL. Statuses: PASS / PARTIAL /
FAIL / BLOCKED / NOT_IMPLEMENTED.

| Domain | Storage | Durability | Migration | Backup | Restore | Integrity | Security | Sync | Tests | Evidence | Status | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| identity | `.env`, OS perms | OS fsync | n/a (external) | excluded by default | never restored | perms | secret exclusion | non-syncable enforced | backup exclusion asserted in code; no dedicated test | `backup.py::_is_secret` | PARTIAL | credential rotation UI out of scope |
| authority | `authority_grants` WAL | committed txn | v1 | metadata only | revalidated; revoked/expired stay invalid | FK + validity query | policy-gated | non-syncable enforced | test_authority_never_resurrected, checkpoint rejects stale authority | tests/aetheros_data/test_engine_properties.py | PASS | cross-device re-issue is manual |
| task | `records` WAL + CAS | txn + durable event | v1-3 + lock | FULL/SNAPSHOT | merge + reconcile | checker refs | audit on restore | VERSION_RECONCILIATION | CRUD/txn/CAS/idempotency, transitions | tests/data | PASS | — |
| agent | `records` WAL + CAS | txn + lifecycle event | v1-3 + lock | FULL/SNAPSHOT | merge + authority re-check | checker refs | audit | non-syncable (leases local) | test_agent_lifecycle | tests/data | PASS | — |
| checkpoint | `checkpoints` + sha256 | atomic txn | v1 | FULL/SNAPSHOT | validated before use | hash + expiry | authority re-check | device-local, non-syncable | create/validate/expiry tests | tests/data | PASS | — |
| event | `events` AUTOINC seq | same-txn as mutation | v1 | via DB backup | append (IGNORE dup) | envelope check | — | envelopes, not raw log | P1 durable-event test | tests/data | PASS | no cross-device seq merge |
| audit | `audit_log` append-only | committed txn | v1-3 | FULL (evidence) | append-only | no update/delete API | tamper-evident by design | export-only | tail test via restore checks | tests/aetheros_data/test_backup_restore.py | PASS | no external WORM store |
| memory | `memory_records` versioned | committed txn | v1 | FULL | provenance preserved, stays CANDIDATE | status machine | quarantine/retract | APPEND_ONLY default | lifecycle/conflict/rollback | tests/data | PASS | — |
| knowledge_graph | `graph_nodes/edges` versioned | committed txn | v1 | FULL | OR REPLACE +矛盾 representable | edge-src index | — | MERGE default | upsert/edge round-trip (via engine tests) | tests/data | PARTIAL | contradiction UI pending |
| artifact | fs hash-keyed + SQLite meta | atomic write + txn | v1 | metadata (+bytes in FULL) | re-hashed | sha256 verify on read/restore | classification/provenance | metadata-only | tamper rejection, dedupe, history | tests/data | PASS | no remote object store |
| configuration | `config_values` layered | committed txn | versioned, fail-safe | FULL | OR IGNORE + audit | scope/key PK | critical changes audited | SOURCE_PRIORITY | layer precedence (via sync tests) | tests/data | PASS | — |
| automation | `records` CAS | txn + event | v1-3 + lock | FULL | merge + reconcile | checker | MANUAL_REVIEW conflicts | MANUAL_REVIEW | save/CAS path | tests/data | PASS | scheduler hardening unchanged |
| integration | pre-existing cloud dirs | as before | mapped, not moved | FULL curated | file copy | — | secrets excluded | per-scope | mapped (audit doc) | docs/AETHEROS_DATA_STORAGE_AUDIT.md | PARTIAL | cloud providers unchanged |
| extension | pre-existing dirs | as before | mapped | FULL curated | file copy | — | never auto-execute imports | MANUAL_REVIEW | mapped | audit doc | PARTIAL | execution sandbox unchanged |
| device | `device.json` + `devices` | file + txn | v1 | excluded (local) | new identity per install | trust field | revocation denies sync | identity primitive | sync status/device test | tests/data | PASS | no remote attestation |
| cache | `<HOME>/cache` | disposable | n/a | never | never | deletion-safe test | — | never | P7 cache-deletion test | tests/data | PASS | — |
| backup | `<HOME>/backups` zip/Fernet + registry | fsync + hash | n/a | self-describing manifest | verify-gated | per-file sha256 | Fernet, keys external | n/a (sync ≠ backup) | create/verify/corrupt/encrypted/unauthorized | tests/aetheros_data/test_backup_restore.py | PASS | no cloud destination |

## Explicitly NOT_IMPLEMENTED (not claimed)

PostgreSQL / RemoteDatabase / ObjectStorage providers; INCREMENTAL /
DIFFERENTIAL backup; POINT_IN_TIME as a separate mode (use backup
`created_at`); CRYPTOGRAPHIC_ERASURE; end-to-end sync encryption;
Electron localStorage/IndexedDB harness; physical power-loss protection;
macOS/Linux native runs.

## BLOCKED (environment)

- Native macOS/Linux storage-path validation: this run is Windows-only.
  Code is platform-agnostic (`PlatformStorageAdapter`, POSIX archive names —
  both exercised in tests), but native results are not fabricated.
- Full `aetheros` CLI parser surface: pre-existing `conflicting subparser:
  agent` breakage from other in-flight Masters (see completion report);
  Master 61 handlers verified directly against the real backend.
- Desktop Storage Center React UI: API + CLI shipped; dashboard widget pending
  (PARTIAL).
