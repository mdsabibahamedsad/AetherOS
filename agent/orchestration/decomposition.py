from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.types import (
    TaskSpec,
    TaskBudget,
    TaskPriority,
    AgentRole,
    TaskStatus,
)
from agent.orchestration.agent_interface import AgentInterface, AgentCapabilities
from agent.orchestration.agent_registry import AgentRegistry
from agent.orchestration.router import CapabilityRouter
from agent.orchestration.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Decomposition Types
# =============================================================================


class DecompositionStrategy(Enum):
    """Strategies for decomposing tasks."""
    LLM_BASED = "llm_based"          # Use LLM to decompose
    RULE_BASED = "rule_based"        # Use keyword rules
    TEMPLATE_BASED = "template_based" # Use predefined templates
    HYBRID = "hybrid"                # Combine multiple strategies


class SubtaskType(Enum):
    """Types of subtasks in decomposition."""
    SEQUENTIAL = "sequential"        # Must run in order
    PARALLEL = "parallel"            # Can run in parallel
    CONDITIONAL = "conditional"      # Runs based on condition
    LOOP = "loop"                    # Repeats until condition
    BRANCH = "branch"                # Multiple alternative paths


@dataclass
class DecompositionConfig:
    """Configuration for task decomposition."""
    strategy: DecompositionStrategy = DecompositionStrategy.HYBRID
    max_subtasks: int = 20
    max_depth: int = 5
    min_subtask_size: int = 1  # Minimum description length
    include_verification: bool = True
    infer_dependencies: bool = True
    infer_capabilities: bool = True
    include_approval_gates: bool = True
    require_explicit_success_criteria: bool = True


@dataclass
class SubtaskSpec:
    """Specification for a decomposed subtask."""
    goal: str
    description: str = ""
    subtask_type: SubtaskType = SubtaskType.SEQUENTIAL
    required_capabilities: List[str] = field(default_factory=list)
    preferred_agent_role: Optional[str] = None
    priority: int = 50  # 0-100
    estimated_duration: float = 60.0  # seconds
    success_criteria: List[str] = field(default_factory=list)
    verification_criteria: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)  # Other subtask IDs
    condition: str = ""  # For conditional subtasks
    loop_condition: str = ""  # For loop subtasks
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecompositionResult:
    """Result of task decomposition."""
    subtasks: List[SubtaskSpec] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> [dep_ids]
    execution_order: List[str] = field(default_factory=list)  # Topological order
    total_estimated_time: float = 0.0
    total_estimated_cost: float = 0.0
    required_roles: Set[str] = field(default_factory=set)
    required_capabilities: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Capability Inference
# =============================================================================


