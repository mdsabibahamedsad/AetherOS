"""Master-13 slice 2: event dispatcher — dispatch mechanics and boundaries."""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def cron_env(tmp_path, monkeypatch):
    aetheros_home = tmp_path / ".aetheros"
    aetheros_home.mkdir(parents=True)
    monkeypatch.setenv("AETHEROS_HOME", str(aetheros_home))

    import cron.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "HERMES_DIR", aetheros_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", aetheros_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", aetheros_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", aetheros_home / "cron" / "output")

    import automation.dispatcher as dispatcher_mod

    monkeypatch.setattr(dispatcher_mod, "_dispatcher", None)
    return aetheros_home


@pytest.fixture(autouse=True)
def fresh_bus():
    from automation.events import reset_bus

    reset_bus()
    yield
    reset_bus()


def _event_job(trigger=None):
    from cron.jobs import create_job, update_job

    job = create_job(prompt="handle it", schedule="every 1h")
    if trigger is not None:
        update_job(job["id"], {"trigger": trigger})
    return job


def _evt(event_type="task.failed", **overrides):
    base = {
        "event_type": event_type,
        "trust": "internal",
        "payload": {},
        "source": "test",
        "event_id": f"evt-{time.time_ns()}",
    }
    base.update(overrides)
    return base


class TestDispatch:
    def test_matching_event_arms_automation(self, cron_env):
        from automation.dispatcher import Dispatcher
        from cron.jobs import create_job, get_job, update_job

        job = create_job(prompt="p", schedule="every 1h")
        update_job(job["id"], {"trigger": {"kind": "event", "event_types": ["task.failed"]}})

        count = Dispatcher().dispatch(_evt())
        assert count == 1
        stored = get_job(job["id"])
        assert stored["next_run_at"] is not None
        assert stored["last_triggered_at"] is not None

    def test_non_matching_event_ignored(self, cron_env):
        from automation.dispatcher import Dispatcher
        from cron.jobs import create_job, get_job, update_job

        job = create_job(prompt="p", schedule="every 1h")
        update_job(job["id"], {"trigger": {"kind": "event", "event_types": ["file.created"]}})
        before = get_job(job["id"])["next_run_at"]

        assert Dispatcher().dispatch(_evt("task.failed")) == 0
        assert get_job(job["id"])["next_run_at"] == before

    def test_cooldown_blocks_retrigger(self, cron_env):
        from automation.dispatcher import Dispatcher
        from cron.jobs import apply_job_field_updates, create_job, get_job, update_job

        job = create_job(prompt="p", schedule="every 1h")
        update_job(
            job["id"],
            {
                "trigger": {
                    "kind": "event",
                    "event_types": ["task.failed"],
                    "cooldown_seconds": 3600,
                }
            },
        )
        d = Dispatcher()
        assert d.dispatch(_evt()) == 1
        assert d.dispatch(_evt()) == 0       # within cooldown

        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        apply_job_field_updates(job["id"], {"last_triggered_at": past})
        assert d.dispatch(_evt()) == 1

    def test_emergency_stop_blocks_dispatch(self, cron_env, monkeypatch):
        from automation.dispatcher import Dispatcher
        from automation.guard import set_estop
        from cron.jobs import create_job, get_job, update_job

        try:
            job = create_job(prompt="p", schedule="every 1h")
            update_job(
                job["id"],
                {"trigger": {"kind": "event", "event_types": ["task.failed"]}},
            )
            set_estop(True, reason="test")
            before = get_job(job["id"])["next_run_at"]
            assert Dispatcher().dispatch(_evt()) == 0
            assert get_job(job["id"])["next_run_at"] == before
        finally:
            set_estop(False)

    def test_quarantined_automation_not_dispatched(self, cron_env):
        from automation.dispatcher import Dispatcher
        from cron.jobs import (
            apply_job_field_updates,
            create_job,
            get_job,
            update_job,
        )

        job = create_job(prompt="p", schedule="every 1h")
        update_job(
            job["id"],
            {
                "trigger": {
                    "kind": "event",
                    "event_types": ["task.failed"],
                    "allow_untrusted": True,
                }
            },
        )
        apply_job_field_updates(job["id"], {"quarantined": True})
        before = get_job(job["id"])["next_run_at"]
        assert Dispatcher().dispatch(_evt(trust="external")) == 0
        stored = get_job(job["id"])
        assert stored["quarantined"] is True
        assert stored["next_run_at"] == before

    def test_external_events_require_opt_in(self, cron_env):
        from automation.dispatcher import Dispatcher
        from cron.jobs import create_job, get_job, update_job

        job = create_job(prompt="p", schedule="every 1h")
        update_job(
            job["id"],
            {"trigger": {"kind": "event", "event_types": ["file.created"]}},
        )
        before = get_job(job["id"])["next_run_at"]
        assert Dispatcher().dispatch(_evt("file.created", trust="external")) == 0
        assert get_job(job["id"])["next_run_at"] == before

    def test_rate_cap(self, cron_env, monkeypatch):
        import automation.dispatcher as dm
        from cron.jobs import create_job, get_job, update_job

        monkeypatch.setattr(
            dm,
            "_settings",
            lambda cfg=None: {"enabled": True, "max_dispatches_per_minute": 1},
        )
        job = create_job(prompt="p", schedule="every 1h")
        update_job(
            job["id"],
            {"trigger": {"kind": "event", "event_types": ["task.failed"]}},
        )
        d = dm.Dispatcher()
        first = get_job(job["id"])["next_run_at"]
        assert d.dispatch(_evt()) == 1       # one event → one rate slot
        assert d.dispatch(_evt()) == 0       # cap hit for this window
        assert get_job(job["id"])["next_run_at"] != first


class TestEventOnlyLifecycle:
    def test_mark_run_leaves_event_jobs_dormant(self, cron_env):
        from cron.jobs import (
            create_job,
            get_due_jobs,
            get_job,
            mark_job_run,
            update_job,
        )

        job = create_job(prompt="p", schedule="every 1h")
        update_job(
            job["id"],
            {"trigger": {"kind": "event", "event_types": ["task.failed"]}},
        )

        mark_job_run(job["id"], success=True)
        stored = get_job(job["id"])
        assert stored["enabled"] is True
        assert stored["state"] == "scheduled"
        assert stored["next_run_at"] is None
        assert get_due_jobs() == []

    def test_schedule_can_only_be_cleared_with_trigger(self, cron_env):
        import pytest
        from cron.jobs import create_job, get_job, resume_job, update_job

        job = create_job(prompt="p", schedule="every 1h")
        with pytest.raises(ValueError):
            update_job(job["id"], {"schedule": None})

        update_job(
            job["id"],
            {
                "trigger": {"kind": "event", "event_types": ["task.failed"]},
                "schedule": None,
            },
        )
        stored = get_job(job["id"])
        assert stored["schedule_display"] == "on event"
        assert stored["next_run_at"] is None

        resumed = resume_job(job["id"])
        assert resumed["enabled"] is True


class TestHasWork:
    def test_false_without_triggers_or_roots(self, cron_env):
        from automation.dispatcher import Dispatcher

        assert Dispatcher().has_work() is False

    def test_true_with_event_automation(self, cron_env):
        from automation.dispatcher import Dispatcher

        _event_job({"kind": "event", "event_types": ["task.failed"]})
        assert Dispatcher().has_work() is True
