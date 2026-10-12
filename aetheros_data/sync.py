"""Sync architecture (sections 58-68): sync is NOT backup.

Offline-first change queue with versioned SyncEnvelope ops, per-object
versions, explicit conflict records, domain-specific resolution strategies
(MERGE / MANUAL_REVIEW / SOURCE_PRIORITY / VERSION_RECONCILIATION /
APPEND_ONLY — LAST_WRITE_WINS is never the universal default), device
identity independent from user identity, and policy-gated application
(revoked devices cannot sync restricted state).

Transport/QoS claims: TLS is assumed from the caller; end-to-end encryption
is NOT claimed (STATUS: NOT_IMPLEMENTED — see certification matrix).
"""

from __future__ import annotations

import hashlib
import json
import platform
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_data.domains import NON_SYNCABLE_DOMAINS
from aetheros_data.engine import ConflictError, StorageEngine

SYNC_STATUSES = ("SYNCED", "SYNCING", "OFFLINE", "CONFLICT", "ERROR", "PAUSED", "AUTH_REQUIRED")

OPERATIONS = ("CREATE", "UPDATE", "DELETE", "RETRACT", "SUPERSEDE")

STRATEGIES = ("MERGE", "MANUAL_REVIEW", "SOURCE_PRIORITY",
              "VERSION_RECONCILIATION", "APPEND_ONLY", "LAST_WRITE_WINS")

# Domain -> default conflict strategy (section 63).
DOMAIN_STRATEGY = {
    "configuration": "SOURCE_PRIORITY",
    "task": "VERSION_RECONCILIATION",
    "automation": "MANUAL_REVIEW",
    "memory": "APPEND_ONLY",
    "artifact": "VERSION_RECONCILIATION",
    "knowledge_graph": "MERGE",
    "extension": "MANUAL_REVIEW",
}


def _device_file() -> Path:
    return get_aetheros_home() / "data" / "device.json"


def get_device_identity() -> Dict[str, Any]:
    """Device identity independent from user identity (section 59)."""
    p = _device_file()
    if p.exists():
        return json.loads(p.read_text())
    ident = {
        "device_id": f"dev_{uuid.uuid4().hex[:12]}",
        "installation_id": f"inst_{uuid.uuid4().hex[:12]}",
        "platform": platform.system(),
        "version": "1.0",
        "trust": "untrusted",
        "last_seen": time.time(),
        "sync_state": "OFFLINE",
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ident, indent=2))
    return ident


