"""Tests for aetheros_observability health + readiness + degraded mode."""

from aetheros_observability.health import (
    HealthService,
    HealthState,
    get_health_service,
)


class TestHealthService:
    def test_register_and_check(self):
        svc = HealthService()
        svc.register("terminal", lambda: (HealthState.HEALTHY, "ok"))
        result = svc.check("terminal")
        assert result.state == HealthState.HEALTHY
        assert result.is_healthy

    def test_check_failure(self):
        svc = HealthService()

        def failing():
            raise RuntimeError("boom")

        svc.register("model", failing)
        result = svc.check("model")
        assert result.state == HealthState.UNHEALTHY
        assert "boom" in result.message

    def test_check_unregistered(self):
        svc = HealthService()
        result = svc.check("nope")
        assert result.state == HealthState.UNKNOWN

    def test_liveness(self):
        svc = HealthService()
        live = svc.liveness()
        assert live["status"] == "alive"
        assert live["uptime_seconds"] >= 0

    def test_readiness_healthy(self):
        svc = HealthService()
        svc.register("storage", lambda: (HealthState.HEALTHY, "ok"))
        ready = svc.readiness()
        assert ready["ready"] is True
        assert ready["components"]["storage"] == "healthy"

    def test_readiness_unhealthy(self):
        svc = HealthService()

        def failing():
            raise RuntimeError("disk full")

        svc.register("storage", failing)
        ready = svc.readiness()
        assert ready["ready"] is False
        assert ready["status"] == "unhealthy"

    def test_degraded_override(self):
        svc = HealthService()
        svc.register("storage", lambda: (HealthState.HEALTHY, "ok"))
        svc.set_degraded("storage", "read-only disk")
        result = svc.check("storage")
        assert result.state == HealthState.DEGRADED
        svc.clear_degraded("storage")
        assert svc.check("storage").state == HealthState.HEALTHY

    def test_summary_has_status_and_components(self):
        svc = HealthService()
        svc.register("memory", lambda: (HealthState.HEALTHY, "ok"))
        summary = svc.summary()
        assert "status" in summary
        assert "components" in summary
        assert summary["components"]["memory"]["state"] == "healthy"

    def test_dependency_propagation_degrades_dependent(self):
        svc = HealthService()
        svc.register("STORAGE", lambda: (HealthState.HEALTHY, "ok"))

        def failing():
            raise RuntimeError("down")

        svc.register("MEMORY", failing)
        svc.register("AGENT_RUNTIME", lambda: (HealthState.HEALTHY, "ok"))
        results = svc.check_all()
        states = {r.component: r.state for r in results}
        # memory unhealthy; agent_runtime (depends on memory) degraded
        assert states["MEMORY"] == HealthState.UNHEALTHY
        assert states["AGENT_RUNTIME"] == HealthState.DEGRADED


class TestSingleton:
    def test_get_health_service_is_singleton(self):
        assert get_health_service() is get_health_service()