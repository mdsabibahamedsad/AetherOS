"""
AetherOS Autonomous Software Engineering Platform.

A safe, modular, reviewable engineering system that can plan, implement,
test, and refine software with human oversight. Integrates with the AetherOS
Kernel (event bus, lifecycle, registry), Swarm (multi-agent orchestration),
and Memory (project context, learned patterns) to provide a structured
engineering workflow.

Architecture
-----------
The engineering platform sits alongside the kernel, swarm, and memory systems:

    Engineering Goal
         │
         ▼
    ┌──────────────────────────────────────────────────────────┐
    │              EngineeringOrchestrator                      │
    │                                                            │
    │  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐ │
    │  │Requirements│─▶│Architecture  │─▶│Implementation    │ │
    │  │Analyzer    │  │Planner       │  │Plan              │ │
    │  └────────────┘  └──────────────┘  └────────┬─────────┘ │
    │                                              │            │
    │  ┌───────────────────────────────────────────▼──────────┐│
    │  │              Task Decomposition                      ││
    │  │  Parallel │ Dependencies │ Priority │ Estimation     ││
    │  └───────────┬────────────────────────────┬─────────────┘│
    │              │                            │               │
    │  ┌───────────▼──────┐  ┌──────────────────▼─────────────┐│
    │  │Implementation    │  │  Repository Intelligence       ││
    │  │Coordinator       │  │  (Structure, Languages, Deps)  ││
    │  └───────────┬──────┘  └────────────────────────────────┘│
    │              │                                            │
    │  ┌───────────▼──────────────────────────────────────┐   │
    │  │              Quality Pipeline                     │   │
    │  │  Lint │ Type Check │ Security │ Test │ Format     │   │
    │  └───────────┬──────────────────────────────────────┘   │
    │              │                                            │
    │  ┌───────────▼──────┐  ┌──────────────────────────────┐ │
    │  │Automated Review  │  │Documentation Generator       │ │
    │  │Code/Arch/Perf    │  │API/Arch/Dev Guides           │ │
    │  └───────────┬──────┘  └──────────────┬───────────────┘ │
    │              │                         │                  │
    │  ┌───────────▼─────────────────────────▼───────────────┐│
    │  │              Artifact Manager                       ││
    │  │  Patches │ Reports │ Logs │ Bundles │ Design Docs   ││
    │  └──────────────────────┬──────────────────────────────┘│
    │                         │                                 │
    │  ┌──────────────────────▼──────────────────────────────┐│
    │  │              Packaging & Release                     ││
    │  │  Build │ Package │ Release Notes │ Delivery          ││
    │  └─────────────────────────────────────────────────────┘│
    │                                                            │
    │  ┌──────────────────────────────────────────────────────┐ │
    │  │              Execution Policy Layer                   │ │
    │  │  Read-Only │ Draft │ Human Approval │ Auto │ CI      │ │
    │  └──────────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────────────────────────┐
    │   AetherOS Kernel │ Swarm │ Memory │ Event Bus            │
    └──────────────────────────────────────────────────────────┘

Design Principles:
- Safe by default: all destructive operations require explicit policy approval
- Human oversight: approval gates at configurable decision points
- Modular: each stage is independent and composable
- Observable: all stages emit structured events
- Resumable: workflows can be paused, inspected, and resumed
- Plugin-extensible: tools, reviewers, analyzers can be contributed via plugins
- Backward compatible: existing code paths remain unchanged
"""

