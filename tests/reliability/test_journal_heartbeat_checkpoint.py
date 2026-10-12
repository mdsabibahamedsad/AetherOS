"""Tests for the recovery journal, heartbeat registry, checkpoint store."""

from aetheros_reliability.checkpoint import CheckpointStore
from aetheros_reliability.heartbeat import HeartbeatRegistry
from aetheros_reliability.journal import RecoveryJournal


class TestRecoveryJournal:
    def test_lifecycle(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        op = j.begin("gateway", "restart")
        assert j.get(op)["status"] == "STARTED"
        assert j.checkpoint(op, step=1)
        assert j.complete(op)
        assert j.get(op)["status"] == "COMPLETED"
        assert j.pending() == []

    def test_pending_returns_unfinished(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        done = j.begin("gateway", "done")
        j.complete(done)
        open_op = j.begin("agent", "mission")
        pending = j.pending()
        assert len(pending) == 1
        assert pending[0]["operation_id"] == open_op

    def test_fail_abort_recoverable(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        f = j.begin("gateway", "f")
        j.fail(f)
        a = j.begin("gateway", "a")
        j.abort(a)
        r = j.begin("gateway", "r")
        j.mark_recoverable(r)
        assert j.get(f)["status"] == "FAILED"
        assert j.get(a)["status"] == "ABORTED"
        assert j.recoverable()[0]["operation_id"] == r

    def test_recent_orders_newest_first(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        for i in range(5):
            op = j.begin("c", f"op{i}")
            j.complete(op)
        recent = j.recent(limit=3)
        assert len(recent) == 3
        assert recent[0]["operation"] == "op4"

    def test_stats_and_integrity(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        op = j.begin("gateway", "restart")
        j.complete(op)
        stats = j.stats()
        assert stats["total"] == 1
        assert stats["by_status"]["COMPLETED"] == 1
        res = j.integrity()
        assert res["ok"] is True

    def test_append_operation(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        op = j.append_operation(
            operation="recovery:restart", component="gateway",
            status="COMPLETED", detail={"recovery_id": "abc"},
        )
        row = j.get(op)
        assert row["status"] == "COMPLETED"
        assert row["detail"]["recovery_id"] == "abc"


class TestHeartbeatRegistry:
    def test_beat_and_get(self):
        reg = HeartbeatRegistry()
        hb = reg.beat("gateway", version="1.2.3")
        assert reg.get("gateway").version == "1.2.3"
        assert reg.get("gateway").component_id == "gateway"

    def test_age_and_stale(self, monkeypatch):
        import time

        reg = HeartbeatRegistry()
        fake = {"now": 1000.0}
        monkeypatch.setattr(time, "time", lambda: fake["now"])
        reg.beat("gateway")
        fake["now"] = 1050.0
        assert reg.age("gateway") == 50.0
        assert reg.is_stale("gateway", timeout=30) is True
        assert reg.is_stale("gateway", timeout=60) is False

    def test_unknown_component(self):
        reg = HeartbeatRegistry()
        assert reg.is_stale("nope", timeout=10) is None
        assert reg.age("nope") is None

    def test_mark_stopping(self):
        reg = HeartbeatRegistry()
        reg.beat("gateway")
        reg.mark_stopping("gateway")
        assert reg.get("gateway").status == "stopping"

    def test_history(self):
        reg = HeartbeatRegistry()
        reg.beat("gateway", status="busy")
        reg.beat("gateway", status="alive")
        assert len(reg.history("gateway")) == 2


class TestCheckpointStore:
    def test_save_load(self, tmp_path):
        cs = CheckpointStore(root=tmp_path / "cp")
        cs.save("mission", "mission-1", {"step": 3, "data": "x"})
        loaded = cs.load("mission", "mission-1")
        assert loaded is not None
        assert loaded["step"] == 3
        assert loaded["data"] == "x"

    def test_secret_keys_redacted(self, tmp_path):
        cs = CheckpointStore(root=tmp_path / "cp")
        cs.save("mission", "mission-2", {"api_key": "secret123", "step": 1})
        loaded = cs.load("mission", "mission-2")
        assert loaded["step"] == 1
        assert loaded.get("api_key") != "secret123"
        assert "secret123" not in str(loaded)
