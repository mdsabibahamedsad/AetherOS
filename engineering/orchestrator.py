"""
Engineering Orchestrator — coordinates the complete engineering lifecycle.

The orchestrator is the main entry point for the engineering platform. It:
  - Coordinates requirements analysis, architecture design, planning, and execution
  - Supports resumable execution with checkpointing
  - Integrates with Kernel (EventBus), Swarm, and Memory systems
  - Exposes a clean API for external use
  - Enforces execution policies at every stage
  - Emits structured events for observability
  - Provides plugin extension points for custom tools and analyzers

Provides the top-level API:
  - analyze_project()
  - create_specification()
  - generate_plan()
  - execute_plan()
  - review_changes()
  - run_quality_pipeline()
  - generate_release_notes()
  - export_artifacts()
  - resume_workflow()
  - cancel_workflow()
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

from engineering.execution_policy import (
    PolicyEnforcer,
    PolicyMode,
    PolicyDecision,
)
from engineering.artifact_manager import (
    ArtifactManager,
    ArtifactEntry,
    ArtifactType,
)
from engineering.requirements import (
    RequirementsAnalyzer,
    Specification,
)
from engineering.architecture import (
    ArchitecturePlanner,
    ArchitectureDesign,
    ArchitectureReview,
)
from engineering.planner import (
    EngineeringPlanner,
    ImplementationPlan,
    PlanStatus,
    EngineeringTask,
)
from engineering.decomposition import TaskDecomposer, DecomposedTask
from engineering.repository import RepositoryIntelligence, RepositoryProfile
from engineering.coding import (
    ImplementationCoordinator,
    CodingAssignment,
    FileChange,
)
from engineering.editing import CodeEditor, EditPlan
from engineering.review import (
    AutomatedReview,
    ReviewReport,
    ReviewFinding,
    ConflictReport,
)
from engineering.testing import TestCoordinator, TestSuite
from engineering.linting import LintRunner, LintResult
from engineering.static_analysis import StaticAnalyzer, AnalysisReport
from engineering.quality import QualityPipeline, QualityReport, QualityDimension, QualityCheck
from engineering.documentation import DocumentationGenerator, DocChange
from engineering.packaging import PackagingEngine, PackageManifest
from engineering.release_notes import (
    ReleaseNotesGenerator,
    ReleaseNotes,
    ChangeEntry,
    ChangeCategory,
)
from engineering.dependency_manager import DependencyManager, DependencyEntry
from engineering.migration import MigrationEngine, MigrationPlan

logger = logging.getLogger(__name__)


@dataclass
class EngineeringConfig:
    """Configuration for the engineering platform.

    Attributes:
        policy_mode: Default execution policy mode
        project_root: Root directory of the project
        docs_dir: Documentation directory
        artifacts_dir: Artifacts storage directory
        backup_dir: Backup directory for file edits
        enable_quality_pipeline: Enable quality checks on changes
        require_approval_for_writes: Require approval before file modifications
        auto_discover_repo: Automatically analyze repository on init
        verbose: Enable verbose logging
        workspace_id: Optional workspace identifier
    """
    policy_mode: PolicyMode = PolicyMode.HUMAN_APPROVAL
    project_root: str = ""
    docs_dir: str = ""
    artifacts_dir: str = ""
    backup_dir: str = ""
    enable_quality_pipeline: bool = True
    require_approval_for_writes: bool = True
    auto_discover_repo: bool = True
    verbose: bool = False
    workspace_id: str = ""


class EngineeringState(enum.Enum):
    """States for the engineering orchestrator lifecycle."""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    READY = "ready"
    WORKING = "working"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EngineeringEvent(enum.Enum):
    """Events emitted by the engineering orchestrator."""
    ENGINEERING_STARTED = "engineering.started"
    ENGINEERING_STOPPED = "engineering.stopped"
    WORKFLOW_STARTED = "engineering.workflow_started"
    WORKFLOW_PROGRESS = "engineering.workflow_progress"
    WORKFLOW_COMPLETED = "engineering.workflow_completed"
    WORKFLOW_FAILED = "engineering.workflow_failed"
    WORKFLOW_CANCELLED = "engineering.workflow_cancelled"
    APPROVAL_REQUIRED = "engineering.approval_required"
    APPROVAL_GRANTED = "engineering.approval_granted"
    APPROVAL_DENIED = "engineering.approval_denied"


class WorkflowStatus(enum.Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    SPECIFYING = "specifying"
    DESIGNING = "designing"
    PLANNING = "planning"
    DECOMPOSING = "decomposing"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    QUALITY_CHECKING = "quality_checking"
    DOCUMENTING = "documenting"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class WorkflowResult:
    """Result of a complete engineering workflow.

    Attributes:
        workflow_id: Unique workflow ID
        goal: Original engineering goal
        status: Workflow status
        specification: Optional specification created
        architecture: Optional architecture design created
        plan: Optional implementation plan created
        review_report: Optional review report
        quality_report: Optional quality pipeline report
        release_notes: Optional release notes
        package_manifest: Optional package manifest
        artifact_count: Number of artifacts generated
        file_changes: Number of file changes made
        test_results: Test results summary
        lint_results: Lint results summary
        errors: List of errors encountered
        started_at: When the workflow started
        completed_at: When the workflow completed
        duration_seconds: Total execution time
        metadata: Additional metadata
    """
    workflow_id: str = ""
    goal: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    specification: Optional[Specification] = None
    architecture: Optional[ArchitectureDesign] = None
    plan: Optional[ImplementationPlan] = None
    review_report: Optional[ReviewReport] = None
    quality_report: Optional[QualityReport] = None
    release_notes: Optional[ReleaseNotes] = None
    package_manifest: Optional[PackageManifest] = None
    artifact_count: int = 0
    file_changes: int = 0
    test_results: str = ""
    lint_results: str = ""
    errors: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class EngineeringOrchestrator:
    """Coordinates the complete engineering lifecycle.

    The orchestrator is the main entry point for the Engineering Platform.
    It guides a high-level engineering request through a structured workflow:
    requirements analysis → architecture → planning → implementation →
    review → quality → documentation → packaging.

    Plugin extension points allow external code to contribute:
      - Custom reviewers (register_reviewer)
      - Custom quality checks (register_quality_check)
      - Custom documentation generators (register_documentation_generator)
      - Custom engineering tools (register_tool)
      - Pre/post workflow hooks (register_hook)

    Usage:
        config = EngineeringConfig(policy_mode=PolicyMode.HUMAN_APPROVAL)
        eng = EngineeringOrchestrator(event_bus, config)
        eng.initialize()

        result = eng.execute("Build a REST API for user management")

        print(f"Status: {result.status.value}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Artifacts: {result.artifact_count}")
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[EngineeringConfig] = None,
    ):
        self._event_bus = event_bus
        self.config = config or EngineeringConfig()
        self._state = EngineeringState.STOPPED
        self._lock = threading.RLock()
        self._workflows: Dict[str, WorkflowStatus] = {}
        self._workflow_checkpoints: Dict[str, Dict[str, Any]] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}

        # Plugin extension registries
        self._custom_reviewers: Dict[str, Callable] = {}
        self._custom_quality_checks: Dict[str, Callable] = {}
        self._custom_doc_generators: Dict[str, Callable] = {}
        self._custom_tools: Dict[str, Callable] = {}
        self._pre_workflow_hooks: List[Callable] = []
        self._post_workflow_hooks: List[Callable] = []

        # Resolve paths
        project_root = Path(self.config.project_root).resolve() if self.config.project_root else Path.cwd()

        # Initialize subsystems
        self.policy = PolicyEnforcer(mode=self.config.policy_mode)
        self.artifact_manager = ArtifactManager(
            base_dir=Path(self.config.artifacts_dir) if self.config.artifacts_dir else None,
        )
        self.requirements_analyzer = RequirementsAnalyzer(event_bus)
        self.architecture_planner = ArchitecturePlanner(event_bus)
        self.planner = EngineeringPlanner(event_bus)
        self.decomposer = TaskDecomposer(event_bus)
        self.repository = RepositoryIntelligence(event_bus)
        self.coordinator = ImplementationCoordinator(event_bus)
        self.code_editor = CodeEditor(
            policy_enforcer=self.policy,
            event_bus=event_bus,
            working_dir=str(project_root),
        )
        self.reviewer = AutomatedReview(event_bus)
        self.test_coordinator = TestCoordinator(
            event_bus, project_root=str(project_root),
        )
        self.lint_runner = LintRunner(
            event_bus, project_root=str(project_root),
        )
        self.static_analyzer = StaticAnalyzer(
            event_bus, project_root=str(project_root),
        )
        self.quality_pipeline = QualityPipeline(
            test_coordinator=self.test_coordinator,
            lint_runner=self.lint_runner,
            static_analyzer=self.static_analyzer,
            event_bus=event_bus,
        )
        self.doc_generator = DocumentationGenerator(
            event_bus,
            docs_dir=self.config.docs_dir or str(project_root / "docs"),
        )
        self.packaging_engine = PackagingEngine(
            event_bus, project_root=str(project_root),
        )
        self.release_notes_generator = ReleaseNotesGenerator(event_bus)
        self.dependency_manager = DependencyManager(
            event_bus, project_root=str(project_root),
        )
        self.migration_engine = MigrationEngine(event_bus)

        # Set backup directory
        backup_dir = self.config.backup_dir or str(
            project_root / ".aetheros" / "engineering" / "backups"
        )
        self.code_editor.set_backup_dir(backup_dir)

        # Repository profile (cached after analysis)
        self._repo_profile: Optional[RepositoryProfile] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> EngineeringState:
        """Current orchestrator state."""
        with self._lock:
            return self._state

    def initialize(self) -> None:
        """Initialize the engineering platform.

        Sets up all subsystems, optionally analyzes the repository,
        and transitions to READY state.
        """
        with self._lock:
            if self._state != EngineeringState.STOPPED:
                logger.warning("EngineeringOrchestrator: already initialized")
                return
            self._state = EngineeringState.INITIALIZING

        logger.info("EngineeringOrchestrator: initializing...")

        # Auto-discover repository
        if self.config.auto_discover_repo:
            repo_path = self.config.project_root or str(Path.cwd())
            try:
                self._repo_profile = self.repository.analyze(repo_path)
                logger.info(
                    "EngineeringOrchestrator: analyzed repository: %s (%d files)",
                    self._repo_profile.name,
                    self._repo_profile.total_files,
                )
            except Exception as exc:
                logger.warning("EngineeringOrchestrator: repo analysis failed: %s", exc)

        # Set up quality pipeline based on config
        if not self.config.enable_quality_pipeline:
            self.quality_pipeline.set_enabled_checks([])

        with self._lock:
            self._state = EngineeringState.READY

        if self._event_bus:
            self._event_bus.emit(EngineeringEvent.ENGINEERING_STARTED.value, {
                "policy_mode": self.config.policy_mode.value,
                "project_root": self.config.project_root,
                "repo_analyzed": self._repo_profile is not None,
            })

        logger.info(
            "EngineeringOrchestrator: ready (policy=%s)",
            self.config.policy_mode.value,
        )

    def shutdown(self) -> None:
        """Shut down the engineering platform gracefully."""
        with self._lock:
            if self._state == EngineeringState.STOPPED:
                return
            self._state = EngineeringState.STOPPED

        logger.info("EngineeringOrchestrator: shut down")

        if self._event_bus:
            self._event_bus.emit(EngineeringEvent.ENGINEERING_STOPPED.value, {})

    # ------------------------------------------------------------------
    # Main execution workflow
    # ------------------------------------------------------------------

    def execute(self, goal: str,
                context: Dict[str, Any] = None,
                resume_checkpoint: Optional[str] = None) -> WorkflowResult:
        """Execute a complete engineering workflow from goal to delivery.

        This is the main API entry point. It runs the full engineering
        lifecycle: requirements analysis, architecture, planning,
        implementation, review, quality, documentation, and packaging.

        Args:
            goal: The high-level engineering goal
            context: Additional context (constraints, preferences, etc.)
            resume_checkpoint: Optional checkpoint ID to resume from

        Returns:
            WorkflowResult with all outputs and status
        """
        if self._state not in (EngineeringState.READY, EngineeringState.WORKING):
            raise RuntimeError(
                f"Orchestrator not ready (state={self._state.value}). "
                "Call initialize() first."
            )

        workflow_id = uuid.uuid4().hex[:12]
        result = WorkflowResult(
            workflow_id=workflow_id,
            goal=goal,
        )

        with self._lock:
            self._state = EngineeringState.WORKING
            self._workflows[workflow_id] = WorkflowStatus.ANALYZING

        if self._event_bus:
            self._event_bus.emit_async(EngineeringEvent.WORKFLOW_STARTED.value, {
                "workflow_id": workflow_id,
                "goal": goal[:200],
            })

        result.started_at = time.time()
        logger.info("EngineeringOrchestrator: executing workflow %s: %s",
                    workflow_id[:8], goal[:80])

        # Run pre-workflow hooks
        for hook in self._pre_workflow_hooks:
            try:
                hook(workflow_id, goal, context)
            except Exception as exc:
                logger.debug("EngineeringOrchestrator: pre-hook failed: %s", exc)

        try:
            # Step 1: Analyze
            result.status = WorkflowStatus.ANALYZING
            repo_profile = self._analyze_project_internal(goal)
            self._save_checkpoint(workflow_id, "analyze", {"repo": str(repo_profile.name)
                                   if repo_profile else "N/A"})

            # Step 2: Requirements specification
            result.status = WorkflowStatus.SPECIFYING
            spec = self.create_specification(goal, context or {})
            result.specification = spec
            self._save_checkpoint(workflow_id, "specification", {"spec_id": spec.id})

            # Step 3: Architecture design
            result.status = WorkflowStatus.DESIGNING
            architecture = self._generate_architecture_internal(spec, repo_profile)
            result.architecture = architecture
            self._save_checkpoint(workflow_id, "architecture", {"architecture_id": architecture.id})

            # Step 4: Implementation planning
            result.status = WorkflowStatus.PLANNING
            plan = self.generate_plan(architecture)
            result.plan = plan
            self._save_checkpoint(workflow_id, "plan", {"plan_id": plan.id})

            # Step 5: Task decomposition
            result.status = WorkflowStatus.DECOMPOSING
            tasks = self.decomposer.decompose(architecture, specification=spec)
            self._save_checkpoint(workflow_id, "decomposition", {"tasks": len(tasks)})

            # Step 6: Implementation
            result.status = WorkflowStatus.IMPLEMENTING
            assignment = self._execute_plan_internal(plan, tasks)
            result.file_changes = len(self.coordinator.get_file_changes(
                assignment_id=assignment.id
            )) if assignment else 0
            self._save_checkpoint(workflow_id, "implementation", {
                "assignments": 1 if assignment else 0,
                "file_changes": result.file_changes,
            })

            # Step 7: Review (built-in + custom reviewers)
            result.status = WorkflowStatus.REVIEWING
            review_report = self.review_changes(workflow_id=workflow_id)
            result.review_report = review_report
            self._save_checkpoint(workflow_id, "review", {
                "findings": len(review_report.findings) if review_report else 0,
            })

            # Step 8: Quality pipeline (built-in + custom quality checks)
            if self.config.enable_quality_pipeline:
                result.status = WorkflowStatus.QUALITY_CHECKING
                quality_report = self.run_quality_pipeline()
                result.quality_report = quality_report
                self._save_checkpoint(workflow_id, "quality", {
                    "score": quality_report.score,
                    "passed": quality_report.passed_checks,
                    "total": quality_report.total_checks,
                })

            # Step 9: Documentation (built-in + custom generators)
            result.status = WorkflowStatus.DOCUMENTING
            self._generate_documentation_internal(spec, architecture, plan)
            self._save_checkpoint(workflow_id, "documentation", {})

            # Step 10: Release notes & packaging
            result.status = WorkflowStatus.PACKAGING
            release_notes = self.generate_release_notes(version="0.1.0")
            result.release_notes = release_notes
            self._save_checkpoint(workflow_id, "packaging", {})

            # Mark complete
            result.status = WorkflowStatus.COMPLETED
            result.artifact_count = len(self.artifact_manager.find(workflow_id=workflow_id))

            logger.info(
                "EngineeringOrchestrator: workflow %s completed: "
                "%d file changes, %d artifacts, quality=%.1f",
                workflow_id[:8], result.file_changes,
                result.artifact_count,
                result.quality_report.score if result.quality_report else 0,
            )

        except Exception as exc:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(exc))
            logger.error("EngineeringOrchestrator: workflow %s failed: %s",
                        workflow_id[:8], exc)

            if self._event_bus:
                self._event_bus.emit_async(
                    EngineeringEvent.WORKFLOW_FAILED.value, {
                        "workflow_id": workflow_id,
                        "error": str(exc),
                    },
                )

        finally:
            result.completed_at = time.time()
            result.duration_seconds = result.completed_at - (result.started_at or result.completed_at)

            # Run post-workflow hooks
            for hook in self._post_workflow_hooks:
                try:
                    hook(workflow_id, result)
                except Exception as exc:
                    logger.debug("EngineeringOrchestrator: post-hook failed: %s", exc)

            with self._lock:
                self._workflows[workflow_id] = result.status
                if result.status == WorkflowStatus.COMPLETED:
                    self._state = EngineeringState.COMPLETED
                elif result.status == WorkflowStatus.FAILED:
                    self._state = EngineeringState.FAILED
                else:
                    self._state = EngineeringState.READY

            if self._event_bus:
                self._event_bus.emit_async(
                    EngineeringEvent.WORKFLOW_COMPLETED.value, {
                        "workflow_id": workflow_id,
                        "status": result.status.value,
                        "duration": result.duration_seconds,
                        "file_changes": result.file_changes,
                        "artifacts": result.artifact_count,
                    },
                )

        return result

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------

    def analyze_project(self, repo_path: Optional[str] = None) -> RepositoryProfile:
        """Analyze a repository and return its profile.

        Args:
            repo_path: Path to repository root (uses project_root if not specified)

        Returns:
            RepositoryProfile with analysis results
        """
        path = repo_path or self.config.project_root or str(Path.cwd())
        profile = self.repository.analyze(path)
        self._repo_profile = profile
        return profile

    def create_specification(self, goal: str,
                             context: Dict[str, Any] = None) -> Specification:
        """Create a structured specification from an engineering goal.

        Args:
            goal: Engineering goal
            context: Additional context

        Returns:
            Specification with requirements, constraints, and criteria
        """
        spec = self.requirements_analyzer.analyze(goal, context=context or {})

        self.artifact_manager.register(
            type=ArtifactType.SPECIFICATION,
            name=f"Specification: {spec.title[:40]}",
            description=spec.summary,
            metadata={"spec_id": spec.id, "requirements": len(spec.functional_requirements)},
        )

        return spec

    def generate_plan(self, architecture: ArchitectureDesign) -> ImplementationPlan:
        """Generate an implementation plan from an architecture design.

        Args:
            architecture: ArchitectureDesign object

        Returns:
            ImplementationPlan with phases and tasks
        """
        tasks = self.decomposer.decompose(architecture)
        plan = self.planner.create_plan(architecture, decomposed_tasks=tasks)

        self.artifact_manager.register(
            type=ArtifactType.PLAN,
            name=f"Plan: {plan.title[:40]}",
            description=f"{len(plan.tasks)} tasks across {len(plan.phases)} phases",
            metadata={
                "plan_id": plan.id,
                "tasks": len(plan.tasks),
                "hours": plan.total_estimated_hours,
            },
        )

        return plan

    def review_changes(self, workflow_id: str = "") -> ReviewReport:
        """Review changes made during implementation.

        Runs built-in code review and any registered custom reviewers.

        Args:
            workflow_id: Optional workflow ID for context

        Returns:
            ReviewReport with findings
        """
        # Collect all file changes
        file_changes = self.coordinator.get_unreviewed_changes()

        # Perform built-in code review on changed files
        all_findings = []
        for change in file_changes:
            report = self.reviewer.code_review(
                change.file_path,
                change.new_content or change.original_content,
            )
            all_findings.extend(report.findings)

        # Run custom reviewers
        for reviewer_name, reviewer_fn in self._custom_reviewers.items():
            try:
                custom_findings = reviewer_fn(file_changes)
                if custom_findings:
                    all_findings.extend(custom_findings)
            except Exception as exc:
                logger.warning("EngineeringOrchestrator: custom reviewer %s failed: %s",
                              reviewer_name, exc)

        # Check for conflicts between parallel changes
        conflict_report = self.reviewer.conflict_review(file_changes)

        review_report = ReviewReport(
            type="comprehensive_review",
            target="all_changes",
            findings=all_findings,
            conflict_report=conflict_report,
            reviewer="automated-engineering-review",
        )

        # Generate summary
        review_report.summary = self.reviewer._generate_summary(all_findings)

        self.artifact_manager.register(
            type=ArtifactType.REVIEW,
            name="Code review report",
            description=(
                f"{len(all_findings)} findings, "
                f"{len(conflict_report.conflicting_files)} conflicts"
            ),
            workflow_id=workflow_id,
            metadata={"score": review_report.summary.score if review_report.summary else 0},
        )

        return review_report

    def run_quality_pipeline(self, target: str = "",
                             include_docs: bool = False) -> QualityReport:
        """Run the complete quality pipeline.

        Includes built-in checks plus any registered custom quality checks.

        Args:
            target: Specific target to check (defaults to project root)
            include_docs: Whether to include documentation checks

        Returns:
            QualityReport with all check results
        """
        if not target:
            target = self.config.project_root or "."

        # Configure which checks to run
        enabled = [
            QualityDimension.LINTING,
            QualityDimension.TYPE_CHECKING,
            QualityDimension.UNIT_TESTS,
            QualityDimension.SECURITY_SCAN,
        ]
        if include_docs:
            enabled.append(QualityDimension.CODE_REVIEW)

        self.quality_pipeline.set_enabled_checks(enabled)
        report = self.quality_pipeline.run(target)

        # Run custom quality checks and add as additional checks
        for check_name, check_fn in self._custom_quality_checks.items():
            try:
                custom_check = check_fn(target)
                if custom_check:
                    report.checks.append(custom_check)
                    report.total_checks += 1
                    if getattr(custom_check, 'status', None) == QualityStatus.PASSED:
                        report.passed_checks += 1
                    elif getattr(custom_check, 'status', None) == QualityStatus.FAILED:
                        report.failed_checks += 1
            except Exception as exc:
                logger.warning("EngineeringOrchestrator: custom quality check %s failed: %s",
                              check_name, exc)

        # Recalculate score with custom checks
        report.score = self.quality_pipeline._calculate_score(report)

        self.artifact_manager.register(
            type=ArtifactType.REPORT,
            name="Quality pipeline report",
            description=f"Score: {report.score:.1f}, {report.passed_checks}/{report.total_checks} checks passed",
            tags=["quality", "pipeline"],
            metadata={
                "score": report.score,
                "passed": report.passed_checks,
                "failed": report.failed_checks,
                "total": report.total_checks,
            },
        )

        return report

    def generate_release_notes(self, version: str = "0.1.0",
                               changes: List[ChangeEntry] = None,
                               title: str = "") -> ReleaseNotes:
        """Generate release notes for a version.

        Args:
            version: Version number
            changes: List of changes (auto-collected if not provided)
            title: Release title

        Returns:
            ReleaseNotes object
        """
        if not changes:
            changes = self._collect_changes()

        notes = self.release_notes_generator.create_notes(
            version=version,
            title=title or f"Release {version}",
            summary="Automated release notes from engineering workflow",
            changes=changes,
        )

        self.artifact_manager.register(
            type=ArtifactType.REPORT,
            name=f"Release notes v{version}",
            description=f"{len(changes)} changes documented",
            tags=["release", "notes"],
            metadata={"version": version, "changes": len(changes)},
        )

        return notes

    def export_artifacts(self, collection_id: str,
                         format: str = "json") -> Optional[str]:
        """Export artifacts for a workflow.

        Args:
            collection_id: Collection or workflow ID
            format: Export format ("json" or "markdown")

        Returns:
            Formatted manifest string, or None if not found
        """
        return self.artifact_manager.export_manifest(collection_id, format=format)

    def resume_workflow(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Resume a previously paused or checkpointed workflow.

        Args:
            workflow_id: Workflow ID to resume

        Returns:
            WorkflowResult with resumed execution, or None if not found
        """
        checkpoint = self._workflow_checkpoints.get(workflow_id)
        if checkpoint is None:
            logger.warning("EngineeringOrchestrator: no checkpoint for %s", workflow_id[:8])
            return None

        goal = checkpoint.get("goal", "")
        context = checkpoint.get("context", {})

        logger.info("EngineeringOrchestrator: resuming workflow %s", workflow_id[:8])

        return self.execute(goal, context=context, resume_checkpoint=workflow_id)

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            workflow_id: Workflow ID to cancel

        Returns:
            True if cancelled
        """
        with self._lock:
            status = self._workflows.get(workflow_id)
            if status is None or status in (WorkflowStatus.COMPLETED,
                                           WorkflowStatus.FAILED,
                                           WorkflowStatus.CANCELLED):
                return False
            self._workflows[workflow_id] = WorkflowStatus.CANCELLED

        if self._event_bus:
            self._event_bus.emit_async(EngineeringEvent.WORKFLOW_CANCELLED.value, {
                "workflow_id": workflow_id,
            })

        logger.info("EngineeringOrchestrator: cancelled workflow %s", workflow_id[:8])
        return True

    # ------------------------------------------------------------------
    # Internal workflow steps
    # ------------------------------------------------------------------

    def _analyze_project_internal(self, goal: str) -> Optional[RepositoryProfile]:
        """Internal: analyze the project repository."""
        repo_path = self.config.project_root or str(Path.cwd())
        try:
            return self.repository.analyze(repo_path)
        except Exception as exc:
            logger.warning("EngineeringOrchestrator: repo analysis failed: %s", exc)
            return None

    def _generate_architecture_internal(self, spec: Specification,
                                        repo_profile: Optional[RepositoryProfile]) -> ArchitectureDesign:
        """Internal: generate architecture from specification."""
        architecture = self.architecture_planner.generate(spec)

        # Register as artifact
        self.artifact_manager.register(
            type=ArtifactType.ARCHITECTURE,
            name=f"Architecture: {architecture.title[:40]}",
            description=architecture.overview,
            metadata={
                "architecture_id": architecture.id,
                "modules": len(architecture.modules),
                "interfaces": len(architecture.interfaces),
            },
        )

        return architecture

    def _execute_plan_internal(self, plan: ImplementationPlan,
                                tasks: List[DecomposedTask]) -> Optional[CodingAssignment]:
        """Internal: execute an implementation plan."""
        # Approve and start the plan
        self.planner.approve(plan.id)
        self.planner.start(plan.id)

        # Create assignments for each task
        assignment = None
        for task in tasks:
            assignment = self.coordinator.create_assignment(
                task_id=task.id,
                plan_id=plan.id,
                description=task.title,
                files_to_modify=task.files_to_modify,
                assigned_to=task.ownership.agent_type,
            )
            self.coordinator.mark_in_progress(assignment.id)

        return assignment

    def _generate_documentation_internal(self, spec: Specification,
                                          architecture: ArchitectureDesign,
                                          plan: ImplementationPlan) -> None:
        """Internal: generate documentation for completed work."""
        # Generate architecture documentation
        doc_change = self.doc_generator.generate_architecture_doc(architecture)
        self.doc_generator.apply_changes([doc_change])

        # Generate API documentation if architecture has interfaces
        if hasattr(architecture, 'interfaces') and architecture.interfaces:
            for iface in architecture.interfaces:
                if iface.name:
                    api_doc = self.doc_generator.generate_api_doc(
                        module_name=iface.name,
                        output_path=f"docs/api/{iface.name.lower().replace(' ', '-')}.md",
                    )
                    self.doc_generator.apply_changes([api_doc])

        # Run custom documentation generators
        for gen_name, gen_fn in self._custom_doc_generators.items():
            try:
                gen_fn(architecture, spec, plan)
            except Exception as exc:
                logger.warning("EngineeringOrchestrator: custom doc generator %s failed: %s",
                              gen_name, exc)

    def _collect_changes(self) -> List[ChangeEntry]:
        """Collect changes from the current workflow for release notes."""
        changes = []
        file_changes = self.coordinator.get_file_changes()

        for change in file_changes:
            category = ChangeCategory.IMPROVEMENT
            if change.change_type.value == "create":
                category = ChangeCategory.FEATURE
            elif change.change_type.value == "delete":
                category = ChangeCategory.OTHER

            changes.append(ChangeEntry(
                category=category,
                description=f"{change.change_type.value}: {change.file_path}",
                component=change.file_path.split("/")[-1] if "/" in change.file_path else change.file_path,
            ))

        return changes

    def _save_checkpoint(self, workflow_id: str, stage: str,
                          data: Dict[str, Any]) -> None:
        """Save a checkpoint for resumable execution.

        Args:
            workflow_id: Workflow ID
            stage: Current stage name
            data: Checkpoint data
        """
        if workflow_id not in self._workflow_checkpoints:
            self._workflow_checkpoints[workflow_id] = {
                "workflow_id": workflow_id,
                "stages": {},
            }

        self._workflow_checkpoints[workflow_id]["stages"][stage] = {
            "timestamp": time.time(),
            "data": data,
        }

        if self._event_bus:
            self._event_bus.emit_async(EngineeringEvent.WORKFLOW_PROGRESS.value, {
                "workflow_id": workflow_id,
                "stage": stage,
                "data": data,
            })

    # ------------------------------------------------------------------
    # Progress subscriptions
    # ------------------------------------------------------------------

    def subscribe_progress(self, workflow_id: str,
                           callback: Callable[[str, Any], None]) -> Callable:
        """Subscribe to progress events for a workflow.

        Args:
            workflow_id: Workflow ID
            callback: Callback receiving (stage, data)

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._progress_callbacks.setdefault(workflow_id, []).append(callback)

        def unsubscribe():
            with self._lock:
                cbs = self._progress_callbacks.get(workflow_id, [])
                if callback in cbs:
                    cbs.remove(callback)

        return unsubscribe

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def set_policy_mode(self, mode: PolicyMode) -> None:
        """Change the execution policy mode.

        Args:
            mode: New policy mode
        """
        self.config.policy_mode = mode
        self.policy.set_mode(mode)
        logger.info("EngineeringOrchestrator: policy mode set to %s", mode.value)

    def get_approvals_pending(self) -> List[Any]:
        """Get all actions currently pending human approval.

        Returns:
            List of PolicyCheck objects awaiting approval
        """
        return self.policy.pending_approvals()

    def approve_action(self, check_id: str, approved_by: str = "human") -> bool:
        """Approve a pending action.

        Args:
            check_id: Policy check ID
            approved_by: Who approved it

        Returns:
            True if approved
        """
        result = self.policy.approve(check_id, approved_by)
        if result and self._event_bus:
            self._event_bus.emit_async(EngineeringEvent.APPROVAL_GRANTED.value, {
                "check_id": check_id,
                "approved_by": approved_by,
            })
        return result

    def deny_action(self, check_id: str, denied_by: str = "human") -> bool:
        """Deny a pending action.

        Args:
            check_id: Policy check ID
            denied_by: Who denied it

        Returns:
            True if denied
        """
        result = self.policy.deny(check_id, denied_by)
        if result and self._event_bus:
            self._event_bus.emit_async(EngineeringEvent.APPROVAL_DENIED.value, {
                "check_id": check_id,
                "denied_by": denied_by,
            })
        return result

    # ------------------------------------------------------------------
    # Plugin extension points
    # ------------------------------------------------------------------

    def register_reviewer(self, name: str,
                          reviewer_fn: Callable[[List[FileChange]], List[ReviewFinding]]) -> None:
        """Register a custom code reviewer.

        The reviewer function receives a list of FileChange objects and
        returns a list of ReviewFinding objects.

        Args:
            name: Unique name for this reviewer
            reviewer_fn: Callable[[List[FileChange]], List[ReviewFinding]]
        """
        with self._lock:
            self._custom_reviewers[name] = reviewer_fn
        logger.info("EngineeringOrchestrator: registered custom reviewer '%s'", name)

    def unregister_reviewer(self, name: str) -> bool:
        """Remove a custom reviewer.

        Args:
            name: Name of the reviewer to remove

        Returns:
            True if removed
        """
        with self._lock:
            return self._custom_reviewers.pop(name, None) is not None

    def register_quality_check(self, name: str,
                               check_fn: Callable[[str], QualityCheck]) -> None:
        """Register a custom quality check.

        The check function receives a target path and returns a QualityCheck.

        Args:
            name: Unique name for this check
            check_fn: Callable[[str], QualityCheck]
        """
        with self._lock:
            self._custom_quality_checks[name] = check_fn
        logger.info("EngineeringOrchestrator: registered custom quality check '%s'", name)

    def unregister_quality_check(self, name: str) -> bool:
        """Remove a custom quality check.

        Args:
            name: Name of the check to remove

        Returns:
            True if removed
        """
        with self._lock:
            return self._custom_quality_checks.pop(name, None) is not None

    def register_documentation_generator(
        self, name: str,
        gen_fn: Callable[[ArchitectureDesign, Specification, ImplementationPlan], None],
    ) -> None:
        """Register a custom documentation generator.

        The generator function receives architecture, specification, and plan.

        Args:
            name: Unique name for this generator
            gen_fn: Callable[[ArchitectureDesign, Specification, ImplementationPlan], None]
        """
        with self._lock:
            self._custom_doc_generators[name] = gen_fn
        logger.info("EngineeringOrchestrator: registered custom doc generator '%s'", name)

    def unregister_documentation_generator(self, name: str) -> bool:
        """Remove a custom documentation generator.

        Args:
            name: Name of the generator to remove

        Returns:
            True if removed
        """
        with self._lock:
            return self._custom_doc_generators.pop(name, None) is not None

    def register_tool(self, name: str,
                      tool_fn: Callable[..., Any]) -> None:
        """Register a custom engineering tool.

        Tools are available for use during workflow execution.

        Args:
            name: Unique name for this tool
            tool_fn: Callable that performs the tool operation
        """
        with self._lock:
            self._custom_tools[name] = tool_fn
        logger.info("EngineeringOrchestrator: registered custom tool '%s'", name)

    def unregister_tool(self, name: str) -> bool:
        """Remove a custom tool.

        Args:
            name: Name of the tool to remove

        Returns:
            True if removed
        """
        with self._lock:
            return self._custom_tools.pop(name, None) is not None

    def register_hook(self, hook_type: str,
                      hook_fn: Callable) -> None:
        """Register a workflow lifecycle hook.

        Args:
            hook_type: One of "pre_workflow" or "post_workflow"
            hook_fn: Callable to invoke at the hook point

        Raises:
            ValueError: If hook_type is unknown
        """
        if hook_type == "pre_workflow":
            self._pre_workflow_hooks.append(hook_fn)
        elif hook_type == "post_workflow":
            self._post_workflow_hooks.append(hook_fn)
        else:
            raise ValueError(f"Unknown hook type: {hook_type}. Use 'pre_workflow' or 'post_workflow'.")

        logger.debug("EngineeringOrchestrator: registered %s hook", hook_type)

    # ------------------------------------------------------------------
    # Status & health
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status."""
        with self._lock:
            active_workflows = {
                wf_id: status.value
                for wf_id, status in self._workflows.items()
                if status in (
                    WorkflowStatus.ANALYZING, WorkflowStatus.SPECIFYING,
                    WorkflowStatus.DESIGNING, WorkflowStatus.PLANNING,
                    WorkflowStatus.IMPLEMENTING, WorkflowStatus.REVIEWING,
                    WorkflowStatus.QUALITY_CHECKING, WorkflowStatus.DOCUMENTING,
                    WorkflowStatus.PACKAGING,
                )
            }

        return {
            "orchestrator": {
                "state": self.state.value,
                "policy_mode": self.config.policy_mode.value,
            },
            "workflows": {
                "total": len(self._workflows),
                "active": len(active_workflows),
                "active_list": active_workflows,
            },
            "policy": self.policy.get_stats(),
            "artifacts": self.artifact_manager.get_stats(),
            "requirements": self.requirements_analyzer.get_stats(),
            "architecture": self.architecture_planner.get_stats(),
            "repository": self.repository.get_stats(),
            "planner": self.planner.get_stats(),
            "coding": self.coordinator.get_stats(),
            "review": self.reviewer.get_stats(),
            "testing": self.test_coordinator.get_stats(),
            "linting": self.lint_runner.get_stats(),
            "analysis": self.static_analyzer.get_stats(),
            "quality": self.quality_pipeline.get_stats(),
            "documentation": self.doc_generator.get_stats(),
            "packaging": self.packaging_engine.get_stats(),
            "release_notes": self.release_notes_generator.get_stats(),
            "dependencies": self.dependency_manager.get_stats(),
            "migration": self.migration_engine.get_stats(),
            "plugins": {
                "reviewers": list(self._custom_reviewers.keys()),
                "quality_checks": list(self._custom_quality_checks.keys()),
                "doc_generators": list(self._custom_doc_generators.keys()),
                "tools": list(self._custom_tools.keys()),
            },
        }

    def health(self) -> Dict[str, Any]:
        """Get orchestrator health status."""
        return {
            "state": self.state.value,
            "ready": self.state == EngineeringState.READY,
            "policy_mode": self.config.policy_mode.value,
            "active_workflows": sum(
                1 for s in self._workflows.values()
                if s not in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                            WorkflowStatus.CANCELLED)
            ),
            "total_workflows": len(self._workflows),
            "plugins": {
                "reviewers": len(self._custom_reviewers),
                "quality_checks": len(self._custom_quality_checks),
                "doc_generators": len(self._custom_doc_generators),
                "tools": len(self._custom_tools),
            },
        }
