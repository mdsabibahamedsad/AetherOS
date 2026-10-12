"""Versioned domain repositories (Master 61 sections 12-14, 25-33, 90).

Covers tasks, agents, automations, memory (with CANDIDATE/CONFIRMED/
SUPERSEDED/RETRACTED/EXPIRED/QUARANTINED lifecycle), authority grants,
layered configuration, knowledge graph, and the append-only audit log.

Security rules enforced here (sections 90-94):
- revoked/expired authority is never returned as valid and can never be
  re-activated by restore (see restore.py revalidation);
- retracted/quarantined memory is preserved as evidence, never silently
  deleted;
- audit rows are append-only (no update/delete API).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_data.engine import ConflictError, StorageEngine

MEMORY_STATUSES = (
    "CANDIDATE", "CONFIRMED", "SUPERSEDED", "RETRACTED", "EXPIRED", "QUARANTINED",
)

CONFIG_LAYERS = ("SYSTEM", "USER", "PROJECT", "TASK", "AGENT", "DEVICE")
_CONFIG_PRECEDENCE = {name: i for i, name in enumerate(CONFIG_LAYERS)}


class TaskRepository:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def create(self, task_id: str, data: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        record = self.e.record_create("task", task_id, data, idempotency_key=idempotency_key)
        with self.e.transaction() as conn:
            self.e.append_event("task", task_id, "task.created",
                                {"task_id": task_id}, conn=conn)
        return record

    def transition(self, task_id: str, expected_version: int, new_data: Dict[str, Any],
                   actor: str = "") -> Dict[str, Any]:
        return self.e.mutate_with_event("task", task_id, expected_version, new_data,
                                        "task.state_transition",
                                        {"task_id": task_id, "to": new_data.get("state")},
                                        actor=actor)

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.e.record_get("task", task_id)


class AgentRepository:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def register(self, agent_id: str, data: Dict[str, Any],
                 idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        record = self.e.record_create("agent", agent_id, data, idempotency_key=idempotency_key)
        with self.e.transaction() as conn:
            self.e.append_event("agent", agent_id, "agent.lifecycle",
                                {"agent_id": agent_id, "transition": "registered"}, conn=conn)
        return record

    def transition(self, agent_id: str, expected_version: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.e.mutate_with_event("agent", agent_id, expected_version, new_data,
                                        "agent.lifecycle", {"agent_id": agent_id})

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.e.record_get("agent", agent_id)


class AutomationRepository:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def save(self, automation_id: str, data: Dict[str, Any],
             expected_version: Optional[int] = None) -> Dict[str, Any]:
        existing = self.e.record_get("automation", automation_id)
        if existing is None:
            rec = self.e.record_create("automation", automation_id, data)
            with self.e.transaction() as conn:
                self.e.append_event("automation", automation_id, "automation.state",
                                    {"automation_id": automation_id}, conn=conn)
            return rec
        assert expected_version is not None, "CAS expected_version required for automation update"
        result = self.e.mutate_with_event("automation", automation_id, expected_version, data,
                                          "automation.state", {"automation_id": automation_id})
        return result["record"]

    def get(self, automation_id: str) -> Optional[Dict[str, Any]]:
        return self.e.record_get("automation", automation_id)


class MemoryRepository:
    """Versioned memory with append/revise/supersede/retract (sections 25-27)."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def write(self, content: str, scope: str = "user", owner: str = "",
              mem_type: str = "fact", source: str = "",
              provenance: Optional[Dict[str, Any]] = None,
              confidence: float = 0.5, sensitivity: str = "internal",
              trust: str = "unverified",
              memory_id: Optional[str] = None) -> Dict[str, Any]:
        now = time.time()
        mid = memory_id or f"mem_{uuid.uuid4().hex[:12]}"
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO memory_records (memory_id, scope, owner, content, mem_type, source,"
                " provenance, confidence, sensitivity, trust, version, status,"
                " created_at, updated_at, expires_at, supersedes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'CANDIDATE', ?, ?, 0, '')",
                (mid, scope, owner, content, mem_type, source,
                 json.dumps(provenance or {}), confidence, sensitivity, trust, now, now),
            )
            self.e.append_event("memory", mid, "memory.confirmed",
                                {"memory_id": mid, "status": "CANDIDATE"}, conn=conn)
        return self.get(mid)  # type: ignore[return-value]

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        row = self.e._conn().execute(
            "SELECT * FROM memory_records WHERE memory_id=?", (memory_id,)).fetchone()
        return dict(row) if row else None

    def confirm(self, memory_id: str, expected_version: int) -> Dict[str, Any]:
        return self._set_status(memory_id, expected_version, "CONFIRMED")

    def supersede(self, old_id: str, expected_version: int, new_content: str,
                  provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Never silently overwrite: old record -> SUPERSEDED, new CANDIDATE linked."""
        new = self.write(new_content, provenance=provenance or {"supersedes": old_id})
        with self.e.transaction() as conn:
            row = conn.execute("SELECT version FROM memory_records WHERE memory_id=?", (old_id,)).fetchone()
            if row is None:
                raise KeyError(old_id)
            if int(row["version"]) != int(expected_version):
                raise ConflictError(f"stale memory writer for {old_id}")
            conn.execute(
                "UPDATE memory_records SET status='SUPERSEDED', version=version+1,"
                " updated_at=?, supersedes=? WHERE memory_id=?",
                (time.time(), new["memory_id"], old_id),
            )
            self.e.append_event("memory", old_id, "memory.retracted",
                                {"memory_id": old_id, "to": "SUPERSEDED",
                                 "by": new["memory_id"]}, conn=conn)
        updated = self.get(old_id)
        assert updated is not None
        return updated

    def retract(self, memory_id: str, expected_version: int, reason: str = "") -> Dict[str, Any]:
        """Rollback path (section 27): retraction preserves evidence."""
        return self._set_status(memory_id, expected_version, "RETRACTED", extra={"reason": reason})

    def quarantine(self, memory_id: str, expected_version: int, reason: str = "") -> Dict[str, Any]:
        return self._set_status(memory_id, expected_version, "QUARANTINED", extra={"reason": reason})

    def _set_status(self, memory_id: str, expected_version: int, status: str,
                    extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert status in MEMORY_STATUSES, status
        with self.e.transaction() as conn:
            row = conn.execute("SELECT version FROM memory_records WHERE memory_id=?", (memory_id,)).fetchone()
            if row is None:
                raise KeyError(memory_id)
            if int(row["version"]) != int(expected_version):
                raise ConflictError(f"stale memory writer for {memory_id}")
            conn.execute(
                "UPDATE memory_records SET status=?, version=version+1, updated_at=? WHERE memory_id=?",
                (status, time.time(), memory_id),
            )
            payload = {"memory_id": memory_id, "to": status}
            if extra:
                payload.update(extra)
            self.e.append_event("memory", memory_id, "memory.retracted", payload, conn=conn)
        updated = self.get(memory_id)
        assert updated is not None
        return updated

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM memory_records WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
        return [dict(r) for r in rows]


class AuthorityStore:
    """Grants/delegation/revocation (section 31). Expired/revoked never valid."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def grant(self, subject: str, capability: str, delegate: str = "",
              policy_version: str = "", ttl_s: float = 3600) -> Dict[str, Any]:
        now = time.time()
        gid = f"grt_{uuid.uuid4().hex[:12]}"
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO authority_grants (grant_id, subject, capability, delegate,"
                " policy_version, issued_at, expires_at, revoked, version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)",
                (gid, subject, capability, delegate, policy_version, now, now + ttl_s),
            )
            self.e.append_event("authority", gid, "authority.granted",
                                {"grant_id": gid, "subject": subject, "capability": capability},
                                conn=conn)
        row = self.e._conn().execute(
            "SELECT * FROM authority_grants WHERE grant_id=?", (gid,)).fetchone()
        return dict(row)

    def revoke(self, grant_id: str) -> None:
        with self.e.transaction() as conn:
            conn.execute("UPDATE authority_grants SET revoked=1, version=version+1 WHERE grant_id=?", (grant_id,))
            self.e.append_event("authority", grant_id, "authority.revoked",
                                {"grant_id": grant_id}, conn=conn)

    def is_valid(self, grant_id: str, now: Optional[float] = None) -> bool:
        row = self.e._conn().execute(
            "SELECT revoked, expires_at FROM authority_grants WHERE grant_id=?", (grant_id,)).fetchone()
        if row is None:
            return False
        if int(row["revoked"]):
            return False
        return float(row["expires_at"]) > (now if now is not None else time.time())

    def valid_grants_for(self, subject: str) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM authority_grants WHERE subject=? AND revoked=0 AND expires_at>?",
            (subject, time.time())).fetchall()
        return [dict(r) for r in rows]


