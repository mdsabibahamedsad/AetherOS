"""Master-13 core foundation: timezone/DST handling and missed-run policy."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.schedule_time import (
    decide_missed_run,
    effective_missed_policy,
    job_zone,
    preview_next_runs,
    resolve_zone,
)

NY = "America/New_York"


class TestZones:
    def test_resolve_valid_zone(self):
        zone = resolve_zone(NY)
        assert zone is not None

    def test_resolve_invalid_zone_is_none(self):
        assert resolve_zone("Not/AZone") is None
        assert resolve_zone(None) is None

    def test_job_zone(self):
        assert job_zone({"timezone": NY}) == resolve_zone(NY)
        assert job_zone({}) is None


def _decide(policy=None, kind="cron", lateness=4000.0, grace=1800):
    job = {} if policy is None else {"missed_policy": policy}
    return decide_missed_run(
        job,
        kind=kind,
        lateness_seconds=float(lateness),
        grace_seconds=grace,
        now=datetime.now(timezone.utc),
    )


class TestDecideMissedRunRecurring:
    def test_within_grace_always_fires(self):
        action, note = _decide(lateness=60.0)
        assert action == "fire"
        assert note is None

    def test_default_catch_up_fast_forwards_beyond_grace(self):
        assert _decide()[0] == "fast_forward"

    def test_skip_never_fires_late(self):
        assert _decide("skip")[0] == "fast_forward"

    def test_run_next_interval_matches_skip_for_recurring(self):
        assert _decide("run_next_interval")[0] == "fast_forward"

    def test_run_on_start_fires_with_notice_beyond_grace(self):
        action, note = _decide("run_on_start", lateness=7200.0)
        assert action == "fire"
        assert note and "missed-schedule" in note

    def test_run_on_start_respects_max_age(self):
        action, _ = _decide("run_on_start", lateness=48 * 3600.0)
        assert action == "fast_forward"

    def test_ask_user_carries_question_note(self):
        action, note = _decide("ask_user", lateness=7200.0)
        assert action == "fire"
        assert note and "ask_user" in note


class TestDecideMissedRunOneShot:
    def test_expired_one_shot_under_skip_disables(self):
        action, note = _decide("skip", kind="once", lateness=9999.0)
        assert action == "expire"
        assert note

    def test_legacy_one_shot_still_fires_late(self):
        # Historical behavior: a one-shot found past its time still runs.
        action, note = _decide(None, kind="once", lateness=99999.0)
        assert action == "fire"
        assert note is None


class TestEffectivePolicy:
    def test_defaults(self):
        policy, max_late = effective_missed_policy({})
        assert policy == "catch_up"
        assert max_late > 0

    def test_job_override_wins(self):
        policy, _ = effective_missed_policy({"missed_policy": "skip"})
        assert policy == "skip"

    def test_config_section_used_as_fallback(self):
        cfg = {"automation": {"missed_policy": "run_on_start"}}
        policy, _ = effective_missed_policy({}, cfg=cfg)
        assert policy == "run_on_start"


@pytest.mark.skipif(resolve_zone(NY) is None, reason="tzdata unavailable")
class TestTimezoneAwareCronNextRun:
    def test_wall_clock_preserved_across_dst_spring_forward(self):
        from cron.jobs import compute_next_run

        schedule = {"kind": "cron", "expr": "0 9 * * *"}
        before = datetime(2026, 3, 7, 10, 0, tzinfo=resolve_zone(NY))
        nxt = datetime.fromisoformat(
            compute_next_run(schedule, last_run_at=before.isoformat(), tz=resolve_zone(NY))
        )
        local = nxt.astimezone(resolve_zone(NY))
        assert local.hour == 9
        assert local.day == 8
        # 2026-03-08 09:00 in New York is already EDT (spring forward at 02:00).
        assert local.utcoffset().total_seconds() == -4 * 3600

    def test_wall_clock_preserved_across_dst_fall_back(self):
        from cron.jobs import compute_next_run

        schedule = {"kind": "cron", "expr": "30 8 * * *"}
        before = datetime(2026, 10, 31, 12, 0, tzinfo=resolve_zone(NY))
        nxt = datetime.fromisoformat(
            compute_next_run(schedule, last_run_at=before.isoformat(), tz=resolve_zone(NY))
        )
        local = nxt.astimezone(resolve_zone(NY))
        assert local.hour == 8 and local.minute == 30
        assert local.day == 1 and local.month == 11
        assert local.utcoffset().total_seconds() == -5 * 3600

    def test_no_tz_still_works(self):
        from cron.jobs import compute_next_run

        schedule = {"kind": "cron", "expr": "0 9 * * *"}
        nxt = compute_next_run(schedule)
        assert nxt


@pytest.mark.skipif(resolve_zone(NY) is None, reason="tzdata unavailable")
class TestPreview:
    def test_cron_preview_ascending_and_tz_scoped(self):
        runs = preview_next_runs({"kind": "cron", "expr": "0 9 * * *"}, count=3, tz_name=NY)
        assert len(runs) == 3
        assert all(r.astimezone(resolve_zone(NY)).hour == 9 for r in runs)
        assert runs[0] < runs[1] < runs[2]

    def test_interval_preview(self):
        runs = preview_next_runs({"kind": "interval", "minutes": 30}, count=2)
        assert len(runs) == 2
        delta = (runs[1] - runs[0]).total_seconds()
        assert delta == pytest.approx(1800, abs=5)
