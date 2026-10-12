"""
Architecture Planner — generates system architecture designs from specifications.

Produces:
  - System architecture
  - Module boundaries
  - Interfaces
  - Dependencies
  - Technology recommendations
  - Design rationale

Supports iterative refinement through review feedback.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class ModuleBoundary:
    """A module boundary within the architecture.

    Attributes:
        id: Unique module ID
        name: Module name
        description: Module responsibility
        interfaces: List of interface names this module exposes
        dependencies: Module IDs this module depends on
        technology: Recommended technology for this module (optional)
        status: Module status (proposed, approved, implemented, deprecated)
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    interfaces: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    technology: str = ""
    status: str = "proposed"
    notes: str = ""


@dataclass
class InterfaceDefinition:
    """A defined interface between modules.

    Attributes:
        id: Unique interface ID
        name: Interface name
        description: What the interface provides
        provider: Module ID that provides this interface
        consumer: Module ID that consumes this interface
        contract: Interface contract details (e.g. REST, gRPC, function call)
        data_format: Data format (e.g. JSON, Protocol Buffers)
        stability: Interface stability (stable, evolving, experimental)
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    provider: str = ""
    consumer: str = ""
    contract: str = ""
    data_format: str = ""
    stability: str = "proposed"


@dataclass
class TechnologyRecommendation:
    """A technology recommendation for the architecture.

    Attributes:
        id: Unique recommendation ID
        name: Technology name
        category: Category (language, framework, database, tool, etc.)
        description: Why this technology is recommended
        alternatives: Alternative technologies considered
        rationale: Why this choice was made over alternatives
        constraints: Any constraints this technology imposes
        risk_level: Risk level (low, medium, high)
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    category: str = ""
    description: str = ""
    alternatives: List[str] = field(default_factory=list)
    rationale: str = ""
    constraints: str = ""
    risk_level: str = "low"


@dataclass
class DesignRationale:
    """Record of a design decision.

    Attributes:
        id: Unique decision ID
        title: Decision title
        context: Context and background
        options: Options that were considered
        decision: What was decided
        rationale: Why this option was chosen
        consequences: Anticipated consequences
        status: Decision status (proposed, accepted, deprecated, superseded)
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    context: str = ""
    options: List[str] = field(default_factory=list)
    decision: str = ""
    rationale: str = ""
    consequences: str = ""
    status: str = "proposed"


@dataclass
class ArchitectureReview:
    """A review of an architecture design.

    Attributes:
        id: Unique review ID
        architecture_id: The architecture design being reviewed
        findings: List of review findings
        overall_assessment: Overall assessment
        approved: Whether the architecture is approved
        feedback: Detailed feedback
        reviewed_by: Who performed the review
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    architecture_id: str = ""
    findings: List[str] = field(default_factory=list)
    overall_assessment: str = ""
    approved: bool = False
    feedback: str = ""
    reviewed_by: str = ""


