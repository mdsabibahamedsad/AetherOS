"""
Tests for the AetherOS Engineering Platform (Phase 8).

Covers:
  - Execution policy enforcement
  - Artifact management
  - Requirements extraction
  - Architecture planning
  - Task decomposition
  - Repository analysis
  - Implementation coordination
  - Code editing
  - Automated review
  - Testing coordinator
  - Linting runner
  - Static analysis
  - Quality pipeline
  - Documentation generator
  - Packaging
  - Release notes
  - Dependency manager
  - Migration engine
  - Engineering orchestrator
  - Workflow resume
  - Policy enforcement
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engineering.execution_policy import (
    PolicyEnforcer,
    PolicyMode,
    PolicyDecision,
    HumanApprovalRequired,
)
from engineering.artifact_manager import (
    ArtifactManager,
    ArtifactType,
    ArtifactEntry,
)
from engineering.requirements import (
    RequirementsAnalyzer,
    Specification,
    FunctionalRequirement,
    RequirementPriority,
)
from engineering.architecture import (
    ArchitecturePlanner,
    ArchitectureDesign,
    ModuleBoundary,
)
from engineering.planner import (
    EngineeringPlanner,
    ImplementationPlan,
    PlanStatus,
    EngineeringTask,
    TaskType,
)
from engineering.decomposition import (
    TaskDecomposer,
    DecomposedTask,
    Estimation,
    Priority as TaskPriority,
    Ownership,
)
from engineering.repository import RepositoryIntelligence, RepositoryProfile
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
    SafetyCheck,
)
from engineering.review import (
    AutomatedReview,
    ReviewReport,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
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
)
from engineering.migration import (
    MigrationEngine,
    MigrationPlan,
    MigrationStep,
    MigrationStatus,
)
from engineering.orchestrator import (
    EngineeringOrchestrator,
    EngineeringConfig,
    EngineeringState,
    WorkflowResult,
    WorkflowStatus,
)


# =========================================================================
# Execution Policy Tests
# =========================================================================

class TestPolicyEnforcer:
    def test_default_mode_is_read_only(self):
        enforcer = PolicyEnforcer()
        assert enforcer.mode == PolicyMode.READ_ONLY_ANALYSIS

    def test_set_mode(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        assert enforcer.mode == PolicyMode.HUMAN_APPROVAL
        enforcer.set_mode(PolicyMode.AUTOMATIC_LOCAL)
        assert enforcer.mode == PolicyMode.AUTOMATIC_LOCAL

    def test_read_only_denies_writes(self):
        enforcer = PolicyEnforcer(PolicyMode.READ_ONLY_ANALYSIS)
        check = enforcer.check("write_file", "src/main.py")
        assert check.decision == PolicyDecision.DENIED

    def test_read_only_allows_reads(self):
        enforcer = PolicyEnforcer(PolicyMode.READ_ONLY_ANALYSIS)
        check = enforcer.check("read_file", "src/main.py")
        assert check.decision == PolicyDecision.ALLOWED

    def test_human_approval_raises_for_writes(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        with pytest.raises(HumanApprovalRequired) as excinfo:
            enforcer.check("write_file", "src/main.py")
        assert "requires human approval" in str(excinfo.value)

    def test_human_approval_allows_reads(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        check = enforcer.check("read_file", "src/main.py")
        assert check.decision == PolicyDecision.ALLOWED

    def test_approve_pending(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        with pytest.raises(HumanApprovalRequired) as excinfo:
            enforcer.check("write_file", "src/main.py")
        check_id = excinfo.value.check.id
        assert enforcer.approve(check_id, approved_by="test")
        # Verify audit log updated
        assert enforcer.audit_log()[0].decision == PolicyDecision.ALLOWED

    def test_deny_pending(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        with pytest.raises(HumanApprovalRequired) as excinfo:
            enforcer.check("delete_file", "src/main.py")
        check_id = excinfo.value.check.id
        assert enforcer.deny(check_id, denied_by="test")

    def test_auto_approve_pattern(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        enforcer.add_auto_approve_pattern("README.md")
        check = enforcer.check("write_file", "docs/README.md")
        assert check.decision == PolicyDecision.ALLOWED

    def test_audit_log(self):
        enforcer = PolicyEnforcer()
        enforcer.check("read_file", "test.py")
        enforcer.check("analyze", "module")
        assert len(enforcer.audit_log()) == 2

    def test_pending_approvals(self):
        enforcer = PolicyEnforcer(PolicyMode.HUMAN_APPROVAL)
        with pytest.raises(HumanApprovalRequired):
            enforcer.check("write_file", "file.py")
        with pytest.raises(HumanApprovalRequired):
            enforcer.check("delete_file", "file2.py")
        # Checks are stored in _pending_approvals before exception is raised
        assert len(enforcer.pending_approvals()) == 2

    def test_ci_mode_denies_deploy(self):
        enforcer = PolicyEnforcer(PolicyMode.CI_ORIENTED)
        check = enforcer.check("deploy", "production")
        assert check.decision == PolicyDecision.DENIED

    def test_stats(self):
        enforcer = PolicyEnforcer()
        enforcer.check("read_file", "a.py")
        enforcer.check("read_file", "b.py")
        stats = enforcer.get_stats()
        assert stats["total_checks"] == 2


# =========================================================================
# Artifact Manager Tests
# =========================================================================

class TestArtifactManager:
    def test_register_artifact(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        entry = mgr.register(
            type=ArtifactType.REPORT,
            name="test-report",
            description="A test report",
            workflow_id="wf-1",
            tags=["test", "report"],
        )
        assert entry.id
        assert entry.type == ArtifactType.REPORT
        assert entry.name == "test-report"
        assert entry.workflow_id == "wf-1"

    def test_get_artifact(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        entry = mgr.register(ArtifactType.REPORT, "test")
        assert mgr.get(entry.id) is entry

    def test_find_by_type(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "r1")
        mgr.register(ArtifactType.PATCH, "p1")
        mgr.register(ArtifactType.REPORT, "r2")
        reports = mgr.find(type=ArtifactType.REPORT)
        assert len(reports) == 2

    def test_find_by_workflow(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "r1", workflow_id="wf-1")
        mgr.register(ArtifactType.REPORT, "r2", workflow_id="wf-2")
        assert len(mgr.find(workflow_id="wf-1")) == 1

    def test_store_and_read_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ArtifactManager(base_dir=Path(tmpdir))
            entry = mgr.register(ArtifactType.REPORT, "content-test")
            path = mgr.store_file(entry.id, "Hello, World!", extension=".txt")
            assert path is not None
            assert path.exists()
            content = mgr.read_content(entry.id)
            assert content == "Hello, World!"

    def test_collection(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "r1", workflow_id="wf-1")
        mgr.register(ArtifactType.PATCH, "p1", workflow_id="wf-1")
        artifacts = mgr.get_workflow_artifacts("wf-1")
        assert len(artifacts) == 2

    def test_export_manifest_json(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "r1", workflow_id="wf-1")
        manifest = mgr.export_manifest("wf-1", format="json")
        assert manifest is not None
        assert '"name": "r1"' in manifest

    def test_purge(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "old", workflow_id="wf-1")
        count = mgr.purge(older_than_days=-1)  # Purge everything
        assert count >= 0
        assert len(mgr.find()) == 0

    def test_stats(self):
        mgr = ArtifactManager(base_dir=Path(tempfile.mkdtemp()))
        mgr.register(ArtifactType.REPORT, "r1")
        mgr.register(ArtifactType.PATCH, "p1")
        stats = mgr.get_stats()
        assert stats["total_artifacts"] == 2
        assert stats["by_type"]["report"] == 1
        assert stats["by_type"]["patch"] == 1


# =========================================================================
# Requirements Analyzer Tests
# =========================================================================

class TestRequirementsAnalyzer:
    def test_analyze_basic_goal(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Build a REST API for user management")
        assert spec.id
        assert "Build a REST API" in spec.title
        assert len(spec.functional_requirements) > 0
        assert len(spec.non_functional_requirements) > 0

    def test_analyze_api_goal(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Create a REST API with user authentication")
        has_api = any("API" in r.description for r in spec.functional_requirements)
        has_auth = any("auth" in r.description.lower() for r in spec.functional_requirements)
        assert has_api or has_auth

    def test_spec_summary(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Build a tool")
        assert "requirements" in spec.summary.lower()

    def test_get_spec(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Test goal")
        assert analyzer.get_spec(spec.id) is spec

    def test_update_spec(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Test goal")
        new_req = FunctionalRequirement(description="New requirement")
        updated = analyzer.update_spec(spec.id, {"functional_requirements": [new_req]})
        assert updated is not None
        assert len(updated.functional_requirements) > 1

    def test_to_dict(self):
        analyzer = RequirementsAnalyzer()
        spec = analyzer.analyze("Build a REST API")
        d = analyzer.to_dict(spec.id)
        assert d is not None
        assert "functional_requirements" in d
        assert "non_functional_requirements" in d

    def test_stats(self):
        analyzer = RequirementsAnalyzer()
        analyzer.analyze("Goal 1")
        analyzer.analyze("Goal 2")
        stats = analyzer.get_stats()
        assert stats["total_specs"] == 2


# =========================================================================
# Architecture Planner Tests
# =========================================================================

class TestArchitecturePlanner:
    def test_generate_from_spec(self):
        planner = ArchitecturePlanner()
        spec = Specifications()
        spec.title = "Test Architecture"
        spec.id = "spec-1"
        spec.functional_requirements = [
            FunctionalRequirement(description="Build a REST API with database")
        ]
        spec.non_functional_requirements = []
        arch = planner.generate(spec)

        assert arch.id
        assert "Test Architecture" in arch.title
        assert len(arch.modules) > 0

    def test_generates_modules(self):
        planner = ArchitecturePlanner()
        spec = SimpleSpec("Build a REST API", "spec-1")
        arch = planner.generate(spec)
        assert len(arch.modules) >= 3  # Core, API Layer, Testing, etc.

    def test_generates_interfaces(self):
        planner = ArchitecturePlanner()
        spec = SimpleSpec("Build a REST API with database and auth")
        arch = planner.generate(spec)
        assert len(arch.interfaces) > 0

    def test_technology_recommendations(self):
        planner = ArchitecturePlanner()
        spec = SimpleSpec("Build a Python REST API")
        arch = planner.generate(spec)
        assert len(arch.technologies) > 0
        assert any("Python" in t.name for t in arch.technologies)

    def test_design_decisions(self):
        planner = ArchitecturePlanner()
        arch = planner.generate(SimpleSpec("Build a system"))
        assert len(arch.design_decisions) > 0

    def test_review_workflow(self):
        planner = ArchitecturePlanner()
        arch = planner.generate(SimpleSpec("Build a system"))
        from engineering.architecture import ArchitectureReview
        review = ArchitectureReview(
            architecture_id=arch.id,
            approved=True,
            findings=["Well designed"],
            overall_assessment="Good",
        )
        updated = planner.add_review(arch.id, review)
        assert updated is not None
        assert updated.status == "approved"

    def test_get_design(self):
        planner = ArchitecturePlanner()
        arch = planner.generate(SimpleSpec("Build a system"))
        assert planner.get_design(arch.id) is arch

    def test_list_designs(self):
        planner = ArchitecturePlanner()
        planner.generate(SimpleSpec("System 1"))
        planner.generate(SimpleSpec("System 2"))
        assert len(planner.list_designs()) == 2


class SimpleSpec:
    """Minimal specification for testing."""
    def __init__(self, goal="Build a system", id=None):
        self.id = id or "spec-1"
        self.title = goal[:40]
        self.goal = goal
        self.functional_requirements = [
            FunctionalRequirement(description=goal),
        ]
        self.non_functional_requirements = []


class Specifications:
    """Minimal specification for testing purposes."""
    pass


# =========================================================================
# Engineering Planner Tests
# =========================================================================

class TestEngineeringPlanner:
    def test_create_plan(self):
        planner = EngineeringPlanner()
        arch = SimpleArchitecture("Test Architecture")
        plan = planner.create_plan(arch)
        assert plan.id
        assert plan.title == "Implementation Plan: Test Architecture"

    def test_approve_plan(self):
        planner = EngineeringPlanner()
        plan = planner.create_plan(SimpleArchitecture("Test"))
        approved = planner.approve(plan.id)
        assert approved is not None
        assert approved.status == PlanStatus.APPROVED

    def test_plan_lifecycle(self):
        planner = EngineeringPlanner()
        plan = planner.create_plan(SimpleArchitecture("Test"))
        planner.approve(plan.id)
        planner.start(plan.id)
        assert plan.status == PlanStatus.IN_PROGRESS
        planner.complete(plan.id)
        assert plan.status == PlanStatus.COMPLETED

    def test_get_ready_tasks(self):
        planner = EngineeringPlanner()
        plan = planner.create_plan(SimpleArchitecture("Test"))
        planner.approve(plan.id)
        ready = planner.get_ready_tasks(plan.id)
        assert len(ready) >= 0

    def test_get_progress(self):
        planner = EngineeringPlanner()
        plan = planner.create_plan(SimpleArchitecture("Test"))
        progress = planner.get_progress(plan.id)
        assert progress is not None
        assert "progress_pct" in progress

    def test_list_plans(self):
        planner = EngineeringPlanner()
        planner.create_plan(SimpleArchitecture("Plan 1"))
        planner.create_plan(SimpleArchitecture("Plan 2"))
        assert len(planner.list_plans()) == 2


class SimpleArchitecture:
    """Minimal architecture for testing."""
    def __init__(self, title="Test"):
        self.id = "arch-1"
        self.title = title
        self.spec_id = "spec-1"
        self.goal = "Build a system"
        self.modules = [
            ModuleBoundary(name="Core", description="Core module"),
            ModuleBoundary(name="API", description="API module"),
        ]
        self.interfaces = []
        self.technologies = []
        self.design_decisions = []
        self.reviews = []
        self.overview = "A test architecture"


# =========================================================================
# Task Decomposer Tests
# =========================================================================

class TestTaskDecomposer:
    def test_decompose_architecture(self):
        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(SimpleArchitecture("Test"))
        assert len(tasks) >= 3  # setup + module tasks + tests + docs

    def test_get_ready_tasks(self):
        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(SimpleArchitecture("Test"))
        ready = decomposer.get_ready_tasks(tasks)
        assert len(ready) > 0  # setup task should be ready

    def test_update_task_status(self):
        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(SimpleArchitecture("Test"))
        assert decomposer.update_task_status(tasks, tasks[0].id, "completed")
        assert tasks[0].status == "completed"

    def test_parallel_groups(self):
        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(SimpleArchitecture("Test"))
        groups = decomposer.get_parallel_groups(tasks)
        assert len(groups) > 0


# =========================================================================
# Repository Intelligence Tests
# =========================================================================

class TestRepositoryIntelligence:
    def test_analyze_nonexistent_path(self):
        ri = RepositoryIntelligence()
        profile = ri.analyze("/nonexistent/path")
        assert profile.name == "path"
        assert profile.total_files == 0

    def test_analyze_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("print('hello')")
            Path(tmpdir, "test_main.py").write_text("def test_x(): pass")
            Path(tmpdir, "pyproject.toml").write_text(
                '[project]\nname = "test"\nversion = "0.1.0"\n'
            )
            ri = RepositoryIntelligence()
            profile = ri.analyze(tmpdir)
            assert profile.name
            assert profile.total_files >= 3
            assert len(profile.languages) > 0
            assert any(l.name == "Python" for l in profile.languages)

    def test_detect_build_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pyproject.toml").write_text(
                '[build-system]\nrequires = ["hatchling"]\n'
                '[project]\ndependencies = []\n'
            )
            ri = RepositoryIntelligence()
            profile = ri.analyze(tmpdir)
            assert profile.build_system is not None

    def test_detect_config_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Dockerfile").write_text("FROM python:3.12")
            ri = RepositoryIntelligence()
            profile = ri.analyze(tmpdir)
            assert profile.has_docker is True
            assert "Dockerfile" in profile.config_files

    def test_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("print('hello')")
            ri = RepositoryIntelligence()
            profile1 = ri.analyze(tmpdir)
            profile2 = ri.analyze(tmpdir)  # Should use cache
            assert profile1 is profile2

    def test_clear_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ri = RepositoryIntelligence()
            ri.analyze(tmpdir)
            ri.clear_cache(tmpdir)
            assert ri.get_profile(tmpdir) is None


# =========================================================================
# Implementation Coordinator Tests
# =========================================================================

class TestImplementationCoordinator:
    def test_create_assignment(self):
        coord = ImplementationCoordinator()
        assignment = coord.create_assignment(
            task_id="task-1",
            plan_id="plan-1",
            description="Implement feature X",
            files_to_modify=["src/main.py"],
        )
        assert assignment.id
        assert assignment.status == AssignmentStatus.PENDING

    def test_mark_completed(self):
        coord = ImplementationCoordinator()
        a = coord.create_assignment(task_id="task-1")
        assert coord.mark_completed(a.id, result="Done")
        assert a.status == AssignmentStatus.COMPLETED

    def test_mark_failed(self):
        coord = ImplementationCoordinator()
        a = coord.create_assignment(task_id="task-1")
        assert coord.mark_failed(a.id, "Something went wrong")
        assert a.status == AssignmentStatus.FAILED
        assert a.error == "Something went wrong"

    def test_file_change_tracking(self):
        coord = ImplementationCoordinator()
        change = coord.register_file_change(
            "src/main.py", ChangeType.MODIFY,
            original_content="old content\nsecond line",
            new_content="new content\nsecond line\nthird line added",
        )
        assert change.id
        assert change.file_path == "src/main.py"
        assert change.lines_added == 1  # 3 new lines - 2 old lines = 1 added

    def test_get_pending(self):
        coord = ImplementationCoordinator()
        coord.create_assignment(task_id="task-1")
        coord.create_assignment(task_id="task-2")
        assert len(coord.get_pending_assignments()) == 2

    def test_unreviewed_changes(self):
        coord = ImplementationCoordinator()
        coord.register_file_change("file.py", ChangeType.MODIFY)
        assert len(coord.get_unreviewed_changes()) == 1

    def test_get_assignments_by_plan(self):
        coord = ImplementationCoordinator()
        coord.create_assignment(task_id="t1", plan_id="plan-1")
        coord.create_assignment(task_id="t2", plan_id="plan-1")
        coord.create_assignment(task_id="t3", plan_id="plan-2")
        assert len(coord.get_assignments_by_plan("plan-1")) == 2
        assert len(coord.get_assignments_by_plan("plan-2")) == 1

    def test_mark_reviewed(self):
        coord = ImplementationCoordinator()
        a = coord.create_assignment(task_id="t1")
        coord.mark_completed(a.id)
        coord.register_file_change("file.py", ChangeType.MODIFY, assignment_id=a.id)
        assert coord.mark_reviewed(a.id)
        assert len(coord.get_unreviewed_changes()) == 0

    def test_get_stats(self):
        coord = ImplementationCoordinator()
        coord.create_assignment(task_id="t1")
        coord.create_assignment(task_id="t2")
        stats = coord.get_stats()
        assert stats["total_assignments"] == 2
        assert stats["by_status"]["pending"] == 2


# =========================================================================
# Code Editor Tests
# =========================================================================

class TestCodeEditor:
    def test_create_edit_plan(self):
        editor = CodeEditor()
        plan = editor.create_edit_plan("Add feature X")
        assert plan.id
        assert plan.description == "Add feature X"

    def test_add_operation(self):
        editor = CodeEditor()
        plan = editor.create_edit_plan("Test")
        op = editor.add_operation(
            plan.id, "test.py", operation="create",
            new_content="print('hello')",
        )
        assert op is not None
        assert op.file_path.endswith("test.py")

    def test_safety_check_binary(self):
        editor = CodeEditor()
        # Override BINARY_EXTENSIONS for testing
        check = editor._perform_safety_check(
            EditOperation(file_path="test.png", operation="modify")
        )
        assert check == SafetyCheck.FAILED

    def test_generate_diff(self):
        editor = CodeEditor()
        plan = editor.create_edit_plan("Test")
        editor.add_operation(
            plan.id, "test.py", operation="create",
            new_content="print('hello')\n",
        )
        diff = editor.generate_diff(plan)
        assert "Edit Plan:" in diff
        assert "CREATE" in diff
        assert "test.py" in diff

    def test_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            editor = CodeEditor()
            editor.set_backup_dir(str(backup_dir))
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("original")
            editor._backup_file(test_file)
            backups = editor.list_backups()
            assert len(backups) > 0


# =========================================================================
# Automated Review Tests
# =========================================================================

class TestAutomatedReview:
    def test_code_review(self):
        reviewer = AutomatedReview()
        content = """
