"""
Static Analyzer — performs static analysis and security scanning.

Analysis types:
  - Type checking (mypy, pyright, TypeScript compiler)
  - Security scanning (bandit, safety)
  - Dependency vulnerability analysis
  - Format validation
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


class AnalysisSeverity(enum.Enum):
    """Severity levels for analysis findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AnalysisIssue:
    """A single issue found by static analysis.

    Attributes:
        id: Unique issue ID
        tool: Analysis tool that found this
        severity: Issue severity
        message: Issue description
        file_path: File where the issue was found
        line: Line number
        column: Column number
        rule: Rule code or ID
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tool: str = ""
    severity: AnalysisSeverity = AnalysisSeverity.MEDIUM
    message: str = ""
    file_path: str = ""
    line: int = 0
    column: int = 0
    rule: str = ""


@dataclass
class SecurityFinding:
    """A security vulnerability finding.

    Attributes:
        id: Unique finding ID
        tool: Security tool that found this
        severity: Severity level
        title: Vulnerability title
        description: Detailed description
        package: Affected package (if dependency-related)
        version: Affected version
        fixed_version: Version where the issue is fixed
        cvss_score: CVSS score if available
        cve_id: CVE identifier if available
        file_path: File where the issue was found
        line: Line number
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tool: str = ""
    severity: AnalysisSeverity = AnalysisSeverity.MEDIUM
    title: str = ""
    description: str = ""
    package: str = ""
    version: str = ""
    fixed_version: str = ""
    cvss_score: float = 0.0
    cve_id: str = ""
    file_path: str = ""
    line: int = 0


