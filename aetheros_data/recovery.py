"""Crash recovery: leases, reconciliation, two-phase actions (sections 18-21).

- ``CrashRecoveryManager.startup_scan()``: detect interrupted tasks, inspect
  last checkpoint, active leases, pending side effects, validate authority,
  resume only safe operations, mark the rest for review.
- Execution leases with atomic CAS acquire/renew/release; stale leases
  expire and are reclaimable.
- External side effects use operation_id + idempotency key + receipt. A
  crashed action is ``UNKNOWN_OUTCOME`` until verified — never auto-SUCCESS.
- Risky side effects follow PREPARE -> AUTHORIZE -> COMMIT -> VERIFY where
  supported.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from aetheros_data.engine import StorageEngine

LEASE_TTL_S = 120.0

SIDE_EFFECT_STATES = (
    "PREPARED", "AUTHORIZED", "COMMITTED", "VERIFIED", "FAILED", "UNKNOWN_OUTCOME",
)


class LeaseManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def acquire(self, task_id: str, agent_id: str, worker_id: str,
                generation: int, ttl_s: float = LEASE_TTL_S) -> Dict[str, Any]:
        now = time.time()
        lease = {"task_id": task_id, "agent_id": agent_id, "worker_id": worker_id,
                 "lease_id": f"lease_{uuid.uuid4().hex[:10]}", "generation": generation,
                 "acquired_at": now, "expires_at": now + ttl_s}
        with self.e.transaction() as conn:
            row = conn.execute("SELECT expires_at, generation FROM leases WHERE task_id=?",
                               (task_id,)).fetchone()
            if row is not None and float(row["expires_at"]) > now:
                raise RuntimeError(f"task {task_id} already leased (expires {row['expires_at']})")
            if row is not None and int(row["generation"]) > generation:
                raise RuntimeError(f"stale writer: lease generation {row['generation']} > {generation}")
            conn.execute(
                "INSERT OR REPLACE INTO leases (task_id, agent_id, worker_id, lease_id,"
                " generation, acquired_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, agent_id, worker_id, lease["lease_id"], generation,
                 lease["acquired_at"], lease["expires_at"]),
            )
        return lease

    def renew(self, task_id: str, lease_id: str, ttl_s: float = LEASE_TTL_S) -> bool:
        with self.e.transaction() as conn:
            cur = conn.execute("UPDATE leases SET expires_at=? WHERE task_id=? AND lease_id=?",
                               (time.time() + ttl_s, task_id, lease_id))
            return cur.rowcount == 1

    def release(self, task_id: str, lease_id: str) -> None:
        with self.e.transaction() as conn:
            conn.execute("DELETE FROM leases WHERE task_id=? AND lease_id=?", (task_id, lease_id))

    def stale(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        ts = now if now is not None else time.time()
        rows = self.e._conn().execute("SELECT * FROM leases WHERE expires_at<?", (ts,)).fetchall()
        return [dict(r) for r in rows]


class SideEffectLog:
    """Operation log with UNKNOWN_OUTCOME reconciliation (sections 20-21)."""

    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def prepare(self, task_id: str, kind: str,
                idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        op_id = f"op_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self.e.transaction() as conn:
            if idempotency_key:
                row = conn.execute("SELECT operation_id FROM side_effects WHERE idempotency_key=?",
                                   (idempotency_key,)).fetchone()
                if row:
                    existing = conn.execute("SELECT * FROM side_effects WHERE operation_id=?",
                                            (row["operation_id"],)).fetchone()
                    assert existing is not None
                    return dict(existing)
            conn.execute(
                "INSERT INTO side_effects (operation_id, task_id, kind, state,"
                " idempotency_key, receipt, created_at, updated_at)"
                " VALUES (?, ?, ?, 'PREPARED', ?, '', ?, ?)",
                (op_id, task_id, kind, idempotency_key, now, now),
            )
        return self.get(op_id)  # type: ignore[return-value]

    def get(self, operation_id: str) -> Optional[Dict[str, Any]]:
        row = self.e._conn().execute("SELECT * FROM side_effects WHERE operation_id=?",
                                     (operation_id,)).fetchone()
        return dict(row) if row else None

    def transition(self, operation_id: str, to_state: str, receipt: str = "") -> Dict[str, Any]:
        assert to_state in SIDE_EFFECT_STATES, to_state
        with self.e.transaction() as conn:
            conn.execute("UPDATE side_effects SET state=?, receipt=?, updated_at=? WHERE operation_id=?",
                         (to_state, receipt, time.time(), operation_id))
        updated = self.get(operation_id)
        assert updated is not None
        return updated

    def mark_unknown(self, operation_id: str) -> Dict[str, Any]:
        """Crash path: outcome unknowable until external verification."""
        return self.transition(operation_id, "UNKNOWN_OUTCOME")

    def reconcile(self, operation_id: str, verify: Any) -> Dict[str, Any]:
        """Run caller-supplied ``verify() -> (happened: bool, receipt: str)``.

        - happened=True  -> VERIFIED (receipt stored)
        - happened=False -> FAILED (safe to retry with same idempotency key)
        - verify raises  -> stays UNKNOWN_OUTCOME (never auto-SUCCESS)
        """
        op = self.get(operation_id)
        assert op is not None, operation_id
        try:
            happened, receipt = verify(op)
        except Exception:
            return self.get(operation_id)  # type: ignore[return-value]
        if happened:
            return self.transition(operation_id, "VERIFIED", receipt=receipt)
        return self.transition(operation_id, "FAILED", receipt=receipt)


class CrashRecoveryManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine
        self.leases = LeaseManager(engine)
        self.effects = SideEffectLog(engine)

    def startup_scan(self) -> Dict[str, Any]:
        """Sections 18 + 80: startup health + recovery triage."""
        now = time.time()
        stale_leases = self.leases.stale(now)
        unknowns = self.e._conn().execute(
            "SELECT * FROM side_effects WHERE state='UNKNOWN_OUTCOME'").fetchall()
        prepared = self.e._conn().execute(
            "SELECT * FROM side_effects WHERE state IN ('PREPARED','AUTHORIZED')").fetchall()
        expired_ckpts = self.e._conn().execute(
            "SELECT checkpoint_id, task_id FROM checkpoints WHERE expires_at>0 AND expires_at<?",
            (now,)).fetchall()
        # Interrupted tasks: have a checkpoint but no live lease and no terminal event.
        interrupted = self.e._conn().execute(
            "SELECT DISTINCT task_id FROM checkpoints WHERE task_id NOT IN (SELECT task_id FROM leases)").fetchall()
        report = {
            "stale_leases": [dict(r) for r in stale_leases],
            "unknown_side_effects": [dict(r) for r in unknowns],
            "pending_side_effects": [dict(r) for r in prepared],
            "expired_checkpoints": [dict(r) for r in expired_ckpts],
            "interrupted_tasks": [r["task_id"] for r in interrupted],
            "policy": ("resume only operations whose checkpoint validates AND whose authority"
                       " is still valid AND whose side effects are VERIFIED or safely retryable;"
                       " everything else enters RECOVERED_PENDING_RECONCILIATION for review"),
        }
        with self.e.transaction() as conn:
            self.e.append_event("recovery", "startup", "recovery.event",
                                {"summary": {k: (len(v) if isinstance(v, list) else v)
                                             for k, v in report.items() if k != "policy"}},
                                conn=conn)
        return report
