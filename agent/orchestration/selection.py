"""Agent, Model, Skill, and Tool Selection for AetherOS Orchestration Layer.

Implements Phases 14-17 of Master Prompt 11: selecting the right agent, model,
skills, and tools for each subtask based on capabilities, performance,
cost, and constraints.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.agent_interface import AgentInterface, AgentCapabilities
from agent.orchestration.agent_registry import AgentRegistry, AgentRegistration
from agent.orchestration.router import CapabilityRouter, RoutingContext
from agent.orchestration.types import (
    TaskSpec,
    TaskBudget,
    TaskPriority,
    AgentRole,
    AgentCapabilities,
)
from agent.orchestration.decomposition import CapabilityInference

logger = logging.getLogger(__name__)


# =============================================================================
# Selection Types
# =============================================================================


class SelectionStrategy(Enum):
    """Strategies for selecting agents/models/skills/tools."""
    BEST_MATCH = "best_match"
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    LOCAL_PREFERRED = "local_preferred"
    BALANCED = "balanced"


@dataclass
class SelectionCriteria:
    """Criteria for making selection decisions."""
    task: "TaskSpec"
    strategy: SelectionStrategy = SelectionStrategy.BALANCED
    required_capabilities: List[str] = field(default_factory=list)
    preferred_agent_role: Optional[str] = None
    preferred_model: str = ""
    preferred_tools: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    max_cost_usd: Optional[float] = None
    max_latency_seconds: Optional[float] = None
    prefer_local: bool = True
    max_parallel: int = 3
    min_confidence: float = 0.5


@dataclass
class SelectionResult:
    """Result of a selection decision."""
    agent_id: str
    agent_role: str
    model: str
    confidence: float
    reasoning: str
    estimated_cost: float
    estimated_latency: float
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    matched_capabilities: List[str] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)


# =============================================================================
# Agent Selector
# =============================================================================


class AgentSelector:
    """Selects the best agent for a task based on capabilities and constraints."""

    def __init__(
        self,
        agent_registry: "AgentRegistry",
        capability_router: "CapabilityRouter",
        default_strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ):
        self._registry = agent_registry
        self._router = capability_router
        self._default_strategy = default_strategy

    async def select(
        self,
        criteria: SelectionCriteria,
    ) -> SelectionResult:
        """Select the best agent for a task."""
        # Use the capability router for initial routing
        routing_ctx = RoutingContext(
            task=criteria.task,
            strategy=criteria.strategy.value,
            preferred_role=criteria.preferred_agent_role,
            preferred_model=criteria.preferred_model,
            preferred_tools=criteria.preferred_tools,
            max_cost_usd=criteria.max_cost_usd,
            max_latency_seconds=criteria.max_latency_seconds,
            require_local=criteria.prefer_local,
        )

        decision = await self._router.route(criteria.task, routing_ctx)

        if not decision.agent_id:
            return SelectionResult(
                agent_id="",
                agent_role="",
                model="",
                confidence=0.0,
                reasoning="No suitable agent found",
                estimated_cost=0.0,
                estimated_latency=0.0,
                missing_capabilities=criteria.required_capabilities,
            )

        # Get the agent instance
        from agent.orchestration.agent_registry import get_agent_registry
        registry = get_agent_registry()
        instance = await registry.create_instance(decision.registration_id)

        return SelectionResult(
            agent_id=instance.identity.agent_id,
            agent_role=decision.role,
            model=decision.agent_id,  # Would be filled with actual model
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            estimated_cost=decision.estimated_cost,
            estimated_latency=decision.estimated_latency,
            matched_capabilities=decision.matched_capabilities,
            missing_capabilities=decision.missing_capabilities,
        )


# =============================================================================
# Model Selector
# =============================================================================


class ModelSelector:
    """Selects the best model for a task based on requirements and constraints."""

    def __init__(
        self,
        model_router: Optional[Any] = None,
        default_strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ):
        self._model_router = model_router
        self._default_strategy = default_strategy

    async def select(
        self,
        task: "TaskSpec",
        available_models: List[str],
        criteria: SelectionCriteria,
    ) -> str:
        """Select the best model for a task."""
        if not available_models:
            return ""

        # If preferred model specified and available, use it
        if criteria.preferred_model and criteria.preferred_model in available_models:
            return criteria.preferred_model

        # Score models based on strategy
        scored = []
        for model in available_models:
            score = self._score_model(model, criteria)
            if score >= criteria.min_confidence:
                scored.append((score, model))

        if not scored:
            return available_models[0]  # Fallback

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _score_model(self, model: str, criteria: SelectionCriteria) -> float:
        """Score a model based on selection criteria."""
        score = 0.5  # Base score
        model_lower = model.lower()

        # Capability matching
        for cap in criteria.required_capabilities:
            if self._model_has_capability(model, cap):
                score += 0.2

        # Strategy-specific scoring
        if criteria.strategy == SelectionStrategy.COST_OPTIMIZED:
            if "haiku" in model_lower or "mini" in model_lower or "small" in model_lower:
                score += 0.3
            elif "opus" in model_lower or "gpt-4" in model_lower:
                score -= 0.2
        elif criteria.strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            if "haiku" in model_lower or "mini" in model_lower or "flash" in model_lower:
                score += 0.3
            elif "opus" in model_lower or "gpt-4" in model_lower:
                score -= 0.2
        elif criteria.strategy == SelectionStrategy.QUALITY_OPTIMIZED:
            if "opus" in model_lower or "gpt-4" in model_lower:
                score += 0.3
            elif "haiku" in model_lower or "mini" in model_lower:
                score -= 0.1
        elif criteria.strategy == SelectionStrategy.LOCAL_PREFERRED:
            if "local" in model_lower or "ollama" in model_lower:
                score += 0.4

        # Prefer local if specified
        if criteria.prefer_local and ("local" in model_lower or "ollama" in model_lower):
            score += 0.2

        return min(1.0, max(0.0, score))

    def _model_has_capability(self, model: str, capability: str) -> bool:
        """Check if a model supports a capability (simplified)."""
        model_lower = model.lower()
        capability_lower = capability.lower()

        capability_map = {
            "vision": ["vision", "image", "gpt-4", "gemini", "claude-3", "gpt-4o"],
            "code_execution": ["code", "coding", "gpt-4", "claude", "gpt-4o"],
            "web_search": ["search", "web", "gpt-4", "claude", "gemini"],
            "audio": ["audio", "whisper", "tts"],
            "video": ["video", "gemini"],
            "tool_use": ["tool", "function", "gpt-4", "claude", "gemini"],
            "reasoning": ["reasoning", "o1", "opus"],
        }

        if capability_lower in capability_map:
            for keyword in capability_map[capability_lower]:
                if keyword in model_lower:
                    return True
        return False


# =============================================================================
# Skill Selector
# =============================================================================


class SkillSelector:
    """Selects appropriate skills for a task based on requirements."""

    def __init__(self, skills_dir: str = "skills"):
        self._skills_dir = skills_dir
        self._skill_index: Dict[str, Dict[str, Any]] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Load available skills from disk."""
        import os
        import json

        skills_root = os.path.expanduser(f"~/.aetheros/{self._skills_dir}")
        if not os.path.exists(skills_root):
            return

        for category in os.listdir(skills_root):
            cat_path = os.path.join(skills_root, category)
            if not os.path.isdir(cat_path):
                continue
            for skill_name in os.listdir(cat_path):
                skill_path = os.path.join(cat_path, skill_name)
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    try:
                        with open(skill_md, "r") as f:
                            content = f.read()
                        # Parse frontmatter
                        meta = self._parse_skill_metadata(content)
                        meta["category"] = category
                        meta["path"] = skill_path
                        self._skill_index[skill_name] = meta
                    except Exception as e:
                        logger.debug(f"Failed to load skill {skill_name}: {e}")

    def _parse_skill_metadata(self, content: str) -> Dict[str, Any]:
        """Parse SKILL.md frontmatter."""
        import re
        meta = {}
        # Simple frontmatter parsing
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
        return meta

    def select_skills(
        self,
        task: "TaskSpec",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Select skills relevant to a task."""
        if not self._skill_index:
            return []

        # Infer required capabilities from task
        required_caps = set(task.required_capabilities)
        if not required_caps:
            # Infer from goal/description
            from agent.orchestration.decomposition import CapabilityInference
            required_caps = CapabilityInference.infer_capabilities(
                task.goal + " " + task.description
            )

        # Score skills
        scored = []
        for skill_name, meta in self._skill_index.items():
            score = 0
            skill_caps = set(meta.get("metadata.aetheros.tags", []))
            skill_caps.update(meta.get("metadata.aetheros.capabilities", []))

            # Capability overlap
            overlap = len(required_caps & skill_caps)
            score += overlap * 10

            # Category relevance
            if context and meta.get("category") in context.get("preferred_categories", []):
                score += 5

            # Skill quality/maturity (placeholder)
            score += meta.get("quality_score", 0)

            if score > 0:
                scored.append((score, skill_name))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top skills
        max_skills = 5
        return [skill for _, skill in scored[:max_skills]]


# =============================================================================
# Tool Selector
# =============================================================================


class ToolSelector:
    """Selects tools for a task based on requirements and availability."""

    def __init__(self, tool_registry: "ToolRegistry"):
        self._registry = tool_registry

    def select_tools(
        self,
        task: "TaskSpec",
        available_tools: List[str],
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ) -> List[str]:
        """Select the best tools for a task."""
        # If preferred tools specified and available, use them
        if task.preferred_tools:
            return [t for t in task.preferred_tools if t in available_tools]

        # Score available tools
        scored = []
        for tool in available_tools:
            score = self._score_tool(tool, task, strategy)
            scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top tools (respect max parallel)
        max_tools = 5
        return [tool for _, tool in scored[:max_tools]]

    def _score_tool(self, tool: str, task: "TaskSpec", strategy: SelectionStrategy) -> float:
        """Score a tool for a task."""
        score = 0.0
        tool_lower = tool.lower()
        goal_lower = task.goal.lower()

        # Capability matching
        tool_caps = self._get_tool_capabilities(tool)
        for cap in task.required_capabilities:
            if cap in tool_caps:
                score += 0.3

        # Keyword matching in goal
        for keyword in task.goal.lower().split():
            if keyword in tool_lower:
                score += 0.1

        # Strategy adjustments
        if strategy == SelectionStrategy.COST_OPTIMIZED:
            if "local" in tool_lower:
                score += 0.2
        elif strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            if "local" in tool_lower:
                score += 0.1

        return score

    def _get_tool_capabilities(self, tool: str) -> Set[str]:
        """Get capabilities provided by a tool."""
        # Simplified mapping
        cap_map = {
            "web_search": {"web_search", "research", "search"},
            "web_extract": {"web_extract", "extraction", "scraping"},
            "browser_navigate": {"browser", "navigation"},
            "vision_analyze": {"vision", "image_understanding"},
            "screen_capture": {"screen", "screen_capture"},
            "screen_understand": {"screen", "ui_understanding"},
            "terminal": {"terminal", "shell", "command"},
            "file_read": {"file_read", "filesystem"},
            "file_write": {"file_write", "filesystem"},
            "patch": {"patch", "code_modification"},
            "search_files": {"search", "filesystem"},
            "transcribe_audio": {"transcription", "speech_to_text"},
            "text_to_speech": {"tts", "speech_synthesis"},
            "image_generate": {"image_generation", "creative"},
            "video_generate": {"video_generation", "creative"},
        }
        return cap_map.get(tool, set())


# =============================================================================
# Unified Selector
# =============================================================================


class UnifiedSelector:
    """Unified interface for all selection decisions."""

    def __init__(
        self,
        agent_registry: "AgentRegistry",
        capability_router: "CapabilityRouter",
        model_router: Optional[Any] = None,
        tool_registry: Optional["ToolRegistry"] = None,
    ):
        self.agent_selector = AgentSelector(agent_registry, CapabilityRouter(agent_registry))
        self.model_selector = ModelSelector()
        self.skill_selector = SkillSelector()
        self.tool_selector = ToolSelector(None) if tool_registry else None

    async def select_all(
        self,
        task: "TaskSpec",
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ) -> SelectionResult:
        """Make all selection decisions for a task."""
        criteria = SelectionCriteria(
            task=task,
            strategy=task.strategy if hasattr(task, "strategy") else SelectionStrategy.BALANCED,
            required_capabilities=task.required_capabilities,
            preferred_agent_role=task.preferred_agent_role,
            preferred_model=task.preferred_model,
            preferred_tools=task.preferred_tools,
            preferred_skills=task.preferred_skills,
            max_cost_usd=task.budget.max_cost_usd,
            max_latency_seconds=task.budget.max_time_seconds,
        )

        # Select agent
        agent_result = await self.agent_selector.select(criteria)

        # Select model
        available_models = []  # Would come from model router
        model = await self.model_selector.select(task, available_models, criteria)

        # Select skills
        skills = self.skill_selector.select_skills(task)

        # Select tools
        tools = []
        if self.tool_selector:
            available_tools = []  # Would come from tool registry
            tools = self.tool_selector.select_tools(task, available_tools)

        return SelectionResult(
            agent_id=agent_result.agent_id,
            agent_role=agent_result.agent_role,
            model=model,
            skills=skills,
            tools=tools,
            confidence=agent_result.confidence,
            reasoning=agent_result.reasoning,
            estimated_cost=agent_result.estimated_cost,
            estimated_latency=agent_result.estimated_latency,
            matched_capabilities=agent_result.matched_capabilities,
            missing_capabilities=agent_result.missing_capabilities,
        )


# =============================================================================
# Factory
# =============================================================================


async def create_unified_selector(
    agent_registry: "AgentRegistry",
    capability_router: "CapabilityRouter",
    model_router: Optional[Any] = None,
    tool_registry: Optional["ToolRegistry"] = None,
) -> UnifiedSelector:
    """Create a unified selector with all components."""
    return UnifiedSelector(
        agent_registry=agent_registry,
        capability_router=capability_router,
        model_router=model_router,
        tool_registry=tool_registry,
    )


__all__ = [
    "SelectionStrategy",
    "SelectionCriteria",
    "SelectionResult",
    "AgentSelector",
    "ModelSelector",
    "SkillSelector",
    "ToolSelector",
    "UnifiedSelector",
    "create_unified_selector",
]