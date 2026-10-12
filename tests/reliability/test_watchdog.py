"""Tests for the watchdog: heartbeat-staleness detection, backoff, crash-loop."""

import time

from aetheros_reliability.events import RecoveryEventStore
from aetheros_reliability.heartbeat import HeartbeatRegistry
from aetheros_reliability.states import RecoveryState
from aetheros_reliability.watchdog import AetherOSWatchdog, ComponentMonitor


def _make_watchdog():
    return AetherOSWatchdog(
        heartbeat_registry=HeartbeatRegistry(),
        event_store=RecoveryEventStore(),
    )


class TestWatchdog:
    def test_healthy_component_no_failure(self):
        wd = _make_watchdog()
        wd._heartbeats.beat("gateway")
        wd.watch(ComponentMonitor(component_id="gateway", heartbeat_timeout=60))
        wd.tick()
        assert wd.components()["gateway"]["restart_count"] == 0

    def test_stale_component_triggers_restart(self, monkeypatch):
        wd = _make_watchdog()
        restarts = []
        wd._heartbeats.beat("gateway")
        fake = {"now": time.time() + 999}

        def clock():
            return fake["now"]

        monkeypatch.setattr(time, "time", clock)
        mon = ComponentMonitor(
            component_id="gateway",
            heartbeat_timeout=30,
            restart_fn=lambda cid, ctx: (restarts.append(cid), "ok")[1],
            backoff_base=0,
            backoff_max=0,
            backoff_jitter=0,
        )
        wd.watch(mon)
        # Simulate heartbeat going stale.
        fake["now"] = fake["now"] + 1000
        wd._check_one(mon)
        assert restarts == ["gateway"]
        assert wd.components()["gateway"]["restart_count"] == 1

    def test_crash_loop_stops_restart(self, monkeypatch):
        wd = _make_watchdog()
        restarts = []
        wd._heartbeats.beat("gateway")
        fake = {"now": time.time() + 999}

        def clock():
            return fake["now"]

        monkeypatch.setattr(time, "time", clock)
        mon = ComponentMonitor(
            component_id="gateway",
            heartbeat_timeout=30,
            restart_fn=lambda cid, ctx: (restarts.append(cid), "ok")[1],
            backoff_base=0,
            backoff_max=0,
            backoff_jitter=0,
            max_restarts=2,
        )
        wd.watch(mon)
        for _ in range(4):
            fake["now"] += 1000
            wd._check_one(mon)
        # max_restarts=2 means after 2 restarts we detect crash-looping.
        assert len(restarts) <= 2
        assert wd.components()["gateway"]["crash_looping"] is True
        assert "gateway" in wd.status()["crash_loops"]

    def test_backoff_grows_and_caps(self):
        wd = _make_watchdog()
        mon = ComponentMonitor(
            component_id="x",
            backoff_base=2.0,
            backoff_max=10.0,
            backoff_jitter=0,
        )
        assert wd._backoff(mon, 1) == 2.0
        assert wd._backoff(mon, 2) == 4.0
        assert wd._backoff(mon, 3) == 8.0
        # capped
        assert wd._backoff(mon, 10) == 10.0

    def test_backoff_jitter_adds_variation(self, monkeypatch):
        wd = _make_watchdog()
        monkeypatch.setattr("aetheros_reliability.watchdog.random.uniform",
                            lambda a, b: b)
        mon = ComponentMonitor(
            component_id="x",
            backoff_base=2.0,
            backoff_max=100.0,
            backoff_jitter=0.5,
        )
        # jitter upper bound = base * jitter
        assert wd._backoff(mon, 1) == 2.0 + 2.0 * 0.5

    def test_health_probe_failure_detected(self):
        wd = _make_watchdog()
        restarts = []
        wd.watch(ComponentMonitor(
            component_id="backend",
            health_fn=lambda: ("unhealthy", "db down"),
            restart_fn=lambda cid, ctx: (restarts.append(cid), "ok")[1],
            backoff_base=0,
            backoff_max=0,
            backoff_jitter=0,
        ))
        wd.tick()
        assert restarts == ["backend"]

    def test_reset_component(self):
        wd = _make_watchdog()
        mon = ComponentMonitor(component_id="gateway", max_restarts=1)
        wd.watch(mon)
        mon.crash_looping = True
        assert wd.components()["gateway"]["crash_looping"] is True
        wd.reset_component("gateway")
        assert wd.components()["gateway"]["crash_looping"] is False

    def test_start_stop_idempotent(self):
        wd = _make_watchdog()
        wd.start(interval=1.0)
        assert wd.running
        wd.start(interval=1.0)  # idempotent
        wd.stop()
        assert not wd.running
        wd.stop()  # idempotent

    def test_event_recorded_on_failure(self, monkeypatch):
        wd = _make_watchdog()
        wd._heartbeats.beat("gateway")
        fake = {"now": time.time() + 999}
        monkeypatch.setattr(time, "time", lambda: fake["now"])
        mon = ComponentMonitor(
            component_id="gateway",
            heartbeat_timeout=30,
            restart_fn=lambda cid, ctx: "ok",
            backoff_base=0,
            backoff_max=0,
            backoff_jitter=0,
        )
        wd.watch(mon)
        fake["now"] += 1000
        wd._check_one(mon)
        recent = wd._events.recent()
        assert len(recent) == 1
        assert recent[0]["componentId"] == "gateway"
        assert recent[0]["action"] == "restart"
