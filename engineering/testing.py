"""
Test Coordinator — runs and manages tests across the project.

Integrates with existing test frameworks and runs:
  - Unit tests
  - Integration tests
  - Coverage analysis
  - Test result tracking
"""

from __future__ import annotations

import enum
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class TestStatus(enum.Enum):
    """Status of a test execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a single test execution.

    Attributes:
        id: Unique result ID
        name: Test name or identifier
        suite_id: Test suite this belongs to
        status: Test status
        duration_seconds: How long the test took
        assertion_count: Number of assertions
        error_message: Error message if failed
        traceback: Error traceback if failed
        file_path: Test file path
        line_number: Test definition line number
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    suite_id: str = ""
    status: TestStatus = TestStatus.PENDING
    duration_seconds: float = 0.0
    assertion_count: int = 0
    error_message: str = ""
    traceback: str = ""
    file_path: str = ""
    line_number: int = 0


@dataclass
class CoverageReport:
    """Coverage analysis results.

    Attributes:
        line_rate: Percentage of lines covered (0.0 - 1.0)
        branch_rate: Percentage of branches covered (0.0 - 1.0)
        files_covered: Number of files with coverage data
        total_lines: Total lines of code
        covered_lines: Lines covered by tests
        missing_lines: Lines not covered
    """
    line_rate: float = 0.0
    branch_rate: float = 0.0
    files_covered: int = 0
    total_lines: int = 0
    covered_lines: int = 0
    missing_lines: int = 0


@dataclass
class TestSuite:
    """A collection of related tests.

    Attributes:
        id: Unique suite ID
        name: Suite name
        description: Suite description
        test_path: Path to test files
        framework: Test framework (pytest, jest, etc.)
        results: Test results
        coverage: Coverage report (optional)
        total_duration: Total execution time
        status: Overall suite status
        run_at: When the suite was run
        command: The command used to run tests
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    test_path: str = ""
    framework: str = "pytest"
    results: List[TestResult] = field(default_factory=list)
    coverage: Optional[CoverageReport] = None
    total_duration: float = 0.0
    status: TestStatus = TestStatus.PENDING
    run_at: Optional[float] = None
    command: str = ""


