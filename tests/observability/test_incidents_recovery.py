"""Tests for aetheros_observability incidents + recovery."""

from aetheros_observability.incidents import (
    AlertSeverity,
    IncidentDetector,
    IncidentState,
    ThresholdRule,
    get_incident_detector,
)
from aetheros_observability.recovery import (
    RecoveryOutcome,
    RecoveryPolicy,
    RecoveryService,
    get_recovery_service,
)


class TestIncidentDetector:
    def test_record_error_creates_incident(self):
        det = IncidentDetector()
        incident = det.record_error(error_type="RATE_LIMIT", component="model",
                                    message="429 again")
        assert incident is not None
        assert incident.key == "error:RATE_LIMIT:model"
        assert incident.count == 1

    def test_dedup_same_key(self):
        det = IncidentDetector()
        det.record_error(error_type="RATE_LIMIT", component="model")
        incident2 = det.record_error(error_type="RATE_LIMIT", component="model")
        assert incident2.count == 2
        assert len(det.active_incidents()) == 1

    def test_active_incidents(self):
        det = IncidentDetector()
        det.record_error(error_type="TOOL_ERROR", component="terminal",
                         message="tool crashed")
        summary = det.summary()
        assert summary["active_count"] == 1

    def test_resolve(self):
        det = IncidentDetector()
        inc = det.record_error(error_type="TOOL_ERROR", component="terminal")
        assert det.resolve(inc.key) is True
        assert det.active_incidents() == []
        assert len(det.resolved_incidents()) == 1

    def test_acknowledge(self):
        det = IncidentDetector()
        inc = det.record_error(error_type="TOOL_ERROR", component="terminal")
        assert det.acknowledge(inc.key) is True

    def test_security_event_high_severity(self):
        det = IncidentDetector()
        inc = det.record_security_event("auth_failure", message="brute force")
        assert inc is not None
        assert inc.severity in (
            AlertSeverity.ERROR, AlertSeverity.CRITICAL,
            AlertSeverity.SECURITY_CRITICAL)

    def test_threshold_rule_fires(self):
        det = IncidentDetector()
        det.add_rule(ThresholdRule(
            name="err_spike", metric="error_count", threshold=3,
            window_seconds=60, severity=AlertSeverity.ERROR))
        for _ in range(3):
            det.record_error(error_type="RATE_LIMIT", component="model")
        assert len(det.active_incidents()) >= 1


class TestRecoveryService:
    def _service(self):
        svc = RecoveryService()

        def restart_handler(component, context):
            return "restarted ok"

        svc.register("restart_service",
                     RecoveryPolicy(action="restart_service",
                                    trigger="service crashed"),
                     restart_handler)
        return svc

    def test_register_and_attempt_success(self):
        svc = self._service()
        result = svc.attempt("restart_service", "gateway")
        assert result.outcome == RecoveryOutcome.SUCCESS
        assert result.message == "restarted ok"

    def test_failed_handler(self):
        svc = RecoveryService()

        def failing(component, context):
            raise RuntimeError("cannot restart")

        svc.register("restart_service",
                     RecoveryPolicy(action="restart_service", trigger="x"),
                     failing)
        result = svc.attempt("restart_service", "gateway")
        assert result.outcome == RecoveryOutcome.FAILED

    def test_can_recover_unknown(self):
        svc = RecoveryService()
        assert svc.can_recover("does_not_exist") is False

    def test_exhausts_after_max_attempts(self):
        svc = RecoveryService()

        def failing(component, context):
            raise RuntimeError("still down")

        svc.register("flaky",
                     RecoveryPolicy(action="flaky", trigger="x",
                                    max_attempts=2, cooldown_seconds=0),
                     failing)
        r1 = svc.attempt("flaky", "svc")
        # Both attempts fail; the third attempt is refused as exhausted.
        svc.attempt("flaky", "svc")
        r3 = svc.attempt("flaky", "svc")
        assert r1.outcome == RecoveryOutcome.FAILED
        assert r3.outcome == RecoveryOutcome.EXHAUSTED
        assert svc.get_status("flaky") is not None

    def test_history_and_audit(self):
        svc = self._service()
        svc.attempt("restart_service", "gateway")
        assert len(svc.history()) >= 1
        assert len(svc.audit_log()) >= 1

    def test_crash_loop_detection(self):
        svc = RecoveryService()

        def failing(component, context):
            raise RuntimeError("down")

        svc.register("loop",
                     RecoveryPolicy(action="loop", trigger="x",
                                    max_attempts=3, cooldown_seconds=0),
                     failing)
        for _ in range(4):
            svc.attempt("loop", "svc")
        assert svc.is_crash_loop("loop") is True


class TestSingletons:
    def test_incident_singleton(self):
        assert get_incident_detector() is get_incident_detector()

    def test_recovery_singleton(self):
        assert get_recovery_service() is get_recovery_service()