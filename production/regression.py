"""
Regression Testing
==================

Automated regression test suite for AetherOS.

Provides:
- Regression test suites covering all subsystems
- Automated test execution and reporting
- Pass/fail/regression tracking
- Historical regression comparison
- Integration with the existing test infrastructure
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegressionResult:
    """Result of a single regression test.

    Attributes:
        name: Test name
        passed: Whether the test passed
        duration_ms: Test duration
        error: Error message if failed
        details: Additional test details
    """
    name: str
    passed: bool = True
    duration_ms: float = 0.0
    error: str = ""
    details: str = ""


@dataclass
class RegressionSuite:
    """A collection of regression tests in a category.

    Attributes:
        name: Suite name
        category: Test category
        description: Suite description
        test_path: Path to the test directory/file
        results: Individual test results
        duration_ms: Total suite duration
    """
    name: str
    category: str = ""
    description: str = ""
    test_path: str = ""
    results: List[RegressionResult] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def add_result(self, result: RegressionResult) -> None:
        self.results.append(result)


@dataclass
class RegressionReport:
    """Complete regression testing report.

    Attributes:
        timestamp: When the report was generated
        suites: Regression test suites that were run
        total_duration_ms: Total test duration
        summary: Summary statistics
        aetheros_version: Aetheros version under test
    """
    timestamp: float = field(default_factory=time.time)
    suites: List[RegressionSuite] = field(default_factory=list)
    total_duration_ms: float = 0.0
    summary: Dict[str, Any] = field(default_factory=dict)
    aetheros_version: str = ""

    @property
    def total_tests(self) -> int:
        return sum(len(s.results) for s in self.suites)

    @property
    def passed_count(self) -> int:
        return sum(s.passed_count for s in self.suites)

    @property
    def failed_count(self) -> int:
        return sum(s.failed_count for s in self.suites)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "aetheros_version": self.aetheros_version,
            "total_duration_ms": self.total_duration_ms,
            "total_tests": self.total_tests,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "summary": self.summary,
            "suites": [
                {
                    "name": s.name,
                    "category": s.category,
                    "tests": len(s.results),
                    "passed": s.passed_count,
                    "failed": s.failed_count,
                    "duration_ms": s.duration_ms,
                }
                for s in self.suites
            ],
        }


class RegressionTester:
    """Runs regression test suites and produces structured reports.

    Usage:
        tester = RegressionTester()
        report = tester.run_all()
        print(f"Passed: {report.passed_count}/{report.total_tests}")
    """

    def __init__(self, tests_root: Optional[str] = None):
        self._tests_root = Path(tests_root or self._find_tests_root())
        self._project_root = self._tests_root.parent if self._tests_root.name == "tests" else self._tests_root

    def _find_tests_root(self) -> str:
        """Find the tests directory."""
        candidates = [
            Path.cwd() / "tests",
            Path(__file__).resolve().parent.parent / "tests",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return "tests"

    # ------------------------------------------------------------------
    # Suite definitions
    # ------------------------------------------------------------------

    def _get_regression_suites(self) -> List[RegressionSuite]:
        """Return all regression test suites."""
        return [
            RegressionSuite(
                name="kernel",
                category="kernel",
                description="Kernel system regression tests",
                test_path=str(self._tests_root / "kernel"),
            ),
            RegressionSuite(
                name="agent",
                category="agent",
                description="Agent runtime regression tests",
                test_path=str(self._tests_root / "agent"),
            ),
            RegressionSuite(
                name="state",
                category="state",
                description="State management regression tests",
                test_path=str(self._tests_root),
                # Matches test_aetheros_state*.py
            ),
            RegressionSuite(
                name="tools",
                category="tools",
                description="Tool execution regression tests",
                test_path=str(self._tests_root / "tools"),
            ),
            RegressionSuite(
                name="enterprise",
                category="enterprise",
                description="Enterprise feature regression tests",
                test_path=str(self._tests_root / "enterprise") if (self._tests_root / "enterprise").exists() else "",
            ),
            RegressionSuite(
                name="cli",
                category="cli",
                description="CLI command regression tests",
                test_path=str(self._tests_root / "aetheros_cli"),
            ),
            RegressionSuite(
                name="plugins",
                category="plugins",
                description="Plugin system regression tests",
                test_path=str(self._tests_root / "plugins"),
            ),
            RegressionSuite(
                name="gateway",
                category="gateway",
                description="Gateway platform regression tests",
                test_path=str(self._tests_root / "gateway"),
            ),
        ]

    # ------------------------------------------------------------------
    # Running tests
    # ------------------------------------------------------------------

    def run_suite(self, suite: RegressionSuite) -> RegressionSuite:
        """Run a single regression test suite."""
        if not suite.test_path or not os.path.exists(suite.test_path):
            logger.info("Suite '%s': test path not found, skipping", suite.name)
            return suite

        start = time.perf_counter()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", suite.test_path,
                 "-q", "--tb=short", "--no-header", "-x"],
                capture_output=True, text=True, timeout=600,
            )
            suite.duration_ms = (time.perf_counter() - start) * 1000

            if result.returncode == 0:
                suite.add_result(RegressionResult(
                    name=f"suite:{suite.name}",
                    passed=True,
                    duration_ms=suite.duration_ms,
                ))
            else:
                # Extract failure details
                error_lines = result.stdout.strip().split("\n")[-10:]
                error_text = "\n".join(error_lines)
                suite.add_result(RegressionResult(
                    name=f"suite:{suite.name}",
                    passed=False,
                    duration_ms=suite.duration_ms,
                    error=result.stderr.strip()[:500] or error_text[:500],
                ))
        except subprocess.TimeoutExpired:
            suite.duration_ms = (time.perf_counter() - start) * 1000
            suite.add_result(RegressionResult(
                name=f"suite:{suite.name}",
                passed=False,
                duration_ms=suite.duration_ms,
                error="Test suite timed out (10m limit)",
            ))
        except Exception as exc:
            suite.duration_ms = (time.perf_counter() - start) * 1000
            suite.add_result(RegressionResult(
                name=f"suite:{suite.name}",
                passed=False,
                duration_ms=suite.duration_ms,
                error=str(exc),
            ))

        return suite

    def run_suites(self, suites: Optional[List[RegressionSuite]] = None) -> RegressionReport:
        """Run specified or default regression suites."""
        if suites is None:
            suites = self._get_regression_suites()

        # Get version
        try:
            from aetheros_cli import __version__
            version = __version__
        except ImportError:
            version = "unknown"

        report = RegressionReport(aetheros_version=version)
        total_start = time.perf_counter()

        for suite in suites:
            logger.info("Running regression suite: %s (%s)", suite.name, suite.test_path)
            self.run_suite(suite)
            report.suites.append(suite)

        report.total_duration_ms = (time.perf_counter() - total_start) * 1000

        report.summary = {
            "total_suites": len(report.suites),
            "total_tests": report.total_tests,
            "passed": report.passed_count,
            "failed": report.failed_count,
            "total_duration_ms": report.total_duration_ms,
        }

        return report

    def run_all(self) -> RegressionReport:
        """Run all default regression suites."""
        return self.run_suites()

    def save_report(self, report: RegressionReport, path: str) -> Path:
        """Save a regression report to JSON."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return output