class TestCoordinator:
    """Runs and manages tests across the project.

    Discovers test frameworks, runs tests, collects results,
    and tracks coverage.

    Usage:
        coordinator = TestCoordinator(event_bus)
        suite = coordinator.run_suite("tests/", framework="pytest")
        print(f"Passed: {sum(1 for t in suite.results if t.status == TestStatus.PASSED)}")
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 project_root: Optional[str] = None):
        self._event_bus = event_bus
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._suites: Dict[str, TestSuite] = {}

    def run_suite(self, test_path: str, framework: str = "",
                  args: List[str] = None,
                  name: str = "") -> TestSuite:
        """Run a test suite.

        Args:
            test_path: Path to test files or directory
            framework: Test framework (auto-detected if empty)
            args: Additional arguments to pass to the test runner
            name: Suite name

        Returns:
            TestSuite with results
        """
        resolved_path = self._resolve_path(test_path)

        if not framework:
            framework = self._detect_framework(resolved_path)

        suite = TestSuite(
            name=name or f"Test suite: {test_path}",
            test_path=str(resolved_path),
            framework=framework,
        )

        logger.info(
            "TestCoordinator: running %s on %s",
            framework, resolved_path,
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.test_suite_started", {
                "suite_id": suite.id,
                "framework": framework,
                "test_path": str(resolved_path),
            })

        try:
            suite = self._run_tests(suite, args or [])
        except Exception as exc:
            logger.error("TestCoordinator: suite failed: %s", exc)
            suite.status = TestStatus.ERROR
            suite.results.append(TestResult(
                name="suite_execution",
                suite_id=suite.id,
                status=TestStatus.ERROR,
                error_message=str(exc),
            ))

        self._suites[suite.id] = suite

        if self._event_bus:
            self._event_bus.emit_async("engineering.test_suite_completed", {
                "suite_id": suite.id,
                "framework": framework,
                "status": suite.status.value,
                "total": len(suite.results),
                "passed": sum(1 for r in suite.results if r.status == TestStatus.PASSED),
                "failed": sum(1 for r in suite.results if r.status == TestStatus.FAILED),
                "duration": suite.total_duration,
            })

        return suite

    def _run_tests(self, suite: TestSuite, args: List[str]) -> TestSuite:
        """Execute tests using the appropriate framework."""
        start_time = time.time()

        if suite.framework == "pytest":
            result = self._run_pytest(suite, args)
        elif suite.framework == "jest":
            result = self._run_jest(suite, args)
        elif suite.framework == "unittest":
            result = self._run_unittest(suite, args)
        else:
            result = self._run_generic(suite, args)

        suite.total_duration = time.time() - start_time
        suite.run_at = start_time
        return result

    def _run_pytest(self, suite: TestSuite, args: List[str]) -> TestSuite:
        """Run pytest on a test path."""
        cmd = ["python", "-m", "pytest", str(suite.test_path),
               "-v", "--tb=short", "--no-header"]
        cmd.extend(args)
        cmd_str = " ".join(cmd)
        suite.command = cmd_str

        try:
            result = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = result.stdout + result.stderr
            suite.status = TestStatus.PASSED if result.returncode == 0 else TestStatus.FAILED

            # Parse pytest output for individual results
            for line in output.splitlines():
                line = line.rstrip()
                if "PASSED" in line and "::" in line:
                    name = line.split("::")[-1].replace("PASSED", "").strip()
                    suite.results.append(TestResult(
                        name=name or "test",
                        suite_id=suite.id,
                        status=TestStatus.PASSED,
                    ))
                elif "FAILED" in line and "::" in line:
                    parts = line.split("::")
                    name = parts[-1].replace("FAILED", "").strip()
                    suite.results.append(TestResult(
                        name=name or "test",
                        suite_id=suite.id,
                        status=TestStatus.FAILED,
                    ))

            # If no individual tests parsed, create a summary result
            if not suite.results:
                suite.results.append(TestResult(
                    name=f"pytest run (exit code {result.returncode})",
                    suite_id=suite.id,
                    status=suite.status,
                    duration_seconds=suite.total_duration,
                ))

        except subprocess.TimeoutExpired:
            suite.status = TestStatus.TIMEOUT
            suite.results.append(TestResult(
                name="test_execution",
                suite_id=suite.id,
                status=TestStatus.TIMEOUT,
                error_message="Test execution timed out after 300 seconds",
            ))
        except FileNotFoundError:
            suite.status = TestStatus.ERROR
            suite.results.append(TestResult(
                name="framework_not_found",
                suite_id=suite.id,
                status=TestStatus.ERROR,
                error_message="pytest not found. Install with: pip install pytest",
            ))

        return suite

    def _run_jest(self, suite: TestSuite, args: List[str]) -> TestSuite:
        """Run Jest tests."""
        cmd = ["npx", "jest", str(suite.test_path), "--verbose"]
        cmd.extend(args)
        suite.command = " ".join(cmd)

        try:
            result = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            suite.status = TestStatus.PASSED if result.returncode == 0 else TestStatus.FAILED
            suite.results.append(TestResult(
                name=f"jest run (exit code {result.returncode})",
                suite_id=suite.id,
                status=suite.status,
            ))

        except subprocess.TimeoutExpired:
            suite.status = TestStatus.TIMEOUT
        except FileNotFoundError:
            suite.status = TestStatus.ERROR
            suite.results.append(TestResult(
                name="framework_not_found",
                suite_id=suite.id,
                status=TestStatus.ERROR,
                error_message="Jest not found",
            ))

        return suite

    def _run_unittest(self, suite: TestSuite, args: List[str]) -> TestSuite:
        """Run Python unittest."""
        cmd = ["python", "-m", "unittest", "discover",
               "-s", str(suite.test_path), "-v"]
        cmd.extend(args)
        suite.command = " ".join(cmd)

        try:
            result = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            suite.status = TestStatus.PASSED if result.returncode == 0 else TestStatus.FAILED
            suite.results.append(TestResult(
                name=f"unittest run (exit code {result.returncode})",
                suite_id=suite.id,
                status=suite.status,
            ))

        except subprocess.TimeoutExpired:
            suite.status = TestStatus.TIMEOUT

        return suite

    def _run_generic(self, suite: TestSuite, args: List[str]) -> TestSuite:
        """Run a generic test command."""
        suite.status = TestStatus.PENDING
        return suite

    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    def run_coverage(self, test_path: str, source_path: str = "src",
                     args: List[str] = None) -> Optional[CoverageReport]:
        """Run coverage analysis on tests.

        Args:
            test_path: Path to test files
            source_path: Path to source files
            args: Additional arguments

        Returns:
            CoverageReport or None if coverage tool not found
        """
        try:
            cmd = [
                "python", "-m", "coverage", "run",
                "--source", source_path,
                "-m", "pytest",
                str(self._resolve_path(test_path)),
            ]
            if args:
                cmd.extend(args)

            result = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 or result.returncode == 1:
                # Try to get coverage report
                report_cmd = [
                    "python", "-m", "coverage", "report",
                    "--format=total",
                ]
                report_result = subprocess.run(
                    report_cmd,
                    cwd=self._project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                line_rate = 0.0
                if report_result.returncode == 0:
                    try:
                        line_rate = float(report_result.stdout.strip().rstrip("%")) / 100.0
                    except (ValueError, IndexError):
                        pass

                return CoverageReport(
                    line_rate=line_rate,
                    branch_rate=0.0,
                    files_covered=0,
                    total_lines=0,
                    covered_lines=0,
                    missing_lines=0,
                )
        except FileNotFoundError:
            logger.warning("TestCoordinator: coverage tool not found")
        except subprocess.TimeoutExpired:
            logger.warning("TestCoordinator: coverage timed out")

        return None

    # ------------------------------------------------------------------
    # Framework detection
    # ------------------------------------------------------------------

    def _detect_framework(self, test_path: Path) -> str:
        """Detect the test framework from the project configuration."""
        # Check for config files
        config_indicators = [
            ("pytest.ini", "pytest"),
            ("pyproject.toml", "pytest"),
            ("setup.cfg", "pytest"),
            ("jest.config.js", "jest"),
            ("jest.config.ts", "jest"),
            ("vitest.config.ts", "vitest"),
            ("vitest.config.js", "vitest"),
        ]

        for config_file, framework in config_indicators:
            if (self._project_root / config_file).exists():
                return framework

        # Check if path contains Python test files
        try:
            for entry in test_path.iterdir() if test_path.is_dir() else [test_path]:
                if entry.name.endswith(".py"):
                    content = entry.read_text(encoding="utf-8", errors="ignore")
                    if "import pytest" in content or "from pytest" in content:
                        return "pytest"
                    if "import unittest" in content or "from unittest" in content:
                        return "unittest"
        except Exception:
            pass

        return "pytest"

    # ------------------------------------------------------------------
    # Suite management
    # ------------------------------------------------------------------

    def _resolve_path(self, test_path: str) -> Path:
        """Resolve test path relative to project root."""
        path = Path(test_path)
        if not path.is_absolute():
            path = self._project_root / path
        return path

    def get_suite(self, suite_id: str) -> Optional[TestSuite]:
        """Get a test suite by ID."""
        return self._suites.get(suite_id)

    def list_suites(self) -> List[TestSuite]:
        """List all run test suites."""
        return sorted(
            self._suites.values(),
            key=lambda s: s.run_at or 0,
            reverse=True,
        )

    def get_pass_rate(self) -> float:
        """Get overall pass rate across all suites."""
        total = 0
        passed = 0
        for suite in self._suites.values():
            for result in suite.results:
                total += 1
                if result.status == TestStatus.PASSED:
                    passed += 1
        return passed / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        total_results = sum(len(s.results) for s in self._suites.values())
        total_passed = sum(
            sum(1 for r in s.results if r.status == TestStatus.PASSED)
            for s in self._suites.values()
        )
        total_failed = sum(
            sum(1 for r in s.results if r.status == TestStatus.FAILED)
            for s in self._suites.values()
        )
        return {
            "total_suites": len(self._suites),
            "total_tests": total_results,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": total_passed / total_results if total_results > 0 else 0.0,
            "frameworks": list({s.framework for s in self._suites.values()}),
        }
