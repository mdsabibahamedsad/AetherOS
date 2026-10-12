"""
AetherOS Production Module
==========================

Production-readiness, reliability, and operational excellence framework.

This package provides comprehensive production-grade tooling for:
- Performance optimization and profiling
- Benchmarking and regression testing
- Health monitoring and diagnostics
- Telemetry, metrics, and distributed tracing
- Release engineering and migration validation
- Stress and chaos testing
- Compatibility checking

Every module builds on existing Aetheros infrastructure (kernel, cluster,
enterprise, SDK) without replacing it — backward compatibility is preserved.

Usage:
    from production import (
        run_benchmarks,
        run_diagnostics,
        check_health,
        run_profiler,
        validate_release,
    )

    # Run production diagnostics
    report = run_diagnostics()
    print(report)

    # Check system health
    health_status = check_health()
    print(health_status)
"""

from production.optimizer import (
    Optimizer,
    OptimizationResult,
    OptimizationCategory,
)
from production.profiler import (
    Profiler,
    ProfileResult,
    ProfileReport,
    CpuProfiler,
    MemoryProfiler,
    IoProfiler,
)
from production.benchmark import (
    BenchmarkRunner,
    BenchmarkResult,
    BenchmarkSuite,
    run_benchmarks,
)
from production.diagnostics import (
    DiagnosticsEngine,
    DiagnosticReport,
    DiagnosticCheck,
    run_diagnostics,
)
from production.health import (
    HealthChecker,
    HealthStatus,
    HealthReport,
    check_health,
)
from production.maintenance import (
    MaintenanceEngine,
    MaintenanceTask,
    MaintenanceReport,
    run_maintenance,
)
from production.telemetry import (
    TelemetryPipeline,
    TelemetryEvent,
    TelemetryExporter,
)
from production.tracing import (
    Tracer,
    Span,
    TraceContext,
    TraceReport,
)
from production.metrics import (
    MetricsCollector,
    MetricPoint,
    MetricsSnapshot,
)
from production.release_manager import (
    ReleaseManager,
    ReleaseArtifact,
    ReleaseReport,
)
from production.migration_validator import (
    MigrationValidator,
    MigrationReport,
    MigrationCheck,
)
from production.compatibility_checker import (
    CompatibilityChecker,
    CompatibilityReport,
)
from production.regression import (
    RegressionTester,
    RegressionSuite,
    RegressionReport,
)
from production.stress_testing import (
    StressTester,
    StressScenario,
    StressReport,
)
from production.chaos_testing import (
    ChaosTester,
    ChaosExperiment,
    ChaosReport,
)
from production.release_validation import (
    ReleaseValidator,
    ValidationResult,
    ValidationReport,
    validate_release,
)

__all__ = [
    # Optimizer
    "Optimizer", "OptimizationResult", "OptimizationCategory",
    # Profiler
    "Profiler", "ProfileResult", "ProfileReport",
    "CpuProfiler", "MemoryProfiler", "IoProfiler",
    # Benchmark
    "BenchmarkRunner", "BenchmarkResult", "BenchmarkSuite", "run_benchmarks",
    # Diagnostics
    "DiagnosticsEngine", "DiagnosticReport", "DiagnosticCheck", "run_diagnostics",
    # Health
    "HealthChecker", "HealthStatus", "HealthReport", "check_health",
    # Maintenance
    "MaintenanceEngine", "MaintenanceTask", "MaintenanceReport", "run_maintenance",
    # Telemetry
    "TelemetryPipeline", "TelemetryEvent", "TelemetryExporter",
    # Tracing
    "Tracer", "Span", "TraceContext", "TraceReport",
    # Metrics
    "MetricsCollector", "MetricPoint", "MetricsSnapshot",
    # Release
    "ReleaseManager", "ReleaseArtifact", "ReleaseReport",
    # Migration
    "MigrationValidator", "MigrationReport", "MigrationCheck",
    # Compatibility
    "CompatibilityChecker", "CompatibilityReport",
    # Regression
    "RegressionTester", "RegressionSuite", "RegressionReport",
    # Stress
    "StressTester", "StressScenario", "StressReport",
    # Chaos
    "ChaosTester", "ChaosExperiment", "ChaosReport",
    # Release Validation
    "ReleaseValidator", "ValidationResult", "ValidationReport", "validate_release",
]
