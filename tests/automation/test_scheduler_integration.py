"""Master-13 core foundation: scheduler/jobs integration tests."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def cron_env(tmp_path, monkeypatch):
    """Isolated cron environment with temp AETHEROS_HOME (mirrors tests/cron)."""
    aetheros_home = tmp_path / ".aetheros"
    aetheros_home.mkdir(parents=True)
    monkeypatch.setenv("AETHEROS_HOME", str(aetheros_home))

    import cron.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "HERMES_DIR", aetheros_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", aetheros_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", aetheros_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", aetheros_home / "cron" / "output")
    return aetheros_home


def _stale(job_id, seconds_late=7200):
    """Force a job's next_run_at into the past so it looks missed."""
    from cron.jobs import apply_job_field_updates

    past = (datetime.now(timezone.utc) - timedelta(seconds=seconds_late)).isoformat()
    apply_job_field_updates(job_id, {"next_run_at": past})


class TestBreakerGateInDueList:
    def test_quarantined_job_never_due(self, cron_env):
        from automation.guard import recover_automation
        from cron.jobs import apply_job_field_updates, create_job, get_due_jobs, load_jobs

        job = create_job(prompt="p", schedule="every 1h")
        _stale(job["id"], seconds_late=60)
        apply_job_field_updates(
            job["id"],
            {"quarantined": True, "quarantine_reason": "test"},
        )

        assert get_due_jobs() == []
        recover_automation(job["id"])
        assert len(get_due_jobs()) == 1
        assert load_jobs()[0]["id"] == job["id"]

    def test_open_breaker_holds_back_then_half_opens(self, cron_env):
        from cron.jobs import apply_job_field_updates, create_job, get_due_jobs, load_jobs

        job = create_job(prompt="p", schedule="every 1h")
        _stale(job["id"], seconds_late=60)
        apply_job_field_updates(
            job["id"],
            {
                "failure_streak": 5,
                "breaker_opened_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert get_due_jobs() == []

        cooled = (
            datetime.now(timezone.utc) - timedelta(seconds=7200)
        ).isoformat()
        apply_job_field_updates(job["id"], {"breaker_opened_at": cooled})

        due = get_due_jobs()
        assert [j["id"] for j in due] == [job["id"]]
        stored = load_jobs()[0]
        assert stored.get("breaker_opened_at") is None


class TestMissedPolicies:
    def _recurring_job(self, policy=None):
        from cron.jobs import create_job

        kwargs = {"prompt": "p", "schedule": "every 1h"}
        if policy:
            kwargs["missed_policy"] = policy
        return create_job(**kwargs)

    def test_default_catch_up_fast_forwards_beyond_grace(self, cron_env):
        from cron.jobs import create_job, get_due_jobs, load_jobs

        job = self._recurring_job()
        _stale(job["id"], seconds_late=7200)

        assert get_due_jobs() == []
        stored_next = load_jobs()[0]["next_run_at"]
        assert datetime.fromisoformat(stored_next) > datetime.now(timezone.utc)

    def test_skip_policy_fast_forwards(self, cron_env):
        from cron.jobs import get_due_jobs, load_jobs

        job = self._recurring_job(policy="skip")
        _stale(job["id"], seconds_late=7200)

        assert get_due_jobs() == []
        stored_next = load_jobs()[0]["next_run_at"]
        assert datetime.fromisoformat(stored_next) > datetime.now(timezone.utc)

    def test_run_on_start_fires_with_transient_notice(self, cron_env):
        from cron.jobs import get_due_jobs, load_jobs

        job = self._recurring_job(policy="run_on_start")
        _stale(job["id"], seconds_late=7200)

        due = get_due_jobs()
        assert [j["id"] for j in due] == [job["id"]]
        assert due[0].get("_missed_recovery")
        assert "run_on_start" in due[0]["_missed_recovery"]
        for raw in load_jobs():
            assert "_missed_recovery" not in raw

    def test_ask_user_note_carries_question(self, cron_env):
        from cron.jobs import get_due_jobs

        job = self._recurring_job(policy="ask_user")
        _stale(job["id"], seconds_late=7200)
        due = get_due_jobs()
        assert due and "ask_user" in due[0]["_missed_recovery"]

    def test_within_grace_still_fires_under_any_policy(self, cron_env):
        from cron.jobs import get_due_jobs

        job = self._recurring_job(policy="skip")
        _stale(job["id"], seconds_late=300)
        assert [j["id"] for j in get_due_jobs()] == [job["id"]]


class TestOneShotPolicies:
    def test_expired_one_shot_skips_instead_of_running_late(self, cron_env):
        from cron.jobs import create_job, get_due_jobs, get_job

        job = create_job(prompt="p", schedule="2030-01-01T10:00", missed_policy="skip")
        _stale(job["id"], seconds_late=86400 * 30)

        assert get_due_jobs() == []
        stored = get_job(job["id"])
        assert stored["enabled"] is False
        assert stored["state"] == "skipped"

    def test_legacy_one_shot_still_fires_late(self, cron_env):
        from cron.jobs import create_job, get_due_jobs

        job = create_job(prompt="p", schedule="2030-01-01T10:00")
        _stale(job["id"], seconds_late=86400 * 30)

        due = get_due_jobs()
        assert [j["id"] for j in due] == [job["id"]]
        assert not due[0].get("_missed_recovery")


class TestDefinitionVersioning:
    def test_watched_edits_bump_bookkeeping_does_not(self, cron_env):
        from cron.jobs import (
            apply_job_field_updates,
            create_job,
            get_job,
            update_job,
        )

        job = create_job(prompt="v1", schedule="every 1h")
        assert job["definition_version"] == 1

        update_job(job["id"], {"prompt": "v2"})
        assert get_job(job["id"])["definition_version"] == 2

        update_job(job["id"], {"timezone": "Asia/Kolkata"})
        assert get_job(job["id"])["definition_version"] == 3

        apply_job_field_updates(job["id"], {"failure_streak": 2})
        assert get_job(job["id"])["definition_version"] == 3

        # No-op updates don't bump either.
        update_job(job["id"], {"prompt": "v2"})
        assert get_job(job["id"])["definition_version"] == 3


class TestCreateJobAutomationFields:
    def test_fields_stored_and_validated(self, cron_env):
        import pytest

        from cron.jobs import create_job

        with pytest.raises(ValueError):
            create_job(prompt="p", schedule="every 1h", timezone="Nope/Nope")
        with pytest.raises(ValueError):
            create_job(prompt="p", schedule="every 1h", missed_policy="whenever")

        job = create_job(
            prompt="p",
            schedule="0 9 * * *",
            timezone="Asia/Kolkata",
            missed_policy="skip",
            resource_limits={"max_runtime_seconds": 900},
            breaker={"failure_threshold": 4},
        )
        assert job["timezone"] == "Asia/Kolkata"
        assert job["missed_policy"] == "skip"
        assert job["resource_limits"] == {"max_runtime_seconds": 900}
        assert job["breaker"] == {"failure_threshold": 4}
        assert job["definition_version"] == 1
        assert job["failure_streak"] == 0

    def test_tz_scoped_schedule_keeps_wall_clock_hour(self, cron_env):
        from zoneinfo import ZoneInfo

        from cron.jobs import create_job

        job = create_job(prompt="p", schedule="0 9 * * *", timezone="Asia/Kolkata")
        nxt = datetime.fromisoformat(job["next_run_at"])
        local = nxt.astimezone(ZoneInfo("Asia/Kolkata"))
        assert local.hour == 9


class TestEmergencyStopBlocksTick:
    def test_tick_returns_zero_while_estop_active(self, cron_env):
        from automation.guard import set_estop
        from cron.jobs import apply_job_field_updates, create_job, get_job
        from cron.scheduler import tick

        try:
            job = create_job(prompt="p", schedule="every 1h")
            _stale(job["id"], seconds_late=60)

            set_estop(True, reason="integration test")
            executed = tick(verbose=False, sync=True)
            assert executed == 0
            assert get_job(job["id"])["last_run_at"] is None
        finally:
            set_estop(False)


class TestApplyFieldUpdatesGuardRails:
    def test_immutable_fields_rejected(self, cron_env):
        import pytest as _pytest

        from cron.jobs import apply_job_field_updates, create_job

        job = create_job(prompt="p", schedule="every 1h")
        with _pytest.raises(ValueError):
            apply_job_field_updates(job["id"], {"id": "../escape"})