class CapabilityInference:
    """Infers required capabilities from task descriptions."""

    # Keyword -> capability mappings
    CAPABILITY_KEYWORDS = {
        "research": ["web_search", "research", "information_gathering"],
        "search": ["web_search", "search"],
        "browse": ["browser_navigate", "browser"],
        "navigate": ["browser_navigate", "browser"],
        "scrape": ["web_scrape", "web_extract"],
        "extract": ["web_extract", "data_extraction"],
        "download": ["download", "file_download"],
        "code": ["code_execution", "coding", "programming"],
        "develop": ["code_execution", "development"],
        "program": ["code_execution", "programming"],
        "implement": ["code_execution", "implementation"],
        "refactor": ["code_execution", "refactoring"],
        "debug": ["code_execution", "debugging"],
        "test": ["code_execution", "testing"],
        "write": ["writing", "content_creation"],
        "document": ["documentation", "writing"],
        "draft": ["writing", "drafting"],
        "compose": ["writing", "composition"],
        "summarize": ["summarization", "text_processing"],
        "analyze": ["analysis", "data_analysis"],
        "analyze": ["analysis", "data_analysis"],
        "chart": ["chart_generation", "visualization"],
        "visualize": ["visualization", "chart_generation"],
        "plot": ["plotting", "visualization"],
        "chart": ["chart_understanding", "visualization"],
        "diagram": ["diagram_understanding", "visualization"],
        "image": ["vision", "image_understanding"],
        "screenshot": ["screen_capture", "vision"],
        "screen": ["screen_understanding", "vision"],
        "camera": ["camera", "vision"],
        "photo": ["vision", "image_understanding"],
        "video": ["video_understanding", "video"],
        "transcribe": ["transcription", "speech_to_text"],
        "speech": ["speech_to_text", "transcription"],
        "audio": ["audio_processing", "transcription"],
        "translate": ["translation", "language"],
        "speak": ["text_to_speech", "tts"],
        "synthesize": ["text_to_speech", "tts"],
        "voice": ["voice", "tts"],
        "ocr": ["ocr", "text_extraction"],
        "pdf": ["pdf_processing", "document_processing"],
        "document": ["document_processing", "document_understanding"],
        "pdf": ["pdf_processing", "document_processing"],
        "spreadsheet": ["spreadsheet", "data_processing"],
        "excel": ["spreadsheet", "data_processing"],
        "csv": ["csv_processing", "data_processing"],
        "data": ["data_analysis", "data_processing"],
        "calculate": ["calculation", "math"],
        "compute": ["computation", "math"],
        "math": ["mathematics", "computation"],
        "statistics": ["statistics", "data_analysis"],
        "stat": ["statistics", "data_analysis"],
        "email": ["email", "communication"],
        "message": ["messaging", "communication"],
        "send": ["send_message", "communication"],
        "notify": ["notification", "communication"],
        "schedule": ["scheduling", "calendar"],
        "calendar": ["calendar", "scheduling"],
        "meeting": ["meeting", "calendar"],
        "file": ["file_operations", "filesystem"],
        "read": ["file_read", "filesystem"],
        "write": ["file_write", "filesystem"],
        "save": ["file_write", "filesystem"],
        "copy": ["file_copy", "filesystem"],
        "move": ["file_move", "filesystem"],
        "delete": ["file_delete", "filesystem"],
        "rename": ["file_rename", "filesystem"],
        "folder": ["directory_operations", "filesystem"],
        "directory": ["directory_operations", "filesystem"],
        "archive": ["archive", "compression"],
        "compress": ["compression", "archive"],
        "zip": ["compression", "archive"],
        "unzip": ["decompression", "archive"],
        "git": ["git", "version_control"],
        "commit": ["git", "version_control"],
        "push": ["git", "version_control"],
        "pull": ["git", "version_control"],
        "merge": ["git", "version_control"],
        "branch": ["git", "version_control"],
        "deploy": ["deployment", "deployment"],
        "release": ["release", "deployment"],
        "build": ["build", "compilation"],
        "compile": ["compilation", "build"],
        "package": ["packaging", "build"],
        "test": ["testing", "code_execution"],
        "verify": ["verification", "validation"],
        "validate": ["validation", "verification"],
        "check": ["validation", "verification"],
        "audit": ["auditing", "security"],
        "security": ["security", "auditing"],
        "permission": ["permissions", "security"],
        "encrypt": ["encryption", "security"],
        "decrypt": ["decryption", "security"],
        "backup": ["backup", "data_protection"],
        "restore": ["restore", "data_protection"],
        "monitor": ["monitoring", "observability"],
        "log": ["logging", "observability"],
        "alert": ["alerting", "observability"],
        "metric": ["metrics", "observability"],
        "dashboard": ["dashboard", "visualization"],
    }

    @classmethod
    def infer_capabilities(cls, text: str) -> Set[str]:
        """Infer capabilities from text using keyword matching."""
        capabilities = set()
        text_lower = text.lower()

        for keyword, caps in cls.CAPABILITY_KEYWORDS.items():
            if keyword in text_lower:
                capabilities.update(caps)

        return capabilities

    @classmethod
    def infer_roles(cls, text: str) -> Set[str]:
        """Infer agent roles from text."""
        roles = set()
        text_lower = text.lower()

        role_keywords = {
            "research": "research",
            "search": "research",
            "investigate": "research",
            "code": "developer",
            "develop": "developer",
            "program": "developer",
            "implement": "developer",
            "debug": "developer",
            "write": "writer",
            "document": "writer",
            "draft": "writer",
            "compose": "writer",
            "browse": "browser",
            "navigate": "browser",
            "scrape": "browser",
            "analyze": "data",
            "analyze": "data",
            "chart": "data",
            "visualize": "data",
            "image": "vision",
            "image": "vision",
            "video": "video",
            "transcribe": "audio",
            "speech": "audio",
            "translate": "translation",
            "speak": "tts",
            "synthesize": "tts",
            "ocr": "document",
            "pdf": "document",
            "document": "document",
            "email": "communication",
            "message": "communication",
            "send": "communication",
            "deploy": "deployment",
            "deploy": "deployment",
            "test": "qa",
            "verify": "qa",
            "validate": "qa",
            "audit": "security",
            "security": "security",
            "deploy": "deployment",
            "plan": "planner",
            "organize": "planner",
            "coordinate": "coordinator",
            "design": "creative",
            "create": "creative",
            "generate": "creative",
            "imagine": "creative",
            "data": "data",
            "analyze": "data",
            "statistics": "data",
            "email": "communication",
            "message": "communication",
            "file": "file",
            "folder": "file",
            "directory": "file",
        }

        for keyword, role in role_keywords.items():
            if keyword in text_lower:
                roles.add(role)

        return roles


