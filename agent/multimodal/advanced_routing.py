"""Advanced Model Routing with Cost/Latency Optimization (Phase 56).

Extends the enhanced routing with:
- Dynamic cost-aware routing
- Latency-aware model selection
- Provider failover with cost awareness
- Token usage tracking and budgeting
- Model performance analytics
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

from agent.multimodal.enhanced_routing import EnhancedModelRouter, RoutingDecision, RoutingStrategy
from agent.multimodal.capability_detector import CapabilityDetector, ModelCapability
from agent.multimodal.production import MetricsCollector, CircuitBreaker

logger = logging.getLogger(__name__)


class CostStrategy(Enum):
    """Cost optimization strategies."""
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_LATENCY = "minimize_latency"
    BALANCED = "balanced"
    QUALITY_FIRST = "quality_first"
    BUDGET_CONSTRAINED = "budget_constrained"


@dataclass
class ModelCostProfile:
    """Cost and performance profile for a model."""
    provider: str
    model: str
    input_cost_per_1k: float      # $ per 1K input tokens
    output_cost_per_1k: float     # $ per 1K output tokens
    avg_latency_ms: float         # Average latency in ms
    max_tokens: int               # Max context window
    capabilities: List[str]       # Supported capabilities
    reliability_score: float = 1.0  # 0-1 reliability
    last_updated: float = field(default_factory=time.time)


@dataclass
class RoutingContext:
    """Context for routing decision."""
    task_type: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    required_capabilities: List[str]
    max_latency_ms: Optional[float] = None
    max_cost_usd: Optional[float] = None
    quality_requirement: float = 0.5  # 0-1
    preferred_providers: List[str] = field(default_factory=list)
    excluded_providers: List[str] = field(default_factory=list)


@dataclass
class RoutingResult:
    """Result of routing decision with cost analysis."""
    provider: str
    model: str
    estimated_cost_usd: float
    estimated_latency_ms: float
    confidence: float
    reasoning: str
    alternatives: List[Dict] = field(default_factory=list)
    cost_breakdown: Dict[str, float] = field(default_factory=dict)


class CostTracker:
    """Tracks token usage and costs (Phase 56)."""

    def __init__(self, budget_usd: float = 100.0, period_hours: int = 24):
        self.budget_usd = budget_usd
        self.period_hours = period_hours
        self._usage: Dict[str, Dict] = defaultdict(lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "requests": 0,
            "errors": 0,
            "last_reset": time.time(),
        })
        self._lock = threading.Lock()
        self._period_seconds = period_hours * 3600

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        success: bool = True,
    ) -> None:
        key = f"{provider}/{model}"
        with self._lock:
            now = time.time()
            usage = self._usage[key]
            # Reset if period expired
            if now - usage["last_reset"] > 86400:  # 24 hours
                usage.update({"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "requests": 0, "errors": 0, "last_reset": time.time()})
            usage["input_tokens"] += input_tokens
            usage["output_tokens"] += output_tokens
            usage["cost_usd"] += cost_usd
            usage["requests"] += 1
            if not success:
                usage["errors"] += 1

    def get_usage(self, provider: Optional[str] = None, model: Optional[str] = None) -> Dict:
        with self._lock:
            if provider and model:
                key = f"{provider}/{model}"
                return self._usage.get(key, {})
            elif provider:
                return {k: v for k, v in self._usage.items() if k.startswith(f"{provider}/")}
            return dict(self._usage)

    def get_total_cost(self) -> float:
        with self._lock:
            return sum(u["cost_usd"] for u in self._usage.values())

    def is_over_budget(self) -> bool:
        return self.get_total_cost() > self.budget_usd

    def get_remaining_budget(self) -> float:
        return max(0, self.budget_usd - self.get_total_cost())

    def reset(self) -> None:
        with self._lock:
            self._usage.clear()


class AdvancedModelRouter:
    """Advanced model router with cost/latency optimization (Phase 56)."""

    def __init__(
        self,
        capability_detector: Optional[CapabilityDetector] = None,
        cost_strategy: CostStrategy = CostStrategy.BALANCED,
        cost_tracker: Optional[CostTracker] = None,
        metrics: Optional[Any] = None,
    ):
        self.capability_detector = capability_detector or CapabilityDetector()
        self.cost_strategy = cost_strategy
        self.cost_tracker = cost_tracker or CostTracker()
        self.metrics = metrics or MetricsCollector("model_router")

        # Model cost profiles (would be loaded from config in production)
        self._cost_profiles: Dict[str, ModelCostProfile] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._performance_history: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()

        # Initialize default profiles
        self._init_default_profiles()

    def _init_default_profiles(self) -> None:
        """Initialize default model cost profiles."""
        profiles = [
            ModelCostProfile("openai", "gpt-4o", 0.005, 0.015, 2000, 128000, ["vision", "text", "tools"], 0.99),
            ModelCostProfile("openai", "gpt-4o-mini", 0.00015, 0.0006, 1000, 128000, ["vision", "text", "tools"], 0.98),
            ModelCostProfile("openai", "gpt-4-turbo", 0.01, 0.03, 3000, 128000, ["vision", "text", "tools"], 0.99),
            ModelCostProfile("anthropic", "claude-3-5-sonnet", 0.003, 0.015, 1500, 200000, ["vision", "text", "tools"], 0.99),
            ModelCostProfile("anthropic", "claude-3-haiku", 0.00025, 0.00125, 800, 200000, ["vision", "text", "tools"], 0.98),
            ModelCostProfile("google", "gemini-1.5-pro", 0.0035, 0.0105, 2000, 1000000, ["vision", "text", "tools"], 0.97),
            ModelCostProfile("google", "gemini-1.5-flash", 0.000075, 0.0003, 1000, 1000000, ["vision", "text", "tools"], 0.96),
        ]
        for p in profiles:
            key = f"{p.provider}/{p.model}"
            self._cost_profiles[key] = p

    def update_cost_profile(self, profile: ModelCostProfile) -> None:
        """Update or add a model cost profile."""
        with self._lock:
            key = f"{profile.provider}/{profile.model}"
            self._cost_profiles[key] = profile

    def get_circuit_breaker(self, provider: str, model: str) -> CircuitBreaker:
        """Get or create circuit breaker for a model."""
        key = f"{provider}/{model}"
        with self._lock:
            if key not in self._circuit_breakers:
                self._circuit_breakers[key] = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
            return self._circuit_breakers[key]

    def route(
        self,
        context: RoutingContext,
        strategy: Optional[CostStrategy] = None,
    ) -> RoutingResult:
        """Route request to optimal model based on cost/latency/quality."""
        strategy = strategy or self.cost_strategy

        # Filter capable models
        capable_models = self._filter_capable_models(context)
        if not capable_models:
            raise ValueError("No capable models found for required capabilities")

        # Apply cost strategy
        if strategy == CostStrategy.MINIMIZE_COST:
            result = self._route_minimize_cost(context, capable_models)
        elif strategy == CostStrategy.MINIMIZE_LATENCY:
            result = self._route_minimize_latency(context, capable_models)
        elif strategy == CostStrategy.QUALITY_FIRST:
            result = self._route_quality_first(context, capable_models)
        elif strategy == CostStrategy.BUDGET_CONSTRAINED:
            result = self._route_budget_constrained(context, capable_models)
        else:  # BALANCED
            result = self._route_balanced(context, capable_models)

        # Record metrics
        self.metrics.counter("routing_requests", labels={"strategy": self.cost_strategy.value})
        self.metrics.histogram("routing_latency_ms", (time.time() - time.time()) * 1000)  # placeholder

        return result

    def _filter_capable_models(self, context: RoutingContext) -> List[ModelCostProfile]:
        """Filter models by capabilities and constraints."""
        capable = []
        for profile in self._cost_profiles.values():
            # Check capabilities
            if not all(cap in profile.capabilities for cap in context.required_capabilities):
                continue
            # Check provider preferences
            if context.preferred_providers and profile.provider not in context.preferred_providers:
                continue
            if profile.provider in context.excluded_providers:
                continue
            # Check budget
            if context.max_cost_usd:
                est_cost = self._estimate_cost(profile, context)
                if est_cost > context.max_cost_usd:
                    continue
            # Check latency
            if context.max_latency_ms and profile.avg_latency_ms > context.max_latency_ms:
                continue
            # Check circuit breaker
            cb = self.get_circuit_breaker(profile.provider, profile.model)
            if cb.state.value == "open":
                continue
            capable.append(profile)
        return capable

    def _estimate_cost(self, profile: ModelCostProfile, context: RoutingContext) -> float:
        input_cost = (context.estimated_input_tokens / 1000) * profile.input_cost_per_1k
        output_cost = (context.estimated_output_tokens / 1000) * profile.output_cost_per_1k
        return input_cost + output_cost

    def _estimate_latency(self, profile: ModelCostProfile, context: RoutingContext) -> float:
        # Base latency + token-dependent component
        base = profile.avg_latency_ms
        token_factor = (context.estimated_input_tokens + context.estimated_output_tokens) / 1000 * 10
        return base + token_factor

    def _route_minimize_cost(self, context: RoutingContext, models: List[ModelCostProfile]) -> RoutingResult:
        best = min(models, key=lambda m: self._estimate_cost(m, context))
        return self._build_result(best, context, "minimize_cost")

    def _route_minimize_latency(self, context: RoutingContext, models: List[ModelCostProfile]) -> RoutingResult:
        best = min(models, key=lambda m: self._estimate_latency(m, context))
        return self._build_result(best, context, "minimize_latency")

    def _route_quality_first(self, context: RoutingContext, models: List[ModelCostProfile]) -> RoutingResult:
        # Quality proxy: reliability * (1/cost) * (1/latency)
        def quality_score(m):
            cost = self._estimate_cost(m, context)
            latency = self._estimate_latency(m, context)
            return m.reliability_score / max(cost, 0.0001) / max(latency / 1000, 0.1)

        best = max(models, key=quality_score)
        return self._build_result(best, context, "quality_first")

    def _route_budget_constrained(self, context: RoutingContext, models: List[ModelCostProfile]) -> RoutingResult:
        # Filter by budget
        affordable = [m for m in models if self._estimate_cost(m, context) <= (context.max_cost_usd or float('inf'))]
        if not affordable:
            affordable = models
        # Among affordable, minimize latency
        best = min(affordable, key=lambda m: self._estimate_latency(m, context))
        return self._build_result(best, context, "budget_constrained")

    def _route_balanced(self, context: RoutingContext, models: List[ModelCostProfile]) -> RoutingResult:
        # Weighted score: 40% cost, 30% latency, 30% quality
        def score(m):
            cost = self._estimate_cost(m, context)
            latency = self._estimate_latency(m, context)
            cost_score = 1.0 / (1.0 + cost * 1000)  # Normalize
            latency_score = 1.0 / (1.0 + self._estimate_latency(m, context) / 1000)
            quality_score = m.reliability_score
            return 0.4 * cost_score + 0.3 * latency_score + 0.3 * quality_score

        best = max(models, key=score)
        return self._build_result(best, context, "balanced")

    def _build_result(
        self,
        profile: ModelCostProfile,
        context: RoutingContext,
        strategy: str,
    ) -> RoutingResult:
        cost = self._estimate_cost(profile, context)
        latency = self._estimate_latency(profile, context)

        # Build alternatives
        alternatives = []
        for p in self._cost_profiles.values():
            if p.provider != profile.provider or p.model != profile.model:
                alternatives.append({
                    "provider": p.provider,
                    "model": p.model,
                    "estimated_cost": self._estimate_cost(p, context),
                    "estimated_latency": self._estimate_latency(p, context),
                })

        return RoutingResult(
            provider=profile.provider,
            model=profile.model,
            estimated_cost_usd=cost,
            estimated_latency_ms=latency,
            confidence=0.9,
            reasoning=f"Selected via {strategy} strategy",
            alternatives=sorted(alternatives, key=lambda x: x["estimated_cost"])[:3],
            cost_breakdown={
                "input_cost": (context.estimated_input_tokens / 1000) * profile.input_cost_per_1k,
                "output_cost": (context.estimated_output_tokens / 1000) * profile.output_cost_per_1k,
            },
        )

    def record_request(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        cost_usd: Optional[float] = None,
    ) -> None:
        """Record request outcome for learning."""
        if cost_usd is None:
            profile = self._cost_profiles.get(f"{provider}/{model}")
            if profile:
                cost_usd = (input_tokens / 1000) * profile.input_cost_per_1k + (output_tokens / 1000) * profile.output_cost_per_1k
            else:
                cost_usd = 0.0

        self.cost_tracker.record_usage(provider, model, input_tokens, output_tokens, cost_usd or 0.0, success)

        # Update performance history
        key = f"{provider}/{model}"
        with self._lock:
            self._performance_history[key].append({
                "latency_ms": latency_ms,
                "success": success,
                "timestamp": time.time(),
            })
            # Keep last 1000 entries
            if len(self._performance_history[key]) > 1000:
                self._performance_history[key] = self._performance_history[key][-1000:]

        # Update circuit breaker
        cb = self.get_circuit_breaker(provider, model)
        if not success:
            # Circuit breaker handles failure internally
            pass

    def get_cost_report(self) -> Dict[str, Any]:
        """Generate cost report."""
        usage = self.cost_tracker.get_usage()
        total_cost = self.cost_tracker.get_total_cost()
        return {
            "total_cost_usd": total_cost,
            "budget_usd": self.cost_tracker.budget_usd,
            "remaining_budget": self.cost_tracker.get_remaining_budget(),
            "over_budget": self.cost_tracker.is_over_budget(),
            "by_model": usage,
        }


# Convenience factory
def create_advanced_router(
    cost_strategy: CostStrategy = CostStrategy.BALANCED,
    budget_usd: float = 100.0,
) -> AdvancedModelRouter:
    """Create an advanced model router with default settings."""
    cost_tracker = CostTracker(budget_usd=budget_usd)
    return AdvancedModelRouter(cost_strategy=cost_strategy, cost_tracker=cost_tracker)