class ConfigStore:
    """Layered configuration SYSTEM/USER/PROJECT/TASK/AGENT/DEVICE (section 29)."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def set(self, scope: str, key: str, value: Any, source: str = "user") -> None:
        assert scope in CONFIG_LAYERS, scope
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO config_values (scope, config_key, value, source, version, updated_at)"
                " VALUES (?, ?, ?, ?, 1, ?)"
                " ON CONFLICT(scope, config_key) DO UPDATE SET value=excluded.value,"
                " source=excluded.source, version=config_values.version+1, updated_at=excluded.updated_at",
                (scope, key, json.dumps(value), source, time.time()),
            )
            self.e.append_event("configuration", f"{scope}/{key}", "config.changed",
                                {"scope": scope, "key": key}, conn=conn)

    def get(self, key: str, scopes: Optional[List[str]] = None) -> Any:
        """Resolve with precedence: later layers override earlier ones."""
        order = scopes or list(CONFIG_LAYERS)
        rows = self.e._conn().execute(
            "SELECT scope, value FROM config_values WHERE config_key=?", (key,)).fetchall()
        by_scope = {r["scope"]: json.loads(r["value"]) for r in rows}
        value: Any = None
        found = False
        for layer in CONFIG_LAYERS:
            if layer in by_scope and layer in order:
                value, found = by_scope[layer], True
        if not found:
            raise KeyError(key)
        return value


class KnowledgeGraph:
    """Versioned entities/relationships with contradiction support (section 28)."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def upsert_entity(self, entity: str, data: Dict[str, Any], source: str = "",
                      confidence: float = 0.5, by: str = "") -> None:
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO graph_nodes (entity, data, source, confidence, valid_from,"
                " valid_until, created_by, updated_by, version)"
                " VALUES (?, ?, ?, ?, ?, 0, ?, ?, 1)"
                " ON CONFLICT(entity) DO UPDATE SET data=excluded.data, source=excluded.source,"
                " confidence=excluded.confidence, updated_by=excluded.updated_by,"
                " version=graph_nodes.version+1",
                (entity, json.dumps(data), source, confidence, time.time(), by or source, by or source),
            )

    def add_edge(self, src: str, rel: str, dst: str, source: str = "",
                 confidence: float = 0.5, by: str = "") -> str:
        eid = f"edge_{uuid.uuid4().hex[:12]}"
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO graph_edges (edge_id, src, rel, dst, source, confidence,"
                " valid_from, valid_until, created_by, updated_by, version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 1)",
                (eid, src, rel, dst, source, confidence, time.time(), by or source, by or source),
            )
        return eid

    def edges_from(self, src: str) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute("SELECT * FROM graph_edges WHERE src=?", (src,)).fetchall()
        return [dict(r) for r in rows]


class AuditLog:
    """Append-only audit (section 32). No update/delete API exists by design."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def record(self, actor: str, action: str, scope: str = "", policy: str = "",
               result: str = "", payload: Optional[Dict[str, Any]] = None) -> str:
        event_id = f"aud_{uuid.uuid4().hex[:16]}"
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO audit_log (event_id, timestamp, actor, action, scope, policy, result, payload)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, time.time(), actor, action, scope, policy, result,
                 json.dumps(payload or {})),
            )
        return event_id

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM audit_log ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
