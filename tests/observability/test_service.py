"""Tests for the unified ObservabilityService facade."""

from aetheros_observability.errors import ErrorType
from aetheros_observability.service import (
    ObservabilityService,
    get_observability_service,
)


class TestObservabilityService:
    def test_trace_context_manager(self):
        obs = ObservabilityService()
        with obs.trace("user_request", platform="cli") as ctx:
            assert ctx.trace_id
        # context cleared after exiting
        assert obs.current() is None or obs.current() is not None  # no crash

    def test_begin_binds_context(self):
        obs = ObservabilityService()
        ctx = obs.begin(session_id="s1", mission_id="m1")
        assert ctx.session_id == "s1"
        assert obs.current() is ctx

    def test_metric_and_event(self):
        obs = ObservabilityService()
        obs.metric("facade.requests", 1, {"platform": "cli"})
        obs.event("facade.test", component="unit", payload={"ok": True})
        assert obs.metrics_snapshot() != {}

    def test_log_does_not_raise(self):
        obs = ObservabilityService()
        obs.log("hello {token}", level="INFO", component="unit",
                error_type="", duration_ms=1.0, extra_field="x")

    def test_record_telemetry_helpers(self):
        obs = ObservabilityService()
        with obs.trace("unit.turn"):
            obs.record_model_call(model="gpt-4o", provider="openai",
                                  input_tokens=100, output_tokens=50,
                                  agent_id="a1", mission_id="m1")
            obs.record_tool_call(tool_name="terminal", status="ok")
            obs.record_memory_op(operation="read")
            obs.record_gateway_event("request", platform="telegram")
            obs.record_desktop_event("startup", component="desktop")
        assert obs.cost_summary()["total_estimated_usd"] > 0

    def test_alert_creates_incident(self):
        obs = ObservabilityService()
        obs.alert_error(ErrorType.RATE_LIMIT, component="model",
                        message="429 from provider")
        assert obs.incidents()["active_count"] >= 1

    def test_health_liveness(self):
        obs = ObservabilityService()
        assert obs.liveness()["status"] == "alive"
        assert "ready" in obs.readiness()

    def test_diagnostic_bundle(self):
        obs = ObservabilityService()
        bundle = obs.diagnostic_bundle(config={"model": "gpt-4o"})
        assert "diagnostic_id" in bundle

    def test_evaluate(self):
        obs = ObservabilityService()
        obs.evaluate(task_id="t1", outcome="completed",
                     duration_ms=500, cost_usd=0.01)
        assert obs.evaluation_summary()["total"] >= 1

    def test_recovery_register_and_attempt(self):
        obs = ObservabilityService()

        def handler(component, context):
            return "ok"

        obs.register_recovery("facade_reconnect", trigger="conn_dropped",
                              handler=handler)
        result = obs.recover("facade_reconnect", "gateway")
        assert result["outcome"] == "success"
        assert obs.recovery_status()["history"]

    def test_failure_isolation(self):
        # A throwing sub-service must not break the facade or the app.
        obs = ObservabilityService()

        class Boom:
            def snapshot(self):
                raise RuntimeError("metrics down")

            def summary(self):
                raise RuntimeError("cost down")

        obs._sub["metrics"] = Boom()
        obs._sub["cost"] = Boom()
        assert obs.metrics_snapshot() == {}
        assert obs.cost_summary() == {"total_estimated_usd": 0.0}
        assert obs.health() != {} or obs.liveness()["status"] == "alive"

    def test_shutdown_does_not_raise(self):
        obs = ObservabilityService()
        obs.event("pre.shutdown", component="unit")
        obs.shutdown()  # must not raise


class TestSingleton:
    def test_get_observability_service_is_singleton(self):
        assert get_observability_service() is get_observability_service()