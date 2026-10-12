"""Workflow store — SQLite-backed persistence with version history."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from workflows.models import (
    WorkflowConfig, WorkflowNode, Connection, ExecutionRecord,
    WorkflowStatus, ExecutionStatus, WorkflowVersion,
)

logger = logging.getLogger(__name__)

_LOCAL = threading.local()
_LOCK = threading.Lock()


def _get_db_path() -> Path:
    return get_aetheros_home() / "workflows.db"


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_LOCAL, "conn") or _LOCAL.conn is None:
        db_path = _get_db_path()
        _LOCAL.conn = sqlite3.connect(str(db_path))
        _LOCAL.conn.row_factory = sqlite3.Row
        _LOCAL.conn.execute("PRAGMA journal_mode=WAL")
        _LOCAL.conn.execute("PRAGMA foreign_keys=ON")
    return _LOCAL.conn


def init_db() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'draft',
            nodes TEXT DEFAULT '[]',
            connections TEXT DEFAULT '[]',
            config TEXT DEFAULT '{}',
            version INTEGER DEFAULT 1,
            schedule TEXT DEFAULT '',
            error_policy TEXT DEFAULT 'stop',
            max_retries INTEGER DEFAULT 3,
            timeout_seconds INTEGER DEFAULT 3600,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            background INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS workflow_versions (
            workflow_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            created_at TEXT DEFAULT '',
            nodes TEXT DEFAULT '[]',
            connections TEXT DEFAULT '[]',
            config TEXT DEFAULT '{}',
            comment TEXT DEFAULT '',
            PRIMARY KEY (workflow_id, version),
            FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workflow_executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            trigger TEXT DEFAULT '',
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            duration_ms REAL DEFAULT 0,
            nodes_total INTEGER DEFAULT 0,
            nodes_completed INTEGER DEFAULT 0,
            nodes_failed INTEGER DEFAULT 0,
            logs TEXT DEFAULT '[]',
            error TEXT DEFAULT '',
            input_data TEXT DEFAULT '{}',
            output_data TEXT DEFAULT 'null',
            FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_wf_name ON workflows(name);
        CREATE INDEX IF NOT EXISTS idx_wf_status ON workflows(status);
        CREATE INDEX IF NOT EXISTS idx_wf_category ON workflows(category);
        CREATE INDEX IF NOT EXISTS idx_wf_exec_workflow ON workflow_executions(workflow_id);
        CREATE INDEX IF NOT EXISTS idx_wf_exec_status ON workflow_executions(status);
    """)
    conn.commit()


class WorkflowStore:
    def __init__(self) -> None:
        init_db()

    def list_workflows(self, include_drafts: bool = True) -> list[WorkflowConfig]:
        return list_workflows(include_drafts=include_drafts)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        return get_workflow(workflow_id)

    def save_workflow(self, workflow: WorkflowConfig) -> WorkflowConfig:
        return save_workflow(workflow)

    def delete_workflow(self, workflow_id: str) -> bool:
        return delete_workflow(workflow_id)

    def update_workflow(self, workflow: WorkflowConfig) -> WorkflowConfig:
        return save_workflow(workflow)

    def save_version(self, workflow_id: str, version: WorkflowVersion) -> None:
        save_version(workflow_id, version)

    def list_versions(self, workflow_id: str) -> list[WorkflowVersion]:
        return list_versions(workflow_id)

    def get_version(self, workflow_id: str, version: int) -> Optional[WorkflowVersion]:
        return get_version(workflow_id, version)

    def save_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        return save_execution(record)

    def list_executions(self, workflow_id: str = None, limit: int = 50) -> list[ExecutionRecord]:
        return list_executions(workflow_id=workflow_id, limit=limit)

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        return get_execution(execution_id)

    def get_recent_executions(self, limit: int = 20) -> list[ExecutionRecord]:
        return get_recent_executions(limit=limit)


# ── Workflow CRUD ─────────────────────────────────────────────────


def list_workflows(include_drafts: bool = True) -> list[WorkflowConfig]:
    conn = _get_conn()
    query = "SELECT * FROM workflows"
    if not include_drafts:
        query += " WHERE status != 'draft'"
    query += " ORDER BY updated_at DESC"
    return [_row_to_workflow(r) for r in conn.execute(query).fetchall()]


def get_workflow(workflow_id: str) -> Optional[WorkflowConfig]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
    return _row_to_workflow(row) if row else None


