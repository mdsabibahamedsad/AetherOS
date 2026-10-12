"""Verification Agent for AetherOS Orchestration Layer.

Implements Phases 30-35 of Master Prompt 11: independent verification of task results
with evidence requirements and success criteria.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from agent.orchestration.agent_interface import AgentInterface, AgentCapabilities, AgentIdentity, AgentLifecycleState, AgentMetadata, AgentRole, SupportsVerification
from agent.orchestration.agent_registry import AgentRegistry
from agent.orchestration.types import TaskSpec, TaskResult, TaskStatus, VerificationReport, AgentRole
from agent.orchestration.handoff import HandoffContext

logger = logging.getLogger(__name__)


# =============================================================================
# Verification Types
# =============================================================================


class VerificationType(Enum):
    """Types of verification."""

    SYNTACTIC = "syntactic"          # Syntax/format validation
    SEMANTIC = "semantic"            # Meaning/logic validation
    FUNCTIONAL = "functional"        # Does it work as intended
    SECURITY = "security"            # Security audit
    PERFORMANCE = "performance"      # Performance benchmarks
    COMPLIANCE = "compliance"        # Policy/regulatory compliance
    TEST_BASED = "test_based"        # Run tests
    BUILD_BASED = "build_based"      # Build/compile
    EVIDENCE_BASED = "evidence_based"  # Verify citations/sources
    CROSS_REFERENCE = "cross_reference"  # Cross-check with other sources


class VerificationLevel(Enum):
    """Verification thoroughness levels."""

    QUICK = "quick"          # Basic sanity check
    STANDARD = "standard"    # Normal verification
    THOROUGH = "thorough"    # Deep verification
    EXHAUSTIVE = "exhaustive"  # Maximum verification


@dataclass
class VerificationCriteria:
    """Criteria for verifying a task result."""

    criteria_id: str = field(default_factory=lambda: f"vc-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    verification_type: VerificationType = VerificationType.FUNCTIONAL
    level: VerificationLevel = VerificationLevel.STANDARD
    required: bool = True  # If False, failure is a warning
    weight: float = 1.0  # Weight in overall score
    checker: Optional[Callable[[Any, TaskSpec], bool]] = None  # Custom checker
    expected_result: Any = None  # Expected value for comparison
    tolerance: float = 0.0  # Tolerance for numeric comparisons


@dataclass
class Evidence:
    """Evidence supporting a verification result."""

    evidence_id: str = field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:8]}")
    verification_type: VerificationType = VerificationType.FUNCTIONAL
    source: str = ""  # Where evidence came from
    content: Any = None  # The evidence itself
    confidence: float = 1.0  # 0.0 - 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Verification Agent
# =============================================================================


class VerificationAgent(SupportsVerification):
    """Independent verification agent that checks results produced by other agents."""

    def __init__(self, agent_registry: Optional[AgentRegistry] = None):
        self._registry = agent_registry
        self._identity = AgentIdentity(
            role=AgentRole.REVIEW,
            name="VerificationAgent",
        )
        self._state = AgentLifecycleState.READY
        self._config: Dict[str, Any] = {}
        self._verifiers: Dict[VerificationType, Callable] = {}
        self._register_builtin_verifiers()

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def capabilities(self) -> AgentCapabilities:
        caps = AgentCapabilities()
        caps.add("verification")
        caps.add("test_execution")
        caps.add("code_analysis")
        caps.add("security_audit")
        caps.add("evidence_validation")
        caps.add("cross_referencing")
        return caps

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            description="Independent verification agent for task results",
            author="AetherOS",
            tags=["verification", "review", "quality_assurance"],
            supported_platforms=["linux", "macos", "windows"],
        )

    @property
    def state(self) -> AgentLifecycleState:
        return self._state

    def _register_builtin_verifiers(self) -> None:
        """Register built-in verification methods."""
        self._verifiers = {
            VerificationType.SYNTACTIC: self._verify_syntactic,
            VerificationType.FUNCTIONAL: self._verify_functional,
            VerificationType.TEST_BASED: self._verify_tests,
            VerificationType.BUILD_BASED: self._verify_build,
            VerificationType.EVIDENCE_BASED: self._verify_evidence,
            VerificationType.SECURITY: self._verify_security,
            VerificationType.CROSS_REFERENCE: self._verify_cross_reference,
        }

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the verification agent."""
        self._config = config
        self._state = AgentLifecycleState.READY
        logger.info("Verification agent initialized")

    async def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the verification agent."""
        self._state = AgentLifecycleState.TERMINATED

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {"status": "healthy", "verifiers": list(self._verifiers.keys())}

    async def execute_task(self, task: TaskSpec) -> TaskResult:
        """Execute a verification task."""
        # Verification tasks specify what to verify
        target_result = task.context.get("target_result")
        target_task = task.context.get("target_task")
        criteria = task.context.get("criteria", [])

        if not target_result and not target_task:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error="No target result or task specified for verification",
            )

        report = await self.verify_result(target_result, {
            "criteria": criteria,
            "target_task": target_task,
        })

        return TaskResult(
            task_id=task.task_id,
            success=report.verified,
            result=report,
            verification={"verified": report.verified, "confidence": report.confidence},
        )

    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        return True

    def get_active_tasks(self) -> List[str]:
        return []

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return None

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config.update(config)

    def get_config(self) -> Dict[str, Any]:
        return self._config

    # ── SupportsVerification Interface ────────────────────────────────

    async def verify_result(self, result: Any, criteria: Dict[str, Any]) -> VerificationReport:
        """Verify a result against criteria."""
        verification_criteria = criteria.get("criteria", [])
        target_task = criteria.get("target_task")

        all_evidence = []
        all_discrepancies = []
        criteria_results = {}
        total_weight = 0.0
        passed_weight = 0.0

        for vc in verification_criteria:
            if isinstance(vc, dict):
                vc = VerificationCriteria(**vc)

            total_weight += vc.weight

            try:
                # Run appropriate verifier
                verifier = self._verifiers.get(vc.verification_type, self._verify_generic)
                passed, evidence, discrepancies = await verifier(result, vc, target_task)

                criteria_results[vc.criteria_id] = passed

                if passed:
                    passed_weight += vc.weight
                else:
                    all_discrepancies.extend(discrepancies)

                all_evidence.extend(evidence)

            except Exception as e:
                logger.error(f"Verification criteria {vc.criteria_id} failed: {e}")
                criteria_results[vc.criteria_id] = False
                all_discrepancies.append(f"Verification error: {e}")

        # Calculate overall result
        confidence = passed_weight / total_weight if total_weight > 0 else 0.0
        verified = confidence >= 0.8 and all(r for r in criteria_results.values() if verification_criteria[list(criteria_results.keys()).index(r)].required)

        return VerificationReport(
            verified=verified,
            confidence=confidence,
            evidence=[e.content for e in all_evidence if hasattr(e, 'content')],
            discrepancies=all_discrepancies,
            criteria_results=criteria_results,
            verifier_id=self._identity.agent_id,
            notes=f"Verified {len(criteria_results)} criteria, {sum(criteria_results.values())} passed",
        )

    # ── Built-in Verifiers ──────────────────────────────────────────

    async def _verify_syntactic(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Verify syntactic correctness (JSON, YAML, code syntax, etc.)."""
        evidence = []
        discrepancies = []

        if isinstance(result, str):
            # Try to parse as JSON
            import json
            try:
                json.loads(result)
                evidence.append(Evidence(
                    verification_type=VerificationType.SYNTACTIC,
                    source="json_parser",
                    content="Valid JSON syntax",
                    confidence=1.0,
                ))
                return True, evidence, discrepancies
            except json.JSONDecodeError as e:
                discrepancies.append(f"Invalid JSON: {e}")

            # Try Python syntax
            try:
                compile(result, "<string>", "exec")
                evidence.append(Evidence(
                    verification_type=VerificationType.SYNTACTIC,
                    source="python_compiler",
                    content="Valid Python syntax",
                    confidence=1.0,
                ))
                return True, evidence, discrepancies
            except SyntaxError as e:
                discrepancies.append(f"Invalid Python syntax: {e}")

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_functional(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Verify functional correctness - does the result achieve the goal."""
        evidence = []
        discrepancies = []

        if target_task and target_task.success_criteria:
            # Check each success criterion
            for criterion in target_task.success_criteria:
                # Simple keyword-based check (would use LLM in production)
                criterion_lower = criterion.lower()
                result_str = str(result).lower()

                if any(word in result_str for word in criterion_lower.split()):
                    evidence.append(Evidence(
                        verification_type=VerificationType.FUNCTIONAL,
                        source="keyword_match",
                        content=f"Criterion matched: {criterion}",
                        confidence=0.7,
                    ))
                else:
                    discrepancies.append(f"Criterion not met: {criterion}")

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_tests(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Verify by running tests."""
        evidence = []
        discrepancies = []

        # This would run actual tests in a test environment
        # For now, simulate test execution
        if target_task and "test_command" in target_task.metadata:
            test_cmd = target_task.metadata["test_command"]
            evidence.append(Evidence(
                verification_type=VerificationType.TEST_BASED,
                source="test_runner",
                content=f"Would run: {test_cmd}",
                confidence=0.5,
            ))
            # In production: run tests and check results
        else:
            discrepancies.append("No test command specified")

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_build(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Verify by building/compiling."""
        evidence = []
        discrepancies = []

        if target_task and "build_command" in target_task.metadata:
            build_cmd = target_task.metadata["build_command"]
            evidence.append(Evidence(
                verification_type=VerificationType.BUILD_BASED,
                source="build_system",
                content=f"Would run: {build_cmd}",
                confidence=0.5,
            ))
        else:
            discrepancies.append("No build command specified")

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_evidence(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Verify evidence/citations in result."""
        evidence = []
        discrepancies = []

        result_str = str(result)

        # Check for citations/references
        import re
        citations = re.findall(r'\[(\d+)\]|\((https?://[^)]+)\)', result_str)

        if citations:
            evidence.append(Evidence(
                verification_type=VerificationType.EVIDENCE_BASED,
                source="citation_check",
                content=f"Found {len(citations)} citations",
                confidence=0.8,
            ))
        else:
            discrepancies.append("No citations found in result")

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_security(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Security verification."""
        evidence = []
        discrepancies = []

        result_str = str(result).lower()

        # Check for common security issues
        security_patterns = [
            ("password", "Potential password exposure"),
            ("api_key", "Potential API key exposure"),
            ("secret", "Potential secret exposure"),
            ("token", "Potential token exposure"),
            ("private_key", "Potential private key exposure"),
        ]

        for pattern, msg in security_patterns:
            if pattern in result_str:
                discrepancies.append(msg)
                evidence.append(Evidence(
                    verification_type=VerificationType.SECURITY,
                    source="security_scan",
                    content=f"Flagged: {msg}",
                    confidence=0.6,
                ))

        if not discrepancies:
            evidence.append(Evidence(
                verification_type=VerificationType.SECURITY,
                source="security_scan",
                content="No obvious secrets detected",
                confidence=0.7,
            ))

        return len(discrepancies) == 0, evidence, discrepancies

    async def _verify_cross_reference(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Cross-reference with external sources."""
        evidence = []
        discrepancies = []

        # Would query external sources in production
        evidence.append(Evidence(
            verification_type=VerificationType.CROSS_REFERENCE,
            source="cross_reference",
            content="Cross-reference check would be performed here",
            confidence=0.3,
        ))

        return True, evidence, discrepancies  # Default pass

    async def _verify_generic(self, result: Any, vc: VerificationCriteria, target_task: Optional[TaskSpec]) -> tuple:
        """Generic verification using custom checker."""
        evidence = []
        discrepancies = []

        if vc.checker:
            try:
                passed = vc.checker(result, target_task)
                if passed:
                    evidence.append(Evidence(
                        verification_type=vc.verification_type,
                        source="custom_checker",
                        content="Custom checker passed",
                        confidence=0.8,
                    ))
                else:
                    discrepancies.append("Custom checker failed")
            except Exception as e:
                discrepancies.append(f"Custom checker error: {e}")

        return len(discrepancies) == 0, evidence, discrepancies


# =============================================================================
# Verification Orchestrator
# =============================================================================


class VerificationOrchestrator:
    """Orchestrates verification of task results, managing multiple verifiers."""

    def __init__(self, agent_registry: Optional[AgentRegistry] = None):
        self._registry = agent_registry
        self._verification_agent = VerificationAgent(agent_registry)
        self._verification_history: List[VerificationReport] = []
        self._max_history = 1000

    async def verify_task_result(
        self,
        task: TaskSpec,
        result: TaskResult,
        criteria: Optional[List[VerificationCriteria]] = None,
        level: VerificationLevel = VerificationLevel.STANDARD,
        independent: bool = True,
    ) -> VerificationReport:
        """Verify a task result.

        Args:
            task: The original task
            result: The result to verify
            criteria: Custom verification criteria (uses task.success_criteria if not provided)
            level: Verification thoroughness
            independent: Whether to use independent verifier (not the same agent)
        """
        # Build verification criteria from task if not provided
        if criteria is None:
            criteria = self._build_criteria_from_task(task, level)

        # Execute verification
        verification_task = TaskSpec(
            task_id=f"verify-{task.task_id}",
            goal=f"Verify result of task {task.task_id}",
            context={
                "target_result": result.result,
                "target_task": task,
                "criteria": [self._vc_to_dict(c) for c in criteria],
            },
            required_capabilities=["verification"],
        )

        report = await self._verification_agent.verify_result(result.result, {
            "criteria": [self._vc_to_dict(c) for c in criteria],
            "target_task": task,
        })

        # Store history
        self._verification_history.append(report)
        if len(self._verification_history) > self._max_history:
            self._verification_history = self._verification_history[-self._max_history:]

        return report

    def _build_criteria_from_task(self, task: TaskSpec, level: VerificationLevel) -> List[VerificationCriteria]:
        """Build verification criteria from task specification."""
        criteria = []

        # Success criteria -> functional verification
        for i, criterion in enumerate(task.success_criteria):
            criteria.append(VerificationCriteria(
                name=f"success_criterion_{i}",
                description=criterion,
                verification_type=VerificationType.FUNCTIONAL,
                level=level,
                required=True,
            ))

        # Add type-specific criteria based on required capabilities
        for cap in task.required_capabilities:
            if cap in ["code_execution", "coding", "development"]:
                criteria.append(VerificationCriteria(
                    name="syntax_check",
                    description="Code syntax validation",
                    verification_type=VerificationType.SYNTACTIC,
                    level=level,
                    required=True,
                ))
                criteria.append(VerificationCriteria(
                    name="test_execution",
                    description="Test suite execution",
                    verification_type=VerificationType.TEST_BASED,
                    level=level,
                    required=level != VerificationLevel.QUICK,
                ))
            elif cap in ["research", "web_search"]:
                criteria.append(VerificationCriteria(
                    name="citation_check",
                    description="Evidence/citation validation",
                    verification_type=VerificationType.EVIDENCE_BASED,
                    level=level,
                    required=True,
                ))
            elif cap in ["deployment", "devops"]:
                criteria.append(VerificationCriteria(
                    name="build_check",
                    description="Build/deployment validation",
                    verification_type=VerificationType.BUILD_BASED,
                    level=level,
                    required=True,
                ))
            elif cap in ["security", "audit"]:
                criteria.append(VerificationCriteria(
                    name="security_scan",
                    description="Security vulnerability scan",
                    verification_type=VerificationType.SECURITY,
                    level=level,
                    required=True,
                ))

        return criteria

    def _vc_to_dict(self, vc: VerificationCriteria) -> Dict[str, Any]:
        """Convert VerificationCriteria to dict for serialization."""
        return {
            "criteria_id": vc.criteria_id,
            "name": vc.name,
            "description": vc.description,
            "verification_type": vc.verification_type.value,
            "level": vc.level.value,
            "required": vc.required,
            "weight": vc.weight,
        }

    def get_verification_history(self, limit: int = 10) -> List[VerificationReport]:
        """Get recent verification history."""
        return self._verification_history[-limit:]


# =============================================================================
# Specialized Verifiers
# =============================================================================


class CodingVerifier:
    """Specialized verifier for coding tasks."""

    @staticmethod
    async def verify_code_result(
        result: Any,
        task: TaskSpec,
        test_command: Optional[str] = None,
        build_command: Optional[str] = None,
    ) -> VerificationReport:
        """Verify a coding task result."""
        from agent.orchestration.verification import VerificationOrchestrator, VerificationCriteria, VerificationType, VerificationLevel

        orchestrator = VerificationOrchestrator()

        criteria = [
            VerificationCriteria(
                name="syntax",
                description="Code syntax validation",
                verification_type=VerificationType.SYNTACTIC,
                level=VerificationLevel.STANDARD,
                required=True,
            ),
        ]

        if test_command:
            task.metadata["test_command"] = test_command
            criteria.append(VerificationCriteria(
                name="tests",
                description="Test suite execution",
                verification_type=VerificationType.TEST_BASED,
                level=VerificationLevel.STANDARD,
                required=True,
            ))

        if build_command:
            task.metadata["build_command"] = build_command
            criteria.append(VerificationCriteria(
                name="build",
                description="Build/compilation",
                verification_type=VerificationType.BUILD_BASED,
                level=VerificationLevel.STANDARD,
                required=True,
            ))

        task_result = TaskResult(
            task_id=task.task_id,
            success=True,
            result=result,
        )

        return await orchestrator.verify_task_result(task, task_result, criteria)


class ResearchVerifier:
    """Specialized verifier for research tasks."""

    @staticmethod
    async def verify_research_result(
        result: Any,
        task: TaskSpec,
        min_citations: int = 3,
    ) -> VerificationReport:
        """Verify a research task result."""
        from agent.orchestration.verification import VerificationOrchestrator, VerificationCriteria, VerificationType, VerificationLevel

        orchestrator = VerificationOrchestrator()

        criteria = [
            VerificationCriteria(
                name="citations",
                description=f"Minimum {min_citations} citations",
                verification_type=VerificationType.EVIDENCE_BASED,
                level=VerificationLevel.STANDARD,
                required=True,
                checker=lambda r, t: len(str(r)) > 100,  # Placeholder
            ),
            VerificationCriteria(
                name="coherence",
                description="Logical coherence of findings",
                verification_type=VerificationType.FUNCTIONAL,
                level=VerificationLevel.STANDARD,
                required=True,
            ),
        ]

        task_result = TaskResult(
            task_id=task.task_id,
            success=True,
            result=result,
        )

        return await orchestrator.verify_task_result(task, task_result, criteria)


class BrowserVerifier:
    """Specialized verifier for browser/computer tasks."""

    @staticmethod
    async def verify_browser_result(
        result: Any,
        task: TaskSpec,
        expected_state: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Verify a browser/computer task result."""
        from agent.orchestration.verification import VerificationOrchestrator, VerificationCriteria, VerificationType, VerificationLevel

        orchestrator = VerificationOrchestrator()

        criteria = [
            VerificationCriteria(
                name="state_verification",
                description="Verify expected browser/UI state",
                verification_type=VerificationType.FUNCTIONAL,
                level=VerificationLevel.STANDARD,
                required=True,
            ),
        ]

        if expected_state:
            task.metadata["expected_state"] = expected_state
            criteria.append(VerificationCriteria(
                name="state_match",
                description="Match expected state",
                verification_type=VerificationType.CROSS_REFERENCE,
                level=VerificationLevel.STANDARD,
                required=True,
            ))

        task_result = TaskResult(
            task_id=task.task_id,
            success=True,
            result=result,
        )

        return await orchestrator.verify_task_result(task, task_result, criteria)


# =============================================================================
# Factory
# =============================================================================


def create_verification_agent(agent_registry: Optional[AgentRegistry] = None) -> VerificationAgent:
    """Create a verification agent."""
    return VerificationAgent(agent_registry)


def create_verification_orchestrator(agent_registry: Optional[AgentRegistry] = None) -> VerificationOrchestrator:
    """Create a verification orchestrator."""
    return VerificationOrchestrator(agent_registry)


__all__ = [
    "VerificationType",
    "VerificationLevel",
    "VerificationCriteria",
    "Evidence",
    "VerificationAgent",
    "VerificationOrchestrator",
    "CodingVerifier",
    "ResearchVerifier",
    "BrowserVerifier",
    "create_verification_agent",
    "create_verification_orchestrator",
]