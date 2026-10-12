"""SQLite substrate for the unified memory layer (P75 adapter default).

Profile-safe path ``<AETHEROS_HOME>/memory_os/memory_os.db`` (WAL), following
the Master 17 research-store precedent. Existing memory stores are NOT
touched or migrated. Storage is behind a tiny protocol so alternate backends
can be adapted later (P75).

Threading model: one shared connection guarded by a single reentrant lock —
every public operation is serialized, which is the only safe mode when a
sqlite3 connection is shared across threads.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from agent.memory_os.models import MemoryItem, MemoryStatus


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    memory_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT DEFAULT '',
    content_hash TEXT,
    source_type TEXT,
    source_id TEXT DEFAULT '',
    scope TEXT,
    owner TEXT DEFAULT 'default',
    project_id TEXT DEFAULT '',
    task_id TEXT DEFAULT '',
    confidence TEXT,
    importance REAL DEFAULT 0.5,
    sensitivity TEXT,
    preference_kind TEXT DEFAULT '',
    status TEXT,
    version INTEGER DEFAULT 1,
    created_at REAL, updated_at REAL, last_accessed_at REAL,
    expires_at REAL, valid_from REAL, valid_until REAL, revalidate_after REAL,
    semantic_key TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    entity_ids TEXT DEFAULT '[]',
    relationship_ids TEXT DEFAULT '[]',
    allow_agents INTEGER DEFAULT 0,
    hint_only INTEGER DEFAULT 0,
    provenance TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_scope ON items(scope);
CREATE INDEX IF NOT EXISTS idx_items_project ON items(project_id);
CREATE INDEX IF NOT EXISTS idx_items_task ON items(task_id);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner);
CREATE INDEX IF NOT EXISTS idx_items_skey ON items(semantic_key);

CREATE TABLE IF NOT EXISTS item_versions (
    memory_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    at REAL,
    actor TEXT DEFAULT '',
    note TEXT DEFAULT '',
    PRIMARY KEY (memory_id, version)
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    etype TEXT,
    name TEXT,
    canonical_key TEXT,
    confidence REAL DEFAULT 0.5,
    resolution TEXT DEFAULT 'separate',
    merged_into TEXT DEFAULT '',
    created_at REAL, updated_at REAL,
    meta TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (entity_id, alias)
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    src_kind TEXT NOT NULL,
    src_id TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    rel TEXT NOT NULL,
    evidence_item_id TEXT DEFAULT '',
    confidence REAL DEFAULT 0.5,
    created_at REAL,
    valid_from REAL, valid_until REAL,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS working_slots (
    session_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    payload TEXT DEFAULT '{}',
    updated_at REAL,
    PRIMARY KEY (session_id, slot)
);

CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    at REAL NOT NULL,
    actor TEXT,
    action TEXT NOT NULL,
    target TEXT DEFAULT '',
    detail TEXT DEFAULT '{}',
    prev_hash TEXT DEFAULT '',
    hash TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS counters (
    name TEXT PRIMARY KEY,
    value REAL DEFAULT 0
);
"""

FTS_DDL = [
    "CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5("
    "memory_id UNINDEXED, content, summary)",
]


def _serialized(fn):
    """Serialize an operation on the shared sqlite3 connection."""

    def wrapper(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)

    return wrapper


