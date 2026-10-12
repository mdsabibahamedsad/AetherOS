"""Tests for aetheros_integrations.scheduler — cron math, event triggers, tick."""

import time

import pytest

from aetheros_integrations.scheduler import Scheduler


@pytest.fixture
def scheduler(tmp_path):
    return Scheduler(dirpath=tmp_path)


class TestCreate:
    def test_once_job(self, scheduler):
        job = scheduler.create("one-shot", "echo", schedule_type="once", run_at=time.time() + 500)
        assert job.schedule_type == "once"
        assert job.next_run_at > time.time()
        assert scheduler.get(job.id).id == job.id

    def test_daily_job(self, scheduler):
        job = scheduler.create("daily", "echo", schedule_type="daily")
        assert job.next_run_at > time.time()

    def test_invalid_cron_rejected(self, scheduler):
        with pytest.raises(ValueError):
            scheduler.create("bad", "echo", schedule_type="cron", cron_expr="not-a-cron")

    def test_valid_cron_computes_next(self, scheduler):
        job = scheduler.create("good", "echo", schedule_type="cron", cron_expr="0 9 * * *")
        assert job.next_run_at > time.time()

    def test_event_job(self, scheduler):
        job = scheduler.create("on-push", "echo", schedule_type="event", event_type="git.push")
        assert job.params["event_type"] == "git.push"
        assert job.next_run_at == 0

    def test_remove(self, scheduler):
        job = scheduler.create("x", "echo")
        assert scheduler.remove(job.id) is True
        assert scheduler.remove(job.id) is False
        assert scheduler.list() == []


class TestExecution:
    def test_run_now_with_executor(self, scheduler):
        calls = []

        def executor(job):
            calls.append(job.id)
            return "ok"

        scheduler.set_executor(executor)
        job = scheduler.create("x", "echo")
        result = scheduler.run_now(job.id)
        assert result == "ok"
        assert calls == [job.id]
        assert scheduler.get(job.id).run_count == 1
        assert scheduler.get(job.id).last_status == "success"

    def test_run_now_propagates_executor_error(self, scheduler):
        def executor(job):
            raise RuntimeError("boom")

        scheduler.set_executor(executor)
        job = scheduler.create("x", "echo")
        with pytest.raises(RuntimeError):
            scheduler.run_now(job.id)
        assert "boom" in scheduler.get(job.id).last_status

    def test_no_executor_raises(self, scheduler):
        job = scheduler.create("x", "echo")
        with pytest.raises(RuntimeError):
            scheduler.run_now(job.id)


class TestEventTrigger:
    def test_event_trigger_fires_job(self, tmp_path):
        from aetheros_integrations.events import EventBus

        bus = EventBus(dirpath=tmp_path)
        scheduler = Scheduler(event_bus=bus, dirpath=tmp_path)
        calls = []
        scheduler.set_executor(lambda job: calls.append(job.id))
        job = scheduler.create("on-x", "echo", schedule_type="event", event_type="x.happened")
        bus.publish("scheduler.trigger", {"event_type": "x.happened"}, dedup_key=f"trig-{time.time()}")
        assert calls == [job.id]

    def test_event_trigger_ignores_other_type(self, tmp_path):
        from aetheros_integrations.events import EventBus

        bus = EventBus(dirpath=tmp_path)
        scheduler = Scheduler(event_bus=bus, dirpath=tmp_path)
        calls = []
        scheduler.set_executor(lambda job: calls.append(job.id))
        scheduler.create("on-x", "echo", schedule_type="event", event_type="x.happened")
        bus.publish("scheduler.trigger", {"event_type": "y.happened"}, dedup_key=f"trig-{time.time()}")
        assert calls == []


class TestTick:
    def test_tick_fires_due_job(self, scheduler):
        calls = []
        scheduler.set_executor(lambda job: calls.append(job.id))
        job = scheduler.create("due", "echo", schedule_type="once", run_at=time.time() - 1)
        scheduler._tick()
        assert calls == [job.id]

    def test_tick_skips_future_job(self, scheduler):
        calls = []
        scheduler.set_executor(lambda job: calls.append(job.id))
        scheduler.create("future", "echo", schedule_type="once", run_at=time.time() + 10000)
        scheduler._tick()
        assert calls == []

    def test_tick_skips_disabled_job(self, scheduler):
        calls = []
        scheduler.set_executor(lambda job: calls.append(job.id))
        job = scheduler.create("disabled", "echo", schedule_type="once", run_at=time.time() - 1)
        job.enabled = False
        scheduler._tick()
        assert calls == []

    def test_compute_next_runs(self, scheduler):
        scheduler.create("once", "echo", schedule_type="once", run_at=time.time() + 30)
        scheduler.create("event", "echo", schedule_type="event", event_type="e.t")
        runs = scheduler.compute_next_runs()
        by_name = {r["name"]: r for r in runs}
        assert by_name["once"]["kind"] == "once"
        assert by_name["event"]["kind"] == "event"
        assert by_name["event"]["waits_for"] == "e.t"


class TestPersistence:
    def test_jobs_persist_across_instances(self, tmp_path):
        sched1 = Scheduler(dirpath=tmp_path)
        job = sched1.create("persist-me", "echo", schedule_type="daily")
        sched2 = Scheduler(dirpath=tmp_path)
        reloaded = sched2.get(job.id)
        assert reloaded.name == "persist-me"
        assert reloaded.schedule_type == "daily"
