"""Canonical data domains (Master 61 sections 3-4, 34, 60-61).

Logical separation is mandatory; physical separation is one SQLite database
(``aetheros_data/engine.py``) plus a filesystem artifact store, which is
appropriate for a local-first single-writer workload.
"""

from __future__ import annotations

STORAGE_DOMAINS = (
    "identity",
    "authority",
    "task",
    "agent",
    "checkpoint",
    "event",
    "audit",
    "memory",
    "knowledge_graph",
    "artifact",
    "configuration",
    "automation",
    "integration",
    "extension",
    "device",
    "cache",
    "backup",
)

# Storage classification per domain (section 34).
STORAGE_CLASSIFICATION = {
    "identity": "CRITICAL",
    "authority": "CRITICAL",
    "task": "DURABLE",
    "agent": "DURABLE",
    "checkpoint": "DURABLE",
    "event": "DURABLE",
    "audit": "ARCHIVAL",
    "memory": "DURABLE",
    "knowledge_graph": "DURABLE",
    "artifact": "DURABLE",
    "configuration": "CRITICAL",
    "automation": "DURABLE",
    "integration": "DURABLE",
    "extension": "DURABLE",
    "device": "DURABLE",
    "cache": "EPHEMERAL",
    "backup": "ARCHIVAL",
}

# Retention defaults in days per domain (section 33). None = keep until
# explicit user action.
RETENTION_DEFAULTS_DAYS = {
    "audit_security": 365,
    "audit_debug": 30,
    "checkpoint": 30,
    "event_durable": 180,
    "cache": 7,
    "backup": 90,
}

# Sync classification (section 61).
SYNCABLE_DOMAINS = frozenset({
    "configuration",
    "task",
    "automation",
    "memory",
    "artifact",  # metadata only; bytes travel separately on demand
    "knowledge_graph",
    "extension",
})

NON_SYNCABLE_DOMAINS = frozenset({
    "identity",  # secrets/credentials never auto-sync
    "authority",  # grants require explicit re-issue per device
    "audit",  # local evidence chain; export only via governed path
    "checkpoint",  # execution leases are device-local
    "event",  # device-local log; sync via SyncEnvelope ops instead
    "device",
    "cache",
    "backup",
})

STATE_VS_MEMORY = {
    "execution_state": "required to resume an active task; lifecycle ends with the task",
    "memory": "knowledge intended to persist across tasks; versioned, provenance-tracked",
    "authority_state": "identity/grants/delegation/revocation; revalidated on restore",
    "audit_state": "append-only security/policy evidence; never rewritten",
    "artifact_state": "files/reports/datasets; content-addressed, versioned",
    "configuration_state": "layered SYSTEM/USER/PROJECT/TASK/AGENT/DEVICE settings",
    "cache_state": "disposable derived data; deletion must never destroy truth",
}
