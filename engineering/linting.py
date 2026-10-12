"""
Lint Runner — runs linting tools on the codebase.

Integrates with:
  - Python: ruff, pylint, flake8
  - TypeScript/JavaScript: ESLint
  - General: custom lint rules
"""

from __future__ import annotations

import enum
import logging
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class LintSeverity(enum.Enum):
    """Severity levels for lint issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class LintIssue:
    """A single issue found by a linting tool.

    Attributes:
        id: Unique issue ID
        tool: Linting tool that found this issue
        severity: Issue severity
        message: Issue description
        file_path: File where the issue was found
        line: Line number
        column: Column number
        rule: Lint rule code
        fixable: Whether the issue is auto-fixable
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tool: str = ""
    severity: LintSeverity = LintSeverity.WARNING
    message: str = ""
    file_path: str = ""
    line: int = 0
    column: int = 0
    rule: str = ""
    fixable: bool = False


@dataclass
class LintResult:
    """Result of a linting run.

    Attributes:
        id: Unique result ID
        tool: Linting tool used
        target: What was linted (file path, directory, pattern)
        issues: List of issues found
        issue_count: Total number of issues
        error_count: Number of errors
        warning_count: Number of warnings
        passed: Whether linting passed (no errors or warnings)
        duration_seconds: Execution time
        run_at: When the lint run occurred
        command: The command used
        output: Raw output from the linting tool
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tool: str = ""
    target: str = ""
    issues: List[LintIssue] = field(default_factory=list)
    issue_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    passed: bool = True
    duration_seconds: float = 0.0
    run_at: float = field(default_factory=time.time)
    command: str = ""
    output: str = ""


class LintRunner:
    """Runs linting tools and collects results.

    Supports multiple lint tools per language and provides
    a unified result format.

    Usage:
        runner = LintRunner(event_bus)
        result = runner.lint("src/", tool="ruff")
        print(f"Found {result.issue_count} issues")
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 project_root: Optional[str] = None):
        self._event_bus = event_bus
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._results: Dict[str, LintResult] = {}

    def lint(self, target: str, tool: str = "",
             fix: bool = False, args: List[str] = None) -> LintResult:
        """Run linting on a target.

        Args:
            target: File, directory, or pattern to lint
            tool: Lint tool to use (auto-detected if empty)
            fix: Whether to apply auto-fixes
            args: Additional arguments

        Returns:
            LintResult with findings
        """
        if not tool:
            tool = self._detect_lint_tool(target)

        result = self._run_tool(tool, target, fix, args or [])
        self._results[result.id] = result

        logger.info(
            "LintRunner: %s on %s: %d issues (%d errors, %d warnings), passed=%s",
            tool, target, result.issue_count, result.error_count,
            result.warning_count, result.passed,
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.lint_completed", {
                "result_id": result.id,
                "tool": tool,
                "target": target,
                "issues": result.issue_count,
                "errors": result.error_count,
                "warnings": result.warning_count,
                "passed": result.passed,
            })

        return result

    def _detect_lint_tool(self, target: str) -> str:
        """Detect the best lint tool for the target."""
        target_path = self._resolve_path(target)

        # Check for config files
        config_checks = [
            (".pylintrc", "pylint"),
            ("pyproject.toml", "ruff"),  # ruff uses pyproject.toml
            (".ruff.toml", "ruff"),
            (".eslintrc.js", "eslint"),
            (".eslintrc.json", "eslint"),
            (".eslintrc.yaml", "eslint"),
        ]

        for config_file, tool in config_checks:
            if (self._project_root / config_file).exists():
                return tool

        # Check file extension
        if target_path.is_file():
            ext = target_path.suffix.lower()
            if ext == ".py":
                return "ruff"
            elif ext in (".js", ".ts", ".tsx", ".jsx"):
                return "eslint"
            return "ruff"

        # Default: guess from common files in target
        try:
            for entry in target_path.iterdir():
                if entry.name.endswith(".py"):
                    return "ruff"
                elif entry.name.endswith((".js", ".ts", ".tsx")):
                    return "eslint"
        except Exception:
            pass

        return "ruff"

    def _run_tool(self, tool: str, target: str,
                  fix: bool, args: List[str]) -> LintResult:
        """Run a specific linting tool."""
        runners = {
            "ruff": self._run_ruff,
            "pylint": self._run_pylint,
            "eslint": self._run_eslint,
            "flake8": self._run_flake8,
        }

        runner = runners.get(tool, self._run_ruff)
        return runner(target, fix, args)

    def _run_ruff(self, target: str, fix: bool, args: List[str]) -> LintResult:
        """Run ruff linting."""
        result = LintResult(tool="ruff", target=target)
        start = time.time()

        cmd = ["python", "-m", "ruff", "check", target, "--output-format=concise"]
        if fix:
            cmd.append("--fix")

        cmd.extend(args)
        result.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            result.output = proc.stdout + proc.stderr
            result.duration_seconds = time.time() - start

            # Parse output
            for line in result.output.splitlines():
                line = line.strip()
                if not line:
                    continue

                # ruff format: file:line:col: severity message Rule
                # Use rsplit from the right to handle Windows paths with colons (e.g. C:\...)
                parts = line.rsplit(":", 3)
                if len(parts) >= 4:
                    file_part = parts[0].strip()
                    try:
                        line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                        col_num = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
                    except (ValueError, IndexError):
                        line_num, col_num = 0, 0

                    severity_str = parts[3].strip() if len(parts) > 3 else ""
                    message_parts = line.split(" ", 1)
                    message = message_parts[-1] if len(message_parts) > 1 else ""

                    if "Error" in severity_str or "F" in line:
                        severity = LintSeverity.ERROR
                    elif "Warning" in severity_str or "W" in line:
                        severity = LintSeverity.WARNING
                    else:
                        severity = LintSeverity.INFO

                    # Extract rule code
                    rule = ""
                    rule_match = re.search(r'[A-Z]\d{3}', line)
                    if rule_match:
                        rule = rule_match.group(0)

                    issue = LintIssue(
                        tool="ruff",
                        severity=severity,
                        message=message or line[:100],
                        file_path=file_part,
                        line=line_num,
                        column=col_num,
                        rule=rule,
                        fixable="safe fix" in line or "FIXABLE" in line.upper(),
                    )
                    result.issues.append(issue)

            result.issue_count = len(result.issues)
            result.error_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.ERROR
            )
            result.warning_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.WARNING
            )
            result.passed = result.error_count == 0 and result.issue_count == 0

        except FileNotFoundError:
            result.output = "ruff not found. Install with: pip install ruff"
            result.passed = False
        except subprocess.TimeoutExpired:
            result.output = "ruff timed out"
            result.passed = False

        return result

    def _run_pylint(self, target: str, fix: bool, args: List[str]) -> LintResult:
        """Run pylint."""
        result = LintResult(tool="pylint", target=target)
        start = time.time()

        cmd = ["python", "-m", "pylint", target, "--output-format=text"]
        cmd.extend(args)
        result.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            result.output = proc.stdout + proc.stderr
            result.duration_seconds = time.time() - start

            # Parse pylint output
            for line in result.output.splitlines():
                line = line.strip()
                if ": " in line and line[0].isalpha():
                    # pylint format: file:line:col: category (code): message
                    match = re.match(
                        r'(.+?):(\d+):(\d+):\s*(\w+)\s*\((.+?)\):\s*(.+)',
                        line,
                    )
                    if match:
                        severity_map = {
                            "C": LintSeverity.INFO,
                            "R": LintSeverity.HINT,
                            "W": LintSeverity.WARNING,
                            "E": LintSeverity.ERROR,
                            "F": LintSeverity.ERROR,
                        }
                        sev = severity_map.get(match.group(4)[:1], LintSeverity.INFO)

                        issue = LintIssue(
                            tool="pylint",
                            severity=sev,
                            message=match.group(6),
                            file_path=match.group(1),
                            line=int(match.group(2)),
                            column=int(match.group(3)),
                            rule=match.group(5),
                        )
                        result.issues.append(issue)

            result.issue_count = len(result.issues)
            result.error_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.ERROR
            )
            result.warning_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.WARNING
            )
            result.passed = result.error_count == 0

        except FileNotFoundError:
            result.output = "pylint not found"
        except subprocess.TimeoutExpired:
            result.output = "pylint timed out"

        return result

    def _run_eslint(self, target: str, fix: bool, args: List[str]) -> LintResult:
        """Run ESLint."""
        result = LintResult(tool="eslint", target=target)
        start = time.time()

        cmd = ["npx", "eslint", target, "--format=compact"]
        if fix:
            cmd.append("--fix")
        cmd.extend(args)
        result.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            result.duration_seconds = time.time() - start

            # Parse ESLint compact format
            for line in proc.stdout.splitlines():
                line = line.strip()
                if ": " in line and ("Error" in line or "Warning" in line):
                    parts = line.split(": ", 1)
                    file_info = parts[0]
                    message = parts[1] if len(parts) > 1 else ""

                    match = re.match(r'(.+?):\s*line\s*(\d+),\s*col\s*(\d+)', file_info)
                    if match:
                        sev = LintSeverity.ERROR if "Error" in line else LintSeverity.WARNING
                        issue = LintIssue(
                            tool="eslint",
                            severity=sev,
                            message=message[:200],
                            file_path=match.group(1),
                            line=int(match.group(2)),
                            column=int(match.group(3)),
                        )
                        result.issues.append(issue)

            result.output = proc.stdout + proc.stderr
            result.issue_count = len(result.issues)
            result.error_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.ERROR
            )
            result.warning_count = sum(
                1 for i in result.issues if i.severity == LintSeverity.WARNING
            )
            result.passed = result.error_count == 0

        except FileNotFoundError:
            result.output = "ESLint not found"
        except subprocess.TimeoutExpired:
            result.output = "ESLint timed out"

        return result

    def _run_flake8(self, target: str, fix: bool, args: List[str]) -> LintResult:
        """Run flake8."""
        result = LintResult(tool="flake8", target=target)
        start = time.time()

        cmd = ["python", "-m", "flake8", target]
        cmd.extend(args)
        result.command = " ".join(cmd)

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            result.output = proc.stdout + proc.stderr
            result.duration_seconds = time.time() - start

            for line in result.output.splitlines():
                line = line.strip()
                if ": " in line and line.count(":") >= 2:
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        issue = LintIssue(
                            tool="flake8",
                            severity=LintSeverity.WARNING,
                            message=parts[3].strip(),
                            file_path=parts[0].strip(),
                            line=int(parts[1]) if parts[1].strip().isdigit() else 0,
                            column=int(parts[2]) if parts[2].strip().isdigit() else 0,
                            rule=parts[3].strip().split(" ")[0] if " " in parts[3] else "",
                        )
                        result.issues.append(issue)

            result.issue_count = len(result.issues)
            result.passed = result.issue_count == 0

        except FileNotFoundError:
            result.output = "flake8 not found"

        return result

    def _resolve_path(self, target: str) -> Path:
        """Resolve target path relative to project root."""
        path = Path(target)
        if not path.is_absolute():
            path = self._project_root / path
        return path

    def apply_fixes(self, target: str, tool: str = "ruff") -> LintResult:
        """Apply auto-fixes to a target.

        Args:
            target: File or directory to fix
            tool: Lint tool to use for fixes

        Returns:
            LintResult showing what was fixed
        """
        return self.lint(target, tool=tool, fix=True)

    def get_result(self, result_id: str) -> Optional[LintResult]:
        """Get a lint result by ID."""
        return self._results.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics."""
        return {
            "total_runs": len(self._results),
            "total_issues": sum(r.issue_count for r in self._results.values()),
            "total_errors": sum(r.error_count for r in self._results.values()),
            "passed_runs": sum(1 for r in self._results.values() if r.passed),
            "tools_used": list({r.tool for r in self._results.values()}),
        }
