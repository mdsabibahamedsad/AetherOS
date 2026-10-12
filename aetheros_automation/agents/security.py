from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)

_SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|credential)\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)(-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----)"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)export\s+\w+_API_KEY\s*="),
]

_DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)eval\s*\("),
    re.compile(r"(?i)exec\s*\("),
    re.compile(r"(?i)__import__\s*\("),
    re.compile(r"(?i)subprocess\.(call|popen|run)\s*\(.*shell\s*=\s*True"),
    re.compile(r"(?i)os\.system\s*\("),
    re.compile(r"(?i)pickle\.loads?\s*\("),
    re.compile(r"(?i)shelve\.open\s*\("),
    re.compile(r"(?i)sql_injection|SELECT\s+.*FROM.*WHERE.*=.*['\"].*['\"]"),
]


class SecurityAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.SECURITY

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("Security agent executing: %s", task.name)

        code_path = task.metadata.get("code_path", "")
        if code_path and Path(code_path).exists():
            findings = await self.audit(code_path)
            return self._format_audit(findings)

        action = task.metadata.get("action", "")
        if action:
            allowed = await self.check_permissions(action, ctx)
            return f"Permission for '{action}': {'GRANTED' if allowed else 'DENIED'}"

        return "No code path or action provided for security check."

    async def audit(self, code_path: str) -> list[dict]:
        logger.info("Auditing: %s", code_path)
        path = Path(code_path)
        findings: list[dict] = []

        if path.is_file():
            findings.extend(await self._audit_file(path))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                findings.extend(await self._audit_file(py_file))

        return findings

    async def check_permissions(self, action: str, context: dict | None = None) -> bool:
        logger.info("Checking permission for: %s", action)
        ctx = context or {}
        permissions = ctx.get("granted_permissions", [])

        if permissions == ["*"]:
            return True
        if action in permissions:
            return True

        dangerous = any(w in action.lower() for w in (
            "delete", "shutdown", "payment", "install", "deploy", "publish"
        ))
        return not dangerous

    async def _audit_file(self, path: Path) -> list[dict]:
        findings: list[dict] = []
        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            findings.append({
                "severity": "error",
                "file": str(path),
                "line": 0,
                "message": f"Cannot read file: {e}",
            })
            return findings

        for line_no, line in enumerate(code.splitlines(), 1):
            for pat in _SENSITIVE_PATTERNS:
                if pat.search(line):
                    findings.append({
                        "severity": "critical",
                        "file": str(path),
                        "line": line_no,
                        "message": f"Sensitive data pattern detected: {pat.pattern[:50]}",
                    })
            for pat in _DANGEROUS_PATTERNS:
                if pat.search(line):
                    findings.append({
                        "severity": "warning",
                        "file": str(path),
                        "line": line_no,
                        "message": f"Dangerous pattern detected: {pat.pattern[:50]}",
                    })

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("request", "get", "post", "put", "delete"):
                            findings.append({
                                "severity": "info",
                                "file": str(path),
                                "line": node.lineno,
                                "message": f"HTTP call via {node.func.attr}() - verify TLS and auth",
                            })
                    if isinstance(node.func, ast.Name):
                        if node.func.id == "input" and path.suffix == ".py":
                            parent = getattr(node, "parent", None)
                            if not isinstance(parent, ast.Call) or not (
                                isinstance(parent.func, ast.Attribute)
                                and parent.func.attr == "eval"
                            ):
                                findings.append({
                                    "severity": "info",
                                    "file": str(path),
                                    "line": node.lineno,
                                    "message": "input() call - ensure sanitization in production",
                                })
        except SyntaxError:
            pass

        return findings

    def _format_audit(self, findings: list[dict]) -> str:
        if not findings:
            return "# Security Audit\nNo issues found."

        critical = sum(1 for f in findings if f["severity"] == "critical")
        warnings = sum(1 for f in findings if f["severity"] == "warning")
        info = sum(1 for f in findings if f["severity"] == "info")

        lines = [
            "# Security Audit",
            f"\nSummary: {critical} critical, {warnings} warnings, {info} info",
        ]
        for sev in ("critical", "warning", "info"):
            items = [f for f in findings if f["severity"] == sev]
            if items:
                lines.append(f"\n## {sev.upper()}")
                for item in items:
                    lines.append(f"\n- [{item['severity'].upper()}] {item['file']}:{item['line']}")
                    lines.append(f"  {item['message']}")

        return "\n".join(lines)


AgentRegistry.register(AgentRole.SECURITY, SecurityAgent)
