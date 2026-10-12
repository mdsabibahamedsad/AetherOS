"""Tests for mission recovery, queue recovery, and IPC health."""

from aetheros_reliability.ipc import (
    IPCChannel,
    IPCHealth,
    IPCState,
)
from aetheros_reliability.journal import RecoveryJournal
from aetheros_reliability.mission import (
    MissionClassification,
    MissionRecovery,
)
from aetheros_reliability.queue import QueueRecovery


class TestMissionRecovery:
    def test_unknown_mission(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        mr = MissionRecovery(journal=j)
        status = mr.classify("never-seen")
        assert status.classification == MissionClassification.UNKNOWN

    def test_completed_mission_classified(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        op = j.begin("mission-deploy-1", "mission:run")
        j.complete(op)
        mr = MissionRecovery(journal=j)
        status = mr.classify("mission-deploy-1")
        assert status.classification == MissionClassification.COMPLETED

    def test_pending_mission_requires_review(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        j.begin("mission-deploy-2", "mission:run")
        mr = MissionRecovery(journal=j)
        status = mr.classify("mission-deploy-2")
        assert status.classification == MissionClassification.REQUIRES_REVIEW

    def test_high_risk_mission_cannot_resume(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        j.begin("mission-sec-1", "mission:revoke_access")
        mr = MissionRecovery(journal=j)
        status = mr.classify("mission-sec-1")
        assert status.classification == MissionClassification.CANNOT_RESUME

    def test_checkpointed_mission_safe_to_resume(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        op = j.begin("mission-deploy-3", "mission:run")
        j.checkpoint(op, step=2)
        mr = MissionRecovery(journal=j)
        status = mr.classify("mission-deploy-3")
        assert status.classification == MissionClassification.SAFE_TO_RESUME
        assert status.last_checkpoint == 2

    def test_analyze_from_journal(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        j.begin("mission-deploy-4", "mission:run")
        mr = MissionRecovery(journal=j)
        statuses = mr.analyze()
        assert len(statuses) == 1
        assert statuses[0].mission_id == "mission-deploy-4"


class TestQueueRecovery:
    def test_mark_and_recover(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        qr = QueueRecovery(journal=j)
        task_id = qr.persist("billing", {"invoice_id": 7})
        qr.mark_started(task_id, queue="billing")
        recoverable = qr.recoverable_jobs("billing")
        assert any(r["job_id"] == task_id for r in recoverable)

    def test_completed_not_recoverable(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        qr = QueueRecovery(journal=j)
        task_id = qr.persist("billing", {"invoice_id": 8})
        qr.mark_started(task_id, queue="billing")
        qr.mark_done(task_id, queue="billing")
        assert not qr.recoverable_jobs("billing")

    def test_dead_letter_persisted(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        qr = QueueRecovery(journal=j, dead_letter_dir=tmp_path / "dl")
        path = qr.dead_letter("billing", "job-3", reason="retries exhausted", attempts=5)
        assert path.exists()
        entries = qr.dead_letter_queue("billing")
        assert len(entries) == 1
        assert entries[0]["job_id"] == "job-3"

    def test_replay_idempotency_key(self, tmp_path):
        j = RecoveryJournal(db_path=tmp_path / "journal.db")
        qr = QueueRecovery(journal=j)
        k1 = qr.replay_idempotency_key({"job_id": "task-4"})
        k2 = qr.replay_idempotency_key({"job_id": "task-4"})
        assert k1 == k2 == "task-4"
        k3 = qr.replay_idempotency_key({"type": "a", "n": 1})
        k4 = qr.replay_idempotency_key({"type": "a", "n": 1})
        assert k3 == k4


class TestIPCHealth:
    def test_initial_healthy(self):
        ipc = IPCHealth()
        assert ipc.state(IPCChannel.AGENT_TOOL) == IPCState.CONNECTED

    def test_disconnect_and_reconnect(self):
        ipc = IPCHealth()
        chan = IPCChannel.AGENT_TOOL
        ipc.set_on_reconnect(chan, lambda c, ctx: "ok")
        ipc.disconnect(chan, error="crash")
        assert ipc.state(chan) == IPCState.DISCONNECTED
        assert ipc.get(chan).disconnect_count == 1
        ok = ipc.reconnect(chan)
        assert ok is True
        assert ipc.state(chan) == IPCState.CONNECTED
        assert ipc.get(chan).connect_count == 1

    def test_reconnect_runs_revalidate_hook(self):
        ipc = IPCHealth()
        chan = IPCChannel.ELECTRON_BACKEND
        ipc.set_on_reconnect(chan, lambda c, ctx: "reconnected")
        ipc.set_on_revalidate(chan, lambda c: {"tools": ["terminal"]})
        ipc.disconnect(chan, error="backend restart")
        assert ipc.reconnect(chan) is True
        assert ipc.get(chan).capabilities == {"tools": ["terminal"]}

    def test_revalidate_failure_degrades(self):
        ipc = IPCHealth()
        chan = IPCChannel.AGENT_MCP
        ipc.set_on_reconnect(chan, lambda c, ctx: "reconnected")
        ipc.set_on_revalidate(chan, lambda c: (_ for _ in ()).throw(RuntimeError("bad")))
        ipc.disconnect(chan, error="reset")
        assert ipc.reconnect(chan) is False
        assert ipc.state(chan) == IPCState.DEGRADED

    def test_all_channels(self):
        ipc = IPCHealth()
        assert len(ipc.all()) >= 4

    def test_unhealthy_and_summary(self):
        ipc = IPCHealth()
        ipc.disconnect(IPCChannel.BACKEND_GATEWAY, error="x")
        assert IPCChannel.BACKEND_GATEWAY.value in ipc.unhealthy()
        s = ipc.summary()
        assert s["total"] >= 4
