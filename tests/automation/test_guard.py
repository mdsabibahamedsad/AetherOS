"""Master-13 core foundation: circuit breaker, quarantine, estop, safe mode."""

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


class TestEmergencyStop:
    def test_inactive_by_default(self):
        from automation.guard import estop_active

        assert estop_active() is None

    def test_engage_and_lift(self, cron_env):
        from automation.guard import estop_active, set_estop

        record = set_estop(True, reason="runaway job")
        assert record and record["reason"] == "runaway job"
        active = estop_active()
        assert active and active["reason"] == "runaway job"

        set_estop(False)
        assert estop_active() is None


class TestSafeMode:
    def test_off_by_default(self):
        from automation.guard import safe_mode_enabled

        assert safe_mode_enabled({}) is False

    def test_config_gate(self):
        from automation.guard import safe_mode_enabled

        assert safe_mode_enabled({"automation": {"safe_mode": True}}) is True


def _job(**overrides):
    base = {"id": "j1", "name": "watcher"}
    base.update(overrides)
    return base


class TestGateJob:
    def test_clean_job_allowed(self):
        from automation.guard import gate_job

        allowed, reason, half_open = gate_job(_job())
        assert allowed and not half_open and not reason

    def test_quarantined_blocked(self):
        from automation.guard import gate_job

        allowed, reason, _ = gate_job(_job(quarantined=True))
        assert not allowed and "quarantine" in reason

    def test_open_breaker_blocks_with_time_left(self):
        from automation.guard import gate_job

        job = _job(breaker_opened_at=datetime.now(timezone.utc).isoformat())
        allowed, reason, half_open = gate_job(job)
        assert not allowed
        assert "breaker_open" in reason
        assert not half_open

    def test_elapsed_cooldown_half_opens(self):
        from automation.guard import gate_job

        opened = datetime.now(timezone.utc) - timedelta(seconds=7200)
        job = _job(breaker_opened_at=opened.isoformat())
        allowed, _, half_open = gate_job(job)
        assert allowed and half_open


class TestEvaluateResult:
    CFG = {"automation": {"breaker": {
        "failure_threshold": 3, "cooldown_seconds": 60, "quarantine_after_opens": 2,
    }}}

    def test_success_resets_streak(self):
        from automation.guard import evaluate_result

        updates, action = evaluate_result(_job(failure_streak=2), True, cfg=self.CFG)
        assert action == "reset" and updates == {"failure_streak": 0}

    def test_success_without_streak_is_noop(self):
        from automation.guard import evaluate_result

        updates, action = evaluate_result(_job(), True, cfg=self.CFG)
        assert action == "none" and updates is None

    def test_failures_below_threshold_only_count(self):
        from automation.guard import evaluate_result

        updates, action = evaluate_result(_job(failure_streak=1), False, cfg=self.CFG)
        assert action == "none" and updates["failure_streak"] == 2

    def test_threshold_opens_breaker(self):
        from automation.guard import evaluate_result

        updates, action = evaluate_result(_job(failure_streak=2), False, cfg=self.CFG)
        assert action == "open"
        assert updates["breaker_opens"] == 1
        assert updates.get("breaker_opened_at")

    def test_repeated_opens_quarantine(self):
        from automation.guard import evaluate_result

        updates, action = evaluate_result(
            _job(failure_streak=2, breaker_opens=1,
                 breaker_opened_at=datetime.now(timezone.utc).isoformat()),
            False,
            cfg=self.CFG,
        )
        # Failure while open → reopen path, no second opening yet.
        assert action == "reopen"

        # Half-open probe failure after cooldown elapsed opens again → quarantine.
        updates, action = evaluate_result(
            _job(failure_streak=2, breaker_opens=1), False, cfg=self.CFG
        )
        assert action == "quarantine"
        assert updates["quarantined"] is True
        assert updates["quarantine_reason"]

    def test_never_persists_anything_itself(self):
        from automation.guard import evaluate_result

        job = _job()
        evaluate_result(job, False, cfg=self.CFG)
        assert "failure_streak" not in job or job["failure_streak"] in (None, 0)


class TestRecordResultPersistence:
    def test_breaker_opens_and_recovers(self, cron_env):
        from automation.guard import recover_automation, record_result
        from cron.jobs import create_job, get_job

        job = create_job(prompt="p", schedule="every 1h", breaker={"failure_threshold": 2})

        assert record_result(job["id"], False, "boom") == "none"
        assert record_result(job["id"], False, "boom") == "open"

        stored = get_job(job["id"])
        assert stored["failure_streak"] == 2
        assert stored["breaker_opens"] == 1
        assert stored["breaker_opened_at"]

        assert record_result(job["id"], True) == "reset"
        stored = get_job(job["id"])
        assert stored["failure_streak"] == 0
        assert stored["breaker_opened_at"]

        assert recover_automation(job["id"]) is True
        stored = get_job(job["id"])
        assert not stored.get("quarantined")
        assert stored["breaker_opens"] == 1

    def test_unknown_job_is_noop(self, cron_env):
        from automation.guard import record_result

        assert record_result("does-not-exist", False) == "none"


class TestBreakerNotice:
    def test_notice_texts(self):
        from automation.guard import breaker_notice

        assert breaker_notice("open", "n", "ref", "err") 
        assert breaker_notice("quarantine", "n", "ref", "err")
        assert breaker_notice("none", "n", "ref", "err") is None
