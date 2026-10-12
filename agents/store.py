"""Agent store — SQLite-backed persistent registry for multi-agent configurations."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from agents.models import AgentConfig

logger = logging.getLogger(__name__)


_LOCAL = threading.local()
_LOCK = threading.Lock()


def _get_db_path() -> Path:
    return get_aetheros_home() / "agents.db"


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_LOCAL, "conn") or _LOCAL.conn is None:
        db_path = _get_db_path()
        _LOCAL.conn = sqlite3.connect(str(db_path))
        _LOCAL.conn.row_factory = sqlite3.Row
        _LOCAL.conn.execute("PRAGMA journal_mode=WAL")
        _LOCAL.conn.execute("PRAGMA foreign_keys=ON")
    return _LOCAL.conn


def init_db() -> None:
    """Initialize the agents database schema."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            avatar TEXT DEFAULT '{"icon":"🤖","color":"#58a6ff"}',
            role TEXT DEFAULT 'general_assistant',
            role_custom TEXT DEFAULT '',
            personality TEXT DEFAULT 'professional',
            personality_custom TEXT DEFAULT '',
            reasoning TEXT DEFAULT 'balanced',
            provider TEXT DEFAULT '',
            fallback_providers TEXT DEFAULT '[]',
            models TEXT DEFAULT '{}',
            memory_scope TEXT DEFAULT 'personal',
            knowledge_sources TEXT DEFAULT '[]',
            tools TEXT DEFAULT '["filesystem","terminal","web_search"]',
            permissions TEXT DEFAULT '["read_files","internet_access"]',
            prompt TEXT DEFAULT '',
            skills TEXT DEFAULT '[]',
            mcp_servers TEXT DEFAULT '[]',
            workflows TEXT DEFAULT '[]',
            temperature REAL DEFAULT 0.7,
            max_iterations INTEGER DEFAULT 90,
            enabled INTEGER DEFAULT 1,
            status TEXT DEFAULT 'idle',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            version INTEGER DEFAULT 1,
            metrics TEXT DEFAULT '{}',
            tags TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS agent_sessions (
            session_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            started_at TEXT DEFAULT '',
            ended_at TEXT DEFAULT '',
            status TEXT DEFAULT 'running',
            tokens_used INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS marketplace_install (
            package_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT DEFAULT '1.0.0',
            installed_at TEXT DEFAULT '',
            source TEXT DEFAULT 'marketplace',
            config TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
        CREATE INDEX IF NOT EXISTS idx_agents_role ON agents(role);
        CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
        CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent ON agent_sessions(agent_id);
    """)
    conn.commit()


# =============================================================================
# Agent CRUD
# =============================================================================


def list_agents() -> list[AgentConfig]:
    """List all registered agents."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
    return [_row_to_agent(r) for r in rows]


def get_agent(agent_id: str) -> Optional[AgentConfig]:
    """Get a single agent by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return _row_to_agent(row) if row else None


def save_agent(config: AgentConfig) -> AgentConfig:
    """Insert or update an agent configuration."""
    conn = _get_conn()
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    config.updated_at = now
    if not config.created_at:
        config.created_at = now

    conn.execute("""
        INSERT INTO agents (
            id, name, description, avatar, role, role_custom,
            personality, personality_custom, reasoning,
            provider, fallback_providers, models,
            memory_scope, knowledge_sources,
            tools, permissions, prompt,
            skills, mcp_servers, workflows,
            temperature, max_iterations,
            enabled, status,
            created_at, updated_at, version,
            metrics, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, description=excluded.description,
            avatar=excluded.avatar, role=excluded.role,
            role_custom=excluded.role_custom,
            personality=excluded.personality,
            personality_custom=excluded.personality_custom,
            reasoning=excluded.reasoning,
            provider=excluded.provider,
            fallback_providers=excluded.fallback_providers,
            models=excluded.models,
            memory_scope=excluded.memory_scope,
            knowledge_sources=excluded.knowledge_sources,
            tools=excluded.tools, permissions=excluded.permissions,
            prompt=excluded.prompt,
            skills=excluded.skills, mcp_servers=excluded.mcp_servers,
            workflows=excluded.workflows,
            temperature=excluded.temperature,
            max_iterations=excluded.max_iterations,
            enabled=excluded.enabled, status=excluded.status,
            updated_at=excluded.updated_at, version=version + 1,
            metrics=excluded.metrics, tags=excluded.tags
    """, (
        config.id, config.name, config.description,
        json.dumps(config.avatar.to_dict()),
        config.role, config.role_custom,
        config.personality, config.personality_custom,
        config.reasoning,
        config.provider, json.dumps([p.to_dict() for p in config.fallback_providers]),
        json.dumps(config.models),
        config.memory_scope, json.dumps([k.to_dict() for k in config.knowledge_sources]),
        json.dumps(config.tools), json.dumps(config.permissions),
        config.prompt,
        json.dumps(config.skills), json.dumps(config.mcp_servers),
        json.dumps(config.workflows),
        config.temperature, config.max_iterations,
        1 if config.enabled else 0, config.status,
        config.created_at, config.updated_at, config.version,
        json.dumps(config.metrics.to_dict()),
        json.dumps(config.tags),
    ))
    conn.commit()
    # Reload to get updated version
    return get_agent(config.id) or config


def delete_agent(agent_id: str) -> bool:
    """Delete an agent by ID."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    return cur.rowcount > 0


def duplicate_agent(agent_id: str, new_name: str = "") -> Optional[AgentConfig]:
    """Duplicate an agent configuration."""
    original = get_agent(agent_id)
    if not original:
        return None
    import copy
    import uuid
    new_config = copy.deepcopy(original)
    new_config.id = str(uuid.uuid4())
    new_config.name = new_name or f"{original.name} (Copy)"
    new_config.created_at = ""
    new_config.updated_at = ""
    new_config.version = 1
    new_config.status = "idle"
    new_config.metrics = type(original.metrics)()
    return save_agent(new_config)


# =============================================================================
# Agent Sessions
# =============================================================================


def record_session_start(agent_id: str, session_id: str) -> None:
    """Record the start of an agent session."""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    conn = _get_conn()
    conn.execute(
        "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?, ?, ?)",
        (session_id, agent_id, now),
    )
    conn.commit()


def record_session_end(session_id: str, tokens: int = 0, messages: int = 0) -> None:
    """Record the end of an agent session."""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    conn = _get_conn()
    conn.execute(
        """UPDATE agent_sessions SET ended_at = ?, status = 'completed',
           tokens_used = ?, messages_count = ? WHERE session_id = ?""",
        (now, tokens, messages, session_id),
    )
    conn.commit()


def get_agent_sessions(agent_id: str, limit: int = 20) -> list[dict]:
    """Get recent sessions for an agent."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT * FROM agent_sessions WHERE agent_id = ?
           ORDER BY started_at DESC LIMIT ?""",
        (agent_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# =============================================================================
# Marketplace persistence
# =============================================================================


def list_installed_marketplace() -> list[dict]:
    """List installed marketplace packages."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM marketplace_install ORDER BY installed_at DESC").fetchall()
    return [dict(r) for r in rows]


def install_marketplace_package(package_id: str, name: str, version: str = "1.0.0",
                                config: dict | None = None) -> None:
    """Record a marketplace package installation."""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO marketplace_install
           (package_id, name, version, installed_at, config)
           VALUES (?, ?, ?, ?, ?)""",
        (package_id, name, version, now, json.dumps(config or {})),
    )
    conn.commit()


def uninstall_marketplace_package(package_id: str) -> bool:
    """Remove a marketplace package installation record."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM marketplace_install WHERE package_id = ?", (package_id,))
    conn.commit()
    return cur.rowcount > 0


# =============================================================================
# Internal helpers
# =============================================================================


def _row_to_agent(row: sqlite3.Row) -> AgentConfig:
    d = dict(row)
    avatar = d.get("avatar", "{}")
    d["avatar"] = json.loads(avatar) if isinstance(avatar, str) else avatar
    for json_field in ("fallback_providers", "models", "knowledge_sources",
                       "tools", "permissions", "skills", "mcp_servers",
                       "workflows", "metrics", "tags"):
        val = d.get(json_field)
        if isinstance(val, str):
            d[json_field] = json.loads(val)
        elif val is None:
            d[json_field] = {} if json_field in ("models", "metrics") else []
    d["enabled"] = bool(d.get("enabled", 1))
    return AgentConfig.from_dict(d)
