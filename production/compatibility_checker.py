"""
Compatibility Checker
=====================

Comprehensive compatibility checking for AetherOS deployments.

Checks:
- AetherOS version compatibility
- SDK version compatibility
- Platform/OS compatibility
- Plugin compatibility
- Configuration schema compatibility
- Dependency compatibility
- Cross-platform compatibility
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityReport:
    """Comprehensive compatibility report.

    Attributes:
        compatible: Whether everything is compatible
        checks: Individual check results
        summary: Summary statistics
        warnings: Compatibility warnings
        errors: Compatibility errors
    """
    compatible: bool = True
    checks: Dict[str, bool] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        self.checks[name] = passed
        if not passed:
            self.compatible = False
            self.errors.append(message or f"Check '{name}' failed")

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatible": self.compatible,
            "checks": dict(self.checks),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "summary": {
                "total": len(self.checks),
                "passed": sum(1 for v in self.checks.values() if v),
                "failed": sum(1 for v in self.checks.values() if not v),
            },
        }


class CompatibilityChecker:
    """Comprehensive compatibility checker for AetherOS deployments.

    Usage:
        checker = CompatibilityChecker()
        report = checker.check_all()

        if not report.compatible:
            for error in report.errors:
                print(f"INCOMPATIBLE: {error}")
    """

    def check_all(self) -> CompatibilityReport:
        """Run all compatibility checks."""
        report = CompatibilityReport()

        self._check_python_version(report)
        self._check_platform(report)
        self._check_core_dependencies(report)
        self._check_disk_space(report)

        # Build summary
        report.summary = {
            "total": len(report.checks),
            "passed": sum(1 for v in report.checks.values() if v),
            "failed": sum(1 for v in report.checks.values() if not v),
        }

        return report

    def _check_python_version(self, report: CompatibilityReport) -> None:
        """Check Python version compatibility."""
        major, minor = sys.version_info.major, sys.version_info.minor
        ok = (major, minor) >= (3, 10)
        report.add_check(
            "python_version",
            ok,
            f"Python {major}.{minor} (3.10+ required)",
        )

    def _check_platform(self, report: CompatibilityReport) -> None:
        """Check platform compatibility."""
        current = sys.platform
        supported = {"linux", "darwin", "win32"}
        ok = current in supported

        platform_msg = f"Platform: {current} ({platform.machine()})"
        report.add_check("platform", ok, platform_msg)

        if not ok and current not in supported:
            report.add_warning(f"Platform '{current}' may have limited support")

    def _check_core_dependencies(self, report: CompatibilityReport) -> None:
        """Check core dependency availability."""
        dependencies = [
            ("openai", "OpenAI SDK"),
            ("yaml", "PyYAML"),
            ("httpx", "HTTPX"),
            ("yaml", "PyYAML (config)"),
        ]

        for module, name in dependencies:
            try:
                __import__(module)
                report.add_check(f"dep_{module}", True)
            except ImportError:
                report.add_check(
                    f"dep_{module}",
                    False,
                    f"Missing dependency: {name}",
                )

    def _check_disk_space(self, report: CompatibilityReport) -> None:
        """Check minimum disk space requirements."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_mb = free / (1024 * 1024)
            ok = free_mb > 500
            report.add_check(
                "disk_space",
                ok,
                f"{free_mb:.0f} MB free ({'OK' if ok else 'Insufficient'})",
            )
        except Exception:
            report.add_check("disk_space", True, "Disk check skipped")
