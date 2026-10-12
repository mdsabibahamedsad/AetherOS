# AetherOS Data Integrity (§51-52, §79-80)

Detection: `PRAGMA integrity_check`, `foreign_key_check`, schema-version
check, orphan references (checkpoint→task/memory/authority), artifact hash
re-verification, event-envelope completeness, record JSON validity.
`ConsistencyChecker.check()` → HEALTHY / DEGRADED / CORRUPTED with evidence.

Response (§52): never silently repair. Classify RECOVERABLE /
PARTIALLY_RECOVERABLE / UNRECOVERABLE / UNKNOWN, preserve evidence, append an
incident event. Startup (`startup_health_check`) recovers safe state and
reports unresolved issues without blocking on non-critical corruption.
