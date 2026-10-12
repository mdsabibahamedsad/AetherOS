"""
Requirements Analyzer — extracts structured specifications from engineering goals.

Produces a structured specification containing:
  - Functional requirements
  - Non-functional requirements
  - Constraints
  - Dependencies
  - Acceptance criteria
  - Unknowns and open questions
"""

from __future__ import annotations

import enum
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class RequirementPriority(enum.Enum):
    """Priority levels for requirements."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


class RequirementCategory(enum.Enum):
    """Categories for requirements."""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"
    SCALABILITY = "scalability"
    COMPATIBILITY = "compatibility"
    ACCESSIBILITY = "accessibility"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


@dataclass
class FunctionalRequirement:
    """A single functional requirement.

    Attributes:
        id: Unique requirement ID
        description: Description of the requirement
        priority: Priority level
        category: Requirement category
        source: Source of the requirement (e.g. "user", "stakeholder")
        acceptance_criteria: Associated acceptance criteria IDs
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    priority: RequirementPriority = RequirementPriority.MEDIUM
    category: RequirementCategory = RequirementCategory.FUNCTIONAL
    source: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class NonFunctionalRequirement:
    """A single non-functional requirement.

    Attributes:
        id: Unique requirement ID
        description: Description of the requirement
        metric: How this requirement is measured (e.g. "response time < 200ms")
        threshold: The target threshold/value
        priority: Priority level
        category: Requirement category
        source: Source of the requirement
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    metric: str = ""
    threshold: str = ""
    priority: RequirementPriority = RequirementPriority.MEDIUM
    category: RequirementCategory = RequirementCategory.PERFORMANCE
    source: str = ""


@dataclass
class Constraint:
    """A project or technical constraint.

    Attributes:
        id: Unique constraint ID
        description: Description of the constraint
        type: Type of constraint (e.g. "technology", "time", "resource", "regulation")
        is_flexible: Whether the constraint can be negotiated
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    type: str = "technology"
    is_flexible: bool = False
    notes: str = ""


@dataclass
class Dependency:
    """An external dependency identified during requirements analysis.

    Attributes:
        id: Unique dependency ID
        name: Name of the dependency
        version: Required version constraint
        type: Type of dependency (e.g. "library", "service", "tool", "system")
        required_by: Requirement IDs that need this dependency
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    version: str = ""
    type: str = "library"
    required_by: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion.

    Attributes:
        id: Unique criterion ID
        description: Description of the criterion
        scenario: The test scenario (Given/When/Then format)
        is_met: Whether this criterion is currently satisfied
        verified_by: How this criterion is verified (e.g. "test", "review", "demo")
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    scenario: str = ""
    is_met: bool = False
    verified_by: str = "test"


@dataclass
class Unknown:
    """An unknown or open question identified during analysis.

    Attributes:
        id: Unique unknown ID
        question: The open question
        impact: Potential impact if not resolved
        resolved: Whether this unknown has been resolved
        resolution: How it was resolved
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    question: str = ""
    impact: str = ""
    resolved: bool = False
    resolution: str = ""