# =============================================================================
# Rule-Based Decomposer
# =============================================================================


class RuleBasedDecomposer:
    """Decomposes tasks using rule-based patterns."""

    # Common task patterns and their decompositions
    TASK_PATTERNS = [
        {
            "keywords": ["research and write", "research and compose", "investigate and document"],
            "decomposition": [
                {"goal": "Research {topic}", "capabilities": ["research", "web_search"]},
                {"goal": "Synthesize findings", "capabilities": ["analysis", "summarization"]},
                {"goal": "Write report", "capabilities": ["writing", "documentation"]},
            ],
        },
        {
            "keywords": ["build and test", "develop and test", "implement and verify"],
            "decomposition": [
                {"goal": "Design implementation", "capabilities": ["planning", "architecture"]},
                {"goal": "Implement code", "capabilities": ["code_execution", "coding"]},
                {"goal": "Write tests", "capabilities": ["testing", "code_execution"]},
                {"goal": "Run tests and verify", "capabilities": ["testing", "verification"]},
            ],
        },
        {
            "keywords": ["research and analyze", "investigate and analyze", "study and analyze"],
            "decomposition": [
                {"goal": "Gather sources", "capabilities": ["research", "web_search"]},
                {"goal": "Analyze data", "capabilities": ["data_analysis", "analysis"]},
                {"goal": "Create visualizations", "capabilities": ["visualization", "chart_generation"]},
                {"goal": "Write analysis report", "capabilities": ["writing", "documentation"]},
            ],
        },
        {
            "keywords": ["design and build", "design and implement", "architect and build"],
            "decomposition": [
                {"goal": "Design architecture", "capabilities": ["architecture", "planning"]},
                {"goal": "Implement components", "capabilities": ["code_execution", "development"]},
                {"goal": "Integrate and test", "capabilities": ["testing", "integration"]},
                {"goal": "Document and deploy", "capabilities": ["documentation", "deployment"]},
            ],
        },
        {
            "keywords": ["audit and fix", "review and fix", "analyze and fix"],
            "decomposition": [
                {"goal": "Audit current state", "capabilities": ["auditing", "analysis"]},
                {"goal": "Identify issues", "capabilities": ["analysis", "verification"]},
                {"goal": "Implement fixes", "capabilities": ["code_execution", "debugging"]},
                {"goal": "Verify fixes", "capabilities": ["testing", "verification"]},
            ],
        },
        {
            "keywords": ["migrate and validate", "move and verify", "transfer and validate"],
            "decomposition": [
                {"goal": "Plan migration", "capabilities": ["planning", "architecture"]},
                {"goal": "Execute migration", "capabilities": ["data_processing", "migration"]},
                {"goal": "Validate results", "capabilities": ["verification", "validation"]},
                {"goal": "Rollback plan", "capabilities": ["contingency_planning", "recovery"]},
            ],
        },
    ]

    @classmethod
    def match_pattern(cls, goal: str) -> Optional[List[Dict[str, Any]]]:
        """Match goal against known patterns."""
        goal_lower = goal.lower()
        for pattern in cls.TASK_PATTERNS:
            for keyword in pattern["keywords"]:
                if keyword in goal_lower:
                    return pattern["decomposition"]
        return None

    @classmethod
    def decompose(cls, goal: str, description: str = "") -> List[SubtaskSpec]:
        """Decompose using rule-based patterns."""
        pattern = cls.match_pattern(goal)
        if not pattern:
            return []

        subtasks = []
        for i, step in enumerate(pattern):
            subtask = SubtaskSpec(
                goal=step["goal"],
                description=f"Step {i+1}: {step['goal']}",
                subtask_type=SubtaskType.SEQUENTIAL,
                required_capabilities=step.get("capabilities", []),
                priority=50,
                estimated_duration=60.0,
                success_criteria=[f"Complete: {step['goal']}"],
            )
            subtasks.append(subtask)
        return subtasks


# =============================================================================
# LLM-Based Decomposer (Placeholder for LLM Integration)
# =============================================================================


