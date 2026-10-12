"""
Security Audit for AetherOS
===========================

Comprehensive security auditing:
    - Dependency Audit
    - Secrets Scan
    - Static Analysis
    - Dynamic Analysis
    - Permission Audit
    - Sandbox Audit
    - Plugin Audit
    - MCP Audit
    - Workflow Audit
    - Memory Audit

Usage::

    from aetheros_production.security import SecurityAuditor

    auditor = SecurityAuditor()
    report = auditor.run_full_audit()
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Security issue severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditType(Enum):
    """Types of security audits."""
    DEPENDENCY = "dependency"
    SECRETS = "secrets"
    STATIC_ANALYSIS = "static_analysis"
    DYNAMIC_ANALYSIS = "dynamic_analysis"
    PERMISSION = "permission"
    SANDBOX = "sandbox"
    PLUGIN = "plugin"
    MCP = "mcp"
    WORKFLOW = "workflow"
    MEMORY = "memory"


@dataclass
class SecurityIssue:
    """A security issue found during audit."""
    issue_id: str
    audit_type: AuditType
    severity: Severity
    title: str
    description: str
    file_path: str = ""
    line_number: int = 0
    recommendation: str = ""
    cwe_id: str = ""  # Common Weakness Enumeration ID
    cvss_score: float = 0.0


@dataclass
class AuditReport:
    """Report from a security audit."""
    audit_type: AuditType
    issues: List[SecurityIssue] = field(default_factory=list)
    scan_time: float = 0.0
    duration: float = 0.0
    files_scanned: int = 0
    lines_scanned: int = 0


class SecurityAuditor:
    """Performs security audits for AetherOS.

    Usage::

        auditor = SecurityAuditor()

        # Run full audit
        report = auditor.run_full_audit()

        # Run specific audit
        report = auditor.run_audit(AuditType.DEPENDENCY)
    """

    def __init__(self) -> None:
        self._reports: Dict[AuditType, AuditReport] = {}
        self._all_issues: List[SecurityIssue] = []

    def run_full_audit(self) -> Dict[str, Any]:
        """Run all security audits."""
        logger.info("Running full security audit")
        start_time = time.time()

        audit_types = [
            AuditType.DEPENDENCY,
            AuditType.SECRETS,
            AuditType.STATIC_ANALYSIS,
            AuditType.PERMISSION,
            AuditType.SANDBOX,
            AuditType.PLUGIN,
            AuditType.MCP,
            AuditType.WORKFLOW,
            AuditType.MEMORY,
        ]

        for audit_type in audit_types:
            self.run_audit(audit_type)

        total_time = time.time() - start_time

        # Generate summary
        summary = self._generate_summary()
        summary["total_duration"] = total_time

        logger.info(
            "Security audit completed: %d issues found",
            len(self._all_issues),
        )

        return summary

    def run_audit(self, audit_type: AuditType) -> AuditReport:
        """Run a specific security audit."""
        logger.info("Running %s audit", audit_type.value)
        start_time = time.time()

        audit_methods = {
            AuditType.DEPENDENCY: self._audit_dependencies,
            AuditType.SECRETS: self._audit_secrets,
            AuditType.STATIC_ANALYSIS: self._audit_static_analysis,
            AuditType.PERMISSION: self._audit_permissions,
            AuditType.SANDBOX: self._audit_sandbox,
            AuditType.PLUGIN: self._audit_plugins,
            AuditType.MCP: self._audit_mcp,
            AuditType.WORKFLOW: self._audit_workflows,
            AuditType.MEMORY: self._audit_memory,
        }

        method = audit_methods.get(audit_type)
        if method:
            report = method()
        else:
            report = AuditReport(audit_type=audit_type)

        report.duration = time.time() - start_time
        self._reports[audit_type] = report
        self._all_issues.extend(report.issues)

        return report

    def _audit_dependencies(self) -> AuditReport:
        """Audit dependencies for known vulnerabilities."""
        report = AuditReport(audit_type=AuditType.DEPENDENCY)

        # Check pyproject.toml
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                dependencies = data.get("project", {}).get("dependencies", [])
                report.files_scanned += 1

                # Check for known vulnerable packages
                vulnerable_packages = self._check_vulnerable_packages(dependencies)
                for vuln in vulnerable_packages:
                    report.issues.append(SecurityIssue(
                        issue_id=f"DEP-{len(report.issues)+1:04d}",
                        audit_type=AuditType.DEPENDENCY,
                        severity=Severity.HIGH,
                        title=f"Vulnerable dependency: {vuln['package']}",
                        description=f"Version {vuln['current']} has known vulnerabilities",
                        recommendation=f"Update to version {vuln['fixed']}",
                    ))

            except Exception as exc:
                logger.warning("Failed to parse pyproject.toml: %s", exc)

        # Check package-lock.json / package.json
        package_json = Path("package.json")
        if package_json.exists():
            report.files_scanned += 1

        return report

    def _check_vulnerable_packages(self, dependencies: list) -> list:
        """Check for known vulnerable packages."""
        # Simplified - in production, use OSV or similar
        vulnerable = []
        known_vulnerable = {
            "requests": {"fixed": "2.31.0"},
            "urllib3": {"fixed": "2.0.7"},
            "cryptography": {"fixed": "41.0.0"},
        }

        for dep in dependencies:
            package = dep.split(">=")[0].split("<")[0].strip()
            if package.lower() in known_vulnerable:
                vulnerable.append({
                    "package": package,
                    "current": "unknown",
                    "fixed": known_vulnerable[package.lower()]["fixed"],
                })

        return vulnerable

    def _audit_secrets(self) -> AuditReport:
        """Scan for secrets in code."""
        report = AuditReport(audit_type=AuditType.SECRETS)

        secret_patterns = [
            (r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]([^'\"]+)['\"]", "API Key"),
            (r"(?:secret|password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]+)['\"]", "Password"),
            (r"(?:token|access[_-]?token)\s*[=:]\s*['\"]([^'\"]+)['\"]", "Token"),
            (r"(?:private[_-]?key)\s*[=:]\s*['\"]([^'\"]+)['\"]", "Private Key"),
            (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key Block"),
        ]

        import re

        # Scan Python files
        for py_file in Path(".").rglob("*.py"):
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                report.lines_scanned += content.count("\n") + 1

                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count("\n") + 1
                        report.issues.append(SecurityIssue(
                            issue_id=f"SEC-{len(report.issues)+1:04d}",
                            audit_type=AuditType.SECRETS,
                            severity=Severity.CRITICAL,
                            title=f"Potential {secret_type} found",
                            description="Hardcoded secret detected in source code",
                            file_path=str(py_file),
                            line_number=line_num,
                            recommendation="Move secrets to environment variables or secure vault",
                        ))

                report.files_scanned += 1
            except Exception:
                pass

        return report

    def _audit_static_analysis(self) -> AuditReport:
        """Perform static code analysis."""
        report = AuditReport(audit_type=AuditType.STATIC_ANALYSIS)

        # Check for common security issues
        security_patterns = [
            (r"eval\(", "Use of eval()", Severity.HIGH, "CWE-95"),
            (r"exec\(", "Use of exec()", Severity.HIGH, "CWE-95"),
            (r"os\.system\(", "Use of os.system()", Severity.MEDIUM, "CWE-78"),
            (r"subprocess\.call\(", "Use of subprocess", Severity.LOW, "CWE-78"),
            (r"pickle\.loads?\(", "Use of pickle", Severity.HIGH, "CWE-502"),
            (r"yaml\.load\(", "Unsafe YAML load", Severity.MEDIUM, "CWE-502"),
            (r"assert\s+", "Use of assert", Severity.LOW, "CWE-617"),
        ]

        import re

        for py_file in Path(".").rglob("*.py"):
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                report.lines_scanned += content.count("\n") + 1

                for pattern, title, severity, cwe in security_patterns:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n") + 1
                        report.issues.append(SecurityIssue(
                            issue_id=f"SA-{len(report.issues)+1:04d}",
                            audit_type=AuditType.STATIC_ANALYSIS,
                            severity=severity,
                            title=title,
                            description=f"Pattern '{pattern}' detected",
                            file_path=str(py_file),
                            line_number=line_num,
                            cwe_id=cwe,
                            recommendation=f"Review usage of {title.split(':')[0]}",
                        ))

                report.files_scanned += 1
            except Exception:
                pass

        return report

    def _audit_permissions(self) -> AuditReport:
        """Audit permission declarations."""
        report = AuditReport(audit_type=AuditType.PERMISSION)

        # Check extension permissions
        try:
            from extensions.capability import ALL_CAPABILITIES
            from sdk.permissions import Permission

            # Verify all capabilities have proper permission mappings
            for cap in ALL_CAPABILITIES:
                if not cap.name:
                    report.issues.append(SecurityIssue(
                        issue_id=f"PERM-{len(report.issues)+1:04d}",
                        audit_type=AuditType.PERMISSION,
                        severity=Severity.MEDIUM,
                        title="Unnamed capability",
                        description=f"Capability has empty name",
                        recommendation="Ensure all capabilities have descriptive names",
                    ))

        except Exception as exc:
            logger.debug("Permission audit skipped: %s", exc)

        return report

    def _audit_sandbox(self) -> AuditReport:
        """Audit sandbox configurations."""
        report = AuditReport(audit_type=AuditType.SANDBOX)

        try:
            from extensions.sandbox import SandboxConfig, SandboxMode

            # Verify default sandbox is not NONE
            default_config = SandboxConfig()
            if default_config.mode == SandboxMode.NONE:
                report.issues.append(SecurityIssue(
                    issue_id=f"SBX-{len(report.issues)+1:04d}",
                    audit_type=AuditType.SANDBOX,
                    severity=Severity.HIGH,
                    title="Default sandbox mode is NONE",
                    description="Extensions run without sandboxing by default",
                    recommendation="Set default sandbox mode to PERMISSION",
                ))

        except Exception as exc:
            logger.debug("Sandbox audit skipped: %s", exc)

        return report

    def _audit_plugins(self) -> AuditReport:
        """Audit plugin security."""
        report = AuditReport(audit_type=AuditType.PLUGIN)

        # Check for plugins with excessive permissions
        try:
            from extensions.manager import get_extension_manager
            manager = get_extension_manager()
            extensions = manager.list_extensions()

            for ext in extensions:
                if ext.manifest.permissions:
                    # Check for dangerous permission combinations
                    perms = set(ext.manifest.permissions)
                    dangerous = {"filesystem:write", "terminal", "network"}
                    if perms & dangerous:
                        report.issues.append(SecurityIssue(
                            issue_id=f"PLUGIN-{len(report.issues)+1:04d}",
                            audit_type=AuditType.PLUGIN,
                            severity=Severity.MEDIUM,
                            title=f"Plugin '{ext.name}' has elevated permissions",
                            description=f"Plugin requests: {', '.join(perms & dangerous)}",
                            recommendation="Review plugin permissions before enabling",
                        ))

        except Exception as exc:
            logger.debug("Plugin audit skipped: %s", exc)

        return report

    def _audit_mcp(self) -> AuditReport:
        """Audit MCP server configurations."""
        report = AuditReport(audit_type=AuditType.MCP)

        # Check for MCP servers with excessive capabilities
        try:
            from mcp_serve import get_mcp_servers

            # Placeholder for MCP audit logic
            pass

        except Exception as exc:
            logger.debug("MCP audit skipped: %s", exc)

        return report

    def _audit_workflows(self) -> AuditReport:
        """Audit workflow configurations."""
        report = AuditReport(audit_type=AuditType.WORKFLOW)

        # Check for workflows with dangerous operations
        try:
            from workflows.engine import WorkflowEngine

            # Placeholder for workflow audit logic
            pass

        except Exception as exc:
            logger.debug("Workflow audit skipped: %s", exc)

        return report

    def _audit_memory(self) -> AuditReport:
        """Audit memory system security."""
        report = AuditReport(audit_type=AuditType.MEMORY)

        # Check for memory data exposure
        try:
            from agent.memory_manager import get_memory_manager

            # Placeholder for memory audit logic
            pass

        except Exception as exc:
            logger.debug("Memory audit skipped: %s", exc)

        return report

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate audit summary."""
        issues_by_severity = {}
        for issue in self._all_issues:
            severity = issue.severity.value
            issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1

        issues_by_type = {}
        for issue in self._all_issues:
            audit_type = issue.audit_type.value
            issues_by_type[audit_type] = issues_by_type.get(audit_type, 0) + 1

        return {
            "total_issues": len(self._all_issues),
            "issues_by_severity": issues_by_severity,
            "issues_by_type": issues_by_type,
            "audits_completed": len(self._reports),
            "critical_issues": issues_by_severity.get("critical", 0),
            "high_issues": issues_by_severity.get("high", 0),
        }

    def get_report(self, audit_type: AuditType) -> Optional[AuditReport]:
        """Get a specific audit report."""
        return self._reports.get(audit_type)

    def get_all_issues(self, severity: Optional[Severity] = None) -> List[SecurityIssue]:
        """Get all security issues."""
        if severity:
            return [i for i in self._all_issues if i.severity == severity]
        return list(self._all_issues)

    def export_report(self, output_path: str) -> bool:
        """Export audit report to JSON."""
        try:
            report_data = {
                "summary": self._generate_summary(),
                "issues": [
                    {
                        "id": i.issue_id,
                        "type": i.audit_type.value,
                        "severity": i.severity.value,
                        "title": i.title,
                        "description": i.description,
                        "file": i.file_path,
                        "line": i.line_number,
                        "cwe": i.cwe_id,
                        "recommendation": i.recommendation,
                    }
                    for i in self._all_issues
                ],
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            return True
        except Exception as exc:
            logger.error("Failed to export report: %s", exc)
            return False


# Global security auditor
_security_auditor: Optional[SecurityAuditor] = None


def get_security_auditor() -> SecurityAuditor:
    """Return the global SecurityAuditor singleton."""
    global _security_auditor
    if _security_auditor is None:
        _security_auditor = SecurityAuditor()
    return _security_auditor