@dataclass
class Specification:
    """A complete structured specification for an engineering goal.

    Attributes:
        id: Unique specification ID
        title: Title of the specification
        goal: The original engineering goal
        functional_requirements: List of functional requirements
        non_functional_requirements: List of non-functional requirements
        constraints: List of constraints
        dependencies: List of dependencies
        acceptance_criteria: List of acceptance criteria
        unknowns: List of unknowns and open questions
        summary: Executive summary
        created_at: When the specification was created
        updated_at: When the specification was last updated
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    goal: str = ""
    functional_requirements: List[FunctionalRequirement] = field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    unknowns: List[Unknown] = field(default_factory=list)
    summary: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequirementsAnalyzer:
    """Analyzes engineering goals and produces structured specifications.

    Extracts functional and non-functional requirements, constraints,
    dependencies, acceptance criteria, and unknowns from a high-level goal.

    Integrates with the kernel EventBus for observability.

    Usage:
        analyzer = RequirementsAnalyzer(event_bus)
        spec = analyzer.analyze("Build a REST API for user management")
        print(f"Found {len(spec.functional_requirements)} requirements")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._specs: Dict[str, Specification] = {}

    def analyze(self, goal: str, title: str = "",
                context: Dict[str, Any] = None) -> Specification:
        """Analyze an engineering goal and produce a structured specification.

        Uses analysis patterns to extract requirements, constraints,
        dependencies, acceptance criteria, and unknowns from the goal text.

        Args:
            goal: The high-level engineering goal
            title: Optional title for the specification
            context: Additional context (project info, constraints, preferences)

        Returns:
            A Specification object with all extracted information
        """
        spec = Specification(
            title=title or goal[:60],
            goal=goal,
        )

        # Analyze the goal text to extract structured information
        self._extract_requirements(goal, context or {}, spec)
        self._extract_constraints(goal, context or {}, spec)
        self._extract_dependencies(goal, context or {}, spec)
        self._extract_acceptance_criteria(goal, context or {}, spec)
        self._extract_unknowns(goal, context or {}, spec)

        # Generate summary
        spec.summary = self._generate_summary(spec)

        self._specs[spec.id] = spec

        logger.info(
            "RequirementsAnalyzer: created spec %s: %d functional, %d non-functional, "
            "%d constraints, %d criteria, %d unknowns",
            spec.id[:8],
            len(spec.functional_requirements),
            len(spec.non_functional_requirements),
            len(spec.constraints),
            len(spec.acceptance_criteria),
            len(spec.unknowns),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.spec_created", {
                "spec_id": spec.id,
                "title": spec.title,
                "functional_count": len(spec.functional_requirements),
                "non_functional_count": len(spec.non_functional_requirements),
                "constraint_count": len(spec.constraints),
            })

        return spec

    def _extract_requirements(self, goal: str, context: Dict[str, Any],
                              spec: Specification) -> None:
        """Extract functional and non-functional requirements from the goal."""
        goal_lower = goal.lower()

        # Detect common requirement patterns
        if "api" in goal_lower or "endpoint" in goal_lower:
            spec.functional_requirements.append(FunctionalRequirement(
                description="Define and implement REST API endpoints",
                priority=RequirementPriority.CRITICAL,
                category=RequirementCategory.FUNCTIONAL,
                notes="API design should follow RESTful conventions",
            ))

        if "auth" in goal_lower or "login" in goal_lower or "user" in goal_lower:
            spec.functional_requirements.append(FunctionalRequirement(
                description="Implement user authentication and authorization",
                priority=RequirementPriority.CRITICAL,
                category=RequirementCategory.SECURITY,
            ))

        if "database" in goal_lower or "data" in goal_lower or "store" in goal_lower:
            spec.functional_requirements.append(FunctionalRequirement(
                description="Implement data persistence and storage layer",
                priority=RequirementPriority.HIGH,
            ))

        if "test" in goal_lower:
            spec.functional_requirements.append(FunctionalRequirement(
                description="Implement comprehensive test coverage",
                priority=RequirementPriority.HIGH,
            ))

        if "ui" in goal_lower or "frontend" in goal_lower or "web" in goal_lower:
            spec.functional_requirements.append(FunctionalRequirement(
                description="Build user interface components",
                priority=RequirementPriority.HIGH,
            ))

        # Add goal as the primary functional requirement
        if not spec.functional_requirements:
            spec.functional_requirements.append(FunctionalRequirement(
                description=goal,
                priority=RequirementPriority.CRITICAL,
            ))

        # Extract non-functional requirements
        if "perform" in goal_lower or "fast" in goal_lower or "speed" in goal_lower:
            spec.non_functional_requirements.append(NonFunctionalRequirement(
                description="System should perform efficiently under expected load",
                metric="Response time",
                threshold="< 500ms for 95th percentile",
                category=RequirementCategory.PERFORMANCE,
            ))

        if "scale" in goal_lower or "large" in goal_lower:
            spec.non_functional_requirements.append(NonFunctionalRequirement(
                description="System should scale horizontally",
                metric="Throughput under load",
                threshold="Linear scaling up to 10x normal load",
                category=RequirementCategory.SCALABILITY,
            ))

        if "secure" in goal_lower or "security" in goal_lower:
            spec.non_functional_requirements.append(NonFunctionalRequirement(
                description="System should meet security best practices",
                metric="Security scan pass rate",
                threshold="100% critical/high severity findings resolved",
                category=RequirementCategory.SECURITY,
            ))

        spec.non_functional_requirements.append(NonFunctionalRequirement(
            description="Code should be maintainable and well-documented",
            metric="Code quality score",
            threshold="All lint checks pass, documentation coverage > 80%",
            priority=RequirementPriority.MEDIUM,
            category=RequirementCategory.MAINTAINABILITY,
        ))

    def _extract_constraints(self, goal: str, context: Dict[str, Any],
                             spec: Specification) -> None:
        """Extract constraints from the goal and context."""
        goal_lower = goal.lower()

        # Detect constraint patterns
        if "python" in goal_lower or "javascript" in goal_lower:
            # Language constraint implied
            pass

        context_constraints = context.get("constraints", [])
        if isinstance(context_constraints, list):
            for c in context_constraints:
                if isinstance(c, str):
                    spec.constraints.append(Constraint(
                        description=c,
                        type="general",
                    ))

    def _extract_dependencies(self, goal: str, context: Dict[str, Any],
                              spec: Specification) -> None:
        """Extract dependencies from the goal and context."""
        goal_lower = goal.lower()

        # Detect dependency patterns
        if "python" in goal_lower:
            spec.dependencies.append(Dependency(
                name="Python",
                version=">=3.10",
                type="runtime",
            ))

        if "database" in goal_lower:
            spec.dependencies.append(Dependency(
                name="Database driver/framework",
                type="library",
                notes="Select based on database type (SQLite, PostgreSQL, etc.)",
            ))

    def _extract_acceptance_criteria(self, goal: str, context: Dict[str, Any],
                                     spec: Specification) -> None:
        """Extract acceptance criteria from the goal."""
        spec.acceptance_criteria.append(AcceptanceCriterion(
            description="All functional requirements are implemented and passing",
            scenario="Given the implementation, When all requirements are checked, Then all pass",
            verified_by="review",
        ))

        spec.acceptance_criteria.append(AcceptanceCriterion(
            description="All tests pass",
            scenario="Given the test suite, When all tests are run, Then all pass with no failures",
            verified_by="test",
        ))

        spec.acceptance_criteria.append(AcceptanceCriterion(
            description="No lint or type errors",
            scenario="Given the codebase, When lint and type checks are run, Then no errors found",
            verified_by="analysis",
        ))

        if spec.functional_requirements:
            for req in spec.functional_requirements[:3]:
                criterion = AcceptanceCriterion(
                    description=f"Implementation satisfies: {req.description[:80]}",
                    scenario=f"Given the system, When {req.description[:60]}, Then it works correctly",
                    verified_by="test",
                )
                spec.acceptance_criteria.append(criterion)
                req.acceptance_criteria.append(criterion.id)

    def _extract_unknowns(self, goal: str, context: Dict[str, Any],
                          spec: Specification) -> None:
        """Identify unknowns and open questions."""
        goal_lower = goal.lower()
        has_unknowns = False

        if "database" in goal_lower and any(
            db not in goal_lower for db in ["sqlite", "postgres", "mysql"]
        ):
            spec.unknowns.append(Unknown(
                question="Which database technology should be used?",
                impact="Architecture and implementation approach depends on DB choice",
            ))
            has_unknowns = True

        if "deploy" in goal_lower:
            spec.unknowns.append(Unknown(
                question="What is the deployment target and strategy?",
                impact="May affect infrastructure decisions and CI/CD setup",
            ))
            has_unknowns = True

        if not has_unknowns:
            spec.unknowns.append(Unknown(
                question="Are there any specific technology preferences or constraints not mentioned?",
                impact="May affect implementation approach",
            ))

    def _generate_summary(self, spec: Specification) -> str:
        """Generate an executive summary of the specification."""
        total_req = (
            len(spec.functional_requirements) +
            len(spec.non_functional_requirements)
        )
        return (
            f"Specification for '{spec.title}': "
            f"{total_req} requirements "
            f"({len(spec.functional_requirements)} functional, "
            f"{len(spec.non_functional_requirements)} non-functional), "
            f"{len(spec.constraints)} constraints, "
            f"{len(spec.acceptance_criteria)} acceptance criteria, "
            f"{len(spec.unknowns)} open questions."
        )

    # ------------------------------------------------------------------
    # Specification management
    # ------------------------------------------------------------------

    def get_spec(self, spec_id: str) -> Optional[Specification]:
        """Get a specification by ID."""
        return self._specs.get(spec_id)

    def update_spec(self, spec_id: str,
                    updates: Dict[str, Any]) -> Optional[Specification]:
        """Update a specification with new information.

        Args:
            spec_id: Specification ID
            updates: Dict of updates to apply

        Returns:
            Updated Specification, or None if not found
        """
        spec = self._specs.get(spec_id)
        if spec is None:
            return None

        if "functional_requirements" in updates:
            spec.functional_requirements.extend(updates["functional_requirements"])
        if "non_functional_requirements" in updates:
            spec.non_functional_requirements.extend(updates["non_functional_requirements"])
        if "constraints" in updates:
            spec.constraints.extend(updates["constraints"])
        if "dependencies" in updates:
            spec.dependencies.extend(updates["dependencies"])
        if "acceptance_criteria" in updates:
            spec.acceptance_criteria.extend(updates["acceptance_criteria"])
        if "unknowns" in updates and isinstance(updates["unknowns"], list):
            for u in updates["unknowns"]:
                if isinstance(u, Unknown):
                    spec.unknowns.append(u)

        spec.updated_at = time.time()
        spec.summary = self._generate_summary(spec)

        logger.info("RequirementsAnalyzer: updated spec %s", spec_id[:8])
        return spec

    def list_specs(self) -> List[Specification]:
        """List all specifications."""
        return sorted(
            self._specs.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )

    def to_dict(self, spec_id: str) -> Optional[Dict[str, Any]]:
        """Export a specification as a dictionary."""
        spec = self._specs.get(spec_id)
        if spec is None:
            return None
        return {
            "id": spec.id,
            "title": spec.title,
            "goal": spec.goal,
            "summary": spec.summary,
            "functional_requirements": [
                {
                    "id": fr.id,
                    "description": fr.description,
                    "priority": fr.priority.value,
                    "category": fr.category.value,
                }
                for fr in spec.functional_requirements
            ],
            "non_functional_requirements": [
                {
                    "id": nfr.id,
                    "description": nfr.description,
                    "metric": nfr.metric,
                    "threshold": nfr.threshold,
                    "priority": nfr.priority.value,
                }
                for nfr in spec.non_functional_requirements
            ],
            "constraints": [
                {
                    "id": c.id,
                    "description": c.description,
                    "type": c.type,
                    "is_flexible": c.is_flexible,
                }
                for c in spec.constraints
            ],
            "dependencies": [
                {
                    "id": d.id,
                    "name": d.name,
                    "version": d.version,
                    "type": d.type,
                }
                for d in spec.dependencies
            ],
            "acceptance_criteria": [
                {
                    "id": ac.id,
                    "description": ac.description,
                    "scenario": ac.scenario,
                    "verified_by": ac.verified_by,
                }
                for ac in spec.acceptance_criteria
            ],
            "unknowns": [
                {
                    "id": u.id,
                    "question": u.question,
                    "impact": u.impact,
                    "resolved": u.resolved,
                }
                for u in spec.unknowns
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_specs": len(self._specs),
            "total_functional": sum(
                len(s.functional_requirements) for s in self._specs.values()
            ),
            "total_non_functional": sum(
                len(s.non_functional_requirements) for s in self._specs.values()
            ),
            "total_constraints": sum(
                len(s.constraints) for s in self._specs.values()
            ),
            "total_criteria": sum(
                len(s.acceptance_criteria) for s in self._specs.values()
            ),
        }