def save_workflow(workflow: WorkflowConfig) -> WorkflowConfig:
    conn = _get_conn()
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    workflow.updated_at = now
    if not workflow.created_at:
        workflow.created_at = now

    conn.execute("""
        INSERT INTO workflows (
            id, name, description, tags, category, status,
            nodes, connections, config, version, schedule,
            error_policy, max_retries, timeout_seconds,
            created_at, updated_at, created_by, background
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, description=excluded.description,
            tags=excluded.tags, category=excluded.category,
            status=excluded.status,
            nodes=excluded.nodes, connections=excluded.connections,
            config=excluded.config, version=version + 1,
            schedule=excluded.schedule,
            error_policy=excluded.error_policy,
            max_retries=excluded.max_retries,
            timeout_seconds=excluded.timeout_seconds,
            updated_at=excluded.updated_at, background=excluded.background
    """, (
        workflow.id, workflow.name, workflow.description,
        json.dumps(workflow.tags), workflow.category,
        workflow.status.value if isinstance(workflow.status, WorkflowStatus) else workflow.status,
        json.dumps([n.to_dict() for n in workflow.nodes]),
        json.dumps([c.to_dict() for c in workflow.connections]),
        json.dumps(workflow.config), workflow.version,
        workflow.schedule, workflow.error_policy,
        workflow.max_retries, workflow.timeout_seconds,
        workflow.created_at, workflow.updated_at,
        workflow.created_by, 1 if workflow.background else 0,
    ))
    conn.commit()
    saved = get_workflow(workflow.id)
    if saved:
        saved.version = workflow.version + 1
    return saved or workflow


def delete_workflow(workflow_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Version History ────────────────────────────────────────────────


def save_version(workflow_id: str, version: WorkflowVersion) -> None:
    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO workflow_versions
        (workflow_id, version, created_at, nodes, connections, config, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (workflow_id, version.version, version.created_at,
          json.dumps(version.nodes), json.dumps(version.connections),
          json.dumps(version.config), version.comment))
    conn.commit()


def list_versions(workflow_id: str) -> list[WorkflowVersion]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM workflow_versions WHERE workflow_id = ? ORDER BY version DESC",
        (workflow_id,),
    ).fetchall()
    return [_row_to_version(r) for r in rows]


def get_version(workflow_id: str, version: int) -> Optional[WorkflowVersion]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM workflow_versions WHERE workflow_id = ? AND version = ?",
        (workflow_id, version),
    ).fetchone()
    return _row_to_version(row) if row else None


# ── Execution Records ──────────────────────────────────────────────


def save_execution(record: ExecutionRecord) -> ExecutionRecord:
    conn = _get_conn()
    import datetime
    if not record.id:
        record.id = __import__("uuid").uuid4().hex[:12]
    if not record.started_at:
        record.started_at = datetime.datetime.utcnow().isoformat() + "Z"

    conn.execute("""
        INSERT OR REPLACE INTO workflow_executions
        (id, workflow_id, status, trigger, started_at, completed_at,
         duration_ms, nodes_total, nodes_completed, nodes_failed,
         logs, error, input_data, output_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.id, record.workflow_id, record.status, record.trigger,
        record.started_at, record.completed_at, record.duration_ms,
        record.nodes_total, record.nodes_completed, record.nodes_failed,
        json.dumps(record.logs), record.error,
        json.dumps(record.input_data),
        json.dumps(record.output_data) if record.output_data is not None else "null",
    ))
    conn.commit()
    return record


def list_executions(workflow_id: str, limit: int = 50) -> list[ExecutionRecord]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
        (workflow_id, limit),
    ).fetchall()
    return [_row_to_execution(r) for r in rows]


def get_execution(execution_id: str) -> Optional[ExecutionRecord]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM workflow_executions WHERE id = ?", (execution_id,)).fetchone()
    return _row_to_execution(row) if row else None


def get_recent_executions(limit: int = 20) -> list[ExecutionRecord]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM workflow_executions ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_execution(r) for r in rows]


# ── Internal ───────────────────────────────────────────────────────


def _row_to_workflow(row: sqlite3.Row) -> WorkflowConfig:
    d = dict(row)
    for json_field in ("tags", "nodes", "connections", "config"):
        val = d.get(json_field)
        if isinstance(val, str):
            d[json_field] = json.loads(val)
    d["background"] = bool(d.get("background", 0))
    return WorkflowConfig.from_dict(d)


def _row_to_version(row: sqlite3.Row) -> WorkflowVersion:
    d = dict(row)
    for json_field in ("nodes", "connections", "config"):
        val = d.get(json_field)
        if isinstance(val, str):
            d[json_field] = json.loads(val)
    return WorkflowVersion.from_dict(d)


def _row_to_execution(row: sqlite3.Row) -> ExecutionRecord:
    d = dict(row)
    for json_field in ("logs", "input_data"):
        val = d.get(json_field)
        if isinstance(val, str):
            d[json_field] = json.loads(val)
    output = d.get("output_data")
    if isinstance(output, str):
        d["output_data"] = json.loads(output)
    return ExecutionRecord.from_dict(d)