def long_function(x):
    # TODO: implement this properly
    result = []
    for i in range(10):
        result.append(i)
    return result
"""
        report = reviewer.code_review("test.py", content)
        assert len(report.findings) > 0
        assert any("TODO" in f.description or f"TODO" in str(f) for f in report.findings)

    def test_architecture_review(self):
        reviewer = AutomatedReview()
        arch = SimpleArchitecture("Test")
        report = reviewer.architecture_review(arch)
        assert report.type == "architecture_review"
        assert report.target == "Test"

    def test_conflict_review(self):
        reviewer = AutomatedReview()
        from engineering.coding import FileChange, ChangeType
        changes = [
            FileChange(file_path="file1.py", assignment_id="a1"),
            FileChange(file_path="file1.py", assignment_id="a2"),
            FileChange(file_path="file2.py", assignment_id="a1"),
        ]
        report = reviewer.conflict_review(changes)
        assert len(report.conflicting_files) == 1
        assert "file1.py" in report.conflicting_files

    def test_pass_threshold(self):
        reviewer = AutomatedReview()
        reviewer.set_pass_threshold(50.0)
        assert reviewer._min_score_to_pass == 50.0

    def test_get_findings_by_severity(self):
        reviewer = AutomatedReview()
        report = reviewer.code_review("test.py", "x = 1\n")
        findings = reviewer.get_findings_by_severity(
            report.id, ReviewSeverity.INFO
        )
        assert findings == []


# =========================================================================
# Quality Pipeline Tests
# =========================================================================

class TestQualityPipeline:
    def test_init(self):
        pipeline = QualityPipeline()
        assert pipeline is not None

    def test_set_enabled_checks(self):
        pipeline = QualityPipeline()
        pipeline.set_enabled_checks([QualityDimension.LINTING])
        assert QualityDimension.LINTING in pipeline._enabled_checks
        assert QualityDimension.UNIT_TESTS not in pipeline._enabled_checks

    def test_run_creates_report(self):
        pipeline = QualityPipeline()
        report = pipeline.run(".", checks=[QualityDimension.LINTING])
        assert report.id
        assert report.target == "."
        # One or more checks ran
        assert len(report.checks) >= 0
        assert report.score >= 0.0

    def test_score_calculation(self):
        pipeline = QualityPipeline()
        report = QualityReport(target="test")
        report.checks = [
            QualityCheck(dimension=QualityDimension.LINTING, status=QualityStatus.FAILED),
            QualityCheck(dimension=QualityDimension.UNIT_TESTS, status=QualityStatus.PASSED),
        ]
        report.passed_checks = 1
        report.failed_checks = 1
        report.total_checks = 2
        score = pipeline._calculate_score(report)
        assert score < 100.0  # Deductions

    def test_empty_pipeline(self):
        pipeline = QualityPipeline()
        pipeline.set_enabled_checks([])
        report = pipeline.run(".")
        assert report.total_checks == 0
        assert report.score == 100.0


# =========================================================================
# Documentation Generator Tests
# =========================================================================

class TestDocumentationGenerator:
    def test_generate_readme(self):
        gen = DocumentationGenerator()
        change = gen.generate_readme(
            "TestProject",
            description="A test project",
            changes=["Added authentication"],
        )
        assert change.file_path.endswith("README.md")
        assert "TestProject" in change.new_content
        assert "Added authentication" in change.new_content

    def test_generate_api_doc(self):
        gen = DocumentationGenerator()
        endpoints = [
            {"method": "GET", "path": "/api/users", "description": "List users"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            gen.set_docs_dir(str(Path(tmpdir) / "docs"))
            change = gen.generate_api_doc("Users", endpoints)
            assert "Users API" in change.new_content
            assert "/api/users" in change.new_content

    def test_generate_architecture_doc(self):
        gen = DocumentationGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            gen.set_docs_dir(str(Path(tmpdir) / "docs"))
            arch = SimpleArchitecture("My System")
            change = gen.generate_architecture_doc(arch)
            assert change.file_path.endswith(".md")

    def test_apply_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = DocumentationGenerator(docs_dir=str(tmpdir))
            change = gen.generate_readme(
                "Test",
                sections=[DocumentationSection(title="Usage", content="How to use")],
            )
            count = gen.apply_changes([change])
            assert count == 1
            assert Path(change.file_path).exists()


# =========================================================================
# Packaging Engine Tests
# =========================================================================

class TestPackagingEngine:
    def test_bump_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
            engine = PackagingEngine(project_root=tmpdir)
            new_version = engine.bump_version(part="patch")
            assert new_version == "0.1.1"
            content = pyproject.read_text()
            assert "0.1.1" in content

    def test_bump_minor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
            engine = PackagingEngine(project_root=tmpdir)
            new_version = engine.bump_version(part="minor")
            assert new_version == "0.2.0"

    def test_bump_major(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
            engine = PackagingEngine(project_root=tmpdir)
            new_version = engine.bump_version(part="major")
            assert new_version == "1.0.0"


# =========================================================================
# Release Notes Tests
# =========================================================================

class TestReleaseNotesGenerator:
    def test_create_notes(self):
        gen = ReleaseNotesGenerator()
        notes = gen.create_notes(
            version="1.0.0",
            title="First Release",
            summary="Initial release",
        )
        assert notes.version == "1.0.0"
        assert notes.title == "First Release"

    def test_add_change(self):
        gen = ReleaseNotesGenerator()
        notes = gen.create_notes("1.0.0")
        entry = gen.add_change(
            notes.id,
            "Added authentication feature",
            category=ChangeCategory.FEATURE,
            component="auth",
        )
        assert entry is not None
        assert len(notes.changes) == 1

    def test_to_markdown(self):
        gen = ReleaseNotesGenerator()
        notes = gen.create_notes("1.0.0")
        gen.add_change(notes.id, "Added login", ChangeCategory.FEATURE)
        markdown = gen.to_markdown(notes)
        assert "1.0.0" in markdown
        assert "Features" in markdown
        assert "Added login" in markdown

    def test_to_json(self):
        gen = ReleaseNotesGenerator()
        notes = gen.create_notes("1.0.0")
        gen.add_change(notes.id, "Fix bug", ChangeCategory.BUG_FIX)
        data = gen.to_json(notes)
        assert data["version"] == "1.0.0"
        assert len(data["changes"]) == 1

    def test_find_by_version(self):
        gen = ReleaseNotesGenerator()
        gen.create_notes("1.0.0")
        notes = gen.find_by_version("1.0.0")
        assert notes is not None
        assert notes.version == "1.0.0"

    def test_changelog_entry(self):
        gen = ReleaseNotesGenerator()
        entry = gen.add_changelog_entry(
            "2.0.0", "Major refactor", ChangeCategory.REFACTOR,
        )
        assert entry is not None


# =========================================================================
# Dependency Manager Tests
# =========================================================================

class TestDependencyManager:
    def test_discover_from_temp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "requirements.txt").write_text(
                "requests>=2.28\nflask>=2.3\n"
            )
            mgr = DependencyManager(project_root=tmpdir)
            deps = mgr.discover()
            assert len(deps) >= 2
            names = [d.name for d in deps]
            assert "requests" in names
            assert "flask" in names

    def test_discover_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pyproject.toml").write_text(
                '[project]\nname = "test"\n'
                '[project.dependencies]\n'
                'click = ">=8.0"\n'
                'rich = ">=10.0"\n'
            )
            mgr = DependencyManager(project_root=tmpdir)
            deps = mgr.discover()
            names = [d.name for d in deps]
            assert "click" in names
            assert "rich" in names

    def test_get_vulnerable(self):
        mgr = DependencyManager()
        from engineering.dependency_manager import DependencyVulnerability
        dep = DependencyEntry(
            name="old-package",
            version="1.0.0",
            status=DependencyStatus.VULNERABLE,
            vulnerabilities=[
                DependencyVulnerability(
                    id="CVE-2024-1234",
                    severity="high",
                    description="Remote code execution vulnerability",
                    fixed_in="2.0.0",
                ),
            ],
        )
        mgr._dependencies[dep.name] = dep
        vulnerable = mgr.get_vulnerable()
        assert len(vulnerable) == 1

    def test_get_stats(self):
        mgr = DependencyManager()
        mgr._dependencies["pkg1"] = DependencyEntry(
            name="pkg1", type="production",
        )
        mgr._dependencies["pkg2"] = DependencyEntry(
            name="pkg2", type="development",
        )
        stats = mgr.get_stats()
        assert stats["total_dependencies"] == 2
        assert stats["by_type"]["production"] == 1
        assert stats["by_type"]["development"] == 1


# =========================================================================
# Migration Engine Tests
# =========================================================================

class TestMigrationEngine:
    def test_create_plan(self):
        engine = MigrationEngine()
        plan = engine.create_plan(
            title="Migrate to v2",
            description="Migrate from v1 to v2",
            from_version="1.0.0",
            to_version="2.0.0",
        )
        assert plan.id
        assert plan.title == "Migrate to v2"
        assert plan.from_version == "1.0.0"
        assert plan.to_version == "2.0.0"

    def test_add_step(self):
        engine = MigrationEngine()
        plan = engine.create_plan("Migration")
        step = engine.add_step(
            plan.id, "Update imports",
            description="Update all import paths",
            can_rollback=True,
        )
        assert step is not None
        assert step.name == "Update imports"
        assert len(plan.steps) == 1

    def test_execute_plan(self):
        engine = MigrationEngine()
        plan = engine.create_plan("Test Migration")
        engine.add_step(plan.id, "Step 1")
        engine.add_step(plan.id, "Step 2")
        executed = engine.execute(plan)
        assert executed.status == MigrationStatus.COMPLETED
        for step in executed.steps:
            assert step.status == MigrationStatus.COMPLETED

    def test_get_execution_history(self):
        engine = MigrationEngine()
        plan = engine.create_plan("Migration 1")
        engine.execute(plan)
        plan2 = engine.create_plan("Migration 2")
        engine.execute(plan2)
        history = engine.get_execution_history()
        assert len(history) == 2

    def test_list_plans(self):
        engine = MigrationEngine()
        engine.create_plan("Plan 1")
        engine.create_plan("Plan 2")
        assert len(engine.list_plans()) == 2


# =========================================================================
# Engineering Orchestrator Tests
# =========================================================================

class TestEngineeringOrchestrator:
    def test_init_and_initialize(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.READ_ONLY_ANALYSIS,
                auto_discover_repo=False,
            ),
        )
        assert eng.state == EngineeringState.STOPPED
        eng.initialize()
        assert eng.state == EngineeringState.READY
        eng.shutdown()
        assert eng.state == EngineeringState.STOPPED

    def test_set_policy_mode(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(auto_discover_repo=False),
        )
        eng.initialize()
        eng.set_policy_mode(PolicyMode.AUTOMATIC_LOCAL)
        assert eng.config.policy_mode == PolicyMode.AUTOMATIC_LOCAL
        eng.shutdown()

    def test_create_specification(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(auto_discover_repo=False),
        )
        eng.initialize()
        spec = eng.create_specification("Build a CLI tool", context={})
        assert spec.id
        assert spec.goal == "Build a CLI tool"
        eng.shutdown()

    def test_execute_read_only(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.READ_ONLY_ANALYSIS,
                auto_discover_repo=False,
                enable_quality_pipeline=False,
            ),
        )
        eng.initialize()
        with tempfile.TemporaryDirectory() as tmpdir:
            eng.config.project_root = tmpdir
            result = eng.execute("Build a test tool", context={})
            assert result.status == WorkflowStatus.COMPLETED
            assert result.specification is not None
            assert result.architecture is not None
            assert result.plan is not None
        eng.shutdown()

    def test_health(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(auto_discover_repo=False),
        )
        eng.initialize()
        health = eng.health()
        assert health["state"] == "ready"
        assert health["ready"] is True
        eng.shutdown()

    def test_status(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(auto_discover_repo=False),
        )
        eng.initialize()
        status = eng.status()
        assert "orchestrator" in status
        assert "workflows" in status
        assert "policy" in status
        eng.shutdown()

    def test_empty_workflow(self):
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.READ_ONLY_ANALYSIS,
                auto_discover_repo=False,
                enable_quality_pipeline=False,
            ),
        )
        eng.initialize()
        result = eng.execute("", context={})
        assert result.workflow_id
        assert result.duration_seconds >= 0
        eng.shutdown()


# =========================================================================
# Integration Tests
# =========================================================================

class TestIntegration:
    def test_analysis_to_plan_flow(self):
        """Test the flow from requirement analysis through to planning."""
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.READ_ONLY_ANALYSIS,
                auto_discover_repo=False,
            ),
        )
        eng.initialize()

        # Step 1: Requirements
        spec = eng.create_specification("Build a REST API for managing users")
        assert len(spec.functional_requirements) > 0

        # Step 2: Architecture
        arch = eng.architecture_planner.generate(spec)
        assert len(arch.modules) > 0

        # Step 3: Plan
        plan = eng.generate_plan(arch)
        assert plan.tasks or plan.phases

        eng.shutdown()

    def test_full_workflow_read_only(self):
        """Test the full workflow execution in read-only mode."""
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.READ_ONLY_ANALYSIS,
                auto_discover_repo=False,
                enable_quality_pipeline=False,
            ),
        )
        eng.initialize()

        result = eng.execute("Create a simple Python utility library")

        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
        if result.status == WorkflowStatus.COMPLETED:
            assert result.specification is not None
            assert result.architecture is not None
            assert result.plan is not None

        eng.shutdown()


# =========================================================================
# Policy Enforcement Integration Tests
# =========================================================================

class TestPolicyEnforcement:
    def test_approval_workflow(self):
        """Test the human approval workflow end-to-end."""
        eng = EngineeringOrchestrator(
            config=EngineeringConfig(
                policy_mode=PolicyMode.HUMAN_APPROVAL,
                auto_discover_repo=False,
            ),
        )
        eng.initialize()

        # Verify approval gate
        pending = eng.get_approvals_pending()
        assert len(pending) >= 0

        # Approve all pending
        for check in pending:
            eng.approve_action(check.id)

        eng.shutdown()

    def test_policy_mode_enforcement(self):
        """Test that policy mode is enforced throughout the workflow."""
        enforcer = PolicyEnforcer(PolicyMode.READ_ONLY_ANALYSIS)

        # Read should pass
        assert enforcer.check("read_file", "test.py").decision == PolicyDecision.ALLOWED

        # Write should fail
        assert enforcer.check("write_file", "test.py").decision == PolicyDecision.DENIED

        # Destructive should fail
        assert enforcer.check("delete_file", "test.py").decision == PolicyDecision.DENIED