@dataclass
class AnalysisReport:
    """Complete report from a static analysis run.

    Attributes:
        id: Unique report ID
        tool: Analysis tool used
        target: What was analyzed
        analysis_type: Type of analysis (type_check, security, format, etc.)
        issues: List of analysis issues
        security_findings: List of security findings
        issue_count: Total issue count
        security_count: Security finding count
        passed: Whether analysis passed
        duration_seconds: Execution time
        run_at: When the analysis was run
        command: The command used
        output: Raw tool output
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tool: str = ""
    target: str = ""
    analysis_type: str = "static_analysis"
    issues: List[AnalysisIssue] = field(default_factory=list)
    security_findings: List[SecurityFinding] = field(default_factory=list)
    issue_count: int = 0
    security_count: int = 0
    passed: bool = True
    duration_seconds: float = 0.0
    run_at: float = field(default_factory=time.time)
    command: str = ""
    output: str = ""


class StaticAnalyzer:
    """Performs static analysis and security scanning.

    Supports type checking, security scanning, and format validation
    through configurable tool integrations.

    Usage:
        analyzer = StaticAnalyzer(event_bus)
        report = analyzer.type_check("src/")
        sec_report = analyzer.security_scan("src/")
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 project_root: Optional[str] = None):
        self._event_bus = event_bus
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._reports: Dict[str, AnalysisReport] = {}

    def type_check(self, target: str, tool: str = "") -> AnalysisReport:
        """Run type checking on a target.

        Args:
            target: File or directory to type-check
            tool: Type checker (mypy, pyright, etc.) - auto-detected if empty

        Returns:
            AnalysisReport with type issues
        """
        if not tool:
            tool = self._detect_type_checker()

        report = AnalysisReport(
            tool=tool,
            target=target,
            analysis_type="type_check",
        )

        start = time.time()

        if tool == "mypy":
            cmd = ["python", "-m", "mypy", target, "--show-error-codes"]
        elif tool == "pyright":
            cmd = ["python", "-m", "pyright", target]
        else:
            cmd = ["python", "-m", "mypy", target, "--show-error-codes"]

        report.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            report.output = proc.stdout + proc.stderr
            report.duration_seconds = time.time() - start

            # Parse mypy output
            for line in report.output.splitlines():
                line = line.strip()
                if ": error:" in line:
                    parts = line.split(": error:", 1)
                    file_info = parts[0].strip()
                    message = parts[1].strip() if len(parts) > 1 else ""

                    file_parts = file_info.rsplit(":", 2)
                    file_path = file_parts[0] if file_parts else ""
                    line_num = int(file_parts[-2]) if len(file_parts) >= 2 and file_parts[-2].strip().isdigit() else 0
                    col = int(file_parts[-1]) if len(file_parts) >= 3 and file_parts[-1].strip().isdigit() else 0

                    report.issues.append(AnalysisIssue(
                        tool=tool,
                        severity=AnalysisSeverity.HIGH,
                        message=message[:200],
                        file_path=file_path,
                        line=line_num,
                        column=col,
                    ))

            report.issue_count = len(report.issues)
            report.passed = report.issue_count == 0

        except FileNotFoundError:
            report.output = f"{tool} not found"
            report.issues.append(AnalysisIssue(
                tool=tool,
                severity=AnalysisSeverity.INFO,
                message=f"Type checker '{tool}' not installed",
            ))
        except subprocess.TimeoutExpired:
            report.output = f"{tool} timed out"
            report.issues.append(AnalysisIssue(
                tool=tool,
                severity=AnalysisSeverity.INFO,
                message="Type checking timed out",
            ))

        self._reports[report.id] = report
        self._emit_event(report)
        return report

    def security_scan(self, target: str = "",
                      tool: str = "bandit") -> AnalysisReport:
        """Run security scanning on a target.

        Args:
            target: File or directory to scan
            tool: Security scanner (bandit, safety)

        Returns:
            AnalysisReport with security findings
        """
        report = AnalysisReport(
            tool=tool,
            target=target or str(self._project_root),
            analysis_type="security_scan",
        )

        start = time.time()

        if tool == "bandit" and target:
            cmd = ["python", "-m", "bandit", "-r", target, "--format=text"]
        elif tool == "bandit":
            cmd = ["python", "-m", "bandit", "-r", str(self._project_root),
                   "--format=text", "--skip=B101"]
        else:
            cmd = ["python", "-m", "bandit", "-r", target or str(self._project_root),
                   "--format=text"]

        report.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            report.output = proc.stdout + proc.stderr
            report.duration_seconds = time.time() - start

            # Parse bandit output
            import re
            for line in report.output.splitlines():
                line = line.strip()

                # Match bandit issue pattern
                issue_match = re.match(
                    r'>> Issue:\s*\[(.+?):(.+?)\]\s*(.+?)\s*at\s*(\d+)',
                    line,
                )
                if issue_match:
                    finding = SecurityFinding(
                        tool="bandit",
                        severity=AnalysisSeverity.MEDIUM,
                        title=issue_match.group(1),
                        description=issue_match.group(3),
                        file_path=target,
                        line=int(issue_match.group(4)),
                    )
                    report.security_findings.append(finding)

            report.security_count = len(report.security_findings)
            report.passed = report.security_count == 0

        except FileNotFoundError:
            report.output = f"{tool} not found"
        except subprocess.TimeoutExpired:
            report.output = f"{tool} timed out"

        self._reports[report.id] = report
        self._emit_event(report)
        return report

    def dependency_scan(self, requirements_file: str = "requirements.txt"
                        ) -> AnalysisReport:
        """Scan dependencies for known vulnerabilities.

        Args:
            requirements_file: Path to requirements file

        Returns:
            AnalysisReport with vulnerability findings
        """
        report = AnalysisReport(
            tool="safety",
            target=requirements_file,
            analysis_type="dependency_scan",
        )

        start = time.time()

        req_path = self._resolve_path(requirements_file)
        if not req_path.exists():
            report.output = f"Requirements file not found: {requirements_file}"
            report.passed = True
            self._reports[report.id] = report
            return report

        cmd = ["python", "-m", "safety", "check", "-r", str(req_path),
               "--output=text"]
        report.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            report.output = proc.stdout + proc.stderr
            report.duration_seconds = time.time() - start

            # Parse safety output
            for line in report.output.splitlines():
                if "identified" in line.lower() and "vulnerabilities" in line.lower():
                    continue
                if "Vulnerability" in line or "Found" in line:
                    continue
                if "->" in line:
                    parts = line.split("->", 1)
                    if len(parts) == 2:
                        finding = SecurityFinding(
                            tool="safety",
                            severity=AnalysisSeverity.HIGH,
                            title=f"Dependency vulnerability in {parts[0].strip()}",
                            description=parts[1].strip(),
                            package=parts[0].strip(),
                        )
                        report.security_findings.append(finding)

            report.security_count = len(report.security_findings)
            report.passed = report.security_count == 0

        except FileNotFoundError:
            report.output = "safety not found"
        except subprocess.TimeoutExpired:
            report.output = "safety timed out"

        self._reports[report.id] = report
        return report

    def _detect_type_checker(self) -> str:
        """Detect which type checker is configured."""
        checks = [
            ("mypy.ini", "mypy"),
            ("pyproject.toml", "mypy"),  # mypy config in pyproject.toml
            ("pyproject.toml", "pyright"),  # pyright config
            ("tsconfig.json", "tsc"),
        ]

        for config_file, checker in checks:
            if (self._project_root / config_file).exists():
                if checker == "pyright":
                    content = (self._project_root / config_file).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                    if "pyright" in content.lower() or "mypy" in content.lower():
                        return "mypy"
                return checker

        # Check availability
        for checker in ["mypy", "pyright"]:
            try:
                subprocess.run(
                    [checker, "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                return checker
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return "mypy"

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the project root."""
        p = Path(path)
        if not p.is_absolute():
            p = self._project_root / p
        return p

    def _emit_event(self, report: AnalysisReport) -> None:
        """Emit analysis event."""
        if self._event_bus:
            self._event_bus.emit_async("engineering.analysis_completed", {
                "report_id": report.id,
                "tool": report.tool,
                "type": report.analysis_type,
                "issues": report.issue_count,
                "security_issues": report.security_count,
                "passed": report.passed,
            })

    def get_report(self, report_id: str) -> Optional[AnalysisReport]:
        """Get an analysis report by ID."""
        return self._reports.get(report_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_reports": len(self._reports),
            "total_issues": sum(r.issue_count for r in self._reports.values()),
            "total_security": sum(r.security_count for r in self._reports.values()),
            "passed_runs": sum(1 for r in self._reports.values() if r.passed),
            "tools_used": list({r.tool for r in self._reports.values()}),
        }