from engineering.orchestrator import (
    EngineeringOrchestrator,
    EngineeringConfig,
    EngineeringState,
    EngineeringEvent,
    WorkflowResult,
    WorkflowStatus,
)
from engineering.execution_policy import (
    PolicyEnforcer,
    PolicyMode,
    PolicyDecision,
    PolicyCheck,
    HumanApprovalRequired,
)
from engineering.requirements import (
    RequirementsAnalyzer,
    Specification,
    FunctionalRequirement,
    NonFunctionalRequirement,
    Constraint,
    AcceptanceCriterion,
    Dependency,
    Unknown,
    RequirementPriority,
    RequirementCategory,
)
from engineering.architecture import (
    ArchitecturePlanner,
    ArchitectureDesign,
    ModuleBoundary,
    InterfaceDefinition,
    TechnologyRecommendation,
    DesignRationale,
    ArchitectureReview,
)
from engineering.planner import (
    EngineeringPlanner,
    ImplementationPlan,
    PlanPhase,
    EngineeringTask,
    TaskType,
    PlanStatus,
)
from engineering.decomposition import (
    TaskDecomposer,
    DecomposedTask,
    TaskDependency,
    Estimation,
    Priority,
    Ownership,
)
from engineering.repository import (
    RepositoryIntelligence,
    RepositoryProfile,
    LanguageInfo,
    FrameworkInfo,
    BuildSystemInfo,
    DependencyGraph,
)
from engineering.coding import (
    ImplementationCoordinator,
    CodingAssignment,
    FileChange,
    ChangeType,
    AssignmentStatus,
)
from engineering.editing import (
    CodeEditor,
    EditOperation,
    EditPlan,
    EditResult,
    SafetyCheck,
)
from engineering.review import (
    AutomatedReview,
    ReviewReport,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
    ReviewSummary,
    ConflictReport,
)
from engineering.testing import (
    TestCoordinator,
    TestSuite,
    TestResult,
    TestStatus,
    CoverageReport,
)
from engineering.linting import (
    LintRunner,
    LintResult,
    LintIssue,
    LintSeverity,
)
from engineering.static_analysis import (
    StaticAnalyzer,
    AnalysisReport,
    AnalysisIssue,
    AnalysisSeverity,
    SecurityFinding,
)
from engineering.quality import (
    QualityPipeline,
    QualityReport,
    QualityCheck,
    QualityStatus,
    QualityDimension,
)
from engineering.documentation import (
    DocumentationGenerator,
    DocumentationSection,
    DocumentationType,
    DocChange,
)
from engineering.packaging import (
    PackagingEngine,
    PackageManifest,
    PackageArtifact,
    PackageFormat,
)
from engineering.release_notes import (
    ReleaseNotesGenerator,
    ReleaseNotes,
    ChangeEntry,
    ChangeCategory,
)
from engineering.dependency_manager import (
    DependencyManager,
    DependencyEntry,
    DependencyStatus,
    DependencyVulnerability,
)
from engineering.migration import (
    MigrationEngine,
    MigrationPlan,
    MigrationStep,
    MigrationStatus,
)
from engineering.artifact_manager import (
    ArtifactManager,
    ArtifactEntry,
    ArtifactType,
    ArtifactCollection,
)

__all__ = [
    # Orchestrator
    "EngineeringOrchestrator",
    "EngineeringConfig",
    "EngineeringState",
    "EngineeringEvent",
    "WorkflowResult",
    "WorkflowStatus",
    # Execution Policy
    "PolicyEnforcer",
    "PolicyMode",
    "PolicyDecision",
    "PolicyCheck",
    "HumanApprovalRequired",
    # Requirements
    "RequirementsAnalyzer",
    "Specification",
    "FunctionalRequirement",
    "NonFunctionalRequirement",
    "Constraint",
    "AcceptanceCriterion",
    "Dependency",
    "Unknown",
    "RequirementPriority",
    "RequirementCategory",
    # Architecture
    "ArchitecturePlanner",
    "ArchitectureDesign",
    "ModuleBoundary",
    "InterfaceDefinition",
    "TechnologyRecommendation",
    "DesignRationale",
    "ArchitectureReview",
    # Implementation Plan
    "EngineeringPlanner",
    "ImplementationPlan",
    "PlanPhase",
    "EngineeringTask",
    "TaskType",
    "PlanStatus",
    # Decomposition
    "TaskDecomposer",
    "DecomposedTask",
    "TaskDependency",
    "Estimation",
    "Priority",
    "Ownership",
    # Repository
    "RepositoryIntelligence",
    "RepositoryProfile",
    "LanguageInfo",
    "FrameworkInfo",
    "BuildSystemInfo",
    "DependencyGraph",
    # Coding
    "ImplementationCoordinator",
    "CodingAssignment",
    "FileChange",
    "ChangeType",
    "AssignmentStatus",
    # Editing
    "CodeEditor",
    "EditOperation",
    "EditPlan",
    "EditResult",
    "SafetyCheck",
    # Review
    "AutomatedReview",
    "ReviewReport",
    "ReviewFinding",
    "ReviewSeverity",
    "ReviewCategory",
    "ReviewSummary",
    "ConflictReport",
    # Testing
    "TestCoordinator",
    "TestSuite",
    "TestResult",
    "TestStatus",
    "CoverageReport",
    # Linting
    "LintRunner",
    "LintResult",
    "LintIssue",
    "LintSeverity",
    # Static Analysis
    "StaticAnalyzer",
    "AnalysisReport",
    "AnalysisIssue",
    "AnalysisSeverity",
    "SecurityFinding",
    # Quality
    "QualityPipeline",
    "QualityReport",
    "QualityCheck",
    "QualityStatus",
    "QualityDimension",
    # Documentation
    "DocumentationGenerator",
    "DocumentationSection",
    "DocumentationType",
    "DocChange",
    # Packaging
    "PackagingEngine",
    "PackageManifest",
    "PackageArtifact",
    "PackageFormat",
    # Release Notes
    "ReleaseNotesGenerator",
    "ReleaseNotes",
    "ChangeEntry",
    "ChangeCategory",
    # Dependency Manager
    "DependencyManager",
    "DependencyEntry",
    "DependencyStatus",
    "DependencyVulnerability",
    # Migration
    "MigrationEngine",
    "MigrationPlan",
    "MigrationStep",
    "MigrationStatus",
    # Artifact Manager
    "ArtifactManager",
    "ArtifactEntry",
    "ArtifactType",
    "ArtifactCollection",
]
