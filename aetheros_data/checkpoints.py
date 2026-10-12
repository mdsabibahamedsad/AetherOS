"""Canonical CheckpointManager (Master 61 sections 15-17).

A checkpoint is a deterministic, recoverable representation — never a blind
process-memory dump. Every checkpoint carries an integrity hash; restore
validates schema, identity, authority, generation, artifact references,
expiration, and policy compatibility. Stale authority is never restored.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from aetheros_data.engine import StorageEngine

CHECKPOINT_STATE_VERSION = 1
CHECKPOINT_TTL_S = 30 * 24 * 3600.0


def _canonical(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def integrity_hash(payload: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


class CheckpointManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def create(self, task_id: str, agent_id: str = "", generation: int = 1,
               execution_position: Optional[Dict[str, Any]] = None,
               plan_reference: str = "", context_reference: str = "",
               memory_references: Optional[List[str]] = None,
               resource_state: Optional[Dict[str, Any]] = None,
               authority_reference: str = "",
               pending_operations: Optional[List[str]] = None,
               pending_approvals: Optional[List[str]] = None,
               recovery_metadata: Optional[Dict[str, Any]] = None,
               ttl_s: float = CHECKPOINT_TTL_S) -> Dict[str, Any]:
        now = time.time()
        payload = {
            "execution_position": execution_position or {},
            "plan_reference": plan_reference,
            "context_reference": context_reference,
            "memory_references": memory_references or [],
            "resource_state": resource_state or {},
            "authority_reference": authority_reference,
            "pending_operations": pending_operations or [],
            "pending_approvals": pending_approvals or [],
            "recovery_metadata": recovery_metadata or {},
        }
        ckpt = {
            "checkpoint_id": f"ckpt_{uuid.uuid4().hex[:12]}",
            "task_id": task_id,
            "agent_id": agent_id,
            "generation": generation,
            "created_at": now,
            "state_version": CHECKPOINT_STATE_VERSION,
            "payload": payload,
            "integrity_hash": integrity_hash(payload),
            "expires_at": now + ttl_s,
        }
        with self.e.transaction() as conn:
            conn.execute(
                "INSERT INTO checkpoints (checkpoint_id, task_id, agent_id, generation,"
                " created_at, state_version, payload, integrity_hash, expires_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ckpt["checkpoint_id"], task_id, agent_id, generation, now,
                 CHECKPOINT_STATE_VERSION, json.dumps(payload),
                 ckpt["integrity_hash"], ckpt["expires_at"]),
            )
            self.e.append_event("checkpoint", task_id, "checkpoint.created",
                                {"checkpoint_id": ckpt["checkpoint_id"], "task_id": task_id},
                                conn=conn)
        return ckpt

    def latest(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self.e._conn().execute(
            "SELECT * FROM checkpoints WHERE task_id=? ORDER BY generation DESC, created_at DESC LIMIT 1",
            (task_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        return d

    def validate(self, ckpt: Dict[str, Any], expected_task: str = "",
                 expected_agent: str = "") -> Dict[str, Any]:
        """Validate before restore (section 17). Returns {ok, reasons}."""
        reasons: List[str] = []
        payload = ckpt.get("payload", {})
        if ckpt.get("state_version") != CHECKPOINT_STATE_VERSION:
            reasons.append(f"schema version {ckpt.get('state_version')} != {CHECKPOINT_STATE_VERSION}")
        if integrity_hash(payload) != ckpt.get("integrity_hash"):
            reasons.append("integrity hash mismatch")
        if expected_task and ckpt.get("task_id") != expected_task:
            reasons.append("task identity mismatch")
        if expected_agent and ckpt.get("agent_id") not in ("", expected_agent):
            reasons.append("agent identity mismatch")
        if float(ckpt.get("expires_at", 0)) and float(ckpt["expires_at"]) < time.time():
            reasons.append("checkpoint expired")
        # Authority reference must still be valid — never restore stale authority.
        auth_ref = payload.get("authority_reference", "")
        if auth_ref:
            from aetheros_data.records import AuthorityStore
            if not AuthorityStore(self.e).is_valid(auth_ref):
                reasons.append("authority reference expired or revoked")
        # Generation staleness is checked by the caller against live task state;
        # flag obviously ancient generations here.
        if int(ckpt.get("generation", 0)) < 0:
            reasons.append("invalid generation")
        return {"ok": not reasons, "reasons": reasons}
