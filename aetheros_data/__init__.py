"""AetherOS canonical data layer (Master 61).

Local-first durable state foundation. Single SQLite database with WAL,
foreign keys, busy timeout, versioned migrations, transactional state
transitions, CAS/optimistic concurrency, idempotency keys, durable events,
checkpoints, leases, side-effect reconciliation, artifacts, memory, knowledge
graph, authority, audit, config, devices, sync ops, conflicts, backups.

All paths are profile-aware via ``get_aetheros_home()``. Nothing here
requires cloud access. ``LOCAL_ONLY`` is the default mode.
"""

from aetheros_data.domains import (
    STORAGE_DOMAINS,
    STORAGE_CLASSIFICATION,
    SYNCABLE_DOMAINS,
    NON_SYNCABLE_DOMAINS,
)
from aetheros_data.engine import StorageEngine, get_engine, SCHEMA_VERSION

__all__ = [
    "STORAGE_DOMAINS",
    "STORAGE_CLASSIFICATION",
    "SYNCABLE_DOMAINS",
    "NON_SYNCABLE_DOMAINS",
    "StorageEngine",
    "get_engine",
    "SCHEMA_VERSION",
]
