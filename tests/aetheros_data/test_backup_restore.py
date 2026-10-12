"""Backup/restore round-trip + failure injection (Master 61 §88, §118)."""

from __future__ import annotations

import sqlite3
import time

import pytest

from aetheros_data.backup import BackupManager
from aetheros_data.engine import StorageEngine
from aetheros_data.records import TaskRepository
from aetheros_data.restore import RestoreManager


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(home))
    (home / "config.yaml").write_text("model: test\n")
    return StorageEngine(db_path=home / "data" / "rt.db")


def _seed(engine):
    tasks = TaskRepository(engine)
    tasks.create("job-1", {"state": "RUNNING", "title": "demo"}, idempotency_key="seed-1")
    from aetheros_data.records import MemoryRepository
    MemoryRepository(engine).write("project uses sqlite", provenance={"src": "t"})
    from aetheros_data.artifacts import ArtifactStore
    ArtifactStore(engine).put(b"report-bytes", filename="r.txt")


def test_backup_certified_only_after_restore(engine, tmp_path):
    """P6: CREATE -> VERIFY -> DESTROY -> RESTORE -> INTEGRITY -> START -> CHECKS."""
    _seed(engine)
    bm = BackupManager(engine)
    res = bm.create(scope="critical", kind="FULL")
    assert res.backup_id
    # VERIFY
    v = bm.verify(res.backup_id)
    assert v["ok"], v["reasons"]
    # DESTROY test environment (wipe live DB rows + config).
    with engine.transaction() as conn:
        conn.execute("DELETE FROM records")
        conn.execute("DELETE FROM memory_records")
    # RESTORE (full cycle incl. safety snapshot + integrity + reconcile).
    rm = RestoreManager(engine)
    prev = rm.preview(res.backup_id)
    assert prev["ok"]
    out = rm.restore(res.backup_id, assume_yes=True)
    assert out["ok"], out
    # APPLICATION START: fresh engine init runs migrations cleanly.
    engine2 = StorageEngine(db_path=engine.db_path)
    assert engine2.integrity_check()["status"] in ("HEALTHY", "DEGRADED")
    # TASK/MEMORY/AUDIT CHECKS
    assert TaskRepository(engine2).get("job-1") is not None
    assert engine2._conn().execute("SELECT COUNT(*) FROM memory_records").fetchone()[0] >= 1
    assert engine2._conn().execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] >= 1


def test_corrupted_backup_rejected(engine):
    _seed(engine)
    bm = BackupManager(engine)
    res = bm.create(scope="critical", kind="FULL")
    from pathlib import Path
    p = Path(res.path)
    raw = bytearray(p.read_bytes())
    raw[len(raw) // 2] ^= 0xFF
    p.write_bytes(bytes(raw))
    v = bm.verify(res.backup_id)
    assert not v["ok"]


def test_encrypted_backup_roundtrip(engine):
    from cryptography.fernet import Fernet
    _seed(engine)
    key = Fernet.generate_key()
    bm = BackupManager(engine)
    res = bm.create(scope="critical", kind="FULL", encryption_key=key)
    assert res.encryption == "fernet"
    assert bm.verify(res.backup_id, encryption_key=key)["ok"] is True
    out = RestoreManager(engine).restore(res.backup_id, encryption_key=key, assume_yes=True)
    assert out["ok"]


def test_unauthorized_restore_refused(engine):
    _seed(engine)
    res = BackupManager(engine).create(scope="critical", kind="FULL")
    with pytest.raises(PermissionError):
        RestoreManager(engine).restore(res.backup_id, assume_yes=False)


def test_failure_injection(engine):
    """§118: crash points, locks, corruption, stale writer, duplicates, revocation."""
    from aetheros_data.recovery import CrashRecoveryManager, SideEffectLog
    from aetheros_data.records import AuthorityStore
    from aetheros_data.sync import SyncEngine
    from aetheros_data.engine import ConflictError

    tasks = TaskRepository(engine)
    tasks.create("f1", {"state": "PENDING"})
    # crash before/after commit simulated via rollback + committed path.
    with pytest.raises(RuntimeError):
        with engine.transaction() as conn:
            conn.execute("INSERT INTO records (domain, record_id, version, generation, data,"
                         " created_at, updated_at, deleted) VALUES ('task','f-crash',1,1,'{}',0,0,0)")
            raise RuntimeError("simulated crash before commit")
    assert engine.record_get("task", "f-crash") is None
    # database locked: hold BEGIN IMMEDIATE on second connection.
    conn2 = sqlite3.connect(str(engine.db_path), timeout=0.2)
    try:
        conn2.execute("BEGIN IMMEDIATE")
        conn2.execute("INSERT INTO records (domain, record_id, version, generation, data,"
                      " created_at, updated_at, deleted) VALUES ('task','f-lock',1,1,'{}',0,0,0)")
        with pytest.raises(Exception):
            with engine.transaction():
                pass
    finally:
        try:
            conn2.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn2.close()
    # corrupted row (bad JSON) detected by checker.
    with engine.transaction() as conn:
        conn.execute("INSERT INTO records (domain, record_id, version, generation, data,"
                     " created_at, updated_at, deleted) VALUES ('task','f-bad',1,1,'{oops',0,0,0)")
    from aetheros_data.services import ConsistencyChecker
    rep = ConsistencyChecker(engine).check()
    assert any(f["check"] == "record.json" for f in rep["findings"])
    with engine.transaction() as conn:
        conn.execute("DELETE FROM records WHERE record_id='f-bad'")
    # stale writer.
    tasks.transition("f1", 1, {"state": "RUNNING"})
    with pytest.raises(ConflictError):
        tasks.transition("f1", 1, {"state": "DONE"})
    # duplicate request deduped.
    log = SideEffectLog(engine)
    a = log.prepare("f1", "git.push", idempotency_key="dup-op")
    b = log.prepare("f1", "git.push", idempotency_key="dup-op")
    assert a["operation_id"] == b["operation_id"]
    # device revocation blocks restricted sync.
    sync = SyncEngine(engine)
    env = sync.enqueue("task", "f1", 2, "UPDATE", {"state": "RUNNING"})
    out = sync.apply_remote(env, policy_check=lambda _e: False)
    assert out["applied"] is False
    # revoked authority invalid.
    auth = AuthorityStore(engine)
    g = auth.grant("ops", "deploy", ttl_s=3600)
    auth.revoke(g["grant_id"])
    assert not auth.is_valid(g["grant_id"])
    # startup scan runs and reports.
    scan = CrashRecoveryManager(engine).startup_scan()
    assert "stale_leases" in scan
