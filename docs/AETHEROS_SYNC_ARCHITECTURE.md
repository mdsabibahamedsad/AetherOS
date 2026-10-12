# AetherOS Sync Architecture (§58-68)

Sync ≠ backup: sync keeps runtimes compatible; backup keeps history.
Sync is never the only backup.

Device identity (§59): device_id/installation_id/platform/version/trust/
last_seen/sync_state in `<HOME>/data/device.json`, independent from user
identity.

Syncable (§61): preferences, projects, approved memory, task metadata,
automation definitions, model settings, artifact metadata. Never auto-synced:
secrets, browser cookies, device credentials, OS paths, hardware state,
process handles, locks, caches. Enforced in `SyncEngine.enqueue` (raises
`PermissionError`) and `apply_remote`.

Protocol (§62): SyncEnvelope {device_id, sequence, object_type, object_id,
version, operation, payload, timestamp, provenance, integrity} with
CREATE/UPDATE/DELETE/RETRACT/SUPERSEDE.

Offline-first (§65-66): ops queue locally with state QUEUED; statuses
SYNCED/SYNCING/OFFLINE/CONFLICT/ERROR/PAUSED/AUTH_REQUIRED reflect reality;
remote success is never faked while offline.

Security (§67-68): `apply_remote` accepts a `policy_check` (identity/
authority/policy/DLP/revocation); revoked devices get policy-deny. Transport
TLS is the caller's responsibility; end-to-end encryption NOT claimed.