@dataclass
class ArchitectureDesign:
    """A complete system architecture design.

    Attributes:
        id: Unique architecture ID
        title: Architecture title
        spec_id: The specification this architecture implements
        overview: High-level architecture overview
        modules: Module boundaries
        interfaces: Interface definitions
        technologies: Technology recommendations
        design_decisions: Design rationale records
        reviews: Architecture reviews
        diagram_url: Optional URL to an architecture diagram
        version: Architecture version
        status: Architecture status (draft, reviewed, approved, superseded)
        created_at: When the architecture was created
        updated_at: When the architecture was last updated
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    spec_id: str = ""
    overview: str = ""
    modules: List[ModuleBoundary] = field(default_factory=list)
    interfaces: List[InterfaceDefinition] = field(default_factory=list)
    technologies: List[TechnologyRecommendation] = field(default_factory=list)
    design_decisions: List[DesignRationale] = field(default_factory=list)
    reviews: List[ArchitectureReview] = field(default_factory=list)
    diagram_url: str = ""
    version: str = "1.0.0"
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArchitecturePlanner:
    """Generates system architecture designs from specifications.

    Produces structured architecture designs with module boundaries,
    interfaces, technology recommendations, and design rationale.

    Supports iterative refinement via review feedback.

    Usage:
        planner = ArchitecturePlanner(event_bus)
        arch = planner.generate(spec)
        planner.add_review(arch.id, review)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._designs: Dict[str, ArchitectureDesign] = {}

    def generate(self, specification, context: Dict[str, Any] = None) -> ArchitectureDesign:
        """Generate an architecture design from a specification.

        Args:
            specification: A Specification object (or dict-like with requirements)
            context: Additional context for the architecture generation

        Returns:
            An ArchitectureDesign with modules, interfaces, and recommendations
        """
        design = ArchitectureDesign(
            title=f"Architecture: {getattr(specification, 'title', 'Untitled')}",
            spec_id=getattr(specification, 'id', ''),
        )

        # Extract requirements text for analysis
        requirements_text = ""
        if hasattr(specification, 'functional_requirements'):
            requirements_text = " ".join(
                fr.description for fr in specification.functional_requirements
            )
        if hasattr(specification, 'non_functional_requirements'):
            requirements_text += " " + " ".join(
                nfr.description for nfr in specification.non_functional_requirements
            )
        if hasattr(specification, 'goal'):
            requirements_text = specification.goal + " " + requirements_text

        # Generate architecture components
        self._design_modules(requirements_text, design)
        self._design_interfaces(requirements_text, design)
        self._recommend_technologies(requirements_text, design)
        self._record_design_decisions(requirements_text, design)

        # Generate overview
        design.overview = self._generate_overview(design)

        self._designs[design.id] = design

        logger.info(
            "ArchitecturePlanner: created design %s: %d modules, %d interfaces, "
            "%d technologies, %d decisions",
            design.id[:8],
            len(design.modules),
            len(design.interfaces),
            len(design.technologies),
            len(design.design_decisions),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.architecture_created", {
                "architecture_id": design.id,
                "spec_id": design.spec_id,
                "title": design.title,
                "module_count": len(design.modules),
            })

        return design

    def _design_modules(self, requirements: str, design: ArchitectureDesign) -> None:
        """Design module boundaries based on requirements."""
        req_lower = requirements.lower()

        # Core application module
        design.modules.append(ModuleBoundary(
            name="Core",
            description="Core application logic, configuration, and shared utilities",
            interfaces=["IConfig", "ILogging", "IErrorHandler"],
            status="proposed",
        ))

        # API layer if API is mentioned
        if "api" in req_lower or "rest" in req_lower or "endpoint" in req_lower:
            design.modules.append(ModuleBoundary(
                name="API Layer",
                description="REST API endpoints, request handling, and response formatting",
                interfaces=["IRouter", "IMiddleware", "IRequestHandler"],
                dependencies=["core"],
                status="proposed",
            ))

        # Data layer if data storage is mentioned
        if "database" in req_lower or "data" in req_lower or "store" in req_lower:
            design.modules.append(ModuleBoundary(
                name="Data Layer",
                description="Data persistence, querying, and migration management",
                interfaces=["IRepository", "IMigration", "IQuery"],
                dependencies=["core"],
                status="proposed",
            ))

        # Auth module if auth is mentioned
        if "auth" in req_lower or "login" in req_lower or "user" in req_lower:
            design.modules.append(ModuleBoundary(
                name="Authentication",
                description="User authentication, authorization, and session management",
                interfaces=["IAuth", "ISession", "IPermission"],
                dependencies=["core", "data"],
                status="proposed",
            ))

        # UI module if frontend is mentioned
        if "ui" in req_lower or "frontend" in req_lower or "web" in req_lower:
            design.modules.append(ModuleBoundary(
                name="User Interface",
                description="Frontend components, routing, and state management",
                interfaces=["IComponent", "IRoute", "IState"],
                dependencies=["api"],
                status="proposed",
            ))

        # Testing module
        design.modules.append(ModuleBoundary(
            name="Testing",
            description="Unit tests, integration tests, and test utilities",
            interfaces=["ITestFixture", "IMock", "IAssertion"],
            dependencies=["core", "api", "data"],
            status="proposed",
        ))

    def _design_interfaces(self, requirements: str, design: ArchitectureDesign) -> None:
        """Design interfaces between modules."""
        module_map = {m.name: m.id for m in design.modules}

        # API interfaces
        if "API Layer" in module_map:
            design.interfaces.append(InterfaceDefinition(
                name="REST API Contract",
                description="HTTP REST API endpoints and request/response schemas",
                provider=module_map.get("API Layer", ""),
                consumer=module_map.get("User Interface", ""),
                contract="REST over HTTP",
                data_format="JSON",
            ))

        # Data interfaces
        if "Data Layer" in module_map:
            design.interfaces.append(InterfaceDefinition(
                name="Repository Interface",
                description="Data access operations (CRUD, query, transaction)",
                provider=module_map.get("Data Layer", ""),
                consumer=module_map.get("API Layer", ""),
                contract="Repository pattern",
                data_format="Domain objects",
            ))

        # Auth interfaces
        if "Authentication" in module_map:
            design.interfaces.append(InterfaceDefinition(
                name="Authentication Interface",
                description="Login, logout, token validation, permission checks",
                provider=module_map.get("Authentication", ""),
                consumer=module_map.get("API Layer", ""),
                contract="JWT / OAuth2 tokens",
                data_format="Token + Claims",
            ))

    def _recommend_technologies(self, requirements: str,
                                design: ArchitectureDesign) -> None:
        """Recommend technologies based on requirements."""
        req_lower = requirements.lower()

        # Language recommendation
        if "python" in req_lower:
            design.technologies.append(TechnologyRecommendation(
                name="Python 3.12+",
                category="language",
                description="Primary programming language",
                alternatives=["Python 3.10", "Python 3.11"],
                rationale="Latest stable Python with performance improvements",
            ))
        elif "javascript" in req_lower or "typescript" in req_lower:
            design.technologies.append(TechnologyRecommendation(
                name="TypeScript 5.x",
                category="language",
                description="Primary programming language with type safety",
                rationale="Type safety for large-scale application development",
            ))
        else:
            design.technologies.append(TechnologyRecommendation(
                name="Python 3.12+",
                category="language",
                description="Recommended primary language (adjustable)",
                rationale="Versatile, well-supported, and AI-friendly",
                risk_level="low",
            ))

        # Web framework
        if "api" in req_lower:
            design.technologies.append(TechnologyRecommendation(
                name="FastAPI",
                category="framework",
                description="High-performance Python web framework for APIs",
                alternatives=["Flask", "Django REST Framework"],
                rationale="Async support, automatic OpenAPI docs, type validation via Pydantic",
                risk_level="low",
            ))

        # Database
        if "database" in req_lower:
            design.technologies.append(TechnologyRecommendation(
                name="SQLite (development) / PostgreSQL (production)",
                category="database",
                description="Relational database for data persistence",
                alternatives=["MySQL", "MongoDB"],
                rationale="SQLite for simplicity in dev, PostgreSQL for production reliability",
                risk_level="low",
            ))

    def _record_design_decisions(self, requirements: str,
                                 design: ArchitectureDesign) -> None:
        """Record key design decisions."""
        design.design_decisions.append(DesignRationale(
            title="Modular Architecture",
            context="System needs to be maintainable and extensible",
            options=["Monolithic", "Modular monolith", "Microservices"],
            decision="Modular monolith with clear module boundaries",
            rationale="Simplifies development while maintaining separation of concerns. "
                     "Can evolve to microservices if needed.",
            consequences="Modules can be extracted to services later. Clear interfaces required.",
            status="accepted",
        ))

        design.design_decisions.append(DesignRationale(
            title="Separation of Concerns",
            context="Different responsibilities should be in different modules",
            options=["Single layer", "Two-layer", "Three-layer (API/Logic/Data)"],
            decision="Three-layer architecture with API, Business Logic, and Data layers",
            rationale="Clear separation enables parallel development and independent testing",
            consequences="More files but better maintainability and testability.",
            status="accepted",
        ))

    def _generate_overview(self, design: ArchitectureDesign) -> str:
        """Generate a high-level architecture overview."""
        module_names = [m.name for m in design.modules]
        tech_names = [t.name for t in design.technologies]

        return (
            f"Architecture overview for '{design.title}': "
            f"{len(design.modules)} modules "
            f"({', '.join(module_names[:5])}), "
            f"using {', '.join(tech_names[:3])}. "
            f"Design follows separation of concerns with clear module interfaces."
        )

    # ------------------------------------------------------------------
    # Review & refinement
    # ------------------------------------------------------------------

    def add_review(self, architecture_id: str,
                   review: ArchitectureReview) -> Optional[ArchitectureDesign]:
        """Add a review to an architecture design.

        Args:
            architecture_id: Architecture design ID
            review: The review to add

        Returns:
            Updated architecture design, or None if not found
        """
        design = self._designs.get(architecture_id)
        if design is None:
            return None

        design.reviews.append(review)
        design.updated_at = time.time()

        if review.approved:
            design.status = "approved"

        logger.info(
            "ArchitecturePlanner: review added to %s: approved=%s, findings=%d",
            architecture_id[:8], review.approved, len(review.findings),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.architecture_reviewed", {
                "architecture_id": architecture_id,
                "approved": review.approved,
                "finding_count": len(review.findings),
            })

        return design

    def refine(self, architecture_id: str,
               feedback: str) -> Optional[ArchitectureDesign]:
        """Refine an architecture design based on feedback.

        Args:
            architecture_id: Architecture design ID
            feedback: Feedback to incorporate

        Returns:
            Refined architecture design, or None if not found
        """
        design = self._designs.get(architecture_id)
        if design is None:
            return None

        design.status = "revised"
        design.updated_at = time.time()
        design.metadata["last_feedback"] = feedback

        logger.info("ArchitecturePlanner: refined design %s", architecture_id[:8])
        return design

    def get_design(self, architecture_id: str) -> Optional[ArchitectureDesign]:
        """Get an architecture design by ID."""
        return self._designs.get(architecture_id)

    def list_designs(self, status: Optional[str] = None) -> List[ArchitectureDesign]:
        """List all architecture designs, optionally filtered by status."""
        designs = list(self._designs.values())
        if status:
            designs = [d for d in designs if d.status == status]
        designs.sort(key=lambda d: d.updated_at, reverse=True)
        return designs

    def get_stats(self) -> Dict[str, Any]:
        """Get planner statistics."""
        return {
            "total_designs": len(self._designs),
            "total_modules": sum(len(d.modules) for d in self._designs.values()),
            "total_interfaces": sum(len(d.interfaces) for d in self._designs.values()),
            "total_decisions": sum(len(d.design_decisions) for d in self._designs.values()),
            "by_status": {
                status: sum(1 for d in self._designs.values() if d.status == status)
                for status in {d.status for d in self._designs.values()}
            },
        }