class LLMDecomposer:
    """Decomposes tasks using LLM reasoning (placeholder for LLM integration)."""

    @classmethod
    async def decompose(
        cls,
        goal: str,
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
        config: Optional[DecompositionConfig] = None,
    ) -> List[SubtaskSpec]:
        """Decompose using LLM reasoning.

        This is a placeholder for actual LLM integration.
        In production, this would call an LLM with a structured prompt.
        """
        # For now, fall back to rule-based
        return RuleBasedDecomposer.decompose(goal, description)

    @classmethod
    def build_decomposition_prompt(
        cls,
        goal: str,
        description: str = "",
        config: Optional[DecompositionConfig] = None,
    ) -> str:
        """Build a prompt for LLM-based decomposition."""
        prompt = f"""Decompose the following goal into subtasks:

Goal: {goal}
Description: {description}

Requirements:
- Break into {config.max_subtasks if config else 10} or fewer subtasks
- Each subtask must have clear goal, capabilities, and success criteria
- Include verification criteria for each subtask
- Identify dependencies between subtasks
- Specify preferred agent role for each subtask
- Estimate duration for each subtask

Output format (JSON):
{{
  "subtasks": [
    {{
      "goal": "string",
      "description": "string",
      "subtask_type": "sequential|parallel|conditional|loop|branch",
      "required_capabilities": ["cap1", "cap2"],
      "preferred_agent_role": "role",
      "priority": 50,
      "estimated_duration": 60,
      "success_criteria": ["criteria1", "criteria2"],
      "verification_criteria": ["verify1", "verify2"],
      "depends_on": ["subtask_id"],
      "condition": "",
      "loop_condition": "",
    }}
  ]
}}

Return ONLY the JSON."""
        return prompt


# =============================================================================
# Hybrid Decomposer (Main Entry Point)
# =============================================================================


