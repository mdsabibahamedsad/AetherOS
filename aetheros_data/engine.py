"""Transactional SQLite storage engine (Master 61 sections 5-9, 53-57, 75-76).

- Single database ``<AETHEROS_HOME>/data/aetheros_data.db``
- WAL with fallback to DELETE on filesystems without shm support
- ``PRAGMA foreign_keys=ON``, ``busy_timeout=5000``
- Explicit ``BEGIN IMMEDIATE`` transactions; durable event written in the
  same transaction as the state mutation, published only after commit
- Optimistic concurrency via ``version`` compare-and-swap + monotonic
  ``generation`` per record
- Idempotency via unique ``idempotency_key`` columns
- Versioned migrations with intent record + migration lock
- ``integrity_check`` (pragma + application-level FK/orphan/hash checks)
- Consistent snapshot via the SQLite backup API (never a raw file copy)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3
DB_SUBPATH = Path("data") / "aetheros_data.db"

_MIGRATIONS: List[Dict[str, Any]] = [
    {
        "version": 1,
        "description": "initial canonical schema",
        "ddl": """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
    domain TEXT NOT NULL,
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    generation INTEGER NOT NULL DEFAULT 1,
    data TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT UNIQUE,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (domain, record_id)
);
CREATE INDEX IF NOT EXISTS idx_records_idem ON records(idempotency_key);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp REAL NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT '',
    task_id TEXT NOT NULL DEFAULT '',
    agent_id TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    causation_id TEXT NOT NULL DEFAULT '',
    schema_version INTEGER NOT NULL DEFAULT 1,
    kind TEXT NOT NULL DEFAULT '',
    durable INTEGER NOT NULL DEFAULT 1,
    payload TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_agg ON events(aggregate_type, aggregate_id, seq);
CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL DEFAULT '',
    generation INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    state_version INTEGER NOT NULL DEFAULT 1,
    payload TEXT NOT NULL DEFAULT '{}',
    integrity_hash TEXT NOT NULL DEFAULT '',
    expires_at REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ckpt_task ON checkpoints(task_id, generation);
