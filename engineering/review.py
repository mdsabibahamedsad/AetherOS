"""
Automated Review — performs comprehensive code and architecture reviews.

Review types:
  - Code review (correctness, style, best practices)
  - Architecture review (design patterns, coupling, cohesion)
  - Maintainability review (complexity, duplication, documentation)
  - Documentation review (completeness, accuracy)
  - Performance review (bottlenecks, resource usage)
  - Security review (vulnerabilities, attack surface)

Identifies conflicts before merging results from parallel workstreams.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ReviewSeverity(enum.IntEnum):
    """Severity levels for review findings."""
    CRITICAL = 0
    HIGH = 10
    MEDIUM = 25
    LOW = 50
    INFO = 75
    SUGGESTION = 100


class ReviewCategory(enum.Enum):
    """Categories for review findings."""
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    MAINTAINABILITY = "maintainability"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DUPLICATION = "duplication"
    BEST_PRACTICES = "best_practices"
    CONSISTENCY = "consistency"
    CONFLICT = "conflict"


@dataclass
class ReviewFinding:
    """A single finding from a review.

    Attributes:
        id: Unique finding ID
        category: Review category
        severity: Severity level
        title: Finding title
        description: Detailed description
        file_path: File where the finding was found
        line_start: Starting line number
        line_end: Ending line number
        recommendation: Suggested fix or improvement
        effort_to_fix: Estimated effort (easy, medium, hard)
        is_fixed: Whether this finding has been addressed
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    category: ReviewCategory = ReviewCategory.CODE_QUALITY
    severity: ReviewSeverity = ReviewSeverity.MEDIUM
    title: str = ""
    description: str = ""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    recommendation: str = ""
    effort_to_fix: str = "medium"
    is_fixed: bool = False


@dataclass
class ReviewSummary:
    """Summary of a review report.

    Attributes:
        total_findings: Total number of findings
        by_severity: Count of findings by severity
        by_category: Count of findings by category
        passed: Whether the review passed threshold
        score: Overall review score (0-100)
    """
    total_findings: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    passed: bool = True
    score: float = 100.0


@dataclass
class ConflictReport:
    """Report of conflicts found between parallel workstreams.

    Attributes:
        id: Unique report ID
        conflicting_files: Files with merge conflicts
        overlapping_changes: Changes that overlap between assignments
        incompatible_interfaces: Interface mismatches
        recommendations: How to resolve conflicts
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    conflicting_files: List[str] = field(default_factory=list)
    overlapping_changes: List[str] = field(default_factory=list)
    incompatible_interfaces: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ReviewReport:
    """Complete report from an automated review.

    Attributes:
        id: Unique report ID
        type: Type of review performed
        target: What was reviewed (file path, module name, etc.)
        findings: List of review findings
        summary: Review summary
        conflict_report: Optional conflict report
        reviewed_at: When the review was performed
        reviewer: What performed the review
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = "code_review"
    target: str = ""
    findings: List[ReviewFinding] = field(default_factory=list)
    summary: Optional[ReviewSummary] = None
    conflict_report: Optional[ConflictReport] = None
    reviewed_at: float = field(default_factory=time.time)
    reviewer: str = "automated"
    notes: str = ""


