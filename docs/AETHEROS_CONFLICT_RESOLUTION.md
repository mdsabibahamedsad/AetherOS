# AetherOS Conflict Resolution (§63-64)

LAST_WRITE_WINS is never universal. Defaults per domain
(`aetheros_data/sync.py::DOMAIN_STRATEGY`): configuration SOURCE_PRIORITY,
task/automation VERSION_RECONCILIATION/MANUAL_REVIEW, memory APPEND_ONLY,
knowledge MERGE, artifact VERSION_RECONCILIATION, extension MANUAL_REVIEW.

ConflictRecord {conflict_id, object_id, object_type, local_version,
remote_version, detected_at, reason, resolution, resolver}: both versions
preserved until `resolve()` with KEEP_LOCAL / KEEP_REMOTE / MERGED and an
identified resolver. Resolution appends a durable `sync.conflict_resolved`
event.
