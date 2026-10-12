"""Integrity, retention, GC, paths, health, metrics (sections 33-36, 51-52, 73-84)."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_data.engine import StorageEngine

# ---------------------------------------------------------------------------
# ConsistencyChecker (section 79)
# ---------------------------------------------------------------------------

CORRUPTION_CLASSES = ("RECOVERABLE", "PARTIALLY_RECOVERABLE", "UNRECOVERABLE", "UNKNOWN")


class ConsistencyChecker:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def check(self) -> Dict[str, Any]:
        conn = self.e._conn()
        findings: List[Dict[str, Any]] = []

        def add(check: str, rows: List[Any], severity: str, klass: str = "UNKNOWN") -> None:
            if rows:
                findings.append({"check": check, "count": len(rows),
                                 "sample": [dict(r) if hasattr(r, "keys") else r for r in rows[:3]],
                                 "severity": severity, "class": klass})

        # Task/agent/automation record refs from checkpoints.
        add("checkpoint.task_ref",
            conn.execute("SELECT checkpoint_id FROM checkpoints WHERE task_id=''").fetchall(),
            "error", "RECOVERABLE")
        # Memory refs from checkpoints.
        ckpts = conn.execute("SELECT checkpoint_id, payload FROM checkpoints").fetchall()
        bad_mem = []
        for c in ckpts:
            try:
                payload = json.loads(c["payload"])
            except (ValueError, TypeError):
                findings.append({"check": "checkpoint.payload_parse", "count": 1,
                                 "sample": [c["checkpoint_id"]], "severity": "error",
                                 "class": "PARTIALLY_RECOVERABLE"})
                continue
            for mid in payload.get("memory_references", []):
                row = conn.execute("SELECT 1 FROM memory_records WHERE memory_id=?", (mid,)).fetchone()
                if row is None:
                    bad_mem.append({"checkpoint_id": c["checkpoint_id"], "memory_id": mid})
        add("checkpoint.memory_ref", bad_mem, "warning", "RECOVERABLE")
        # Authority refs: checkpoint authority_reference must exist (validity checked at restore).
        bad_auth = []
        for c in ckpts:
            try:
                payload = json.loads(c["payload"])
            except (ValueError, TypeError):
                continue
            ref = payload.get("authority_reference", "")
            if ref and conn.execute("SELECT 1 FROM authority_grants WHERE grant_id=?",
                                    (ref,)).fetchone() is None:
                bad_auth.append({"checkpoint_id": c["checkpoint_id"], "grant": ref})
        add("checkpoint.authority_ref", bad_auth, "warning", "RECOVERABLE")
        # Artifact hash verification (metadata vs bytes).
        from aetheros_data.artifacts import ArtifactStore
        store = ArtifactStore(self.e)
        bad_art = []
        for r in conn.execute("SELECT artifact_id FROM artifacts").fetchall():
            try:
                store.get_bytes(r["artifact_id"], verify=True)
            except (ValueError, OSError) as exc:
                bad_art.append({"artifact_id": r["artifact_id"], "error": str(exc)[:120]})
        add("artifact.integrity", bad_art, "error", "PARTIALLY_RECOVERABLE")
        # Sync/conflict refs.
        add("conflict.object_ref",
            conn.execute("SELECT conflict_id FROM conflicts WHERE object_id=''").fetchall(),
            "error", "RECOVERABLE")
        # Event envelope completeness.
        add("event.envelope",
            conn.execute("SELECT event_id FROM events WHERE aggregate_id='' OR kind=''").fetchall(),
            "error", "RECOVERABLE")
        # Malformed record JSON.
        bad_json = []
        for r in conn.execute("SELECT domain, record_id, data FROM records").fetchall():
            try:
                json.loads(r["data"])
            except ValueError:
                bad_json.append({"domain": r["domain"], "record_id": r["record_id"]})
        add("record.json", bad_json, "error", "PARTIALLY_RECOVERABLE")

        errors = sum(1 for f in findings if f["severity"] == "error")
        status = "HEALTHY" if not findings else ("CORRUPTED" if errors else "DEGRADED")
        return {"status": status, "findings": findings,
                "checked_at": time.time(), "evidence": "row-level queries, see findings"}

    def classify(self, finding: Dict[str, Any]) -> str:
        """Never silently repair (section 52): classify + preserve evidence + incident."""
        assert finding.get("check")
        klass = finding.get("class", "UNKNOWN")
        assert klass in CORRUPTION_CLASSES, klass
        with self.e.transaction() as conn:
            self.e.append_event("integrity", finding["check"], "recovery.event",
                                {"finding": finding, "class": klass}, conn=conn)
        return klass


# ---------------------------------------------------------------------------
# RetentionManager + GC (sections 33, 35-36)
# ---------------------------------------------------------------------------

class RetentionManager:
    def __init__(self, engine: StorageEngine) -> None:
        self.e = engine

    def apply(self, now: Optional[float] = None) -> Dict[str, Any]:
        ts = now if now is not None else time.time()
        out: Dict[str, Any] = {}
        with self.e.transaction() as conn:
            # Expired checkpoints (not referenced by active leases).
            cur = conn.execute(
                "DELETE FROM checkpoints WHERE expires_at>0 AND expires_at<?"
                " AND task_id NOT IN (SELECT task_id FROM leases)",
                (ts,))
            out["checkpoints_deleted"] = cur.rowcount
            # Stale leases.
            cur = conn.execute("DELETE FROM leases WHERE expires_at<?", (ts,))
            out["leases_deleted"] = cur.rowcount
            # Sync ops ACKED/CONFLICT-resolved older than 7d are compacted; QUEUED never GC'd.
            cur = conn.execute("DELETE FROM sync_ops WHERE state IN ('ACKED') AND timestamp<?",
                               (ts - 7 * 86400,))
            out["sync_compacted"] = cur.rowcount
            # Old backups beyond retention.
            cur = conn.execute("DELETE FROM backup_registry WHERE ?-created_at>retention_days*86400",
                               (ts,))
            out["backups_expired"] = cur.rowcount
        # Filesystem caches are disposable (section 75).
        cache_dir = get_aetheros_home() / "cache"
        removed = 0
        if cache_dir.exists():
            for f in cache_dir.rglob("*"):
                try:
                    if f.is_file() and ts - f.stat().st_mtime > 7 * 86400:
                        f.unlink()
                        removed += 1
                except OSError:
                    pass
        out["cache_files_removed"] = removed
        return out


# ---------------------------------------------------------------------------
# PlatformStorageAdapter (sections 72-73, 101, 121)
# ---------------------------------------------------------------------------

class PlatformStorageAdapter:
    """Platform-safe locations. No hardcoded C:\\Users /Users /home in logic."""

    @staticmethod
    def home() -> Path:
        return get_aetheros_home()

    @staticmethod
    def platform() -> str:
        if sys.platform == "win32":
            return "windows"
        if sys.platform == "darwin":
            return "macos"
        return "linux"

    @staticmethod
    def data_dir() -> Path:
        return get_aetheros_home() / "data"

    @staticmethod
    def artifacts_dir() -> Path:
        return get_aetheros_home() / "data" / "artifacts"

    @staticmethod
    def backups_dir() -> Path:
        return get_aetheros_home() / "backups"

    @staticmethod
    def logical_to_platform(logical: str) -> Path:
        """Resolve a logical reference (e.g. 'project://report.pdf') to a path."""
        assert "://" in logical or not logical.startswith("/"), logical
        if "://" in logical:
            _, rest = logical.split("://", 1)
            return get_aetheros_home() / rest
        return get_aetheros_home() / logical


# ---------------------------------------------------------------------------
# Startup health check (section 80) + metrics/quotas/backpressure (81-83)
# ---------------------------------------------------------------------------

def startup_health_check(engine: StorageEngine) -> Dict[str, Any]:
    from aetheros_data.recovery import CrashRecoveryManager
    integrity = engine.integrity_check()
    consistency = ConsistencyChecker(engine).check()
    recovery = CrashRecoveryManager(engine).startup_scan()
    issues = [f for f in consistency["findings"] if f["severity"] == "error"]
    ok = integrity["status"] != "CORRUPTED" and not issues
    return {"ok": ok, "integrity": integrity, "consistency": consistency,
            "recovery": {k: (len(v) if isinstance(v, list) else v)
                         for k, v in recovery.items() if k != "policy"},
            "non_blocking": "non-critical corruption reported, startup not blocked"}


class StorageMetrics:
    """In-process counters + latency samples (section 81/113)."""

    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}
        self.latencies: Dict[str, List[float]] = {}

    def inc(self, name: str, n: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + n

    def observe(self, name: str, seconds: float) -> None:
        self.latencies.setdefault(name, []).append(seconds)
        if len(self.latencies[name]) > 256:
            self.latencies[name] = self.latencies[name][-256:]

    def snapshot(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"counters": dict(self.counters), "latency_avg": {}}
        for k, v in self.latencies.items():
            out["latency_avg"][k] = sum(v) / len(v) if v else 0.0
        # DB/artifact sizes.
        home = get_aetheros_home()
        db = home / "data" / "aetheros_data.db"
        out["db_size_bytes"] = db.stat().st_size if db.exists() else 0
        art = home / "data" / "artifacts"
        total = sum(f.stat().st_size for f in art.rglob("*") if f.is_file()) if art.exists() else 0
        out["artifacts_size_bytes"] = total
        out["platform"] = PlatformStorageAdapter.platform()
        return out


METRICS = StorageMetrics()


def check_quotas(engine: StorageEngine, limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Quota check (section 82): WARNING/BLOCK/USER_ACTION_REQUIRED, never silent delete."""
    limits = limits or {}
    snap = METRICS.snapshot()
    stats = engine.stats()
    verdicts = []
    total = snap["db_size_bytes"] + snap["artifacts_size_bytes"]
    cap = limits.get("total_bytes", 10 * 1024**3)
    if total > cap:
        verdicts.append({"resource": "total", "action": "BLOCK",
                         "detail": f"{total} > {cap}: refuse writes, USER_ACTION_REQUIRED"})
    elif total > int(cap * 0.8):
        verdicts.append({"resource": "total", "action": "WARNING",
                         "detail": f"{total} at 80% of {cap}"})
    ckpts = int(stats["tables"].get("checkpoints", 0))
    if ckpts > limits.get("checkpoints", 10000):
        verdicts.append({"resource": "checkpoints", "action": "CLEANUP",
                         "detail": "run retention; expired checkpoints eligible"})
    return {"verdicts": verdicts, "sizes": {"db": snap["db_size_bytes"],
                                            "artifacts": snap["artifacts_size_bytes"]}}
