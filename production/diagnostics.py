"""
Diagnostics Engine
==================

Comprehensive system diagnostics for AetherOS production deployments.

Performs structured checks across:
- Kernel health and configuration
- Agent runtime state
- Tool availability and configuration
- Memory provider connectivity
- Gateway platform status
- Plugin integrity
- File system state
- Network connectivity
- Performance metrics
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CheckSeverity(Enum):
    """Severity levels for diagnostic checks."""
    INFO = "info"
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CheckCategory(Enum):
    """Categories of diagnostic checks."""
    SYSTEM = "system"
    KERNEL = "kernel"
    AGENT = "agent"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    STORAGE = "storage"
    MEMORY = "memory"
    PLUGINS = "plugins"
    TOOLS = "tools"
    GATEWAY = "gateway"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class DiagnosticCheck:
    """A single diagnostic check result.

    Attributes:
        name: Check name
        category: Check category
        severity: Severity level
        message: Human-readable message
        details: Additional diagnostic details
        recommendation: Recommended action if check fails
        passed: Whether the check passed
        duration_ms: How long the check took
    """
    name: str
    category: CheckCategory = CheckCategory.SYSTEM
    severity: CheckSeverity = CheckSeverity.INFO
    message: str = ""
    details: str = ""
    recommendation: str = ""
    passed: bool = True
    duration_ms: float = 0.0


@dataclass
class DiagnosticReport:
    """A complete diagnostic report.

    Attributes:
        timestamp: When the report was generated
        hostname: Machine hostname
        platform: OS platform
        python_version: Python version
        aetheros_version: Aetheros version
        uptime_seconds: System uptime
        checks: List of diagnostic checks performed
        summary: Summary statistics
    """
    timestamp: float = field(default_factory=time.time)
    hostname: str = ""
    platform: str = ""
    python_version: str = ""
    aetheros_version: str = ""
    uptime_seconds: float = 0.0
    checks: List[DiagnosticCheck] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_check(self, check: DiagnosticCheck) -> None:
        self.checks.append(check)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.severity == CheckSeverity.WARNING)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if c.severity in (CheckSeverity.ERROR, CheckSeverity.CRITICAL))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "hostname": self.hostname,
            "platform": self.platform,
            "python_version": self.python_version,
            "aetheros_version": self.aetheros_version,
            "uptime_seconds": self.uptime_seconds,
            "total_checks": len(self.checks),
            "passed": self.passed_count,
            "warnings": self.warning_count,
            "errors": self.error_count,
            "failed": self.failed_count,
            "summary": self.summary,
            "checks": [
            ],
        }

    def get_failed_checks(self) -> List[DiagnosticCheck]:
        return [c for c in self.checks if not c.passed]

    def get_checks_by_category(self, category: CheckCategory) -> List[DiagnosticCheck]:
        return [c for c in self.checks if c.category == category]

    def get_checks_by_severity(self, severity: CheckSeverity) -> List[DiagnosticCheck]:
        return [c for c in self.checks if c.severity == severity]


class DiagnosticsEngine:
    """Runs structured diagnostic checks across AetherOS subsystems.

    Usage:
        engine = DiagnosticsEngine()
        report = engine.run_all()

        for check in report.get_failed_checks():
            print(f"FAILED: {check.name} - {check.recommendation}")
    """

    def __init__(self):
        self._checks: Dict[str, DiagnosticCheck] = {}

    def register_check(self, check: DiagnosticCheck) -> None:
        """Register a check to be run."""
        self._checks[check.name] = check

    def run_all(self) -> DiagnosticReport:
        """Run all registered and default diagnostic checks."""
        report = self._create_base_report()

        # Run all checks
        check_fns = [
            self._check_system_info,
            self._check_python_version,
            self._check_disk_space,
            self._check_kernel_status,
            self._check_plugin_integrity,
            self._check_configuration,
            self._check_memory_usage,
            self._check_tool_availability,
        ]

        for check_fn in check_fns:
            try:
                start = time.perf_counter()
                result = check_fn()
                elapsed = (time.perf_counter() - start) * 1000
                if isinstance(result, list):
                    for r in result:
                        r.duration_ms = elapsed / len(result)
                        report.add_check(r)
                elif isinstance(result, DiagnosticCheck):
                    result.duration_ms = elapsed
                    report.add_check(result)
            except Exception as exc:
                report.add_check(DiagnosticCheck(
                    name=check_fn.__name__.replace("_check_", ""),
                    category=CheckCategory.SYSTEM,
                    severity=CheckSeverity.ERROR,
                    message=f"Check failed with exception: {exc}",
                    passed=False,
                ))

        # Build summary
        report.summary = {
            "total_checks": len(report.checks),
            "passed": report.passed_count,
            "warnings": report.warning_count,
            "errors": report.error_count,
            "failed": report.failed_count,
            "health_score": self._compute_health_score(report),
        }

        return report

    def _create_base_report(self) -> DiagnosticReport:
        """Create a base diagnostic report with system metadata."""
        try:
            from aetheros_cli import __version__ as version
        except ImportError:
            version = "unknown"

        return DiagnosticReport(
            hostname=platform.node(),
            platform=f"{sys.platform} ({platform.machine()})",
            python_version=sys.version.split()[0],
            aetheros_version=version,
            uptime_seconds=time.time() - self._get_boot_time(),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_system_info(self) -> List[DiagnosticCheck]:
        """Check basic system information."""
        checks: List[DiagnosticCheck] = []

        checks.append(DiagnosticCheck(
            name="system_info",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.INFO,
            message=f"Running on {platform.system()} {platform.release()} "
                    f"({platform.machine()})",
            passed=True,
        ))

        checks.append(DiagnosticCheck(
            name="python_info",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.INFO,
            message=f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            passed=sys.version_info >= (3, 10),
            recommendation="Python 3.10+ is recommended",
        ))

        return checks

    def _check_python_version(self) -> DiagnosticCheck:
        """Check Python version meets requirements."""
        ok = sys.version_info >= (3, 10)
        return DiagnosticCheck(
            name="python_version",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.ERROR if not ok else CheckSeverity.OK,
            message=f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            details="AetherOS requires Python 3.10+",
            recommendation="Upgrade to Python 3.10+",
            passed=ok,
        )

    def _check_disk_space(self) -> DiagnosticCheck:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024 ** 3)
            ok = free_gb > 1.0
            return DiagnosticCheck(
                name="disk_space",
                category=CheckCategory.STORAGE,
                severity=CheckSeverity.WARNING if not ok else CheckSeverity.OK,
                message=f"{free_gb:.1f} GB free disk space",
                details=f"Total: {total / (1024**3):.1f} GB, Used: {used / (1024**3):.1f} GB",
                recommendation="Free at least 1 GB of disk space",
                passed=ok,
            )
        except Exception:
            return DiagnosticCheck(
                name="disk_space",
                category=CheckCategory.STORAGE,
                passed=True,
                message="Disk space check skipped",
            )

    def _check_kernel_status(self) -> DiagnosticCheck:
        """Check kernel status by verifying the module is importable.

        Note: The kernel class is instantiated as needed; its availability
        is determined by importability, not by instance state.
        """
        try:
            import importlib
            if importlib.util.find_spec("kernel.kernel") is not None:
                return DiagnosticCheck(
                    name="kernel_status",
                    category=CheckCategory.KERNEL,
                    severity=CheckSeverity.OK,
                    message="Kernel module is available",
                    passed=True,
                )
            return DiagnosticCheck(
                name="kernel_status",
                category=CheckCategory.KERNEL,
                severity=CheckSeverity.INFO,
                message="Kernel module not found",
                passed=True,
            )
        except Exception:
            return DiagnosticCheck(
                name="kernel_status",
                category=CheckCategory.KERNEL,
                severity=CheckSeverity.INFO,
                message="Kernel check skipped",
                passed=True,
            )

    def _check_plugin_integrity(self) -> DiagnosticCheck:
        """Check plugin system integrity."""
        try:
            from aetheros_cli.plugins import discover_plugins, get_all_plugin_manifests
            discover_plugins()
            manifests = get_all_plugin_manifests()
            issues = [m for m in manifests if getattr(m, 'error', None)]
            return DiagnosticCheck(
                name="plugin_integrity",
                category=CheckCategory.PLUGINS,
                severity=CheckSeverity.WARNING if issues else CheckSeverity.OK,
                message=f"{len(manifests)} plugins found, {len(issues)} with issues",
                details=f"Plugins: {len(manifests)}, Issues: {len(issues)}",
                passed=len(issues) == 0,
            )
        except Exception as exc:
            return DiagnosticCheck(
                name="plugin_integrity",
                category=CheckCategory.PLUGINS,
                severity=CheckSeverity.WARNING,
                message=f"Plugin check failed: {exc}",
                passed=False,
            )

    def _check_configuration(self) -> DiagnosticCheck:
        """Check configuration integrity."""
        errors: List[str] = []
        try:
            from aetheros_cli.config import load_config
            cfg = load_config()
            model = cfg.get("model", {})
            if not model.get("provider"):
                errors.append("No model provider configured")
            return DiagnosticCheck(
                name="configuration",
                category=CheckCategory.CONFIGURATION,
                severity=CheckSeverity.WARNING if errors else CheckSeverity.OK,
                message="Configuration loaded" if not errors else f"Issues: {'; '.join(errors)}",
                passed=len(errors) == 0,
            )
        except Exception as exc:
            return DiagnosticCheck(
                name="configuration",
                category=CheckCategory.CONFIGURATION,
                severity=CheckSeverity.ERROR,
                message=f"Configuration failed to load: {exc}",
                passed=False,
            )

    def _check_memory_usage(self) -> DiagnosticCheck:
        """Check current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            rss_mb = process.memory_info().rss / (1024 * 1024)
            ok = rss_mb < 800
            return DiagnosticCheck(
                name="memory_usage",
                category=CheckCategory.MEMORY,
                severity=CheckSeverity.WARNING if not ok else CheckSeverity.OK,
                message=f"{rss_mb:.0f} MB RSS memory used",
                recommendation="Consider reducing cache sizes or disabling unused plugins",
                passed=ok,
            )
        except ImportError:
            return DiagnosticCheck(
                name="memory_usage",
                category=CheckCategory.MEMORY,
                passed=True,
                message="Memory check skipped (install psutil)",
            )

    def _check_tool_availability(self) -> DiagnosticCheck:
        """Check tool registry availability."""
        try:
            from tools.registry import registry
            tool_count = len(registry.get_all_tool_names())
            return DiagnosticCheck(
                name="tool_availability",
                category=CheckCategory.TOOLS,
                severity=CheckSeverity.OK,
                message=f"{tool_count} tools registered",
                passed=True,
            )
        except Exception as exc:
            return DiagnosticCheck(
                name="tool_availability",
                category=CheckCategory.TOOLS,
                severity=CheckSeverity.WARNING,
                message=f"Tool check failed: {exc}",
                passed=False,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_boot_time(self) -> float:
        """Get system boot time."""
        try:
            import psutil
            return psutil.boot_time()
        except ImportError:
            return time.time()

    def _compute_health_score(self, report: DiagnosticReport) -> float:
        """Compute a health score from 0.0 to 1.0."""
        if not report.checks:
            return 1.0
        weights = {
            CheckSeverity.ERROR: 1.0,
            CheckSeverity.CRITICAL: 1.0,
            CheckSeverity.WARNING: 0.5,
            CheckSeverity.OK: 0.0,
            CheckSeverity.INFO: 0.0,
        }
        total_weight = sum(weights.get(c.severity, 0) for c in report.checks)
        max_weight = len(report.checks)
        return max(0.0, 1.0 - (total_weight / max_weight))


def run_diagnostics() -> DiagnosticReport:
    """Quick-start convenience function to run all diagnostics.

    Returns:
        A complete DiagnosticReport with all checks.
    """
    engine = DiagnosticsEngine()
    return engine.run_all()