class HybridDecomposer:
    """Main decomposer combining multiple strategies."""

    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        capability_router: Optional["CapabilityRouter"] = None,
    ):
        self.registry = agent_registry or AgentRegistry()
        self.router = capability_router
        self.config = DecompositionConfig()

    def set_config(self, config: DecompositionConfig) -> None:
        self.config = config

    async def decompose(
        self,
        goal: str,
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> DecompositionResult:
        """Decompose a goal into subtasks using hybrid strategy."""
        # Try rule-based first
        rule_subtasks = RuleBasedDecomposer.decompose(goal, description)

        # If rule-based found a pattern, use it
        if rule_subtasks:
            return self._finalize_decomposition(rule_subtasks, goal)

        # Try LLM-based (placeholder)
        llm_subtasks = await LLMDecomposer.decompose(goal, description)

        if llm_subtasks:
            return self._finalize_decomposition(llm_subtasks, goal)

        # Fallback: generic single task
        return self._create_fallback_decomposition(goal)

    def _finalize_decomposition(
        self,
        subtasks: List[SubtaskSpec],
        goal: str,
    ) -> DecompositionResult:
        """Finalize decomposition with IDs, dependencies, and estimates."""
        result = DecompositionResult()
        subtask_ids = []

        # Assign IDs and build subtasks
        for i, subtask in enumerate(subtasks):
            subtask_id = f"subtask-{uuid.uuid4().hex[:8]}"
            # Add ID to subtask metadata
            subtask.metadata["subtask_id"] = subtask_id
            subtask.metadata["index"] = i
            subtasks[i] = subtask
            subtask_ids.append(subtask_id)

        # Infer dependencies (sequential by default)
        dependencies = {}
        for i, subtask_id in enumerate(subtask_ids):
            deps = []
            if i > 0:
                deps.append(subtask_ids[i - 1])  # Sequential by default
            dependencies[subtask_id] = deps

        # Compute execution order (topological)
        execution_order = self._topological_sort(subtask_ids, dependencies)

        # Aggregate capabilities and roles
        all_capabilities = set()
        all_roles = set()
        total_time = 0.0
        total_cost = 0.0

        for subtask in subtasks:
            all_capabilities.update(subtask.required_capabilities)
            if subtask.preferred_agent_role:
                all_roles.add(subtask.preferred_agent_role)
            total_time += subtask.estimated_duration
            total_cost += subtask.estimated_duration * 0.001  # Rough cost estimate

        return DecompositionResult(
            subtasks=subtasks,
            dependencies=dependencies,
            execution_order=execution_order,
            total_estimated_time=total_time,
            total_estimated_cost=total_cost,
            required_roles=all_roles,
            required_capabilities=all_capabilities,
            warnings=[],
        )

    def _topological_sort(
        self,
        task_ids: List[str],
        dependencies: Dict[str, List[str]],
    ) -> List[str]:
        """Kahn's algorithm for topological sorting."""
        in_degree = {tid: 0 for tid in task_ids}
        for tid, deps in dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[tid] += 1

        queue = [tid for tid in task_ids if in_degree[tid] == 0]
        order = []

        while queue:
            tid = queue.pop(0)
            order.append(tid)
            # Find tasks that depend on this one
            for tid, deps in dependencies.items():
                if tid in order:  # Already processed
                    continue
                # This is simplified; real implementation would track reverse deps
                pass

        # For now, return original order
        return task_ids

    def _create_fallback_decomposition(self, goal: str) -> DecompositionResult:
        """Create a simple single-task decomposition as fallback."""
        subtask = SubtaskSpec(
            goal=goal,
            description=goal,
            subtask_type=SubtaskType.SEQUENTIAL,
            required_capabilities=CapabilityInference.infer_capabilities(goal),
            preferred_agent_role=self._infer_primary_role(goal),
            priority=50,
            estimated_duration=300.0,
            success_criteria=[f"Complete: {goal}"],
            verification_criteria=[f"Verify completion of: {goal}"],
        )

        result = DecompositionResult()
        result.subtasks = [subtask]
        result.dependencies = {subtask.metadata.get("subtask_id", "subtask-0"): []}
        result.execution_order = [subtask.metadata.get("subtask_id", "subtask-0")]
        result.total_estimated_time = 300.0
        result.total_estimated_cost = 0.30
        result.required_roles = {subtask.preferred_agent_role} if subtask.preferred_agent_role else set()
        result.required_capabilities = subtask.required_capabilities
        result.warnings = ["Fallback decomposition used - no pattern matched"]
        return result

    def _infer_primary_role(self, goal: str) -> str:
        roles = CapabilityInference.infer_roles(goal)
        if roles:
            return next(iter(roles))
        return "coordinator"


# =============================================================================
# Recursive Decomposer
# =============================================================================


class RecursiveDecomposer:
    """Decomposes tasks recursively up to a maximum depth."""

    def __init__(
        self,
        decomposer: HybridDecomposer,
        max_depth: int = 5,
    ):
        self.decomposer = decomposer
        self.max_depth = max_depth

    async def decompose_recursive(
        self,
        goal: str,
        description: str = "",
        depth: int = 0,
        parent_id: str = "",
    ) -> Tuple[List[SubtaskSpec], Dict[str, List[str]]]:
        """Recursively decompose until max depth or atomic tasks."""
        if depth >= self.max_depth:
            # Create leaf task
            subtask = SubtaskSpec(
                goal=goal,
                description=description,
                subtask_type=SubtaskType.SEQUENTIAL,
                metadata={"depth": depth, "parent_id": parent_id},
            )
            return [subtask], {}

        # Try to decompose
        result = await self.decomposer.decompose(goal, description)
        if not result.subtasks or len(result.subtasks) <= 1:
            # Can't decompose further
            return result.subtasks, result.dependencies

        # Recursively decompose each subtask
        all_subtasks = []
        all_dependencies = {}

        for subtask in result.subtasks:
            sub_subtasks, sub_deps = await self.decompose_recursive(
                subtask.goal,
                subtask.description,
                depth + 1,
                subtask.metadata.get("subtask_id", ""),
            )
            all_subtasks.extend(sub_subtasks)
            all_dependencies.update(sub_deps)

        return all_subtasks, all_dependencies


# =============================================================================
# Convenience Functions
# =============================================================================


def decompose_task(
    goal: str,
    description: str = "",
    config: Optional[DecompositionConfig] = None,
) -> DecompositionResult:
    """Convenience function to decompose a task."""
    decomposer = HybridDecomposer()
    if config:
        decomposer.set_config(config)
    # For sync usage, run the async method
    import asyncio
    return asyncio.run(decomposer.decompose(goal, description))


def create_subtask(
    goal: str,
    capabilities: Optional[List[str]] = None,
    role: Optional[str] = None,
    priority: int = 50,
    duration: float = 60.0,
    depends_on: Optional[List[str]] = None,
) -> SubtaskSpec:
    """Create a subtask specification."""
    return SubtaskSpec(
        goal=goal,
        required_capabilities=capabilities or [],
        preferred_agent_role=role,
        priority=priority,
        estimated_duration=duration,
        depends_on=depends_on or [],
    )


# Export key symbols
__all__ = [
    # Enums
    "DecompositionStrategy",
    "SubtaskType",
    # Config
    "DecompositionConfig",
    # Specs
    "SubtaskSpec",
    "DecompositionResult",
    # Inference
    "CapabilityInference",
    # Decomposers
    "RuleBasedDecomposer",
    "LLMDecomposer",
    "HybridDecomposer",
    "RecursiveDecomposer",
    # Convenience
    "decompose_task",
    "create_subtask",
]