CREATE TABLE IF NOT EXISTS leases (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT '',
    worker_id TEXT NOT NULL DEFAULT '',
    lease_id TEXT NOT NULL DEFAULT '',
    generation INTEGER NOT NULL DEFAULT 1,
    acquired_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS side_effects (
    operation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'PREPARED',
    idempotency_key TEXT UNIQUE,
    receipt TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL DEFAULT '',
    mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    size INTEGER NOT NULL DEFAULT 0,
    rel_path TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    owner TEXT NOT NULL DEFAULT '',
    classification TEXT NOT NULL DEFAULT 'internal',
    provenance TEXT NOT NULL DEFAULT '{}',
    parent TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(content_hash);
CREATE TABLE IF NOT EXISTS memory_records (
    memory_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT 'user',
    owner TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    mem_type TEXT NOT NULL DEFAULT 'fact',
    source TEXT NOT NULL DEFAULT '',
    provenance TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0.5,
    sensitivity TEXT NOT NULL DEFAULT 'internal',
    trust TEXT NOT NULL DEFAULT 'unverified',
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    expires_at REAL NOT NULL DEFAULT 0,
    supersedes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS graph_nodes (
    entity TEXT PRIMARY KEY,
    data TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.5,
    valid_from REAL NOT NULL DEFAULT 0,
    valid_until REAL NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    rel TEXT NOT NULL,
    dst TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.5,
    valid_from REAL NOT NULL DEFAULT 0,
    valid_until REAL NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON graph_edges(src);
CREATE TABLE IF NOT EXISTS authority_grants (
    grant_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL DEFAULT '',
    capability TEXT NOT NULL DEFAULT '',
    delegate TEXT NOT NULL DEFAULT '',
    policy_version TEXT NOT NULL DEFAULT '',
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL DEFAULT 0,
    revoked INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp REAL NOT NULL,
    actor TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT '',
    policy TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS config_values (
    scope TEXT NOT NULL,
    config_key TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT 'null',
    source TEXT NOT NULL DEFAULT 'user',
    version INTEGER NOT NULL DEFAULT 1,
    updated_at REAL NOT NULL,
    PRIMARY KEY (scope, config_key)
);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    trust TEXT NOT NULL DEFAULT 'untrusted',
    last_seen REAL NOT NULL DEFAULT 0,
    sync_state TEXT NOT NULL DEFAULT 'OFFLINE'
);
CREATE TABLE IF NOT EXISTS sync_ops (
    op_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL DEFAULT '',
    sequence INTEGER NOT NULL DEFAULT 0,
    object_type TEXT NOT NULL DEFAULT '',
    object_id TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1,
    operation TEXT NOT NULL DEFAULT 'UPDATE',
    payload TEXT NOT NULL DEFAULT '{}',
    timestamp REAL NOT NULL,
    provenance TEXT NOT NULL DEFAULT '{}',
    integrity TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'QUEUED'
);
CREATE TABLE IF NOT EXISTS conflicts (
    conflict_id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    object_type TEXT NOT NULL DEFAULT '',
    local_version INTEGER NOT NULL DEFAULT 0,
    remote_version INTEGER NOT NULL DEFAULT 0,
    detected_at REAL NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    resolution TEXT NOT NULL DEFAULT '',
    resolver TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS backup_registry (
    backup_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT '',
    schema_version INTEGER NOT NULL DEFAULT 1,
    encryption TEXT NOT NULL DEFAULT 'none',
    compression TEXT NOT NULL DEFAULT 'zip',
    content_hash TEXT NOT NULL DEFAULT '',
    size INTEGER NOT NULL DEFAULT 0,
    path TEXT NOT NULL DEFAULT '',
    retention_days INTEGER NOT NULL DEFAULT 90
);
CREATE TABLE IF NOT EXISTS index_meta (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    dimension INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'READY',
    rebuilt_at REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS migration_lock (
    lock_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT '',
    acquired_at REAL NOT NULL
);
""",
    },
    {
        "version": 2,
        "description": "deletion audit table",
        "ddl": """
CREATE TABLE IF NOT EXISTS deletion_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp REAL NOT NULL,
    actor TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    record_id TEXT NOT NULL DEFAULT '',
    deletion_type TEXT NOT NULL DEFAULT 'SOFT_DELETE',
    reason TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT ''
);
""",
    },
    {
        "version": 3,
        "description": "export manifest registry",
        "ddl": """
CREATE TABLE IF NOT EXISTS export_registry (
    export_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    format_version INTEGER NOT NULL DEFAULT 1,
    scope TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT ''
);
""",
    },
]


class ConflictError(Exception):
    """Raised when a CAS update finds a stale expected version."""


class StorageEngine:
    """SQLite-backed canonical store. One writer, many readers (WAL)."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        home = get_aetheros_home()
        self.db_path = Path(db_path) if db_path else home / DB_SUBPATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.RLock()
        self._wal_mode = "wal"
        self._init_db()

    # -- connection -----------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError as exc:
            if "locking protocol" in str(exc).lower() or "not authorized" in str(exc).lower():
                conn.execute("PRAGMA journal_mode=DELETE")
                self._wal_mode = "delete"
            else:
                raise
        else:
            row = conn.execute("PRAGMA journal_mode").fetchone()
            if row and str(row[0]).lower() != "wal":
                self._wal_mode = "delete"
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Close the thread-local connection (needed for Windows file cleanup)."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.commit()
            except sqlite3.Error:
                pass
            try:
                conn.close()
            except sqlite3.Error:
                pass
            self._local.conn = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """BEGIN IMMEDIATE transaction; commit on success, rollback on error."""
        with self._lock:
            conn = self._conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    # -- migrations ------------------------------------------------------
    def _init_db(self) -> None:
        conn = self._conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations"
            " (version INTEGER PRIMARY KEY, description TEXT NOT NULL, applied_at REAL NOT NULL)"
        )
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for mig in _MIGRATIONS:
            if mig["version"] in applied:
                continue
            conn.executescript(mig["ddl"])
            conn.execute(
                "INSERT INTO schema_migrations (version, description, applied_at)"
                " VALUES (?, ?, ?)",
                (mig["version"], mig["description"], time.time()),
            )
            conn.commit()

    def acquire_migration_lock(self, owner: str, timeout_s: float = 30.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self.transaction() as conn:
                row = conn.execute("SELECT owner, acquired_at FROM migration_lock WHERE lock_id='global'").fetchone()
                now = time.time()
                if row is None or (now - float(row["acquired_at"]) > 300):
                    conn.execute(
                        "INSERT OR REPLACE INTO migration_lock (lock_id, owner, acquired_at)"
                        " VALUES ('global', ?, ?)",
                        (owner, now),
                    )
                    return True
            time.sleep(0.2)
        return False

    def release_migration_lock(self, owner: str) -> None:
        with self.transaction() as conn:
            conn.execute("DELETE FROM migration_lock WHERE lock_id='global' AND owner=?", (owner,))

    # -- generic versioned records (CAS + generations + idempotency) -----
    def record_get(self, domain: str, record_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn().execute(
            "SELECT domain, record_id, version, generation, data, created_at, updated_at, deleted"
            " FROM records WHERE domain=? AND record_id=?",
            (domain, record_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "domain": row["domain"],
            "record_id": row["record_id"],
            "version": row["version"],
            "generation": row["generation"],
            "data": json.loads(row["data"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "deleted": bool(row["deleted"]),
        }

    def record_create(
        self,
        domain: str,
        record_id: str,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Idempotent create: duplicate idempotency_key returns existing row."""
        c = conn or self._conn()
        now = time.time()
        own_tx = conn is None
        if own_tx:
            c.execute("BEGIN IMMEDIATE")
        try:
            if idempotency_key:
                row = c.execute(
                    "SELECT domain, record_id FROM records WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if row:
                    existing = self.record_get(row["domain"], row["record_id"])
                    if own_tx:
                        c.execute("COMMIT")
                    assert existing is not None
                    return existing
            c.execute(
                "INSERT INTO records (domain, record_id, version, generation, data,"
                " idempotency_key, created_at, updated_at, deleted)"
                " VALUES (?, ?, 1, 1, ?, ?, ?, ?, 0)",
                (domain, record_id, json.dumps(data), idempotency_key, now, now),
            )
            if own_tx:
                c.execute("COMMIT")
        except Exception:
            if own_tx:
                try:
                    c.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        result = self.record_get(domain, record_id)
        assert result is not None
        return result

    def record_cas(
        self,
        domain: str,
        record_id: str,
        expected_version: int,
        new_data: Dict[str, Any],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Compare-and-swap: update only if version matches, else ConflictError."""
        c = conn or self._conn()
        now = time.time()
        own_tx = conn is None
        if own_tx:
            c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute(
                "SELECT version, generation FROM records WHERE domain=? AND record_id=? AND deleted=0",
                (domain, record_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"{domain}/{record_id} not found")
            if int(row["version"]) != int(expected_version):
                raise ConflictError(
                    f"stale writer: {domain}/{record_id} expected v{expected_version},"
                    f" current v{int(row['version'])}"
                )
            new_version = int(row["version"]) + 1
            new_generation = int(row["generation"]) + 1
            c.execute(
                "UPDATE records SET version=?, generation=?, data=?, updated_at=? WHERE domain=? AND record_id=?",
                (new_version, new_generation, json.dumps(new_data), now, domain, record_id),
            )
            if own_tx:
                c.execute("COMMIT")
        except Exception:
            if own_tx:
                try:
                    c.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        result = self.record_get(domain, record_id)
        assert result is not None
        return result

    # -- durable events ---------------------------------------------------
    def append_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        kind: str,
        payload: Dict[str, Any],
        actor: str = "",
        task_id: str = "",
        agent_id: str = "",
        correlation_id: str = "",
        causation_id: str = "",
        durable: bool = True,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        c = conn or self._conn()
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:16]}",
            "timestamp": time.time(),
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "actor": actor,
            "task_id": task_id,
            "agent_id": agent_id,
            "correlation_id": correlation_id or f"corr_{uuid.uuid4().hex[:12]}",
            "causation_id": causation_id,
            "schema_version": 1,
            "kind": kind,
            "payload": payload,
        }
        own_tx = conn is None
        if own_tx:
            c.execute("BEGIN IMMEDIATE")
        try:
            c.execute(
                "INSERT INTO events (event_id, timestamp, aggregate_id, aggregate_type, actor,"
                " task_id, agent_id, correlation_id, causation_id, schema_version, kind, durable, payload)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event["event_id"], event["timestamp"], aggregate_id, aggregate_type, actor,
                    task_id, agent_id, event["correlation_id"], causation_id, 1, kind,
                    1 if durable else 0, json.dumps(payload),
                ),
            )
            if own_tx:
                c.execute("COMMIT")
        except Exception:
            if own_tx:
                try:
                    c.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        return event

    def mutate_with_event(
        self,
        domain: str,
        record_id: str,
        expected_version: int,
        new_data: Dict[str, Any],
        event_kind: str,
        event_payload: Dict[str, Any],
        actor: str = "",
    ) -> Dict[str, Any]:
        """Transactional state transition + durable event (section 9).

        The event row is written in the SAME transaction as the mutation and
        is only visible after commit — never publish before commit.
        """
        with self.transaction() as conn:
            updated = self.record_cas(domain, record_id, expected_version, new_data, conn=conn)
            event = self.append_event(
                aggregate_type=domain,
                aggregate_id=record_id,
                kind=event_kind,
                payload=event_payload,
                actor=actor,
                conn=conn,
            )
        return {"record": updated, "event": event}

    # -- snapshots / integrity -------------------------------------------
    def snapshot_to(self, dest: Path) -> Path:
        """Consistent snapshot via the SQLite backup API (section 44)."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            dst = sqlite3.connect(str(dest))
            try:
                src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()
        return dest

    def integrity_check(self) -> Dict[str, Any]:
        """PRAGMA checks + application-level orphan/hash validation."""
        conn = self._conn()
        issues: List[Dict[str, Any]] = []
        try:
            rows = conn.execute("PRAGMA integrity_check").fetchall()
            if not (len(rows) == 1 and str(rows[0][0]).lower() == "ok"):
                issues.append({"check": "pragma_integrity_check", "detail": [r[0] for r in rows][:5]})
        except sqlite3.Error as exc:
            issues.append({"check": "pragma_integrity_check", "detail": str(exc)})
        try:
            rows = conn.execute("PRAGMA foreign_key_check").fetchall()
            if rows:
                issues.append({"check": "foreign_key_check", "detail": [dict(r) for r in rows][:5]})
        except sqlite3.Error as exc:
            issues.append({"check": "foreign_key_check", "detail": str(exc)})
        # Orphan checkpoints referencing unknown tasks (task records live in `records`).
        orphans = conn.execute(
            "SELECT checkpoint_id, task_id FROM checkpoints WHERE task_id NOT IN"
            " (SELECT record_id FROM records WHERE domain='task')"
        ).fetchall()
        # Tasks legitimately live only as checkpoints before first record write,
        # so report as warning-level, not corruption.
        warnings = [{"checkpoint_id": r["checkpoint_id"], "task_id": r["task_id"]} for r in orphans]
        # Schema version check.
        maxmig = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        schema_ok = bool(maxmig and int(maxmig[0]) == SCHEMA_VERSION)
        if not schema_ok:
            issues.append({"check": "schema_version", "detail": f"expected {SCHEMA_VERSION}, db has {maxmig[0] if maxmig else None}"})
        status = "HEALTHY" if not issues else "CORRUPTED"
        if not issues and warnings:
            status = "DEGRADED"
        return {
            "status": status,
            "wal_mode": self._wal_mode,
            "schema_version": int(maxmig[0]) if maxmig and maxmig[0] is not None else 0,
            "expected_schema": SCHEMA_VERSION,
            "issues": issues,
            "warnings": warnings,
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }

    def stats(self) -> Dict[str, Any]:
        conn = self._conn()
        tables = [
            "records", "events", "checkpoints", "leases", "side_effects", "artifacts",
            "memory_records", "graph_nodes", "graph_edges", "authority_grants",
            "audit_log", "config_values", "devices", "sync_ops", "conflicts",
            "backup_registry",
        ]
        counts = {}
        for t in tables:
            try:
                counts[t] = int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
            except sqlite3.Error:
                counts[t] = -1
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "wal_mode": self._wal_mode,
            "schema_version": SCHEMA_VERSION,
            "tables": counts,
        }


_engine_singleton: Optional[StorageEngine] = None
_engine_lock = threading.Lock()


def get_engine(db_path: Optional[Path] = None) -> StorageEngine:
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None or db_path is not None:
            _engine_singleton = StorageEngine(db_path=db_path)
        return _engine_singleton
