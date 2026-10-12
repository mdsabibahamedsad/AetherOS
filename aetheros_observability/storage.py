"""Telemetry storage — SQLite-backed with retention, rotation and cleanup.

Stores traces, events, incidents and evaluations under
``<aetheros_home>/observability/telemetry.db``.  Supports retention
policies (do not retain everything forever), row caps (avoid unbounded
growth) and offline buffering with bounded memory.  Storage failures are
isolated — they never crash the main application.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_observability.redaction import redact_payload

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    name TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL,
    duration_ms REAL,
    status TEXT,
    attributes TEXT,
    session_id TEXT,
    mission_id TEXT,
    task_id TEXT,
    agent_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_time ON spans(start_time);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    component TEXT,
    severity TEXT,
    message TEXT,
    payload TEXT,
    trace_id TEXT,
    session_id TEXT,
    mission_id TEXT,
    task_id TEXT,
    agent_id TEXT,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    severity TEXT,
    component TEXT,
    message TEXT,
    first_seen REAL,
    last_seen REAL,
    count INTEGER,
    state TEXT,
    trace_ids TEXT,
    recovery_state TEXT
);
CREATE INDEX IF NOT EXISTS idx_incidents_state ON incidents(state);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    outcome TEXT,
    agent_id TEXT,
    mission_id TEXT,
    duration_ms REAL,
    cost_usd REAL,
    error_type TEXT,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evals_time ON evaluations(timestamp);
"""


