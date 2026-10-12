"""Tests for presence detection and performance guard (aetheros_jarvis)."""

import time


from aetheros_jarvis.models import PresenceState
from aetheros_jarvis.performance import PerformanceGuard
from aetheros_jarvis.presence import PresenceDetector


class TestPresenceDetector:
    def test_default_active(self):
        det = PresenceDetector()
        assert det.state == PresenceState.ACTIVE
        assert det.is_available()

    def test_explicit_lock_and_unlock(self):
        det = PresenceDetector()
        det.report_lock()
        assert det.state == PresenceState.LOCKED
        assert not det.is_available()
        det.report_unlock()
        assert det.state == PresenceState.ACTIVE

    def test_explicit_sleep_and_wake(self):
        det = PresenceDetector()
        det.report_sleep()
        assert det.state == PresenceState.SLEEPING
        assert not det.is_available()
        det.report_wake()
        assert det.state == PresenceState.ACTIVE

    def test_explicit_away(self):
        det = PresenceDetector()
        det.report_away(True)
        assert det.state == PresenceState.AWAY
        assert not det.is_available()
        det.report_away(False)
        assert det.state == PresenceState.ACTIVE

    def test_idle_derivation(self):
        det = PresenceDetector(idle_after_seconds=0.05, away_after_seconds=0.1)
        assert det.state == PresenceState.ACTIVE
        time.sleep(0.07)
        assert det.state == PresenceState.IDLE
        assert det.is_available()  # idle still present
        time.sleep(0.06)
        assert det.state == PresenceState.AWAY

    def test_mark_activity_resets_idle(self):
        det = PresenceDetector(idle_after_seconds=0.05, away_after_seconds=0.1)
        time.sleep(0.07)
        assert det.state == PresenceState.IDLE
        det.mark_activity()
        assert det.state == PresenceState.ACTIVE

    def test_change_listener(self):
        det = PresenceDetector()
        transitions = []
        det.on_change(lambda old, new: transitions.append((old, new)))
        det.report_lock()
        assert transitions == [(PresenceState.ACTIVE, PresenceState.LOCKED)]

    def test_snapshot(self):
        det = PresenceDetector()
        snap = det.snapshot()
        assert snap["state"] == "active"
        assert "idle_seconds" in snap
        assert "idle_after" in snap


class TestPerformanceGuard:
    def test_proactive_cooldown_gate(self):
        guard = PerformanceGuard()
        assert guard.should_run_proactive("scan") is True
        assert guard.should_run_proactive("scan") is False

    def test_throttle_respects_interval(self):
        guard = PerformanceGuard()
        assert guard.throttle("kind", 1.0) is True
        assert guard.throttle("kind", 1.0) is False

    def test_different_kinds_are_independent(self):
        guard = PerformanceGuard()
        assert guard.should_run_proactive("a")
        assert guard.should_run_proactive("b")

    def test_set_limits(self):
        guard = PerformanceGuard()
        guard.set_limits({"proactive_min_interval_seconds": 0.1})
        assert guard._limits["proactive_min_interval_seconds"] == 0.1
        assert guard.should_run_proactive("x")
        assert guard.should_run_proactive("x") is False
        time.sleep(0.15)
        assert guard.should_run_proactive("x")

    def test_battery_api_returns_none_or_number(self):
        guard = PerformanceGuard()
        percent = guard.battery_percent()
        assert percent is None or 0 <= percent <= 100

    def test_snapshot_shape(self):
        guard = PerformanceGuard()
        snap = guard.snapshot()
        assert "on_battery" in snap
        assert "can_run_background" in snap
        assert isinstance(snap["can_run_background"], bool)
        assert "limits" in snap