class SyncEngine:
    """Local side of sync: queue ops offline, resolve conflicts explicitly."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine
        self.device = get_device_identity()
        self._paused = False
        self._offline = False

    # -- status ------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        conn = self.e._conn()
        queued = int(conn.execute("SELECT COUNT(*) FROM sync_ops WHERE state='QUEUED'").fetchone()[0])
        conflicts = int(conn.execute(
            "SELECT COUNT(*) FROM conflicts WHERE resolution=''").fetchone()[0])
        if self._paused:
            state = "PAUSED"
        elif self._offline:
            state = "OFFLINE"
        elif conflicts:
            state = "CONFLICT"
        elif queued:
            state = "SYNCING"
        else:
            state = "SYNCED"
        return {"state": state, "device_id": self.device["device_id"],
                "queued": queued, "conflicts": conflicts}

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def set_offline(self, offline: bool) -> None:
        self._offline = offline

    # -- queue ---------------------------------------------------------------
    def enqueue(self, object_type: str, object_id: str, version: int,
                operation: str, payload: Dict[str, Any],
                provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert operation in OPERATIONS, operation
        if object_type in NON_SYNCABLE_DOMAINS:
            raise PermissionError(f"{object_type} is NOT syncable (secrets/device-local state)")
        if self._offline:
            state = "QUEUED"  # preserved locally, never faked as synced
        else:
            state = "QUEUED"
        seq = int(time.time() * 1000)
        env = {"device_id": self.device["device_id"], "sequence": seq,
               "object_type": object_type, "object_id": object_id, "version": version,
               "operation": operation, "payload": payload, "timestamp": time.time(),
               "provenance": provenance or {},
               "integrity": "sha256:" + hashlib.sha256(
                   json.dumps(payload, sort_keys=True).encode()).hexdigest()}
        op_id = f"sync_{uuid.uuid4().hex[:12]}"
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO sync_ops (op_id, device_id, sequence, object_type, object_id,"
                " version, operation, payload, timestamp, provenance, integrity, state)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (op_id, env["device_id"], seq, object_type, object_id, version, operation,
                 json.dumps(payload), env["timestamp"], json.dumps(env["provenance"]),
                 env["integrity"], state),
            )
        env["op_id"] = op_id
        env["state"] = state
        return env

    def pending(self) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute(
            "SELECT * FROM sync_ops WHERE state='QUEUED' ORDER BY sequence").fetchall()
        return [dict(r) for r in rows]

    # -- apply remote ----------------------------------------------------------
    def apply_remote(self, env: Dict[str, Any],
                     policy_check: Optional[Callable[[Dict[str, Any]], bool]] = None) -> Dict[str, Any]:
        """Apply a remote SyncEnvelope. Policy-gated (section 67)."""
        if policy_check is not None and not policy_check(env):
            return {"applied": False, "reason": "policy denied (identity/authority/DLP/revocation)"}
        if env.get("object_type") in NON_SYNCABLE_DOMAINS:
            return {"applied": False, "reason": "non-syncable domain"}
        local = self.e.record_get(env["object_type"], env["object_id"])
        local_v = int(local["version"]) if local else 0
        remote_v = int(env.get("version", 1))
        if local and remote_v < local_v:
            # Stale remote writer must not overwrite newer local state.
            return {"applied": False, "reason": f"stale remote v{remote_v} < local v{local_v}"}
        if local and remote_v == local_v and env.get("operation") in ("CREATE", "UPDATE"):
            conflict = self._record_conflict(env, local_v, remote_v, "same-version concurrent update")
            return {"applied": False, "conflict": conflict}
        try:
            with self.e.transaction() as conn:
                if local is None:
                    self.e.record_create(env["object_type"], env["object_id"],
                                         env.get("payload", {}), conn=conn)
                else:
                    self.e.record_cas(env["object_type"], env["object_id"], local_v,
                                      env.get("payload", {}), conn=conn)
                self.e.append_event("sync", env["object_id"], "sync.conflict_resolved",
                                    {"object_id": env["object_id"], "from": env.get("device_id")},
                                    conn=conn)
        except ConflictError as exc:
            conflict = self._record_conflict(env, local_v, remote_v, str(exc))
            return {"applied": False, "conflict": conflict}
        return {"applied": True}

    def _record_conflict(self, env: Dict[str, Any], local_v: int, remote_v: int,
                         reason: str) -> Dict[str, Any]:
        cid = f"cf_{uuid.uuid4().hex[:10]}"
        strategy = DOMAIN_STRATEGY.get(env.get("object_type", ""), "MANUAL_REVIEW")
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO conflicts (conflict_id, object_id, object_type, local_version,"
                " remote_version, detected_at, reason, resolution, resolver)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, '', '')",
                (cid, env.get("object_id"), env.get("object_type"), local_v, remote_v,
                 time.time(), f"{reason} [strategy={strategy}]"),
            )
        return {"conflict_id": cid, "strategy": strategy, "reason": reason,
                "local_version": local_v, "remote_version": remote_v}

    def resolve(self, conflict_id: str, resolution: str, resolver: str,
                winning_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert resolution in ("KEEP_LOCAL", "KEEP_REMOTE", "MERGED"), resolution
        row = self.e._conn().execute("SELECT * FROM conflicts WHERE conflict_id=?",
                                     (conflict_id,)).fetchone()
        if row is None:
            raise KeyError(conflict_id)
        c = dict(row)
        with self.e.transaction() as conn:
            if resolution in ("KEEP_REMOTE", "MERGED") and winning_payload is not None:
                local = self.e.record_get(c["object_type"], c["object_id"])
                if local is None:
                    self.e.record_create(c["object_type"], c["object_id"], winning_payload, conn=conn)
                else:
                    self.e.record_cas(c["object_type"], c["object_id"],
                                      int(local["version"]), winning_payload, conn=conn)
            conn.execute("UPDATE conflicts SET resolution=?, resolver=? WHERE conflict_id=?",
                         (resolution, resolver, conflict_id))
            self.e.append_event("sync", c["object_id"], "sync.conflict_resolved",
                                {"conflict_id": conflict_id, "resolution": resolution,
                                 "resolver": resolver}, conn=conn)
        return {"conflict_id": conflict_id, "resolution": resolution}

    def open_conflicts(self) -> List[Dict[str, Any]]:
        rows = self.e._conn().execute("SELECT * FROM conflicts WHERE resolution=''").fetchall()
        return [dict(r) for r in rows]