class TelemetryStore:
    """Thread-safe SQLite telemetry store with retention and cleanup.

    Usage::

        store = TelemetryStore()
        store.save_span(span_dict)
        store.save_event(event_dict)
        store.cleanup(retention_days=30)
        rows = store.query_events(limit=50)
    """

    def __init__(self, db_path: Optional[str] = None,
                 max_events: int = 20000,
                 max_spans: int = 20000) -> None:
        if db_path is None:
            db_path = self._default_db_path()
        self._db_path = str(db_path)
        self._max_events = max_events
        self._max_spans = max_spans
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._offline_buffer: List[Dict[str, Any]] = []
        self._max_buffer = 2000
        self._failed = False

    @staticmethod
    def _default_db_path() -> str:
        try:
            from aetheros_constants import get_aetheros_home
            home = get_aetheros_home()
            return str(home / "observability" / "telemetry.db")
        except Exception:
            return "observability/telemetry.db"

    # ------------------------------------------------------------------
    # Connection management (failure-isolated)
    # ------------------------------------------------------------------

    @property
    def conn(self) -> Optional[sqlite3.Connection]:
        if self._conn is None:
            try:
                path = Path(self._db_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
                self._conn.executescript(_SCHEMA)
                self._conn.commit()
                self._failed = False
            except Exception as exc:
                logger.warning("Telemetry store unavailable: %s", exc)
                self._failed = True
                self._conn = None
        return self._conn

    def _close_conn(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Writes (never raise into callers)
    # ------------------------------------------------------------------

    def save_span(self, span: Dict[str, Any]) -> bool:
        attrs = span.get("attributes") or {}
        try:
            conn = self.conn
            if conn is None:
                return self._buffer(("span", span))
            with self._lock:
                conn.execute(
                    """INSERT OR REPLACE INTO spans
                       (span_id, trace_id, parent_span_id, name, start_time,
                        end_time, duration_ms, status, attributes, session_id,
                        mission_id, task_id, agent_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        span.get("span_id", ""),
                        span.get("trace_id", ""),
                        span.get("parent_span_id"),
                        span.get("name", ""),
                        span.get("start_time", time.time()),
                        span.get("end_time"),
                        span.get("duration_ms"),
                        span.get("status", "ok"),
                        json.dumps(attrs, default=str),
                        attrs.get("session_id"),
                        attrs.get("mission_id"),
                        attrs.get("task_id"),
                        attrs.get("agent_id"),
                    ),
                )
                conn.commit()
            self._prune("spans", "span_id", self._max_spans)
            return True
        except Exception as exc:
            logger.debug("Span persistence failed: %s", exc)
            self._close_conn()
            return False

    def save_event(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload") or {}
        try:
            conn = self.conn
            if conn is None:
                return self._buffer(("event", event))
            with self._lock:
                conn.execute(
                    """INSERT INTO events
                       (event_type, component, severity, message, payload,
                        trace_id, session_id, mission_id, task_id, agent_id,
                        timestamp)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        event.get("event_type", "unknown"),
                        event.get("component", ""),
                        event.get("severity", "INFO"),
                        event.get("message", ""),
                        json.dumps(redact_payload(payload), default=str),
                        event.get("trace_id"),
                        event.get("session_id"),
                        event.get("mission_id"),
                        event.get("task_id"),
                        event.get("agent_id"),
                        event.get("timestamp", time.time()),
                    ),
                )
                conn.commit()
            self._prune("events", "id", self._max_events)
            return True
        except Exception as exc:
            logger.debug("Event persistence failed: %s", exc)
            self._close_conn()
            return False

    def save_incident(self, incident: Dict[str, Any]) -> bool:
        try:
            conn = self.conn
            if conn is None:
                return False
            with self._lock:
                conn.execute(
                    """INSERT OR REPLACE INTO incidents
                       (incident_id, key, severity, component, message,
                        first_seen, last_seen, count, state, trace_ids,
                        recovery_state)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        incident.get("incident_id", ""),
                        incident.get("key", ""),
                        incident.get("severity", "WARNING"),
                        incident.get("component", ""),
                        incident.get("message", ""),
                        incident.get("first_seen", time.time()),
                        incident.get("last_seen", time.time()),
                        incident.get("count", 1),
                        incident.get("state", "DETECTED"),
                        json.dumps(incident.get("trace_ids", [])),
                        incident.get("recovery_state", ""),
                    ),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.debug("Incident persistence failed: %s", exc)
            self._close_conn()
            return False

    def save_evaluation(self, evaluation: Dict[str, Any]) -> bool:
        try:
            conn = self.conn
            if conn is None:
                return False
            with self._lock:
                conn.execute(
                    """INSERT INTO evaluations
                       (task_id, outcome, agent_id, mission_id, duration_ms,
                        cost_usd, error_type, timestamp)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        evaluation.get("task_id", ""),
                        evaluation.get("outcome", ""),
                        evaluation.get("agent_id", ""),
                        evaluation.get("mission_id", ""),
                        evaluation.get("duration_ms", 0.0),
                        evaluation.get("cost_usd", 0.0),
                        evaluation.get("error_type", ""),
                        evaluation.get("timestamp", time.time()),
                    ),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.debug("Evaluation persistence failed: %s", exc)
            self._close_conn()
            return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query_events(self, *, limit: int = 100,
                     event_type: str = "") -> List[Dict[str, Any]]:
        conn = self.conn
        if conn is None:
            return []
        try:
            with self._lock:
                if event_type:
                    rows = conn.execute(
                        "SELECT * FROM events WHERE event_type=? "
                        "ORDER BY id DESC LIMIT ?", (event_type, limit)).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                        (limit,)).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM events LIMIT 0").description]
            return [_row_dict(rows[i], cols) for i in range(len(rows))]
        except Exception:
            return []

    def query_spans(self, *, trace_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.conn
        if conn is None:
            return []
        try:
            with self._lock:
                if trace_id:
                    rows = conn.execute(
                        "SELECT * FROM spans WHERE trace_id=? ORDER BY start_time LIMIT ?",
                        (trace_id, limit)).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM spans ORDER BY start_time DESC LIMIT ?",
                        (limit,)).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM spans LIMIT 0").description]
            return [_row_dict(rows[i], cols) for i in range(len(rows))]
        except Exception:
            return []

    def query_incidents(self, *, active_only: bool = True) -> List[Dict[str, Any]]:
        conn = self.conn
        if conn is None:
            return []
        try:
            with self._lock:
                if active_only:
                    rows = conn.execute(
                        "SELECT * FROM incidents WHERE state NOT IN ('RESOLVED','RECOVERED') "
                        "ORDER BY last_seen DESC").fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM incidents ORDER BY last_seen DESC").fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM incidents LIMIT 0").description]
            return [_row_dict(rows[i], cols) for i in range(len(rows))]
        except Exception:
            return []

    def query_evaluations(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.conn
        if conn is None:
            return []
        try:
            with self._lock:
                rows = conn.execute(
                    "SELECT * FROM evaluations ORDER BY id DESC LIMIT ?",
                    (limit,)).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM evaluations LIMIT 0").description]
            return [_row_dict(rows[i], cols) for i in range(len(rows))]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Retention / cleanup
    # ------------------------------------------------------------------

    def cleanup(self, *, retention_days: int = 30) -> Dict[str, int]:
        """Delete rows older than *retention_days* and flush offline buffer."""
        flushed = self.flush_buffer()
        conn = self.conn
        if conn is None:
            return {"flushed": flushed, "deleted": 0}
        cutoff = time.time() - (retention_days * 86400)
        deleted = 0
        try:
            with self._lock:
                for table, col in (
                    ("events", "timestamp"),
                    ("spans", "start_time"),
                    ("evaluations", "timestamp"),
                    ("incidents", "last_seen"),
                ):
                    deleted += conn.execute(
                        f"DELETE FROM {table} WHERE {col} < ?", (cutoff,)).rowcount
                conn.commit()
        except Exception as exc:
            logger.debug("Telemetry cleanup failed: %s", exc)
        return {"flushed": flushed, "deleted": deleted}

    def stats(self) -> Dict[str, Any]:
        conn = self.conn
        counts = {"events": 0, "spans": 0, "incidents": 0, "evaluations": 0}
        if conn is not None:
            try:
                with self._lock:
                    for table in counts:
                        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        counts[table] = row[0] if row else 0
            except Exception:
                pass
        return {
            **counts,
            "offline_buffered": len(self._offline_buffer),
            "store_healthy": not self._failed,
            "db_path": self._db_path,
        }

    # ------------------------------------------------------------------
    # Offline buffering (bounded memory, never unbounded growth)
    # ------------------------------------------------------------------

    def _buffer(self, entry: tuple) -> bool:
        with self._lock:
            if len(self._offline_buffer) >= self._max_buffer:
                return False  # backpressure: drop oldest rather than grow unbounded
            self._offline_buffer.append(entry)
        return True

    def flush_buffer(self) -> int:
        with self._lock:
            buffer = list(self._offline_buffer)
            self._offline_buffer.clear()
        conn = self.conn
        if conn is None:
            with self._lock:
                self._offline_buffer = buffer[:self._max_buffer] + self._offline_buffer
            return 0
        flushed = 0
        for kind, payload in buffer:
            try:
                if kind == "span":
                    self.save_span(payload)
                else:
                    self.save_event(payload)
                flushed += 1
            except Exception:
                break
        return flushed

    # ------------------------------------------------------------------
    # Pruning / rotation
    # ------------------------------------------------------------------

    def _prune(self, table: str, id_col: str, max_rows: int) -> None:
        try:
            conn = self.conn
            if conn is None:
                return
            with self._lock:
                count_row = conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()
                count = count_row[0] if count_row else 0
                if count > max_rows:
                    conn.execute(
                        f"DELETE FROM {table} WHERE {id_col} IN "
                        f"(SELECT {id_col} FROM {table} ORDER BY rowid ASC "
                        f"LIMIT ?)", (count - max_rows,))
                    conn.commit()
        except Exception:
            pass

    def close(self) -> None:
        self.flush_buffer()
        self._close_conn()


def _row_dict(row, cols) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for col, value in zip(cols, row):
        out[col] = value
    return out


_telemetry_store: Optional[TelemetryStore] = None


def get_telemetry_store() -> TelemetryStore:
    """Return the process-wide TelemetryStore singleton."""
    global _telemetry_store
    if _telemetry_store is None:
        _telemetry_store = TelemetryStore()
    return _telemetry_store