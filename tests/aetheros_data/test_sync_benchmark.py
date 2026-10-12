"""Sync conflicts/offline + storage benchmarks (Master 61 §85, §119)."""

from __future__ import annotations

import time

import pytest

from aetheros_data.engine import StorageEngine
from aetheros_data.records import TaskRepository
from aetheros_data.sync import SyncEngine


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(home))
    return StorageEngine(db_path=home / "data" / "sync.db")


def test_offline_queue_preserved(engine):
    sync = SyncEngine(engine)
    sync.set_offline(True)
    env = sync.enqueue("task", "o1", 1, "CREATE", {"state": "PENDING"})
    assert env["state"] == "QUEUED"
    assert sync.status()["state"] == "OFFLINE"
    assert len(sync.pending()) == 1
    sync.set_offline(False)
    out = sync.apply_remote(env, policy_check=lambda _e: True)
    assert out["applied"] is True


def test_conflict_explicit_not_silent(engine):
    tasks = TaskRepository(engine)
    tasks.create("c1", {"state": "PENDING"})
    sync = SyncEngine(engine)
    # Same-version concurrent update -> explicit conflict, both versions kept.
    env = {"device_id": "dev_remote", "sequence": 1, "object_type": "task",
           "object_id": "c1", "version": 1, "operation": "UPDATE",
           "payload": {"state": "REMOTE"}, "timestamp": time.time(),
           "provenance": {}, "integrity": "x"}
    out = sync.apply_remote(env, policy_check=lambda _e: True)
    assert out["applied"] is False and "conflict" in out
    assert len(sync.open_conflicts()) == 1
    cid = out["conflict"]["conflict_id"]
    res = sync.resolve(cid, "KEEP_REMOTE", "tester", winning_payload={"state": "REMOTE"})
    assert res["resolution"] == "KEEP_REMOTE"
    assert tasks.get("c1")["data"]["state"] == "REMOTE"


def test_non_syncable_refused(engine):
    sync = SyncEngine(engine)
    with pytest.raises(PermissionError):
        sync.enqueue("authority", "g1", 1, "CREATE", {})


def test_storage_benchmark(engine, capsys):
    """§85/§119: measure and record actual results (no fabrication)."""
    import json
    tasks = TaskRepository(engine)
    t0 = time.perf_counter()
    for i in range(100):
        tasks.create(f"b{i}", {"state": "PENDING", "i": i})
    create_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    for i in range(100):
        tasks.get(f"b{i}")
    read_s = time.perf_counter() - t0
    from aetheros_data.checkpoints import CheckpointManager
    ck = CheckpointManager(engine)
    t0 = time.perf_counter()
    for i in range(20):
        ck.create(f"b{i}", generation=i + 1)
    ckpt_s = time.perf_counter() - t0
    from aetheros_data.backup import BackupManager
    t0 = time.perf_counter()
    res = BackupManager(engine).create(scope="critical", kind="FULL")
    backup_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    v = BackupManager(engine).verify(res.backup_id)
    verify_s = time.perf_counter() - t0
    results = {"env": "windows/CI-unknown", "n_tasks": 100, "n_ckpts": 20,
               "create_100_s": round(create_s, 3), "read_100_s": round(read_s, 3),
               "ckpt_20_s": round(ckpt_s, 3), "backup_s": round(backup_s, 3),
               "verify_s": round(verify_s, 3), "verify_ok": v["ok"]}
    print("STORAGE_BENCHMARK " + json.dumps(results))
    assert v["ok"]
    assert create_s < 30 and read_s < 30
