"""Tests for the Jarvis runtime lifecycle (aetheros_jarvis.runtime)."""


from aetheros_jarvis.models import JarvisState
from aetheros_jarvis.runtime import JarvisRuntime


class FakeSubsystem:
    def __init__(self, name="sub", healthy=True):
        self.name = name
        self.calls = []
        self._healthy = healthy

    def initialize(self):
        self.calls.append("initialize")

    def sleep(self):
        self.calls.append("sleep")

    def wake(self):
        self.calls.append("wake")

    def pause(self):
        self.calls.append("pause")

    def resume(self):
        self.calls.append("resume")

    def shutdown(self):
        self.calls.append("shutdown")

    def health_check(self):
        return self._healthy


class TestRuntimeLifecycle:
    def test_default_state_is_stopped(self):
        rt = JarvisRuntime()
        assert rt.state == JarvisState.STOPPED

    def test_initialize_runs_and_enters_running(self):
        rt = JarvisRuntime()
        sub = FakeSubsystem()
        rt.register(sub)
        assert rt.initialize() is True
        assert rt.state == JarvisState.RUNNING
        assert rt.is_running
        assert sub.calls == ["initialize"]

    def test_initialize_twice_is_rejected(self):
        rt = JarvisRuntime()
        rt.initialize()
        assert rt.initialize() is False

    def test_full_state_cycle(self):
        rt = JarvisRuntime()
        sub = FakeSubsystem()
        rt.register(sub)
        rt.initialize()
        assert rt.sleep() is True
        assert rt.state == JarvisState.SLEEPING
        assert rt.wake() is True
        assert rt.state == JarvisState.RUNNING
        assert rt.pause() is True
        assert rt.state == JarvisState.PAUSED
        assert rt.resume() is True
        assert rt.state == JarvisState.RUNNING
        assert rt.shutdown() is True
        assert rt.state == JarvisState.SHUTDOWN

    def test_hooks_called_in_order_per_transition(self):
        rt = JarvisRuntime()
        sub = FakeSubsystem()
        rt.register(sub)
        rt.initialize()
        rt.sleep()
        rt.wake()
        rt.pause()
        rt.resume()
        rt.shutdown()
        assert sub.calls == [
            "initialize",
            "sleep",
            "wake",
            "pause",
            "resume",
            "shutdown",
        ]

    def test_sleep_requires_running(self):
        rt = JarvisRuntime()
        assert rt.sleep() is False
        rt.initialize()
        rt.shutdown()
        assert rt.shutdown() is False

    def test_state_listeners_notified(self):
        rt = JarvisRuntime()
        transitions = []
        rt.on_state_change(lambda old, new: transitions.append((old, new)))
        rt.initialize()
        rt.sleep()
        assert (JarvisState.RUNNING, JarvisState.SLEEPING) in transitions
        assert (JarvisState.STOPPED, JarvisState.INITIALIZING) in transitions


class TestRuntimeHealth:
    def test_health_check_reports_all_subsystems(self):
        rt = JarvisRuntime()
        rt.register(FakeSubsystem("a", healthy=True))
        rt.register(FakeSubsystem("b", healthy=True))
        rt.initialize()
        health = rt.check_health()
        assert health == {"a": True, "b": True}
        assert rt.healthy

    def test_unhealthy_subsystem_flips_state_to_error(self):
        rt = JarvisRuntime()
        rt.register(FakeSubsystem("bad", healthy=False))
        rt.initialize()
        rt.check_health()
        assert rt.state == JarvisState.ERROR
        assert not rt.healthy
        assert "unhealthy" in rt.diagnostics()["error"]

    def test_recover_reinitializes_failed_subsystem(self):
        rt = JarvisRuntime()
        sub = FakeSubsystem("flaky", healthy=False)
        rt.register(sub)
        rt.initialize()
        rt.check_health()
        assert rt.state == JarvisState.ERROR
        sub._healthy = True
        assert rt.recover() is True
        assert rt.state == JarvisState.RUNNING
        assert "initialize" in sub.calls

    def test_recover_incomplete_stays_error(self):
        rt = JarvisRuntime()
        rt.register(FakeSubsystem("still-bad", healthy=False))
        rt.initialize()
        rt.check_health()
        assert rt.recover() is False
        assert rt.state == JarvisState.ERROR


class TestRuntimeDiagnostics:
    def test_diagnostics_shape(self):
        rt = JarvisRuntime()
        rt.register(FakeSubsystem("wake", healthy=True))
        rt.initialize()
        diag = rt.diagnostics()
        assert diag["state"] == "running"
        assert diag["healthy"] is True
        assert diag["subsystems"] == ["wake"]
        assert diag["uptime_seconds"] >= 0

    def test_wake_sources_tracked(self):
        rt = JarvisRuntime()
        rt.register(FakeSubsystem("wake_word"), wake_source=True)
        rt.register(FakeSubsystem("voice"), wake_source=False)
        rt.initialize()
        assert rt.diagnostics()["wake_sources"] == ["wake_word"]

    def test_runtime_ignores_subsystems_without_hooks(self):
        class Bare:
            name = "bare"

        rt = JarvisRuntime()
        rt.register(Bare())
        rt.initialize()
        assert rt.state == JarvisState.RUNNING
