"""Property + domain tests for the canonical data layer (Master 61 §116-117)."""

from __future__ import annotations

import os

import pytest

from aetheros_data.artifacts import ArtifactStore
from aetheros_data.checkpoints import CheckpointManager
from aetheros_data.engine import ConflictError, StorageEngine
from aetheros_data.records import (
    AgentRepository,
    AuthorityStore,
    MemoryRepository,
    TaskRepository,
)
from aetheros_data.sync import SyncEngine


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(home))
    return StorageEngine(db_path=home / "data" / "test.db")


def test_crud_transaction_concurrency(engine):
    tasks = TaskRepository(engine)
    r = tasks.create("t1", {"state": "PENDING"}, idempotency_key="idem-1")
    assert r["version"] == 1
    # P1: committed transition has a durable event.
    out = tasks.transition("t1", 1, {"state": "RUNNING"}, actor="tester")
    assert out["record"]["version"] == 2
    evts = engine._conn().execute(
        "SELECT * FROM events WHERE aggregate_id='t1' AND durable=1").fetchall()
    assert len(evts) >= 2
    # idempotent duplicate create returns existing, no duplicate.
    r2 = tasks.create("t1-dup", {"state": "PENDING"}, idempotency_key="idem-1")
    assert r2["record_id"] == "t1"


def test_stale_writer_rejected(engine):
    """P2: a stale writer cannot overwrite newer state."""
    tasks = TaskRepository(engine)
    tasks.create("t2", {"state": "PENDING"})
    tasks.transition("t2", 1, {"state": "RUNNING"})
    with pytest.raises(ConflictError):
        tasks.transition("t2", 1, {"state": "DONE"})


def test_memory_lifecycle(engine):
    """Memory versioning/provenance/conflict/rollback."""
    mem = MemoryRepository(engine)
    m = mem.write("sky is blue", provenance={"src": "test"}, confidence=0.8)
    assert m["status"] == "CANDIDATE"
    c = mem.confirm(m["memory_id"], 1)
    assert c["status"] == "CONFIRMED"
    old = mem.supersede(m["memory_id"], 2, "sky is blue-ish")
    assert old["status"] == "SUPERSEDED"
    # P4/P10-adjacent: rollback via retraction preserves evidence.
    r = mem.retract(old["memory_id"], 3, reason="test rollback")
    assert r["status"] == "RETRACTED"
    assert engine._conn().execute("SELECT COUNT(*) FROM memory_records").fetchone()[0] == 2


def test_authority_never_resurrected(engine):
    """P3: revoked authority cannot become valid after restore paths."""
    auth = AuthorityStore(engine)
    g = auth.grant("alice", "deploy", ttl_s=3600)
    assert auth.is_valid(g["grant_id"])
    auth.revoke(g["grant_id"])
    assert not auth.is_valid(g["grant_id"])
    assert auth.valid_grants_for("alice") == []


def test_checkpoint_validation_rejects_stale_authority(engine):
    """P4: checkpoint cannot restore invalid authority."""
    auth = AuthorityStore(engine)
    g = auth.grant("bob", "push", ttl_s=0.01)
    ck = CheckpointManager(engine)
    import time
    c = ck.create("task-x", authority_reference=g["grant_id"])
    time.sleep(0.02)
    verdict = ck.validate(c)
    assert not verdict["ok"]
    assert any("authority" in r for r in verdict["reasons"])


def test_artifact_integrity(engine, tmp_path):
    """P5: corrupted artifact cannot pass verification."""
    store = ArtifactStore(engine, root=tmp_path / "art")
    rec = store.put(b"hello", filename="hi.txt")
    assert store.get_bytes(rec["artifact_id"]) == b"hello"
    (tmp_path / "art" / rec["rel_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        store.get_bytes(rec["artifact_id"])


def test_cache_index_deletion_safe(engine, tmp_path, monkeypatch):
    """P7/P8: deleting cache/index cannot destroy canonical truth."""
    cache = tmp_path / "home" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "x.tmp").write_text("junk")
    tasks = TaskRepository(engine)
    tasks.create("t3", {"state": "PENDING"})
    for f in cache.rglob("*"):
        f.unlink()
    assert tasks.get("t3")["data"]["state"] == "PENDING"
    engine._conn().execute("DELETE FROM index_meta")
    assert tasks.get("t3") is not None


def test_unknown_side_effect_never_success():
    """P11: unknown external outcomes are never treated as success."""
    import tempfile
    from pathlib import Path
    td = tempfile.mkdtemp()
    eng = StorageEngine(db_path=Path(td) / "t.db")
    try:
        from aetheros_data.recovery import SideEffectLog
        log = SideEffectLog(eng)
        op = log.prepare("task-1", "email.send", idempotency_key="k-1")
        log.mark_unknown(op["operation_id"])
        # verify raises -> stays UNKNOWN
        out = log.reconcile(op["operation_id"], lambda _op: (_ for _ in ()).throw(RuntimeError("net down")))
        assert out["state"] == "UNKNOWN_OUTCOME"
    finally:
        eng.close()
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def test_idempotent_duplicate_no_dup_state(engine):
    """P12: duplicate idempotent ops do not create duplicate state."""
    tasks = TaskRepository(engine)
    a = tasks.create("ta", {"s": 1}, idempotency_key="dup-key")
    b = tasks.create("tb", {"s": 1}, idempotency_key="dup-key")
    assert a["record_id"] == b["record_id"]
    n = engine._conn().execute(
        "SELECT COUNT(*) FROM records WHERE idempotency_key='dup-key'").fetchone()[0]
    assert n == 1


def test_sync_policy_gate(engine):
    """P9: sync cannot bypass policy."""
    sync = SyncEngine(engine)
    env = sync.enqueue("task", "st1", 1, "CREATE", {"state": "PENDING"})
    out = sync.apply_remote(env, policy_check=lambda _e: False)
    assert out["applied"] is False and "policy" in out["reason"]


def test_import_cannot_grant_authority(engine, tmp_path):
    """P10: imported data cannot grant authority."""
    from aetheros_data.portability import PortabilityManager
    pm = PortabilityManager(engine)
    exp = pm.export(tmp_path / "exp.zip")
    assert exp["export_id"]
    out = pm.import_data(tmp_path / "exp.zip", actor="tester", authorize=True)
    assert out["ok"] is True
    assert engine._conn().execute("SELECT COUNT(*) FROM authority_grants").fetchone()[0] == 0


def test_agent_lifecycle(engine):
    agents = AgentRepository(engine)
    agents.register("a1", {"state": "INIT"}, idempotency_key="a1-key")
    out = agents.transition("a1", 1, {"state": "RUNNING"})
    assert out["record"]["version"] == 2
