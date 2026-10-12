"""Tests for aetheros_production.quality and observability singletons."""

import pytest

from aetheros_production.observability import (
    HealthChecker,
    get_crash_reporter,
    get_diagnostics_manager,
    get_health_checker,
    get_metrics_registry,
    get_tracer,
)
from aetheros_production import quality as quality_module

QualityManager = quality_module.QualityManager


class TestQualityManager:
    def test_run_smoke_suite(self):
        qm = QualityManager()
        result = qm.run_suite("smoke")
        assert result["total"] == 4
        assert result["passed"] == 4
        for t in result["tests"]:
            assert t.status == quality_module.TestStatus.PASSED

    def test_run_unknown_suite(self):
        qm = QualityManager()
        result = qm.run_suite("does-not-exist")
        assert "error" in result

    def test_run_test_returns_error_for_unknown(self):
        qm = QualityManager()
        result = qm.run_test("nope")
        assert result.status == quality_module.TestStatus.ERROR

    def test_summary(self):
        qm = QualityManager()
        qm.run_suite("smoke")
        summary = qm.get_summary()
        assert summary["total"] >= 4
        assert summary["passed"] == summary["total"]


class TestObservabilitySingletons:
    def test_singletons(self):
        assert get_health_checker() is get_health_checker()
        assert get_metrics_registry() is get_metrics_registry()
        assert get_tracer() is get_tracer()
        assert get_crash_reporter() is get_crash_reporter()
        assert get_diagnostics_manager() is get_diagnostics_manager()

    def test_health_checker(self):
        checker = HealthChecker()
        status = checker.get_full_health_status()
        assert "status" in status
        assert "components" in status
