"""
CLI subcommand parsers for ``aetheros <benchmark|profile|diagnostics|health|verify|migrate-check>``.

Wires into the existing ``aetheros_cli/main.py`` argparse tree via
normal builder functions.

Backward compatible: all handlers are dependency-injected so these
modules never import ``main``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def _pp_json(data: Any) -> None:
    """Pretty-print JSON data."""
    print(json.dumps(data, indent=2, default=str))


def _print_section(title: str) -> None:
    """Print a section header."""
    print()
    print("━" * 60)
    print(f"  {title}")
    print("━" * 60)


def _print_check(name: str, passed: bool, detail: str = "") -> None:
    """Print a check result."""
    symbol = "✓" if passed else "✗"
    print(f"  {symbol} {name}" + (f"  ({detail})" if detail else ""))


# =========================================================================
# aetheros benchmark
# =========================================================================

def build_benchmark_parser(subparsers, *, cmd_benchmark: Callable) -> None:
    """Build ``aetheros benchmark`` subcommand."""
    parser = subparsers.add_parser(
        "benchmark",
        help="Run performance benchmarks",
        description="Run benchmark suites to measure AetherOS performance",
    )
    parser.add_argument(
        "suite",
        nargs="?",
        default="all",
        choices=["all", "startup", "memory", "workflow", "plugins"],
        help="Benchmark suite to run (default: all)",
    )
    parser.add_argument(
        "--iterations", type=int, default=5,
        help="Number of iterations per benchmark (default: 5)",
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="Directory for JSON result output",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.set_defaults(func=cmd_benchmark)


def handle_benchmark(args: Any) -> int:
    """Handler for ``aetheros benchmark``."""
    from production.benchmark import BenchmarkRunner, BenchmarkSuite, run_benchmarks

    output_dir = args.output or "/tmp/aetheros-benchmarks"
    json_only = getattr(args, "json", False)

    suites = run_benchmarks(output_dir=output_dir)

    for suite in suites:
        if json_only:
            print(suite.to_json())
        else:
            _print_section(f"Benchmark Suite: {suite.name}")
            print(f"  Description: {suite.description}")
            print(f"  Duration: {suite.total_duration:.2f}s")
            print(f"  Benchmarks: {len(suite.benchmarks)}")
            print(f"  Passed: {suite.success_count}")
            print(f"  Failed: {suite.failure_count}")

            for b in suite.benchmarks:
                status = "✓" if b.success else "✗"
                print(f"\n  {status} {b.name}")
                if b.duration_seconds:
                    print(f"      Duration: {b.duration_seconds:.3f}s")
                for key, value in b.metrics.items():
                    print(f"      {key}: {value}")
                if not b.success and b.error:
                    print(f"      Error: {b.error}")

    return 0 if all(s.success_count == len(s.benchmarks) for s in suites) else 1


# =========================================================================
# aetheros profile (system profiling)
# =========================================================================

def build_profile_parser(subparsers, *, cmd_profile: Callable) -> None:
    """Build ``aetheros profile`` subcommand (profiling, not user profiles)."""
    parser = subparsers.add_parser(
        "profile",
        help="Run system profiler",
        description="Profile CPU, memory, and I/O usage",
    )
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "cpu", "memory", "io"],
        help="Profile type (default: all)",
    )
    parser.add_argument(
        "--duration", type=float, default=5.0,
        help="Profiling duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.set_defaults(func=cmd_profile)


def handle_profile(args: Any) -> int:
    """Handler for ``aetheros profile`` (system profiling)."""
    from production.profiler import Profiler

    profiler = Profiler()
    json_only = getattr(args, "json", False)

    profile_type = args.type
    duration = args.duration

    if profile_type == "all":
        report = profiler.profile_all(duration=duration)
    elif profile_type == "cpu":
        result = profiler.profile_cpu(duration)
        from production.profiler import ProfileReport
        report = ProfileReport(profiler="cpu")
        report.add_result(result)
    elif profile_type == "memory":
        result = profiler.profile_memory()
        from production.profiler import ProfileReport
        report = ProfileReport(profiler="memory")
        report.add_result(result)
    elif profile_type == "io":
        result = profiler.profile_io(duration)
        from production.profiler import ProfileReport
        report = ProfileReport(profiler="io")
        report.add_result(result)
    else:
        print(f"Unknown profile type: {profile_type}")
        return 1

    if json_only:
        print(report.to_json() if hasattr(report, 'to_json') else json.dumps(report.to_dict(), indent=2))
    else:
        _print_section("Profiling Results")
        for result in report.results:
            print(f"\n  Type: {result.profile_type.value}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            for key, value in result.summary.items():
                print(f"    {key}: {value}")
            if result.bottlenecks:
                print(f"  Bottlenecks ({len(result.bottlenecks)}):")
                for b in result.bottlenecks:
                    print(f"    [{b.get('severity', 'info')}] {b.get('message', '')}")
            if result.recommendations:
                print(f"  Recommendations:")
                for r in result.recommendations:
                    print(f"    - {r}")

    return 0


# =========================================================================
# aetheros diagnostics
# =========================================================================

def build_diagnostics_parser(subparsers, *, cmd_diagnostics: Callable) -> None:
    """Build ``aetheros diagnostics`` subcommand."""
    parser = subparsers.add_parser(
        "diagnostics",
        help="Run system diagnostics",
        description="Comprehensive system diagnostics for AetherOS",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.add_argument(
        "--severity", choices=["info", "ok", "warning", "error", "critical"],
        default=None,
        help="Only show checks at or above this severity",
    )
    parser.set_defaults(func=cmd_diagnostics)


def handle_diagnostics(args: Any) -> int:
    """Handler for ``aetheros diagnostics``."""
    from production.diagnostics import run_diagnostics, CheckSeverity

    json_only = getattr(args, "json", False)
    severity_filter = getattr(args, "severity", None)

    report = run_diagnostics()

    if json_only:
        print(json.dumps(report.to_dict(), indent=2, default=str))
        return 0

    _print_section("System Diagnostics")
    print(f"  Hostname: {report.hostname}")
    print(f"  Platform: {report.platform}")
    print(f"  Python: {report.python_version}")
    print(f"  AetherOS: {report.aetheros_version}")
    print(f"  Uptime: {report.uptime_seconds:.0f}s")

    _print_section(f"Checks ({len(report.checks)} total)")
    for check in report.checks:
        if severity_filter:
            severity_order = {"info": 0, "ok": 1, "warning": 2, "error": 3, "critical": 4}
            if severity_order.get(check.severity.value, 0) < severity_order.get(severity_filter, 0):
                continue

        _print_check(
            f"[{check.severity.value.upper():>8}] {check.name}",
            check.passed,
            check.message,
        )
        if not check.passed and check.recommendation:
            print(f"           Recommendation: {check.recommendation}")

    _print_section("Summary")
    print(f"  Health Score: {report.summary.get('health_score', 'N/A') * 100:.1f}%")
    print(f"  Passed: {report.summary.get('passed', 0)}")
    print(f"  Warnings: {report.summary.get('warnings', 0)}")
    print(f"  Errors: {report.summary.get('errors', 0)}")

    return report.error_count


# =========================================================================
# aetheros health
# =========================================================================

def build_health_parser(subparsers, *, cmd_health: Callable) -> None:
    """Build ``aetheros health`` subcommand."""
    parser = subparsers.add_parser(
        "health",
        help="Check system health",
        description="Comprehensive health check for AetherOS",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Watch mode: continuously check health every 10s",
    )
    parser.set_defaults(func=cmd_health)


def handle_health(args: Any) -> int:
    """Handler for ``aetheros health``."""
    from production.health import check_health, HealthStatus

    json_only = getattr(args, "json", False)
    watch = getattr(args, "watch", False)

    def _run_check():
        report = check_health()

        if json_only:
            print(json.dumps(report.to_dict(), indent=2, default=str))
            return

        _print_section("Health Status")
        status_colors = {
            HealthStatus.HEALTHY: "✓ HEALTHY",
            HealthStatus.DEGRADED: "⚠ DEGRADED",
            HealthStatus.UNHEALTHY: "✗ UNHEALTHY",
            HealthStatus.UNKNOWN: "? UNKNOWN",
        }
        print(f"  Overall: {status_colors.get(report.overall_status, 'UNKNOWN')}")
        print(f"  Uptime: {report.uptime_seconds:.0f}s")

        _print_section("Component Checks")
        for check in report.checks:
            status = status_colors.get(check.status, "?")
            print(f"  {status}  {check.component.value}")
            if check.message:
                print(f"          {check.message}")
            if check.status != HealthStatus.HEALTHY and check.latency_ms > 0:
                print(f"          ({check.latency_ms:.0f}ms)")

        _print_section("Summary")
        print(f"  Healthy: {report.healthy_count}")
        print(f"  Degraded: {report.degraded_count}")
        print(f"  Unhealthy: {report.unhealthy_count}")

        return 0 if report.overall_status == HealthStatus.HEALTHY else 1

    if watch:
        try:
            while True:
                _run_check()
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n  Health watch stopped.")
            return 0
    else:
        return _run_check()


# =========================================================================
# aetheros verify
# =========================================================================

def build_verify_parser(subparsers, *, cmd_verify: Callable) -> None:
    """Build ``aetheros verify`` subcommand."""
    parser = subparsers.add_parser(
        "verify",
        help="Verify system integrity",
        description="Verify AetherOS system integrity and configuration",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.add_argument(
        "--compat", action="store_true",
        help="Run compatibility checks",
    )
    parser.add_argument(
        "--migrate", action="store_true",
        help="Run migration validation",
    )
    parser.set_defaults(func=cmd_verify)


def handle_verify(args: Any) -> int:
    """Handler for ``aetheros verify``."""
    from production.diagnostics import run_diagnostics
    from production.compatibility_checker import CompatibilityChecker

    json_only = getattr(args, "json", False)
    exit_code = 0

    # Always run basic verification
    _print_section("System Verification")
    diag = run_diagnostics()
    health_score = diag.summary.get("health_score", 0)

    if json_only:
        print(json.dumps({
            "health_score": health_score,
            "passed": diag.passed_count,
            "warnings": diag.warning_count,
            "errors": diag.error_count,
        }, indent=2))
    else:
        print(f"  Health Score: {health_score * 100:.1f}%")
        print(f"  Checks Passed: {diag.passed_count}/{len(diag.checks)}")
        if diag.warning_count:
            print(f"  Warnings: {diag.warning_count}")
        if diag.error_count:
            print(f"  Errors: {diag.error_count}")
            exit_code = 1

    # Compatibility check
    if args.compat:
        _print_section("Compatibility Check")
        checker = CompatibilityChecker()
        compat = checker.check_all()
        if json_only:
            print(json.dumps(compat.to_dict(), indent=2))
        else:
            print(f"  Compatible: {'✓' if compat.compatible else '✗'}")
            for name, passed in compat.checks.items():
                _print_check(name, passed)
            if compat.warnings:
                print(f"  Warnings ({len(compat.warnings)}):")
                for w in compat.warnings:
                    print(f"    ⚠ {w}")

    # Migration validation
    if args.migrate:
        _print_section("Migration Validation")
        try:
            from production.release_manager import ReleaseManager
            from production.migration_validator import MigrationValidator
            mgr = ReleaseManager()
            version = mgr.get_current_version()
            validator = MigrationValidator()
            migration = validator.validate(version, version)

            if json_only:
                print(json.dumps(migration.to_dict(), indent=2))
            else:
                print(f"  Compatible: {'✓' if migration.overall_compatible else '✗'}")
                for check in migration.checks:
                    _print_check(
                        f"[{check.category.value}] {check.name}",
                        check.passed,
                        check.message,
                    )
        except Exception as exc:
            print(f"  Migration check failed: {exc}")
            exit_code = exit_code or 1

    return exit_code


# =========================================================================
# aetheros migrate-check
# =========================================================================

def build_migrate_check_parser(subparsers, *, cmd_migrate_check: Callable) -> None:
    """Build ``aetheros migrate-check`` subcommand."""
    parser = subparsers.add_parser(
        "migrate-check",
        help="Validate upgrade migration",
        description="Validate migration compatibility between AetherOS versions",
    )
    parser.add_argument(
        "from_version",
        nargs="?",
        default="",
        help="Source version being migrated from",
    )
    parser.add_argument(
        "to_version",
        nargs="?",
        default="",
        help="Target version being migrated to",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON only",
    )
    parser.set_defaults(func=cmd_migrate_check)


def handle_migrate_check(args: Any) -> int:
    """Handler for ``aetheros migrate-check``."""
    from production.migration_validator import MigrationValidator
    from production.release_manager import ReleaseManager

    json_only = getattr(args, "json", False)

    mgr = ReleaseManager()
    current = mgr.get_current_version()
    source = getattr(args, "from_version", "") or current
    target = getattr(args, "to_version", "") or current

    validator = MigrationValidator()
    report = validator.validate(source, target)

    if json_only:
        print(json.dumps(report.to_dict(), indent=2, default=str))
        return 0 if report.overall_compatible else 1

    _print_section(f"Migration Check: {source} → {target}")
    print(f"  Compatible: {'✓' if report.overall_compatible else '✗'}")
    print(f"  Total Checks: {len(report.checks)}")

    _print_section("Check Results")
    for check in report.checks:
        _print_check(
            f"[{check.severity.value.upper():>8}] {check.name}",
            check.passed,
            check.message,
        )
        if not check.passed and check.recommendation:
            print(f"           Fix: {check.recommendation}")

    _print_section("Summary")
    print(f"  Passed: {report.passed_count}")
    print(f"  Warnings: {report.warning_count}")
    print(f"  Errors: {report.error_count}")

    if report.get_blocking_issues():
        print(f"\n  Blocking Issues:")
        for issue in report.get_blocking_issues():
            print(f"    ✗ {issue.message}")

    return 0 if report.overall_compatible else 1
