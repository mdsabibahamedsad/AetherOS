from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

from aetheros_automation.terminal.runner import TerminalRunner

logger = logging.getLogger(__name__)


class CodeReviewer:
    """Static analysis, linting, formatting, and fix suggestions."""

    # ------------------------------------------------------------------
    # review
    # ------------------------------------------------------------------

    @staticmethod
    async def review(file_path: str) -> list[dict[str, Any]]:
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = p.suffix.lower()
        issues: list[dict[str, Any]] = []

        source = p.read_text(encoding="utf-8", errors="replace")

        # generic checks
        issues.extend(_check_line_length(source, file_path))
        issues.extend(_check_trailing_whitespace(source, file_path))
        issues.extend(_check_tabs(source, file_path))
        issues.extend(_check_syntax_errors(source, suffix, file_path))

        # language-specific linters
        lang_issues = await _run_linter(file_path, suffix)
        issues.extend(lang_issues)

        return issues

    @staticmethod
    async def suggest_fix(file_path: str, issue: dict[str, Any]) -> str:
        """Generate a suggested fix for a single issue."""
        p = Path(file_path).resolve()
        source = p.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines(keepends=True)

        line_num = issue.get("line", 0)
        rule = issue.get("rule", "")
        message = issue.get("message", "")

        if rule == "line-too-long" and line_num > 0 and line_num <= len(lines):
            line = lines[line_num - 1].rstrip("\n")
            indent = len(line) - len(line.lstrip())
            split_point = _find_split_point(line, 88)
            if split_point > 0:
                continuation = " " * (indent + 4)
                return (
                    line[:split_point].rstrip()
                    + "\n"
                    + continuation
                    + line[split_point:].strip()
                )

        if rule in ("trailing-whitespace",) and line_num > 0 and line_num <= len(lines):
            return lines[line_num - 1].rstrip() + "\n"

        if rule in ("no-newline-at-end",):
            return source.rstrip("\n") + "\n"

        return f"# Manual fix needed: {message}"

    # ------------------------------------------------------------------
    # format
    # ------------------------------------------------------------------

    @staticmethod
    async def format_code(file_path: str, formatter: str = "auto") -> dict[str, Any]:
        p = Path(file_path).resolve()
        suffix = p.suffix.lower()

        if formatter == "auto":
            formatter = _auto_formatter(suffix)

        if formatter == "none":
            return {"success": False, "message": "No formatter available for this file type"}

        cmd = f"{formatter} {file_path}"
        result = await TerminalRunner.run(cmd)
        return {
            "success": result["exit_code"] == 0,
            "formatter": formatter,
            "output": result["stdout"] + "\n" + result["stderr"],
        }

    # ------------------------------------------------------------------
    # lint
    # ------------------------------------------------------------------

    @staticmethod
    async def lint(file_path: str) -> list[dict[str, Any]]:
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return await _run_linter(file_path, p.suffix.lower())


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _check_line_length(source: str, file_path: str, max_len: int = 88) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if len(line) > max_len and not line.startswith("#"):
            issues.append({
                "line": i,
                "column": max_len + 1,
                "rule": "line-too-long",
                "message": f"Line exceeds {max_len} characters ({len(line)})",
                "severity": "warning",
                "file": file_path,
            })
    return issues


