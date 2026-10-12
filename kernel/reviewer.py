"""
Reviewer Agent — automatically reviews code, research, documents, plans,
summaries, and other artifacts produced by agents.

The Reviewer analyzes artifacts for:
  - Correctness (logical errors, bugs, inconsistencies)
  - Completeness (missing pieces, edge cases)
  - Quality (code style, documentation, performance)
  - Security (vulnerabilities, unsafe patterns)
  - Best practices (adherence to conventions)

Provides structured feedback with severity levels and actionable suggestions.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ReviewSeverity(enum.IntEnum):
    INFO = 0
    MINOR = 1
    MAJOR = 2
    CRITICAL = 3
    BLOCKER = 4


class ReviewCategory(enum.Enum):
    CODE = "code"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    PLAN = "plan"
    SUMMARY = "summary"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLETENESS = "completeness"
    LOGIC = "logic"


@dataclass
class ReviewFinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: ReviewCategory = ReviewCategory.CODE
    severity: ReviewSeverity = ReviewSeverity.INFO
    title: str = ""
    description: str = ""
    location: str = ""
    suggestion: str = ""
    line_number: Optional[int] = None
    code_snippet: str = ""


@dataclass
class ReviewResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    artifact_id: str = ""
    artifact_type: str = ""
    reviewer_id: str = ""
    status: str = "completed"
    overall_score: float = 1.0
    findings: List[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    passed: bool = True
    created_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def blocker_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.BLOCKER)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.CRITICAL)

    @property
    def major_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.MAJOR)


class ReviewerAgent:
    """Automatically reviews artifacts produced by agents.

    Performs rule-based, pattern-based, and quality reviews on code,
    research, documentation, plans, and summaries.

    Usage:
        reviewer = ReviewerAgent(event_bus)
        result = reviewer.review_code("def foo(): pass", language="python")
        result = reviewer.review_documentation("# My Doc")
        result = reviewer.review_plan(plan_dict)
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 min_score_to_pass: float = 0.7):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._min_score_to_pass = min_score_to_pass
        self._results: Dict[str, ReviewResult] = {}
        self._custom_rules: List[Dict[str, Any]] = []
        self._review_callbacks: List[Any] = []

    # ------------------------------------------------------------------
    # Code review
    # ------------------------------------------------------------------

    def review_code(self, code: str, language: str = "",
                    context: Dict[str, Any] = None) -> ReviewResult:
        start = time.time()
        findings: List[ReviewFinding] = []

        findings.extend(self._check_syntax_errors(code, language))
        findings.extend(self._check_security_issues(code, language))
        findings.extend(self._check_performance_issues(code, language))
        findings.extend(self._check_style_issues(code, language))
        findings.extend(self._check_completeness(code, language, context or {}))

        for rule in self._custom_rules:
            if rule.get("type") == "code" or rule.get("type") == "*":
                findings.extend(self._apply_custom_rule(rule, code, language))

        return self._finalize("code", language, findings, code[:200], start)

    def _check_syntax_errors(self, code: str, language: str) -> List[ReviewFinding]:
        findings = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if language == "python":
                if "import " in stripped and "import " == stripped[:7]:
                    parts = stripped.split()
                    if len(parts) > 1 and parts[1].strip() == "":
                        findings.append(ReviewFinding(
                            category=ReviewCategory.CODE,
                            severity=ReviewSeverity.MAJOR,
                            title="Incomplete import statement",
                            description=f"Line {i}: import statement appears incomplete",
                            line_number=i,
                            suggestion="Specify what to import: 'import module_name'",
                        ))

                if stripped.startswith("except:") and stripped == "except:":
                    findings.append(ReviewFinding(
                        category=ReviewCategory.CODE,
                        severity=ReviewSeverity.MINOR,
                        title="Bare except clause",
                        description=f"Line {i}: bare except catches all exceptions",
                        line_number=i,
                        suggestion="Use 'except Exception:' to avoid catching SystemExit/KeyboardInterrupt",
                    ))

            common_patterns = [
                ("eval(", "Avoid eval() - can execute arbitrary code", ReviewSeverity.CRITICAL),
                ("exec(", "Avoid exec() - can execute arbitrary code", ReviewSeverity.CRITICAL),
                ("__import__(", "Use import statements instead of __import__()", ReviewSeverity.MAJOR),
            ]
            for pattern, msg, severity in common_patterns:
                if pattern in stripped:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.SECURITY,
                        severity=severity,
                        title=f"Use of {pattern[:-1]}()",
                        description=f"Line {i}: {msg}",
                        line_number=i,
                        suggestion=f"Replace {pattern}... with safe alternatives",
                    ))

        return findings

    def _check_security_issues(self, code: str, language: str) -> List[ReviewFinding]:
        findings = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip().lower()

            security_patterns = [
                ("password", "Hardcoded password detected", ReviewSeverity.CRITICAL),
                ("api_key", "Hardcoded API key detected", ReviewSeverity.CRITICAL),
                ("secret", "Potential secret hardcoded", ReviewSeverity.CRITICAL),
                ("token", "Potential token hardcoded", ReviewSeverity.MAJOR),
                ("subprocess", "Subprocess call - validate arguments", ReviewSeverity.MAJOR),
                ("os.system(", "Use subprocess instead of os.system()", ReviewSeverity.MAJOR),
                ("pickle.load", "Unpickling untrusted data can be dangerous", ReviewSeverity.CRITICAL),
                ("shell=True", "shell=True is a security risk", ReviewSeverity.CRITICAL),
                ("sqlite3.execute(", "Potential SQL injection - use parameterized queries", ReviewSeverity.CRITICAL),
            ]
            for pattern, msg, severity in security_patterns:
                if pattern in stripped:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.SECURITY,
                        severity=severity,
                        title=f"Security: {pattern}",
                        description=f"Line {i}: {msg}",
                        line_number=i,
                        suggestion=f"Review and secure the use of '{pattern}'",
                    ))

        return findings

    def _check_performance_issues(self, code: str, language: str) -> List[ReviewFinding]:
        findings = []
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            perf_patterns = [
                (".append(", "Consider list comprehension instead of loop+append", ReviewSeverity.MINOR),
                ("for ", "Nested loops may impact performance", ReviewSeverity.INFO),
            ]
            for pattern, msg, severity in perf_patterns:
                if pattern in stripped:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.PERFORMANCE,
                        severity=severity,
                        title=f"Performance: {pattern}",
                        description=f"Line {i}: {msg}",
                        line_number=i,
                        suggestion=msg,
                    ))

        return findings

    def _check_style_issues(self, code: str, language: str) -> List[ReviewFinding]:
        findings = []
        lines = code.split("\n")

        long_lines = [(i, l) for i, l in enumerate(lines, 1) if len(l) > 120]
        for line_no, line in long_lines[:5]:
            findings.append(ReviewFinding(
                category=ReviewCategory.STYLE,
                severity=ReviewSeverity.MINOR,
                title="Line too long",
                description=f"Line {line_no}: {len(line)} chars (max 120)",
                line_number=line_no,
                suggestion="Break long lines into multiple lines for readability",
            ))

        has_todos = False
        for i, line in enumerate(lines, 1):
            if "TODO" in line or "FIXME" in line or "HACK" in line:
                if not has_todos:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.COMPLETENESS,
                        severity=ReviewSeverity.INFO,
                        title="Unresolved TODO/FIXME",
                        description=f"Line {i}: {line.strip()[:80]}",
                        line_number=i,
                        suggestion="Resolve TODO items before finalizing",
                    ))
                    has_todos = True

        return findings

    def _check_completeness(self, code: str, language: str,
                            context: Dict[str, Any]) -> List[ReviewFinding]:
        findings = []
        if "def " not in code and "class " not in code and language:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.INFO,
                title="No function or class definitions",
                description="Code appears to be a script without functions/classes",
                suggestion="Consider wrapping logic in functions for reusability",
            ))

        if language == "python":
            has_docstring = '"""' in code or "'''" in code
            if context.get("expect_docstring", True) and not has_docstring:
                findings.append(ReviewFinding(
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.MINOR,
                    title="Missing docstring",
                    description="Python module/function has no docstring",
                    suggestion="Add docstring describing purpose and usage",
                ))

        return findings

    # ------------------------------------------------------------------
    # Documentation review
    # ------------------------------------------------------------------

    def review_documentation(self, content: str, doc_type: str = "markdown",
                             context: Dict[str, Any] = None) -> ReviewResult:
        start = time.time()
        findings: List[ReviewFinding] = []

        if doc_type == "markdown":
            findings.extend(self._review_markdown(content))

        findings.extend(self._check_doc_completeness(content, context or {}))
        return self._finalize("documentation", doc_type, findings, content[:200], start)

    def _review_markdown(self, content: str) -> List[ReviewFinding]:
        findings = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "#" or stripped.startswith("##") and len(stripped.split()) < 2:
                findings.append(ReviewFinding(
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.MINOR,
                    title="Empty heading",
                    description=f"Line {i}: heading has no content after markers",
                    line_number=i,
                    suggestion="Add descriptive heading text",
                ))

        if len(lines) < 3:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.MAJOR,
                title="Very short document",
                description="Document has fewer than 3 lines",
                suggestion="Expand documentation with more details",
            ))

        return findings

    def _check_doc_completeness(self, content: str,
                                 context: Dict[str, Any]) -> List[ReviewFinding]:
        findings = []
        required = context.get("required_sections", [])
        for section in required:
            if f"# {section}" not in content and f"## {section}" not in content:
                findings.append(ReviewFinding(
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.MAJOR,
                    title=f"Missing required section: {section}",
                    description=f"Documentation is missing the '{section}' section",
                    suggestion=f"Add a '# {section}' section to the document",
                ))
        return findings

    # ------------------------------------------------------------------
    # Plan review
    # ------------------------------------------------------------------

    def review_plan(self, plan: Dict[str, Any]) -> ReviewResult:
        start = time.time()
        findings: List[ReviewFinding] = []

        steps = plan.get("steps", [])
        if not steps:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.BLOCKER,
                title="Empty plan",
                description="Plan has no steps defined",
                suggestion="Define at least one step in the plan",
            ))
        else:
            step_ids = set()
            for i, step in enumerate(steps):
                step_id = step.get("id", f"step_{i}")
                if step_id in step_ids:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.LOGIC,
                        severity=ReviewSeverity.MAJOR,
                        title=f"Duplicate step ID: {step_id}",
                        description=f"Step {i} has a duplicate ID",
                        suggestion="Ensure each step has a unique ID",
                    ))
                step_ids.add(step_id)

                deps = step.get("dependencies", [])
                for dep in deps:
                    if dep not in step_ids and dep:
                        findings.append(ReviewFinding(
                            category=ReviewCategory.LOGIC,
                            severity=ReviewSeverity.MAJOR,
                            title=f"Missing dependency: {dep}",
                            description=f"Step '{step_id}' depends on '{dep}' which doesn't exist",
                            suggestion=f"Create step '{dep}' or remove the dependency",
                        ))

            goal = plan.get("goal", "")
            if not goal:
                findings.append(ReviewFinding(
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.MAJOR,
                    title="Missing plan goal",
                    description="Plan has no defined goal",
                    suggestion="Add a goal to the plan describing what it achieves",
                ))

        return self._finalize("plan", "plan", findings, plan, start)

    # ------------------------------------------------------------------
    # Research review
    # ------------------------------------------------------------------

    def review_research(self, content: str,
                        sources: List[str] = None) -> ReviewResult:
        start = time.time()
        findings: List[ReviewFinding] = []

        if not sources:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.MAJOR,
                title="No sources cited",
                description="Research content has no cited sources",
                suggestion="Add source citations to support claims",
            ))

        if len(content) < 100:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.MAJOR,
                title="Research content too brief",
                description=f"Only {len(content)} characters",
                suggestion="Expand research with more detailed findings",
            ))

        return self._finalize("research", "research", findings, content[:200], start)

    # ------------------------------------------------------------------
    # Summary review
    # ------------------------------------------------------------------

    def review_summary(self, content: str, original_length: int = 0) -> ReviewResult:
        start = time.time()
        findings: List[ReviewFinding] = []

        if original_length > 0 and len(content) > original_length:
            findings.append(ReviewFinding(
                category=ReviewCategory.LOGIC,
                severity=ReviewSeverity.MAJOR,
                title="Summary longer than original",
                description=f"Summary ({len(content)} chars) is longer than original ({original_length} chars)",
                suggestion="Condense the summary to be shorter than the original",
            ))

        if len(content) < 20:
            findings.append(ReviewFinding(
                category=ReviewCategory.COMPLETENESS,
                severity=ReviewSeverity.MAJOR,
                title="Summary too brief",
                description="Summary should contain meaningful content",
                suggestion="Provide a more detailed summary",
            ))

        return self._finalize("summary", "summary", findings, content[:200], start)

    # ------------------------------------------------------------------
    # Custom rules
    # ------------------------------------------------------------------

    def add_rule(self, name: str, rule_type: str,
                 pattern: str, severity: ReviewSeverity,
                 title: str, suggestion: str) -> None:
        with self._lock:
            self._custom_rules.append({
                "name": name,
                "type": rule_type,
                "pattern": pattern,
                "severity": severity,
                "title": title,
                "suggestion": suggestion,
            })

    def _apply_custom_rule(self, rule: Dict[str, Any],
                           content: str, language: str) -> List[ReviewFinding]:
        findings = []
        if rule.get("pattern") in content:
            findings.append(ReviewFinding(
                category=ReviewCategory.CODE,
                severity=rule["severity"],
                title=rule.get("title", "Custom rule match"),
                description=f"Matched rule '{rule.get('name', 'custom')}': {rule.get('pattern')}",
                suggestion=rule.get("suggestion", ""),
            ))
        return findings

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _finalize(self, artifact_type: str, label: str,
                  findings: List[ReviewFinding], artifact_preview: Any,
                  start: float) -> ReviewResult:
        total_findings = len(findings)
        score = 1.0
        severity_weights = {
            ReviewSeverity.BLOCKER: 0.4,
            ReviewSeverity.CRITICAL: 0.25,
            ReviewSeverity.MAJOR: 0.1,
            ReviewSeverity.MINOR: 0.03,
            ReviewSeverity.INFO: 0.01,
        }
        for f in findings:
            score -= severity_weights.get(f.severity, 0.01)
        score = max(0.0, score)

        status = "completed"
        has_blockers = any(f.severity == ReviewSeverity.BLOCKER for f in findings)
        has_criticals = any(f.severity == ReviewSeverity.CRITICAL for f in findings)
        passed = not has_blockers and score >= self._min_score_to_pass

        summary_parts = []
        if has_blockers:
            summary_parts.append(f"{sum(1 for f in findings if f.severity == ReviewSeverity.BLOCKER)} blockers")
        if has_criticals:
            summary_parts.append(f"{sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)} critical")
        major_count = sum(1 for f in findings if f.severity == ReviewSeverity.MAJOR)
        if major_count:
            summary_parts.append(f"{major_count} major")
        summary = f"Score: {score:.2f}, {total_findings} findings, {'PASS' if passed else 'FAIL'}"
        if summary_parts:
            summary += f" ({', '.join(summary_parts)})"

        result = ReviewResult(
            artifact_type=artifact_type,
            reviewer_id="reviewer-agent",
            status=status,
            overall_score=score,
            findings=findings,
            summary=summary,
            passed=passed,
            duration_seconds=time.time() - start,
            metadata={"label": label},
        )

        with self._lock:
            self._results[result.id] = result

        if self._event_bus:
            self._event_bus.emit_async("review.completed", {
                "result_id": result.id,
                "artifact_type": artifact_type,
                "passed": passed,
                "score": score,
                "findings_count": total_findings,
            })

        return result

    def get_result(self, result_id: str) -> Optional[ReviewResult]:
        with self._lock:
            return self._results.get(result_id)

    def list_results(self, artifact_type: str = "", passed: bool = None,
                     limit: int = 50) -> List[ReviewResult]:
        with self._lock:
            results = list(self._results.values())
        if artifact_type:
            results = [r for r in results if r.artifact_type == artifact_type]
        if passed is not None:
            results = [r for r in results if r.passed == passed]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._results)
            passed = sum(1 for r in self._results.values() if r.passed)
            failed = total - passed
        return {
            "total_reviews": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "custom_rules": len(self._custom_rules),
        }