"""Capability-Based Router for AetherOS Orchestration Layer.

Implements Phase 3 of Master Prompt 11: route tasks by capabilities
rather than agent names. Integrates with MASTER 6 model routing
and MASTER 8 capability registry.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from agent.orchestration.agent_interface import (
    AgentCapabilities,
    AgentInterface,
)
from agent.orchestration.agent_registry import AgentRegistry
from agent.orchestration.types import (
    AgentRole,
    TaskPriority,
    TaskSpec,
    TaskBudget,
    AgentCapabilities,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Routing Strategy
# =============================================================================


class RoutingStrategy(Enum):
    """Strategies for selecting agents."""

    BEST_MATCH = "best_match"  # Highest priority matching capabilities
    LEAST_LOADED = "least_loaded"  # Agent with fewest active tasks
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    PREFERRED_ROLE = "preferred_role"  # Strict role preference
    COST_OPTIMIZED = "cost_optimized"  # Minimize estimated cost
    LATENCY_OPTIMIZED = "latency_optimized"  # Minimize estimated latency
    LOCAL_PREFERRED = "local_preferred"  # Prefer local models when possible


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    instance_id: str
    registration_id: str
    agent_id: str
    role: str
    confidence: float  # 0.0 - 1.0
    reasoning: str
    strategy: str
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    estimated_cost: float
    estimated_latency: float


@dataclass
class RoutingContext:
    """Context for routing decisions."""

    task: "TaskSpec"
    strategy: str = "best_match"
    preferred_role: Optional[str] = None
    preferred_model: str = ""
    preferred_tools: List[str] = field(default_factory=list)
    exclude_agents: Set[str] = field(default_factory=set)
    required_capabilities: List[str] = field(default_factory=list)
    preferred_capabilities: List[str] = field(default_factory=list)
    max_cost_usd: Optional[float] = None
    max_latency_seconds: Optional[float] = None
    require_local: bool = False
    prefer_local: bool = True
    min_confidence: float = 0.5


# =============================================================================
# Capability Router
# =============================================================================


class CapabilityRouter:
    """Routes tasks to agents based on capabilities and constraints.

    Integrates with:
    - MASTER 6: Model routing (via model_router)
    - MASTER 7: Security boundaries (via approval system)
    - MASTER 8: Capability registry (via agent registry)
    - MASTER 10: Multimodal capabilities (via multimodal module)
    """

    def __init__(
        self,
        agent_registry: "AgentRegistry",
        model_router: Optional[Any] = None,
    ):
        self._registry = agent_registry
        self._model_router = model_router
        self._routing_history: List[Tuple[float, str, RoutingDecision]] = []
        self._max_history = 1000

    async def route(
        self,
        task: "TaskSpec",
        context: Optional[RoutingContext] = None,
    ) -> RoutingDecision:
        """Route a task to the best available agent.

        Args:
            task: Task specification with requirements
            context: Optional routing context with constraints

        Returns:
            RoutingDecision with selected agent and reasoning
        """
        ctx = context or RoutingContext(task=task)

        # Merge task requirements into context
        ctx.required_capabilities.extend(task.required_capabilities)
        if task.preferred_agent_role:
            ctx.preferred_role = task.preferred_agent_role.value
        if task.preferred_model:
            ctx.preferred_model = task.preferred_model
        if task.preferred_tools:
            ctx.preferred_tools.extend(task.preferred_tools)
        ctx.max_cost_usd = ctx.max_cost_usd or task.budget.max_cost_usd
        ctx.max_latency_seconds = ctx.max_latency_seconds or task.budget.max_time_seconds
        ctx.prefer_local = ctx.prefer_local and task.budget.max_cost_usd < 5.0

        # Find candidates
        candidates = await self._find_candidates(ctx)

        if not candidates:
            return RoutingDecision(
                instance_id="",
                registration_id="",
                agent_id="",
                role="",
                confidence=0.0,
                reasoning="No agents found matching requirements",
                strategy=ctx.strategy,
                matched_capabilities=[],
                missing_capabilities=ctx.required_capabilities,
                estimated_cost=0.0,
                estimated_latency=0.0,
            )

        # Use strategy to select best candidate
        strategy_name = ctx.strategy or self.default_strategy
        strategy = self.strategies.get(strategy_name, self.strategies.get("best_match"))
        
        if strategy:
            decision = await strategy.select(candidates, ctx)
        else:
            # Fallback to best_match
            scored = await self._score_candidates(candidates, ctx)
            if not scored:
                return RoutingDecision(
                    instance_id="",
                    registration_id="",
                    agent_id="",
                    role="",
                    confidence=0.0,
                    reasoning="No candidates met minimum requirements",
                    strategy=ctx.strategy,
                    matched_capabilities=[],
                    missing_capabilities=ctx.required_capabilities,
                    estimated_cost=0.0,
                    estimated_latency=0.0,
                )
            decision = self._select_best(scored, ctx)

        # Record for analytics
        self._record_routing(task.task_id, decision)

        return decision

    async def _find_candidates(self, ctx: RoutingContext) -> List[Tuple["AgentRegistration", "AgentInstance"]]:
        """Find agent registrations and instances matching requirements."""
        candidates = []

        # Get registrations matching required capabilities
        for cap in ctx.required_capabilities:
            regs = self._registry.find_by_capability(cap)
            for reg in regs:
                if not reg.enabled:
                    continue
                # Check role preference
                if ctx.preferred_role and reg.identity.role.value != ctx.preferred_role:
                    continue
                # Check excluded agents
                if reg.identity.agent_id in ctx.exclude_agents:
                    continue

                # Find or create instance
                inst = await self._get_or_create_instance(reg)
                if inst:
                    candidates.append((reg, inst))

        # Deduplicate
        seen = set()
        unique = []
        for reg, inst in candidates:
            key = inst.instance.identity.agent_id
            if key not in seen:
                seen.add(key)
                unique.append((reg, inst))

        return unique

    async def _get_or_create_instance(self, reg: "AgentRegistration") -> Optional["AgentInstance"]:
        """Get or create an agent instance."""
        # Check existing instances
        for inst in self._registry.list_instances():
            if inst.registration.registration_id == reg.registration_id:
                if inst.instance.state in (inst.instance.state.READY, inst.instance.state.BUSY):
                    return inst

        # Create new instance
        try:
            instance = await self._registry.create_instance(reg.registration_id)
            return self._registry.get_instance(instance.instance.identity.agent_id)
        except Exception as e:
            logger.warning(f"Failed to create instance for {reg.identity.agent_id}: {e}")
            return None

    async def _score_candidates(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> List[Tuple[float, "AgentRegistration", "AgentInstance", Dict[str, Any]]]:
        """Score candidates based on context."""
        scored = []

        for reg, inst in candidates:
            score = 0.0
            reasons = []
            matched = []
            missing = []

            # Check required capabilities
            for cap in ctx.required_capabilities:
                if reg.capabilities.has(cap):
                    matched.append(cap)
                    score += 10.0
                else:
                    missing.append(cap)
                    score -= 20.0

            # Check preferred capabilities
            for cap in ctx.preferred_capabilities:
                if reg.capabilities.has(cap):
                    matched.append(cap)
                    score += 5.0

            # Role preference
            if ctx.preferred_role and reg.identity.role.value == ctx.preferred_role:
                score += 15.0
                reasons.append(f"role_match:{reg.identity.role.value}")

            # Model preference
            if ctx.preferred_model:
                if ctx.preferred_model in reg.metadata.model_requirements:
                    score += 10.0
                    reasons.append(f"model_match:{ctx.preferred_model}")
                elif not reg.metadata.model_requirements:
                    score += 5.0  # Flexible

            # Tool preference
            for tool in ctx.preferred_tools:
                if tool in reg.capabilities.capabilities:
                    matched.append(tool)
                    score += 3.0

            # Load factor (lower is better)
            load = self._registry._get_instance_load(inst.instance.identity.agent_id)
            score -= load * 2.0
            reasons.append("load:{}".format(inst.active_task_count))

            # Health status
            if inst.health_status == "healthy":
                score += 5.0
            elif inst.health_status == "degraded":
                score -= 10.0
                reasons.append("degraded")
            elif inst.health_status == "unhealthy":
                score -= 50.0
                reasons.append("unhealthy")

            # Local preference
            if ctx.prefer_local and self._is_local(reg):
                score += 8.0
                reasons.append("local")

            # Cost optimization
            if ctx.max_cost_usd:
                est_cost = self._estimate_cost(reg, inst)
                if est_cost > ctx.max_cost_usd:
                    score -= 100.0
                    reasons.append(f"cost_exceeds:{est_cost:.2f}")
                else:
                    score += 3.0
                    reasons.append(f"cost_ok:{est_cost:.2f}")

            # Latency optimization
            if ctx.max_latency_seconds:
                est_latency = self._estimate_latency(reg, inst)
                if est_latency > ctx.max_latency_seconds:
                    score -= 50.0
                    reasons.append(f"latency_exceeds:{est_latency:.1f}s")
                else:
                    score += 2.0
                    reasons.append(f"latency_ok:{est_latency:.1f}s")

            # Capability completeness
            matched_count = len(set(ctx.required_capabilities) & set(reg.capabilities.capabilities))
            total_required = len(ctx.required_capabilities)
            if total_required > 0:
                completeness = matched_count / total_required
                score *= (0.5 + 0.5 * completeness)

            if score >= 0:  # Only consider candidates with non-negative score
                details = {
                    "matched": matched,
                    "missing": missing,
                    "reasons": reasons,
                }
                scored.append((score, reg, inst, details))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _select_best(
        self,
        scored: List[Tuple[float, "AgentRegistration", "AgentInstance", Dict[str, Any]]],
        ctx: RoutingContext,
    ) -> "RoutingDecision":
        """Select the best candidate from scored list."""
        if not scored:
            return RoutingDecision(
                instance_id="",
                registration_id="",
                agent_id="",
                role="",
                confidence=0.0,
                reasoning="No suitable candidates",
                strategy=ctx.strategy,
                matched_capabilities=[],
                missing_capabilities=ctx.required_capabilities,
                estimated_cost=0.0,
                estimated_latency=0.0,
            )

        best_score, reg, inst, details = scored[0]

        # Calculate confidence (0.0 - 1.0)
        confidence = min(1.0, max(0.0, best_score / 100.0))

        # Build reasoning
        reasons = details.get("reasons", [])
        reasoning = "; ".join(reasons) if reasons else "Selected based on capability match"

        # Estimate cost and latency
        est_cost = self._estimate_cost(scored[0][1], scored[0][2])
        est_latency = self._estimate_latency(scored[0][1], scored[0][2])

        return RoutingDecision(
            instance_id=scored[0][2].instance.identity.agent_id,
            registration_id=scored[0][1].registration_id,
            agent_id=scored[0][2].instance.identity.agent_id,
            role=scored[0][1].identity.role.value,
            confidence=confidence,
            reasoning=reasoning,
            strategy="best_match",
            matched_capabilities=details.get("matched", []),
            missing_capabilities=details.get("missing", []),
            estimated_cost=est_cost,
            estimated_latency=est_latency,
        )

    # ── Cost & Latency Estimation ──────────────────────────────────────

    def _estimate_cost(self, reg: "AgentRegistration", inst: "AgentInstance") -> float:
        """Estimate cost for a task on this agent."""
        # Base cost from model requirements
        base_cost = 0.001  # Per 1k tokens estimate

        # Adjust for model
        for req in reg.metadata.model_requirements:
            if "gpt-4" in req.lower() or "opus" in req.lower():
                base_cost += 0.03
            elif "sonnet" in req.lower() or "claude-3" in req.lower():
                base_cost += 0.015
            elif "haiku" in req.lower() or "mini" in req.lower():
                base_cost += 0.005
            else:
                base_cost += 0.01

        # Adjust for tools
        tool_count = len(reg.capabilities.capabilities)
        base_cost += tool_count * 0.001

        # Adjust for load
        load_factor = 1.0 + (inst.active_task_count * 0.1)

        return base_cost * load_factor

    def _estimate_latency(self, reg: "AgentRegistration", inst: "AgentInstance") -> float:
        """Estimate latency in seconds."""
        base = 5.0  # Base latency

        # Model latency
        for req in reg.metadata.model_requirements:
            if "gpt-4" in req.lower() or "opus" in req.lower():
                base += 10.0
            elif "sonnet" in req.lower() or "claude-3" in req.lower():
                base += 5.0
            elif "haiku" in req.lower() or "mini" in req.lower():
                base += 2.0
            else:
                base += 3.0

            if "local" in req.lower():
                base += 5.0  # Local models slower

        # Tool overhead
        tool_count = len(reg.capabilities.capabilities)
        base += tool_count * 0.5

        # Load factor
        load_factor = 1.0 + (inst.active_task_count * 0.2)

        return base * load_factor

    def _is_local(self, reg: "AgentRegistration") -> bool:
        """Check if agent runs locally."""
        for req in reg.metadata.model_requirements:
            if "local" in req.lower() or "ollama" in req.lower() or "llama" in req.lower():
                return True
        return False

    # ── History & Analytics ──────────────────────────────────────────

    def _record_routing(self, task_id: str, decision: RoutingDecision):
        """Record routing decision for analytics."""
        self._routing_history.append((time.time(), task_id, decision))
        if len(self._routing_history) > self._max_history:
            self._routing_history.pop(0)

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self._routing_history:
            return {"total": 0}

        total = len(self._routing_history)
        avg_confidence = sum(d.confidence for _, _, d in self._routing_history) / len(self._routing_history)
        strategies = {}
        for _, _, d in self._routing_history:
            strategies[d.strategy] = strategies.get(d.strategy, 0) + 1

        return {
            "total_routes": len(self._routing_history),
            "avg_confidence": avg_confidence,
            "strategies": strategies,
        }

    def get_recent_routes(self, limit: int = 10) -> List[RoutingDecision]:
        """Get recent routing decisions."""
        return [d for _, _, d in self._routing_history[-limit:]]


# =============================================================================
# Routing Strategies
# =============================================================================


class RoutingStrategy:
    """Base class for routing strategies."""

    def __init__(self, router: CapabilityRouter):
        self.router = router

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        raise NotImplementedError


class BestMatchStrategy(RoutingStrategy):
    """Select highest-scoring candidate."""

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        scored = await self.router._score_candidates(candidates, ctx)
        return self.router._select_best(scored, ctx)


class LeastLoadedStrategy(RoutingStrategy):
    """Select agent with fewest active tasks."""

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        if not candidates:
            return RoutingDecision(
                instance_id="", registration_id="", agent_id="", role="",
                confidence=0.0, reasoning="No candidates", strategy="least_loaded",
                matched_capabilities=[], missing_capabilities=[],
                estimated_cost=0.0, estimated_latency=0.0,
            )

        # Find least loaded
        best = min(candidates, key=lambda x: x[1].active_task_count)
        reg, inst = best

        return RoutingDecision(
            instance_id=inst.instance.identity.agent_id,
            registration_id=reg.registration_id,
            agent_id=inst.instance.identity.agent_id,
            role=reg.identity.role.value,
            confidence=0.7,
            reasoning="Least loaded agent",
            strategy="least_loaded",
            matched_capabilities=[],
            missing_capabilities=[],
            estimated_cost=self.router._estimate_cost(best[0], best[1]),
            estimated_latency=self.router._estimate_latency(best[0], best[1]),
        )


class RoundRobinStrategy(RoutingStrategy):
    """Round-robin selection among capable agents."""

    def __init__(self, router: CapabilityRouter):
        super().__init__(router)
        self._last_index: Dict[str, int] = {}

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        if not candidates:
            return RoutingDecision(
                instance_id="", registration_id="", agent_id="", role="",
                confidence=0.0, reasoning="No candidates", strategy="round_robin",
                matched_capabilities=[], missing_capabilities=[],
                estimated_cost=0.0, estimated_latency=0.0,
            )

        key = ctx.preferred_role or "default"
        idx = self._last_index.get(key, 0)
        selected = candidates[idx % len(candidates)]
        self._last_index[key] = (idx + 1) % len(candidates)

        reg, inst = selected
        return RoutingDecision(
            instance_id=inst.instance.identity.agent_id,
            registration_id=reg.registration_id,
            agent_id=inst.instance.identity.agent_id,
            role=reg.identity.role.value,
            confidence=0.6,
            reasoning="Round-robin selection (index {})".format(idx),
            strategy="round_robin",
            matched_capabilities=[],
            missing_capabilities=[],
            estimated_cost=self.router._estimate_cost(selected[0], selected[1]),
            estimated_latency=self.router._estimate_latency(selected[0], selected[1]),
        )


class CostOptimizedStrategy(RoutingStrategy):
    """Minimize estimated cost."""

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        if not candidates:
            return RoutingDecision(
                instance_id="", registration_id="", agent_id="", role="",
                confidence=0.0, reasoning="No candidates", strategy="cost_optimized",
                matched_capabilities=[], missing_capabilities=[],
                estimated_cost=0.0, estimated_latency=0.0,
            )

        best = min(candidates, key=lambda x: self.router._estimate_cost(x[0], x[1]))
        reg, inst = best

        return RoutingDecision(
            instance_id=inst.instance.identity.agent_id,
            registration_id=reg.registration_id,
            agent_id=inst.instance.identity.agent_id,
            role=reg.identity.role.value,
            confidence=0.7,
            reasoning="Lowest estimated cost",
            strategy="cost_optimized",
            matched_capabilities=[],
            missing_capabilities=[],
            estimated_cost=self.router._estimate_cost(best[0], best[1]),
            estimated_latency=self.router._estimate_latency(best[0], best[1]),
        )


class LatencyOptimizedStrategy(RoutingStrategy):
    """Minimize estimated latency."""

    async def select(
        self,
        candidates: List[Tuple["AgentRegistration", "AgentInstance"]],
        ctx: RoutingContext,
    ) -> RoutingDecision:
        if not candidates:
            return RoutingDecision(
                instance_id="", registration_id="", agent_id="", role="",
                confidence=0.0, reasoning="No candidates", strategy="latency_optimized",
                matched_capabilities=[], missing_capabilities=[],
                estimated_cost=0.0, estimated_latency=0.0,
            )

        best = min(candidates, key=lambda x: self.router._estimate_latency(x[0], x[1]))
        reg, inst = best

        return RoutingDecision(
            instance_id=inst.instance.identity.agent_id,
            registration_id=reg.registration_id,
            agent_id=inst.instance.identity.agent_id,
            role=reg.identity.role.value,
            confidence=0.7,
            reasoning="Lowest estimated latency",
            strategy="latency_optimized",
            matched_capabilities=[],
            missing_capabilities=[],
            estimated_cost=self.router._estimate_cost(best[0], best[1]),
            estimated_latency=self.router._estimate_latency(best[0], best[1]),
        )


# =============================================================================
# Router Factory
# =============================================================================


def create_router(
    agent_registry: "AgentRegistry",
    model_router: Optional[Any] = None,
    default_strategy: str = "best_match",
) -> CapabilityRouter:
    """Create a capability router with the specified strategy."""
    router = CapabilityRouter(agent_registry, model_router)

    # Add strategies
    router.strategies = {
        "best_match": BestMatchStrategy(router),
        "least_loaded": LeastLoadedStrategy(router),
        "round_robin": RoundRobinStrategy(router),
        "cost_optimized": CostOptimizedStrategy(router),
        "latency_optimized": LatencyOptimizedStrategy(router),
    }

    router.default_strategy = default_strategy
    return router


# Backwards compatibility
def create_capability_router(
    agent_registry: "AgentRegistry",
    model_router: Optional[Any] = None,
) -> CapabilityRouter:
    """Create a capability router (backwards compatible)."""
    return create_router(agent_registry, model_router)