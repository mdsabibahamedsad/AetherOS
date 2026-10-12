"""Master-13 core foundation: AutomationDefinition model tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.model import (
    AutomationState,
    definition_fingerprint,
    lifecycle_of,
    normalize_breaker,
    normalize_missed_policy,
    normalize_resource_limits,
    normalize_timezone,
    validate_automation,
)


class TestNormalizeMissedPolicy:
    def test_valid_policies(self):
        for policy in ("catch_up", "skip", "run_on_start", "run_next_interval", "ask_user"):
            assert normalize_missed_policy(policy) == policy

    def test_aliases_normalized(self):
        assert normalize_missed_policy("Run-On-Start") == "run_on_start"
        assert normalize_missed_policy("run next interval") == "run_next_interval"

    def test_none_returns_default(self):
        assert normalize_missed_policy(None) == "catch_up"
        assert normalize_missed_policy("", default="skip") == "skip"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_missed_policy("whenever")


class TestNormalizeTimezone:
    def test_valid(self):
        assert normalize_timezone("Asia/Kolkata") == "Asia/Kolkata"

    def test_empty_is_none(self):
        assert normalize_timezone(None) is None
        assert normalize_timezone("") is None

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_timezone("Mars/Olympus_Mons")


class TestNormalizeLimitsAndBreaker:
    def test_limits_valid(self):
        assert normalize_resource_limits({"max_runtime_seconds": 600}) == {
            "max_runtime_seconds": 600
        }
        assert normalize_resource_limits({"max_turns": "12"}) == {"max_turns": 12}

    def test_limits_empty_is_none(self):
        assert normalize_resource_limits(None) is None
        assert normalize_resource_limits({}) is None

    def test_limits_reject_bad_values(self):
        with pytest.raises(ValueError):
            normalize_resource_limits({"max_turns": -1})
        with pytest.raises(ValueError):
            normalize_resource_limits({"cost_usd": 5})

    def test_breaker_valid_and_rejections(self):
        assert normalize_breaker({"failure_threshold": 3}) == {"failure_threshold": 3}
        with pytest.raises(ValueError):
            normalize_breaker({"cooldown_seconds": 0})
        with pytest.raises(ValueError):
            normalize_breaker(["nope"])


def _base_job(**overrides):
    job = {
        "id": "abc123",
        "name": "nightly",
        "prompt": "do the thing",
        "schedule": {"kind": "interval", "minutes": 60},
        "enabled": True,
        "state": "scheduled",
    }
    job.update(overrides)
    return job


class TestLifecycleOf:
    def test_default_enabled_is_enabled_state(self):
        assert lifecycle_of(_base_job()) == AutomationState.ENABLED

    def test_paused(self):
        assert lifecycle_of(_base_job(enabled=False, state="paused")) == AutomationState.PAUSED

    def test_disabled(self):
        assert lifecycle_of(_base_job(enabled=False)) == AutomationState.DISABLED

    def test_quarantine_wins_over_everything(self):
        assert (
            lifecycle_of(_base_job(quarantined=True, enabled=False))
            == AutomationState.QUARANTINED
        )

    def test_open_breaker_blocks(self):
        from datetime import datetime, timezone

        job = _base_job(breaker_opened_at=datetime.now(timezone.utc).isoformat())
        assert lifecycle_of(job) == AutomationState.BLOCKED

    def test_elapsed_cooldown_unblocks(self):
        from datetime import datetime, timedelta, timezone

        opened = datetime.now(timezone.utc) - timedelta(hours=3)
        job = _base_job(
            breaker_opened_at=opened.isoformat(),
            breaker={"cooldown_seconds": 3600},
        )
        assert lifecycle_of(job) == AutomationState.ENABLED

    def test_error_state_maps_to_failed(self):
        assert lifecycle_of(_base_job(state="error")) == AutomationState.FAILED

    def test_completed(self):
        assert lifecycle_of(_base_job(state="completed")) == AutomationState.COMPLETED

    def test_running_detection(self):
        assert lifecycle_of(_base_job(), running_ids={"abc123"}) == AutomationState.RUNNING


class TestFingerprint:
    def test_stable_for_identical_records(self):
        assert definition_fingerprint(_base_job()) == definition_fingerprint(_base_job())

    def test_changes_when_definition_changes(self):
        before = definition_fingerprint(_base_job())
        after = definition_fingerprint(_base_job(prompt="different"))
        assert before != after

    def test_bookkeeping_does_not_change_fingerprint(self):
        before = definition_fingerprint(_base_job())
        after = definition_fingerprint(_base_job(failure_streak=3))
        assert before == after


class TestValidateAutomation:
    def test_valid_record_has_no_problems(self):
        assert validate_automation(_base_job()) == []

    def test_bad_timezone_reported(self):
        problems = validate_automation(_base_job(timezone="Nope/Nope"))
        assert any("timezone" in p.lower() for p in problems)

    def test_no_agent_without_script_reported(self):
        problems = validate_automation(_base_job(no_agent=True, prompt=None))
        assert problems

    def test_missing_prompt_and_script_reported(self):
        problems = validate_automation(_base_job(prompt=""))
        assert problems