class AuditChain:
    """Append-only hash-chained audit log (P79). Content is not logged for
    sensitive actions beyond ids/metadata."""

    def __init__(self, store: "MemoryStore"):
        self._store = store

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._store._conn

    @property
    def _lock(self) -> threading.RLock:
        return self._store._lock

    @_serialized
    def append(self, action: str, actor: str, target: str = "",
               detail: Optional[Dict] = None) -> None:
        row = self._conn.execute(
            "SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev = row[0] if row else ""
        at = time.time()
        detail_json = json.dumps(detail or {}, sort_keys=True)
        h = hashlib.sha256(
            f"{prev}|{at}|{action}|{actor}|{target}|{detail_json}".encode()
        ).hexdigest()[:32]
        with self._conn:
            self._conn.execute(
                "INSERT INTO audit_log (at, actor, action, target, detail,"
                " prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
                (at, actor, action, target, detail_json, prev, h),
            )

    @_serialized
    def entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT seq, at, actor, action, target, detail FROM audit_log"
            " ORDER BY seq DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            try:
                detail = json.loads(r[5])
            except (json.JSONDecodeError, TypeError):
                detail = {}
            out.append({"seq": r[0], "at": r[1], "actor": r[2], "action": r[3],
                        "target": r[4], "detail": detail})
        return out

    @_serialized
    def verify(self) -> bool:
        rows = self._conn.execute(
            "SELECT at, actor, action, target, detail, prev_hash, hash"
            " FROM audit_log ORDER BY seq ASC"
        ).fetchall()
        prev = ""
        for r in rows:
            # hash order must match append(): prev|at|action|actor|target|detail
            expect = hashlib.sha256(
                f"{prev}|{r[0]}|{r[2]}|{r[1]}|{r[3]}|{r[4]}".encode()
            ).hexdigest()[:32]
            if r[6] != expect or r[5] != prev:
                return False
            prev = r[6]
        return True


def _db_path(db_path: Optional[str]) -> Path:
    if db_path:
        return Path(db_path)
    from aetheros_constants import get_aetheros_home

    d = get_aetheros_home() / "memory_os"
    d.mkdir(parents=True, exist_ok=True)
    return d / "memory_os.db"


class MemoryStore:
    """Default storage adapter. All queries go through here; every public
    operation holds ``self._lock`` for the duration of the call."""

    def __init__(self, db_path: Optional[str] = None):
        self.path = _db_path(db_path)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        for ddl in FTS_DDL:
            self._conn.execute(ddl)
        self._conn.commit()

    @_serialized
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # -- items -----------------------------------------------------------------

    @_serialized
    def upsert_item(self, item: MemoryItem, actor: str = "", note: str = "") -> None:
        row = item.to_row()
        cur = self._conn.execute(
            "SELECT version FROM items WHERE memory_id=?",
            (item.memory_id,),
        ).fetchone()
        with self._lock, self._conn:
            if cur is None:
                self._conn.execute(
                    "INSERT INTO items (" + ",".join(row.keys()) + ")"
                    " VALUES (" + ",".join("?" * len(row)) + ")",
                    tuple(row.values()),
                )
                self._index_fts(item.memory_id, item.content, item.summary)
                # P24: full version history from v1
                self._conn.execute(
                    "INSERT OR REPLACE INTO item_versions VALUES (?,?,?,?,?,?)",
                    (item.memory_id, item.version, item.content,
                     item.updated_at, actor, note or "created"),
                )
            else:
                old_version = int(cur["version"])
                self._conn.execute(
                    "UPDATE items SET " + ",".join(f"{k}=?" for k in row)
                    + " WHERE memory_id=?",
                    tuple(row.values()) + (item.memory_id,),
                )
                if item.version != old_version:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO item_versions VALUES (?,?,?,?,?,?)",
                        (item.memory_id, item.version, item.content,
                         item.updated_at, actor, note),
                    )
                self._index_fts(item.memory_id, item.content, item.summary)

    def _index_fts(self, memory_id: str, content: str, summary: str) -> None:
        self._conn.execute("DELETE FROM items_fts WHERE memory_id=?", (memory_id,))
        self._conn.execute(
            "INSERT INTO items_fts (memory_id, content, summary) VALUES (?,?,?)",
            (memory_id, content, summary),
        )

    @_serialized
    def get_item(self, memory_id: str) -> Optional[MemoryItem]:
        row = self._conn.execute(
            "SELECT * FROM items WHERE memory_id=?", (memory_id,)
        ).fetchone()
        return MemoryItem.from_row(dict(row)) if row else None

    @_serialized
    def query_items(
        self,
        *,
        statuses: Optional[List[MemoryStatus]] = None,
        types: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        owner: Optional[str] = None,
        project_id: Optional[str] = None,
        semantic_key: Optional[str] = None,
        limit: int = 200,
    ) -> List[MemoryItem]:
        where, params = [], []
        if statuses:
            where.append("status IN (%s)" % ",".join("?" * len(statuses)))
            params += [s.value for s in statuses]
        if types:
            where.append("type IN (%s)" % ",".join("?" * len(types)))
            params += list(types)
        if scopes:
            where.append("scope IN (%s)" % ",".join("?" * len(scopes)))
            params += list(scopes)
        if owner:
            where.append("owner=?")
            params.append(owner)
        if project_id is not None:
            where.append("project_id=?")
            params.append(project_id)
        if semantic_key:
            where.append("semantic_key=?")
            params.append(semantic_key)
        sql = "SELECT * FROM items"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        return [MemoryItem.from_row(dict(r)) for r in self._conn.execute(sql, params)]

    @_serialized
    def fts_search(self, text: str, limit: int = 100) -> List[Tuple[str, float]]:
        """Return (memory_id, bm25_rank) pairs; rank is negative-lower=better."""
        q = "".join(ch if ch.isalnum() else " " for ch in text).split()
        if not q:
            return []
        match = " OR ".join(f'"{t}"' for t in q[:12])
        try:
            rows = self._conn.execute(
                "SELECT memory_id, bm25(items_fts) AS rank FROM items_fts"
                " WHERE items_fts MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [(r["memory_id"], float(r["rank"])) for r in rows]

    @_serialized
    def all_active_contents(self) -> Iterable[Tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT memory_id, content FROM items WHERE status='active'"
        ).fetchall()
        return [(r["memory_id"], r["content"]) for r in rows]

    @_serialized
    def delete_item(self, memory_id: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM items WHERE memory_id=?", (memory_id,)
            )
            self._conn.execute("DELETE FROM items_fts WHERE memory_id=?", (memory_id,))
            self._conn.execute(
                "DELETE FROM item_versions WHERE memory_id=?", (memory_id,)
            )
        return cur.rowcount > 0

    @_serialized
    def purge_status(self, status: MemoryStatus) -> int:
        """Physically remove rows already marked with a terminal status."""
        with self._conn:
            ids = [
                r["memory_id"]
                for r in self._conn.execute(
                    "SELECT memory_id FROM items WHERE status=?", (status.value,)
                )
            ]
        for mid in ids:
            self.delete_item(mid)
        return len(ids)

    @_serialized
    def versions(self, memory_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT version, at, actor, note FROM item_versions"
            " WHERE memory_id=? ORDER BY version ASC",
            (memory_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @_serialized
    def touch_items(self, memory_ids: List[str], at: Optional[float] = None) -> None:
        """Batch last-accessed update (single statement)."""
        if not memory_ids:
            return
        at = at if at is not None else time.time()
        with self._conn:
            self._conn.executemany(
                "UPDATE items SET last_accessed_at=? WHERE memory_id=?",
                [(at, mid) for mid in memory_ids],
            )

    @_serialized
    def update_metadata(self, memory_id: str, metadata: Dict[str, Any]) -> None:
        """Metadata-only update (no content/FTS churn)."""
        with self._conn:
            self._conn.execute(
                "UPDATE items SET metadata=? WHERE memory_id=?",
                (json.dumps(metadata), memory_id),
            )

    # -- entities / edges -------------------------------------------------------

    @_serialized
    def upsert_entity(self, ent: Dict[str, Any]) -> None:
        cols = ",".join(ent.keys())
        with self._conn:
            self._conn.execute(
                f"INSERT INTO entities ({cols}) VALUES ({','.join('?' * len(ent))})"
                " ON CONFLICT(entity_id) DO UPDATE SET "
                + ",".join(f"{k}=excluded.{k}" for k in ent if k != "entity_id"),
                tuple(ent.values()),
            )

    @_serialized
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM entities WHERE entity_id=?", (entity_id,)
        ).fetchone()
        return dict(row) if row else None

    @_serialized
    def find_entities(self, *, etype: Optional[str] = None,
                      resolution: Optional[str] = None) -> List[Dict[str, Any]]:
        where, params = [], []
        if etype:
            where.append("etype=?")
            params.append(etype)
        if resolution:
            where.append("resolution=?")
            params.append(resolution)
        sql = "SELECT * FROM entities"
        if where:
            sql += " WHERE " + " AND ".join(where)
        return [dict(r) for r in self._conn.execute(sql, params)]

    @_serialized
    def add_alias(self, entity_id: str, alias: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO entity_aliases VALUES (?,?)",
                (entity_id, alias.lower()),
            )

    @_serialized
    def alias_lookup(self, name: str) -> List[str]:
        rows = self._conn.execute(
            "SELECT entity_id FROM entity_aliases WHERE alias=?", (name.lower(),)
        ).fetchall()
        return [r["entity_id"] for r in rows]

    @_serialized
    def merge_entity(self, keep_id: str, drop_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE entities SET resolution='merged', merged_into=? "
                "WHERE entity_id=?",
                (keep_id, drop_id),
            )
            self._conn.execute(
                "UPDATE edges SET src_id=? WHERE src_kind='entity' AND src_id=?",
                (keep_id, drop_id),
            )
            self._conn.execute(
                "UPDATE edges SET dst_id=? WHERE dst_kind='entity' AND dst_id=?",
                (keep_id, drop_id),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO entity_aliases SELECT ?, alias FROM"
                " entity_aliases WHERE entity_id=?",
                (keep_id, drop_id),
            )

    @_serialized
    def add_edge(self, edge: Dict[str, Any]) -> None:
        cols = ",".join(edge.keys())
        with self._conn:
            self._conn.execute(
                f"INSERT OR REPLACE INTO edges ({cols}) VALUES"
                f" ({','.join('?' * len(edge))})",
                tuple(edge.values()),
            )

    @_serialized
    def remove_edge(self, edge_id: str) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM edges WHERE edge_id=?", (edge_id,))
        return cur.rowcount > 0

    @_serialized
    def edges_for(self, node_kind: str, node_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE status='active' AND"
            " ((src_kind=? AND src_id=?) OR (dst_kind=? AND dst_id=?))",
            (node_kind, node_id, node_kind, node_id),
        ).fetchall()
        return [dict(r) for r in rows]

    @_serialized
    def all_edges(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM edges")]

    # -- working slots ------------------------------------------------------------

    @_serialized
    def set_slot(self, session_id: str, slot: str, payload: Dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO working_slots VALUES (?,?,?,?)",
                (session_id, slot, json.dumps(payload), time.time()),
            )

    @_serialized
    def get_slot(self, session_id: str, slot: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT payload FROM working_slots WHERE session_id=? AND slot=?",
            (session_id, slot),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    @_serialized
    def clear_slots(self, session_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM working_slots WHERE session_id=?", (session_id,)
            )

    # -- counters / audit -----------------------------------------------------------

    @_serialized
    def bump_counter(self, name: str, delta: float = 1.0) -> float:
        with self._conn:
            self._conn.execute(
                "INSERT INTO counters (name, value) VALUES (?,?)"
                " ON CONFLICT(name) DO UPDATE SET value=value+?",
                (name, delta, delta),
            )
        row = self._conn.execute(
            "SELECT value FROM counters WHERE name=?", (name,)
        ).fetchone()
        return float(row["value"]) if row else 0.0

    @_serialized
    def get_counter(self, name: str) -> float:
        row = self._conn.execute(
            "SELECT value FROM counters WHERE name=?", (name,)
        ).fetchone()
        return float(row["value"]) if row else 0.0

    @property
    def audit(self) -> AuditChain:
        return AuditChain(self)

    @_serialized
    def wipe(self) -> None:
        """Test helper: remove everything."""
        with self._conn:
            for table in ("items", "items_fts", "item_versions", "entities",
                          "entity_aliases", "edges", "working_slots",
                          "audit_log", "counters"):
                self._conn.execute(f"DELETE FROM {table}")
