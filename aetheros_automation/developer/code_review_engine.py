from __future__ import annotations
import logging, os, re
from typing import Any

logger = logging.getLogger(__name__)

class CodeReviewEngine:
    def __init__(self):
        self._review_rules = self._load_rules()

    def _load_rules(self) -> list[dict[str, Any]]:
        return [
            {"id": "SEC001", "severity": "critical", "category": "security", "pattern": r"(?:api_key|api_secret|password|secret|token|credential)\s*=\s*['\"][^'\"]+['\"]", "message": "Hardcoded credential detected"},
            {"id": "SEC002", "severity": "high", "category": "security", "pattern": r"eval\s*\(", "message": "Use of eval() can lead to code injection"},
            {"id": "SEC003", "severity": "high", "category": "security", "pattern": r"exec\s*\(", "message": "Use of exec() can lead to code injection"},
            {"id": "SEC004", "severity": "medium", "category": "security", "pattern": r"(?:subprocess\.call|os\.system|os\.popen)\s*\(", "message": "Shell command execution should be sandboxed"},
            {"id": "PERF001", "severity": "medium", "category": "performance", "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(", "message": "Use enumerate() instead of range(len())"},
            {"id": "ERR001", "severity": "high", "category": "error_handling", "pattern": r"except\s*:", "message": "Bare except clause catches all exceptions"},
            {"id": "ERR002", "severity": "medium", "category": "error_handling", "pattern": r"except\s+\w+\s*:\s*\n\s*pass", "message": "Empty except block silently swallows errors"},
            {"id": "MAINT001", "severity": "low", "category": "maintainability", "pattern": r"def\s+\w+\([^)]*(?:self[^)]*)?\)\s*:\s*\n(?:\s*\n)*\s*(?:return|pass)", "message": "Empty function body"},
            {"id": "MAINT002", "severity": "low", "category": "maintainability", "pattern": r"class\s+\w+\(\)\s*:", "message": "Empty class definition"},
            {"id": "STYLE001", "severity": "low", "category": "style", "pattern": r"^\s{1}(?!\s)", "message": "Use 4 spaces for indentation"},
            {"id": "STYLE002", "severity": "low", "category": "style", "pattern": r"print\s*\(", "message": "Consider using logger instead of print()"},
            {"id": "BEST001", "severity": "info", "category": "best_practice", "pattern": r"TODO|FIXME|HACK|XXX", "message": "Code contains a TODO/FIXME marker"},
        ]

    def review_file(self, file_path: str, content: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for rule in self._review_rules:
            for match in re.finditer(rule["pattern"], content, re.MULTILINE):
                line_num = content[:match.start()].count("\n") + 1
                findings.append({
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "message": rule["message"],
                    "file": file_path,
                    "line": line_num,
                    "match": match.group()[:80],
                })
        return findings

    def review_project(self, project_path: str, max_files: int = 200) -> dict[str, Any]:
        all_findings: list[dict[str, Any]] = []
        stats = {"files_reviewed": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith((".", "node_modules", "__pycache__", "venv", ".venv", "target", "build", "dist", ".git"))]
            for file in files:
                if len(all_findings) >= max_files * 5:
                    break
                ext = os.path.splitext(file)[1].lower()
                if ext not in (".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift"):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    rel_path = os.path.relpath(file_path, project_path)
                    findings = self.review_file(rel_path, content)
                    all_findings.extend(findings)
                    stats["files_reviewed"] += 1
                except Exception:
                    pass
                if stats["files_reviewed"] >= max_files:
                    break
        for f in all_findings:
            sev = f["severity"]
            if sev in stats:
                stats[sev] += 1
        return {"findings": all_findings, "stats": stats, "total_findings": len(all_findings)}
