"""Master-13 gap completion: notification preference gating + conflict detection.

Contracts tested:
- Critical lifecycle events are never silenced by preferences (Phase 61).
- Workflow notice delivery honors preferences; safe mode still wins.
- Conflict detection reports duplicate schedules, workdir overlap and
  event fanout without blocking anything (Phase 69).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Notification preferences (Phases 59-61)
# ---------------------------------------------------------------------------

CFG_ALLOWLIST_EXCLUDES_CRITICAL = {
    "automation": {
        "notifications": {
            "events": ["automation.completed"],
            "quiet_hours": {"start": "00:00", "end": "23:59"},
        }
    }
}

CFG_QUIET_ALWAYS = {
    "automation": {
        "notifications": {
            "events": [],
            "quiet_hours": {"start": "00:00", "end": "23:59"},
        }
    }
}


class TestCriticalNotificationsUnbypassable:
    def test_critical_bypasses_allowlist_and_quiet_hours(self):
        from automation.notifications import should_notify

        noon = datetime(2026, 8, 23, 12, 0)
        for critical in ("automation.quarantined", "automation.waiting_approval"):
            assert should_notify(
                critical, cfg=CFG_ALLOWLIST_EXCLUDES_CRITICAL, now=noon
            ) is True

    def test_noncritical_suppressed_by_allowlist(self):
        from automation.notifications import should_notify

        noon = datetime(2026, 8, 23, 12, 0)
        assert (
            should_notify(
                "automation.failed",
                cfg=CFG_ALLOWLIST_EXCLUDES_CRITICAL,
                now=noon,
            )
            is False
        )

    def test_noncritical_suppressed_by_quiet_hours(self):
        from automation.notifications import should_notify

        noon = datetime(2026, 8, 23, 12, 0)
        assert should_notify("automation.failed", cfg=CFG_QUIET_ALWAYS, now=noon) is False


class TestWorkflowNoticeGate:
    def _patch(self, monkeypatch, should):
        import automation.notifications as notif
        import cron.scheduler as cs

        delivered = []
        monkeypatch.setattr(cs, "_safe_mode_active", lambda: False)
        monkeypatch.setattr(
            cs, "_deliver_result", lambda *a, **k: delivered.append(a)
        )
        monkeypatch.setattr(notif, "should_notify", lambda evt, cfg=None, now=None: should)
        return delivered

    def test_suppressed_when_preferences_decline(self, monkeypatch):
        import cron.scheduler as cs

        delivered = self._patch(monkeypatch, should=False)
        cs._deliver_workflow_notice({"id": "j1"}, "hello")
        assert delivered == []

    def test_delivered_when_preferences_allow(self, monkeypatch):
        import cron.scheduler as cs

        delivered = self._patch(monkeypatch, should=True)
        cs._deliver_workflow_notice({"id": "j1"}, "hello")
        assert len(delivered) == 1

    def test_safe_mode_still_wins_over_preferences(self, monkeypatch):
        import automation.notifications as notif
        import cron.scheduler as cs

        delivered = self._patch(monkeypatch, should=True)
        monkeypatch.setattr(cs, "_safe_mode_active", lambda: True)
        cs._deliver_workflow_notice({"id": "j1"}, "hello")
        assert delivered == []
        del notif


# ---------------------------------------------------------------------------
# Conflict detection (Phase 69)
# ---------------------------------------------------------------------------


def _job(id, *, schedule=None, workdir=None, next_run_at=None, trigger=None,
         enabled=True, quarantined=False, name=None):
    return {
        "id": id,
        "name": name or id,
        "enabled": enabled,
        "quarantined": quarantined,
        "schedule": schedule,
        "workdir": workdir,
        "next_run_at": next_run_at,
        "trigger": trigger,
    }


INTERVAL_60 = {"kind": "interval", "minutes": 60}
CRON_9 = {"kind": "cron", "expr": "0 9 * * *"}
ONCE = {"kind": "once", "run_at": "2026-08-23T09:00:00+00:00"}


class TestFindConflicts:
    def test_duplicate_schedules_detected(self):
        from automation.conflicts import find_conflicts

        jobs = [
            _job("a", schedule=CRON_9),
            _job("b", schedule=dict(CRON_9)),
            _job("c", schedule=INTERVAL_60),
        ]
        conflicts = find_conflicts(jobs)
        kinds = {(c["kind"], tuple(sorted(c["refs"]))) for c in conflicts}
        assert ("duplicate_schedule", ("a", "b")) in kinds

    def test_once_schedules_never_conflict(self):
        from automation.conflicts import find_conflicts

        jobs = [_job("a", schedule=ONCE), _job("b", schedule=dict(ONCE))]
        assert find_conflicts(jobs) == []

    def test_workdir_overlap_within_window(self):
        from automation.conflicts import find_conflicts

        t0 = "2026-08-23T09:00:00+00:00"
        t1 = "2026-08-23T09:01:30+00:00"
        far = "2026-08-23T15:00:00+00:00"
        jobs = [
            _job("a", schedule=INTERVAL_60, workdir="/repo", next_run_at=t0),
            _job("b", schedule=INTERVAL_60, workdir="/repo", next_run_at=t1),
            _job("c", schedule=INTERVAL_60, workdir="/repo", next_run_at=far),
            _job("d", schedule=INTERVAL_60, workdir="/other", next_run_at=t0),
        ]
        conflicts = [c for c in find_conflicts(jobs) if c["kind"] == "workdir_overlap"]
        assert len(conflicts) == 1
        assert sorted(conflicts[0]["refs"]) == ["a", "b"]

    def test_event_fanout_detected_only_for_unfiltered_triggers(self):
        from automation.conflicts import find_conflicts

        unfiltered = {"kind": "event", "event_types": ["file.created"]}
        filtered = {
            "kind": "event",
            "event_types": ["file.created"],
            "filters": [{"path": "payload.root", "op": "eq", "value": "/x"}],
        }
        jobs = [
            _job("a", trigger=dict(unfiltered)),
            _job("b", trigger=dict(unfiltered)),
            _job("c", trigger=filtered),
        ]
        fanouts = [c for c in find_conflicts(jobs) if c["kind"] == "event_fanout"]
        assert len(fanouts) == 1
        assert sorted(fanouts[0]["refs"]) == ["a", "b"]

    def test_disabled_and_quarantined_excluded(self):
        from automation.conflicts import find_conflicts

        jobs = [
            _job("a", schedule=CRON_9),
            _job("b", schedule=dict(CRON_9), enabled=False),
            _job("c", schedule=dict(CRON_9), quarantined=True),
        ]
        assert find_conflicts(jobs) == []

    def test_conflicts_for_filters_to_one_ref(self):
        from automation.conflicts import conflicts_for, find_conflicts

        jobs = [_job("a", schedule=CRON_9), _job("b", schedule=dict(CRON_9))]
        all_conflicts = find_conflicts(jobs)
        assert all_conflicts
        mine = conflicts_for("a", jobs)
        assert mine == all_conflicts
        assert conflicts_for("zzz", jobs) == []