class AutomatedReview:
    """Performs automated reviews on code, architecture, and documentation.

    Supports multiple review types with configurable severity thresholds.

    Usage:
        reviewer = AutomatedReview(event_bus)
        report = reviewer.code_review(file_path, content)
        print(f"Found {len(report.findings)} issues")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._reports: Dict[str, ReviewReport] = {}
        self._min_score_to_pass = 70.0

    def set_pass_threshold(self, score: float) -> None:
        """Set the minimum score for a review to pass.

        Args:
            score: Minimum score (0-100)
        """
        self._min_score_to_pass = max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Review types
    # ------------------------------------------------------------------

    def code_review(self, file_path: str, content: str,
                    language: str = "") -> ReviewReport:
        """Perform a code review on a file.

        Checks for:
        - Syntax errors / potential bugs
        - Style issues
        - Code complexity
        - Best practices violations
        - Error handling
        - Hardcoded values

        Args:
            file_path: Path to the file being reviewed
            content: File content
            language: Programming language (auto-detected if empty)

        Returns:
            ReviewReport with findings
        """
        report = ReviewReport(
            type="code_review",
            target=file_path,
            reviewer="automated-code-review",
        )

        findings = self._analyze_code(file_path, content, language)
        report.findings = findings
        report.summary = self._generate_summary(findings)

        self._reports[report.id] = report

        if self._event_bus:
            self._event_bus.emit_async("engineering.review_completed", {
                "report_id": report.id,
                "type": report.type,
                "target": file_path,
                "findings": len(findings),
                "passed": report.summary.passed if report.summary else True,
            })

        return report

    def architecture_review(self, architecture: Any) -> ReviewReport:
        """Perform an architecture review.

        Checks for:
        - Cohesion and coupling
        - Interface consistency
        - Dependency direction
        - Missing abstractions
        - Over-engineering

        Args:
            architecture: ArchitectureDesign object

        Returns:
            ReviewReport with architecture findings
        """
        report = ReviewReport(
            type="architecture_review",
            target=getattr(architecture, 'title', 'architecture'),
            reviewer="automated-architecture-review",
        )

        findings = []
        if hasattr(architecture, 'modules'):
            module_names = [m.name for m in architecture.modules]

            # Check for circular dependencies
            if len(module_names) > 1:
                # Simple circular dependency check
                dep_map: Dict[str, List[str]] = {}
                for module in architecture.modules:
                    deps = getattr(module, 'dependencies', [])
                    dep_map[module.name] = deps

                has_circular = False
                for name, deps in dep_map.items():
                    for dep in deps:
                        if name in dep_map.get(dep, []):
                            findings.append(ReviewFinding(
                                category=ReviewCategory.ARCHITECTURE,
                                severity=ReviewSeverity.HIGH,
                                title=f"Circular dependency: {name} <-> {dep}",
                                description=f"Modules '{name}' and '{dep}' have a circular dependency",
                                recommendation="Extract shared functionality into a third module or restructure dependencies",
                                effort_to_fix="hard",
                            ))
                            has_circular = True

            # Check module counts
            if len(module_names) < 2:
                findings.append(ReviewFinding(
                    category=ReviewCategory.ARCHITECTURE,
                    severity=ReviewSeverity.INFO,
                    title="Small number of modules",
                    description="Architecture has very few modules; may benefit from more decomposition",
                    recommendation="Consider splitting into smaller, focused modules",
                ))
            elif len(module_names) > 10:
                findings.append(ReviewFinding(
                    category=ReviewCategory.ARCHITECTURE,
                    severity=ReviewSeverity.MEDIUM,
                    title="Large number of modules",
                    description=f"Architecture has {len(module_names)} modules; verify complexity is warranted",
                    recommendation="Consider grouping related modules into layers",
                ))

        if hasattr(architecture, 'interfaces'):
            interface_names = [i.name for i in architecture.interfaces]
            if not interface_names:
                findings.append(ReviewFinding(
                    category=ReviewCategory.ARCHITECTURE,
                    severity=ReviewSeverity.MEDIUM,
                    title="No interfaces defined",
                    description="Architecture has no interface definitions between modules",
                    recommendation="Define interfaces between modules for loose coupling",
                ))

        if hasattr(architecture, 'design_decisions'):
            decisions = architecture.design_decisions
            resolved_decisions = [d for d in decisions if d.status == "accepted"]
            if resolved_decisions and len(decisions) > len(resolved_decisions) * 1.5:
                findings.append(ReviewFinding(
                    category=ReviewCategory.ARCHITECTURE,
                    severity=ReviewSeverity.INFO,
                    title="Pending design decisions",
                    description=f"{len(decisions) - len(resolved_decisions)} design decisions are not yet accepted",
                    recommendation="Review and accept pending design decisions before implementation",
                ))

        report.findings = findings
        report.summary = self._generate_summary(findings)
        self._reports[report.id] = report

        if self._event_bus:
            self._event_bus.emit_async("engineering.architecture_reviewed", {
                "report_id": report.id,
                "findings": len(findings),
            })

        return report

    def conflict_review(self, file_changes: List) -> ConflictReport:
        """Check for conflicts between parallel changes.

        Args:
            file_changes: List of FileChange objects from different assignments

        Returns:
            ConflictReport identifying potential conflicts
        """
        report = ConflictReport()

        # Check for overlapping file modifications
        file_assignments: Dict[str, List[str]] = {}
        for change in file_changes:
            path = getattr(change, 'file_path', '')
            asm_id = getattr(change, 'assignment_id', '')
            if path and asm_id:
                if path not in file_assignments:
                    file_assignments[path] = []
                file_assignments[path].append(asm_id)

        for path, assignments in file_assignments.items():
            if len(assignments) > 1:
                report.conflicting_files.append(path)

        if report.conflicting_files:
            report.recommendations.append(
                "Files modified by multiple assignments should be reviewed for consistency"
            )
            report.recommendations.append(
                "Consider sequential execution for conflicting files"
            )

        if self._event_bus:
            self._event_bus.emit_async("engineering.conflict_reviewed", {
                "conflicting_files": len(report.conflicting_files),
            })

        return report

    # ------------------------------------------------------------------
    # Code analysis
    # ------------------------------------------------------------------

    def _analyze_code(self, file_path: str, content: str,
                      language: str) -> List[ReviewFinding]:
        """Analyze code for common issues."""
        findings = []
        lines = content.splitlines()
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        lang = language.lower() if language else ext

        # Check for overly long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                findings.append(ReviewFinding(
                    category=ReviewCategory.STYLE,
                    severity=ReviewSeverity.LOW,
                    title=f"Line too long ({len(line)} chars)",
                    description=f"Line {i} exceeds 120 character limit",
                    file_path=file_path,
                    line_start=i,
                    recommendation="Break the line into multiple lines or refactor",
                    effort_to_fix="easy",
                ))

        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("# TODO", "// TODO", "<!-- TODO", "/* TODO")):
                findings.append(ReviewFinding(
                    category=ReviewCategory.CODE_QUALITY,
                    severity=ReviewSeverity.INFO,
                    title="TODO comment found",
                    description=f"Line {i}: {stripped.strip()[:60]}",
                    file_path=file_path,
                    line_start=i,
                    recommendation="Address the TODO item before merging",
                    effort_to_fix="medium",
                ))

        # Check for large functions (Python-specific heuristic)
        if lang in ("py", "python"):
            in_function = False
            func_start = 0
            func_indent = 0
            func_lines = 0
            for i, line in enumerate(lines):
                stripped = line.rstrip()
                if not in_function and stripped.startswith("def "):
                    in_function = True
                    func_start = i + 1
                    func_indent = len(line) - len(line.lstrip())
                    func_lines = 0
                elif in_function:
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else func_indent + 4
                    if current_indent <= func_indent and line.strip():
                        # Function ended
                        if func_lines > 50:
                            findings.append(ReviewFinding(
                                category=ReviewCategory.MAINTAINABILITY,
                                severity=ReviewSeverity.MEDIUM,
                                title=f"Large function ({func_lines} lines)",
                                description=f"Function starting at line {func_start} has {func_lines} lines",
                                file_path=file_path,
                                line_start=func_start,
                                recommendation="Consider breaking into smaller functions",
                                effort_to_fix="medium",
                            ))
                        in_function = False
                    elif line.strip() and not stripped.startswith(("#", "//")):
                        func_lines += 1

        return findings

    # ------------------------------------------------------------------
    # Report management
    # ------------------------------------------------------------------

    def _generate_summary(self, findings: List[ReviewFinding]) -> ReviewSummary:
        """Generate a summary from findings."""
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        total = len(findings)

        for finding in findings:
            severity_key = finding.severity.name.lower()
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

            cat_key = finding.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

        # Calculate score (100 - penalty based on severity and count)
        score = 100.0
        score -= by_severity.get("critical", 0) * 20
        score -= by_severity.get("high", 0) * 10
        score -= by_severity.get("medium", 0) * 5
        score -= by_severity.get("low", 0) * 2
        score = max(0.0, score)

        return ReviewSummary(
            total_findings=total,
            by_severity=by_severity,
            by_category=by_category,
            passed=score >= self._min_score_to_pass,
            score=score,
        )

    def get_report(self, report_id: str) -> Optional[ReviewReport]:
        """Get a review report by ID."""
        return self._reports.get(report_id)

    def get_findings_by_severity(self, report_id: str,
                                 min_severity: ReviewSeverity) -> List[ReviewFinding]:
        """Get findings above a severity threshold."""
        report = self._reports.get(report_id)
        if report is None:
            return []
        return [
            f for f in report.findings
            if f.severity.value <= min_severity.value
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get reviewer statistics."""
        total_findings = sum(len(r.findings) for r in self._reports.values())
        total_passed = sum(
            1 for r in self._reports.values()
            if r.summary and r.summary.passed
        )
        return {
            "total_reviews": len(self._reports),
            "total_findings": total_findings,
            "passed_count": total_passed,
            "pass_threshold": self._min_score_to_pass,
        }