def _check_trailing_whitespace(source: str, file_path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if line.rstrip("\n").endswith(" "):
            issues.append({
                "line": i,
                "column": len(line),
                "rule": "trailing-whitespace",
                "message": "Trailing whitespace detected",
                "severity": "warning",
                "file": file_path,
            })
    if source and not source.endswith("\n"):
        issues.append({
            "line": len(source.splitlines()),
            "column": 0,
            "rule": "no-newline-at-end",
            "message": "No newline at end of file",
            "severity": "style",
            "file": file_path,
        })
    return issues


def _check_tabs(source: str, file_path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if "\t" in line:
            issues.append({
                "line": i,
                "column": line.index("\t") + 1,
                "rule": "tab-indentation",
                "message": "Tab character used (expect spaces)",
                "severity": "style",
                "file": file_path,
            })
            break
    return issues


_SYNTAX_CHECKERS: dict[str, str] = {
    ".py": "python -c \"import ast; ast.parse(open('{path}').read())\"",
    ".json": "python -c \"import json; json.load(open('{path}'))\"",
    ".yaml": "python -c \"import yaml; yaml.safe_load(open('{path}'))\"",
    ".yml": "python -c \"import yaml; yaml.safe_load(open('{path}'))\"",
}


def _check_syntax_errors(source: str, suffix: str, file_path: str) -> list[dict[str, Any]]:
    checker = _SYNTAX_CHECKERS.get(suffix)
    if not checker:
        return []
    cmd = checker.format(path=file_path)
    try:
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return [{
                "line": 0,
                "column": 0,
                "rule": "syntax-error",
                "message": result.stderr.strip() or result.stdout.strip(),
                "severity": "error",
                "file": file_path,
            }]
    except Exception as exc:
        return [{
            "line": 0,
            "column": 0,
            "rule": "syntax-check-error",
            "message": str(exc),
            "severity": "error",
            "file": file_path,
        }]
    return []


_LINTERS: dict[str, list[str]] = {
    ".py": ["ruff check --no-fix {path}", "pylint {path}", "pyright {path}"],
    ".js": ["npx eslint {path}"],
    ".ts": ["npx eslint {path}", "npx tsc --noEmit"],
    ".tsx": ["npx eslint {path}", "npx tsc --noEmit"],
    ".jsx": ["npx eslint {path}"],
    ".json": ["python -m json.tool {path}"],
}

_FORMATTERS: dict[str, str] = {
    ".py": "ruff format",
    ".js": "npx prettier --write",
    ".ts": "npx prettier --write",
    ".tsx": "npx prettier --write",
    ".jsx": "npx prettier --write",
    ".json": "npx prettier --write",
    ".yaml": "npx prettier --write",
    ".yml": "npx prettier --write",
    ".md": "npx prettier --write",
}


def _auto_formatter(suffix: str) -> str:
    return _FORMATTERS.get(suffix, "none")


async def _run_linter(file_path: str, suffix: str) -> list[dict[str, Any]]:
    linters = _LINTERS.get(suffix, [])
    if not linters:
        return []

    issues: list[dict[str, Any]] = []
    for lint_cmd in linters:
        cmd = lint_cmd.format(path=file_path)
        try:
            result = await TerminalRunner.run(cmd)
            output = result["stdout"] + "\n" + result["stderr"]
            parsed = _parse_linter_output(output, file_path)
            issues.extend(parsed)
        except Exception as exc:
            issues.append({
                "line": 0,
                "column": 0,
                "rule": "linter-error",
                "message": f"Failed to run {lint_cmd}: {exc}",
                "severity": "error",
                "file": file_path,
            })

    return issues


_LINTER_OUTPUT_RE = re.compile(
    r"^(?:.*?):(\d+):(\d+):\s*(\w+):\s*(.+)$", re.MULTILINE
)


def _parse_linter_output(output: str, file_path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for match in _LINTER_OUTPUT_RE.finditer(output):
        issues.append({
            "line": int(match.group(1)),
            "column": int(match.group(2)),
            "rule": match.group(3).lower().replace(" ", "-"),
            "message": match.group(4).strip(),
            "severity": match.group(3).lower(),
            "file": file_path,
        })
    return issues


def _find_split_point(line: str, max_len: int) -> int:
    """Find a good character position to split a long line."""
    candidates = [i for i, c in enumerate(line) if c in (",", " ", "(", ")")]
    candidates = [i for i in candidates if max_len * 0.6 <= i <= max_len]
    return candidates[-1] if candidates else max_len
