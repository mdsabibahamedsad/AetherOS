#!/usr/bin/env python3
"""
Capability Router — Select Optimal Tool/Model Combination for a Goal

Routes user intents to the most appropriate capability, tool, and model
based on availability, cost, latency, capability match, and user preferences.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .models import (
    CapabilityCategory,
    CapabilitySpec,
    ModelReference,
    RoutingDecision,
    ToolReference,
    RiskLevel,
)
from .capability_registry import get_capability_registry

logger = logging.getLogger(__name__)


@dataclass
class RoutingContext:
    """Context for routing decisions."""
    user_intent: str
    available_tools: Set[str] = field(default_factory=set)
    available_models: Set[str] = field(default_factory=set)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM
    preferred_providers: List[str] = field(default_factory=list)
    budget_limit: Optional[float] = None
    latency_requirement: Optional[int] = None  # max ms
    privacy_requirement: str = "standard"  # standard, high, local_only


@dataclass
class CapabilityScore:
    """Scoring for capability routing."""
    capability_id: str
    score: float
    reasoning: str
    matched_keywords: List[str] = field(default_factory=list)
    capability: Optional[CapabilitySpec] = None
    recommended_tool: Optional[ToolReference] = None
    recommended_model: Optional[ModelReference] = None


class CapabilityRouter:
    """
    Routes user intents to optimal capabilities, tools, and models.
    
    Uses keyword matching, semantic similarity (when embeddings available),
    availability checking, cost/latency optimization, and user preferences.
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._registry = get_capability_registry()
        self._lock = threading.RLock()
        self._keyword_index: Dict[str, Set[str]] = {}
        self._intent_cache: Dict[str, RoutingDecision] = {}
        self._cache_ttl_seconds = 300
        self._cache_timestamps: Dict[str, float] = {}
        self._initialized = False
        
        # Scoring weights (configurable)
        self.weights = {
            "keyword_match": 0.4,
            "category_match": 0.2,
            "availability": 0.15,
            "cost": 0.1,
            "latency": 0.1,
            "risk_match": 0.05,
        }

    def initialize(self) -> None:
        """Initialize the router with capability registry."""
        with self._lock:
            if self._initialized:
                return
            self._registry.initialize()
            self._registry.discover_and_register_capabilities()
            self._build_keyword_index()
            self._initialized = True
            logger.info("Capability router initialized")

    def _build_keyword_index(self) -> None:
        """Build keyword index from capability specs."""
        self._keyword_index = {}
        for cap_id, entry in self._registry._capabilities.items():
            spec = entry.spec
            keywords = set()
            # Add capability name words
            keywords.update(spec.name.lower().split())
            # Add description words
            keywords.update(spec.description.lower().split())
            # Add tags
            keywords.update(spec.tags)
            # Add category
            keywords.add(spec.category.value)
            
            for keyword in keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = set()
                self._keyword_index[keyword].add(cap_id)

    def route(self, user_intent: str, context: Dict[str, Any] | None = None) -> RoutingDecision:
        """
        Route a user intent to the best capability/tool/model combination.
        """
        self.initialize()
        
        # Build routing context
        routing_context = self._build_routing_context(user_intent, context)
        
        # Check cache
        cache_key = self._cache_key(user_intent, routing_context)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Score all capabilities
        scored = self._score_capabilities(user_intent, routing_context)
        
        if not scored:
            # Fallback: return a generic decision
            return RoutingDecision(
                capability_id="fallback",
                confidence=0.1,
                reasoning="No matching capabilities found",
            )
        
        # Select best
        best = scored[0]
        
        # Select specific tool and model
        tool = self._select_tool(best.capability, routing_context)
        model = self._select_model(best.capability, routing_context)
        
        decision = RoutingDecision(
            capability_id=best.capability_id,
            tool_name=tool.name if tool else None,
            model_name=model.name if model else None,
            confidence=best.score,
            reasoning=best.reasoning,
            alternatives=[s.capability_id for s in scored[1:3]],
            estimated_cost=self._estimate_cost(best.capability, tool, model),
            estimated_latency_ms=self._estimate_latency(best.capability, tool, model),
        )
        
        # Cache result
        self._cache(cache_key, decision)
        
        return decision

    def _build_routing_context(self, user_intent: str, context: Dict[str, Any] | None) -> RoutingContext:
        """Build routing context from user intent and context."""
        context = context or {}
        
        # Get available tools and models from registry
        available_tools = set()
        available_models = set()
        
        for entry in self._registry._capabilities.values():
            if entry.spec.available:
                for tool in entry.spec.tools:
                    available_tools.add(tool.name)
                for model in entry.spec.models:
                    available_models.add(model.name)
        
        return RoutingContext(
            user_intent=user_intent,
            available_tools=available_tools,
            available_models=available_models,
            user_preferences=context.get("user_preferences", {}),
            constraints=context.get("constraints", {}),
            required_capabilities=context.get("required_capabilities", []),
            risk_tolerance=RiskLevel(context.get("risk_tolerance", "medium")),
            preferred_providers=context.get("preferred_providers", []),
            budget_limit=context.get("budget_limit"),
            latency_requirement=context.get("latency_requirement"),
            privacy_requirement=context.get("privacy_requirement", "standard"),
        )

    def _score_capabilities(self, user_intent: str, context: RoutingContext) -> List[CapabilityScore]:
        """Score all capabilities against the user intent."""
        scores = []
        intent_lower = user_intent.lower()
        intent_words = set(intent_lower.split())
        
        for cap_id, entry in self._registry._capabilities.items():
            if not entry.spec.available:
                continue
            
            # Skip tool-level capabilities (they're selected as tools within parent capabilities)
            if cap_id.startswith("tool:"):
                continue
            
            spec = entry.spec
            
            # Check risk tolerance
            if spec.risk_level > context.risk_tolerance:
                continue
            
            # Check required capabilities
            if context.required_capabilities and cap_id not in context.required_capabilities:
                continue
            
            # Check privacy requirement
            if context.privacy_requirement == "local_only":
                has_local_model = any(m.provider == "local" for m in spec.models)
                if spec.tools and not has_local_model:
                    continue
            
            # Calculate scores
            keyword_score = self._keyword_match_score(intent_words, spec)
            category_score = self._category_match_score(intent_lower, spec)
            availability_score = 1.0 if spec.available else 0.0
            cost_score = self._cost_score(spec, context)
            latency_score = self._latency_score(spec, context)
            risk_score = self._risk_score(spec, context)
            
            # Weighted total
            total_score = (
                keyword_score * self.weights["keyword_match"] +
                category_score * self.weights["category_match"] +
                availability_score * self.weights["availability"] +
                cost_score * self.weights["cost"] +
                latency_score * self.weights["latency"] +
                risk_score * self.weights["risk_match"]
            )
            
            # Find matched keywords
            matched_keywords = []
            for word in intent_words:
                if word in self._keyword_index and cap_id in self._keyword_index[word]:
                    matched_keywords.append(word)
            
            # Select recommended tool/model
            tool = self._select_tool(spec, context)
            model = self._select_model(spec, context)
            
            scores.append(CapabilityScore(
                capability_id=cap_id,
                score=total_score,
                reasoning=self._generate_reasoning(spec, keyword_score, category_score, matched_keywords),
                matched_keywords=matched_keywords,
                capability=spec,
                recommended_tool=tool,
                recommended_model=model,
            ))
        
        # Sort by score descending, then by number of matched keywords (more specific = better)
        scores.sort(key=lambda s: (s.score, len(s.matched_keywords)), reverse=True)
        return scores

    def _keyword_match_score(self, intent_words: Set[str], spec: CapabilitySpec) -> float:
        """Score based on keyword overlap."""
        spec_keywords = set()
        spec_keywords.update(spec.name.lower().split())
        spec_keywords.update(spec.description.lower().split())
        spec_keywords.update(spec.tags)
        spec_keywords.add(spec.category.value)
        
        # Add capability-specific strong keywords
        if spec.category == CapabilityCategory.TERMINAL:
            spec_keywords.update({"run", "execute", "command", "shell", "bash", "cmd", "powerscript", "script", "echo", "cmd"})
        elif spec.category == CapabilityCategory.FILE_SYSTEM:
            spec_keywords.update({"read", "write", "file", "folder", "directory", "path", "create", "delete", "list", "copy", "move"})
        elif spec.category == CapabilityCategory.WEB_BROWSER:
            spec_keywords.update({"search", "browse", "navigate", "website", "url", "page", "web", "internet", "google", "news", "article", "ai", "ml", "machine learning", "deep learning"})
        elif spec.category == CapabilityCategory.COMPUTER_CONTROL:
            spec_keywords.update({"click", "type", "screenshot", "window", "app", "application", "desktop", "automate"})
        elif spec.category == CapabilityCategory.KNOWLEDGE:
            spec_keywords.update({"search", "research", "recall", "remember", "knowledge", "fact", "information"})
        elif spec.category == CapabilityCategory.MEMORY:
            spec_keywords.update({"remember", "recall", "store", "memory", "forget", "save", "forget"})
        
        overlap = intent_words & spec_keywords
        if not spec_keywords:
            return 0.0
        return len(overlap) / len(spec_keywords)

    def _category_match_score(self, intent: str, spec: CapabilitySpec) -> float:
        """Score based on category match."""
        # Simple heuristic: check if category name appears in intent
        category_words = spec.category.value.replace("_", " ").split()
        for word in category_words:
            if word in intent:
                return 1.0
        return 0.0

    def _cost_score(self, spec: CapabilitySpec, context: RoutingContext) -> float:
        """Score based on cost (lower cost = higher score)."""
        if context.budget_limit is None:
            return 1.0  # No budget constraint
        
        # Estimate cost from model cost classes
        total_cost = 0.0
        for model in spec.models:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            total_cost += cost_map.get(model.cost_class, 0.1)
        
        avg_cost = total_cost / max(1, len(spec.models))
        if avg_cost <= context.budget_limit:
            return 1.0
        return max(0.0, 1.0 - (avg_cost - context.budget_limit) / context.budget_limit)

    def _latency_score(self, spec: CapabilitySpec, context: RoutingContext) -> float:
        """Score based on latency (lower latency = higher score)."""
        if context.latency_requirement is None:
            return 1.0
        
        # Estimate latency from model latency classes
        total_latency = 0
        for model in spec.models:
            latency_map = {"fast": 100, "standard": 1000, "slow": 5000}
            total_latency += latency_map.get(model.latency_class, 1000)
        
        avg_latency = total_latency / max(1, len(spec.models))
        if avg_latency <= context.latency_requirement:
            return 1.0
        return max(0.0, 1.0 - (avg_latency - context.latency_requirement) / context.latency_requirement)

    def _risk_score(self, spec: CapabilitySpec, context: RoutingContext) -> float:
        """Score based on risk tolerance match."""
        risk_values = {RiskLevel.NONE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
        spec_risk = risk_values.get(spec.risk_level, 2)
        tolerance = risk_values.get(context.risk_tolerance, 2)
        
        if spec_risk <= tolerance:
            return 1.0
        return max(0.0, 1.0 - (spec_risk - tolerance) / 4.0)

    def _select_tool(self, spec: CapabilitySpec, context: RoutingContext) -> Optional[ToolReference]:
        """Select the best tool for a capability."""
        if not spec.tools:
            return None
        
        # Prefer available tools
        available_tools = [t for t in spec.tools if t.name in context.available_tools]
        if not available_tools:
            available_tools = spec.tools
        
        # Simple selection: first available tool
        return available_tools[0]

    def _select_model(self, spec: CapabilitySpec, context: RoutingContext) -> Optional[ModelReference]:
        """Select the best model for a capability."""
        if not spec.models:
            return None
        
        # Filter by availability
        available_models = [m for m in spec.models if m.name in context.available_models]
        if not available_models:
            available_models = spec.models
        
        # Filter by privacy requirement
        if context.privacy_requirement == "local_only":
            local_models = [m for m in available_models if m.provider == "local"]
            if local_models:
                available_models = local_models
        
        # Filter by preferred providers
        if context.preferred_providers:
            preferred = [m for m in available_models if m.provider in context.preferred_providers]
            if preferred:
                available_models = preferred
        
        # Select based on cost/latency requirements
        if context.budget_limit is not None:
            available_models.sort(key=lambda m: {"free": 0, "low": 1, "standard": 2, "high": 3}.get(m.cost_class, 2))
        elif context.latency_requirement is not None:
            available_models.sort(key=lambda m: {"fast": 0, "standard": 1, "slow": 2}.get(m.latency_class, 1))
        
        return available_models[0] if available_models else None

    def _generate_reasoning(self, spec: CapabilitySpec, keyword_score: float, 
                            category_score: float, matched_keywords: List[str]) -> str:
        """Generate human-readable reasoning for the routing decision."""
        parts = []
        if matched_keywords:
            parts.append(f"Keywords matched: {', '.join(matched_keywords)}")
        if category_score > 0:
            parts.append(f"Category '{spec.category.value}' matches intent")
        if keyword_score > 0.3:
            parts.append("Strong keyword overlap")
        elif keyword_score > 0:
            parts.append("Some keyword overlap")
        return "; ".join(parts) if parts else f"Low relevance to {spec.category.value} category"

    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:
        """Estimate execution cost in arbitrary units."""
        cost = 0.0
        if model:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            cost += cost_map.get(model.cost_class, 0.1)
        if tool and tool.risk_level >= RiskLevel.HIGH:
            cost += 0.05  # Premium for high-risk tools
        return cost

    def _estimate_latency(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> int:
        """Estimate execution latency in milliseconds."""
        latency = 100  # Base overhead
        if model:
            latency_map = {"fast": 100, "standard": 1000, "slow": 5000}
            latency += latency_map.get(model.latency_class, 1000)
        if tool and tool.is_async:
            latency += 500
        return latency

    def _cache_key(self, user_intent: str, context: RoutingContext) -> str:
        """Generate cache key for routing decision."""
        import hashlib
        key_data = f"{user_intent}|{context.risk_tolerance.value}|{context.privacy_requirement}"
        if context.budget_limit:
            key_data += f"|budget:{context.budget_limit}"
        if context.latency_requirement:
            key_data += f"|latency:{context.latency_requirement}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[RoutingDecision]:
        import time
        if key in self._intent_cache:
            ts = self._cache_timestamps.get(key, 0)
            if time.time() - ts < self._cache_ttl_seconds:
                return self._intent_cache[key]
        return None

    def _cache(self, key: str, decision: RoutingDecision) -> None:
        import time
        self._intent_cache[key] = decision
        self._cache_timestamps[key] = time.time()

    def clear_cache(self) -> None:
        """Clear the routing cache."""
        with self._lock:
            self._intent_cache.clear()
            self._cache_timestamps.clear()

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        with self._lock:
            return {
                "cache_size": len(self._intent_cache),
                "keyword_index_size": len(self._keyword_index),
                "total_capabilities": len(self._registry._capabilities),
                "weights": self.weights,
            }

    def update_weights(self, weights: Dict[str, float]) -> None:
        """Update scoring weights."""
        with self._lock:
            total = sum(weights.values())
            if total > 0:
                self.weights = {k: v / total for k, v in weights.items()}
            else:
                self.weights = weights


# Module-level instance
_router_instance: Optional[CapabilityRouter] = None


def get_capability_router(config: Dict[str, Any] | None = None) -> CapabilityRouter:
    """Get the global capability router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CapabilityRouter(config)
    return _router_instance