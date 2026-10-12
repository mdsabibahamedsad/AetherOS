"""
Model Router for AetherOS Intelligence Engine.

Automatically selects the best model for each task based on:
    - Speed requirements
    - Quality requirements
    - Cost constraints
    - Privacy requirements
    - Offline availability
    - Context size needs

Supports routing to different providers and backends.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RoutingPriority(Enum):
    SPEED = "speed"
    QUALITY = "quality"
    COST = "cost"
    PRIVACY = "privacy"
    OFFLINE = "offline"
    BALANCED = "balanced"


@dataclass
class ModelProfile:
    """A model's capabilities and characteristics."""
    id: str
    provider: str
    name: str
    speed_score: float = 0.5
    quality_score: float = 0.5
    cost_per_token: float = 0.0
    privacy_level: int = 1
    offline: bool = False
    context_window: int = 8192
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_reasoning: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRequirement:
    """Requirements for a specific task."""
    min_quality: float = 0.0
    max_cost_per_token: float = float("inf")
    needs_privacy: bool = False
    needs_offline: bool = False
    min_context: int = 4096
    needs_tools: bool = False
    needs_vision: bool = False
    needs_reasoning: bool = False
    priority: RoutingPriority = RoutingPriority.BALANCED


class ModelRouter:
    """Routes tasks to the optimal model based on requirements.

    Maintains a catalog of available models across all providers
    and selects the best match for each task.

    Usage::

        router = ModelRouter()
        router.register_model(ModelProfile(
            id="gpt-4", provider="openai", name="GPT-4",
            quality_score=0.95, speed_score=0.6, cost_per_token=0.03,
        ))

        best = router.select(TaskRequirement(needs_reasoning=True))
    """

    def __init__(self) -> None:
        self._models: Dict[str, ModelProfile] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default model profiles."""
        defaults = [
            ModelProfile("gpt-4o", "openai", "GPT-4o",
                         speed_score=0.85, quality_score=0.92,
                         cost_per_token=0.01, context_window=128000,
                         supports_vision=True, supports_reasoning=True),
            ModelProfile("gpt-4o-mini", "openai", "GPT-4o Mini",
                         speed_score=0.95, quality_score=0.80,
                         cost_per_token=0.001, context_window=128000,
                         supports_vision=True),
            ModelProfile("claude-3.5-sonnet", "anthropic", "Claude 3.5 Sonnet",
                         speed_score=0.80, quality_score=0.94,
                         cost_per_token=0.015, context_window=200000,
                         supports_reasoning=True),
            ModelProfile("claude-3-haiku", "anthropic", "Claude 3 Haiku",
                         speed_score=0.95, quality_score=0.75,
                         cost_per_token=0.002, context_window=200000),
            ModelProfile("deepseek-reasoner", "deepseek", "DeepSeek Reasoner",
                         speed_score=0.70, quality_score=0.90,
                         cost_per_token=0.002, context_window=64000,
                         supports_reasoning=True),
            ModelProfile("deepseek-chat", "deepseek", "DeepSeek Chat",
                         speed_score=0.85, quality_score=0.82,
                         cost_per_token=0.001, context_window=64000),
            ModelProfile("gemini-1.5-pro", "google", "Gemini 1.5 Pro",
                         speed_score=0.80, quality_score=0.90,
                         cost_per_token=0.005, context_window=1000000,
                         supports_vision=True, supports_reasoning=True),
            ModelProfile("gemini-1.5-flash", "google", "Gemini 1.5 Flash",
                         speed_score=0.95, quality_score=0.78,
                         cost_per_token=0.0005, context_window=1000000,
                         supports_vision=True),
            ModelProfile("codestral", "mistral", "Codestral",
                         speed_score=0.80, quality_score=0.85,
                         cost_per_token=0.001, context_window=32000),
            ModelProfile("mixtral-8x7b", "mistral", "Mixtral 8x7B",
                         speed_score=0.75, quality_score=0.78,
                         cost_per_token=0.0005, context_window=32000),
            ModelProfile("llama-3.1-405b", "meta", "Llama 3.1 405B",
                         speed_score=0.65, quality_score=0.88,
                         cost_per_token=0.005, context_window=131072,
                         supports_reasoning=True),
            ModelProfile("llama-3.1-70b", "meta", "Llama 3.1 70B",
                         speed_score=0.75, quality_score=0.82,
                         cost_per_token=0.002, context_window=131072),
            ModelProfile("llama-3.1-8b", "meta", "Llama 3.1 8B",
                         speed_score=0.90, quality_score=0.68,
                         cost_per_token=0.0005, context_window=131072),
            ModelProfile("qwen2.5-72b", "qwen", "Qwen 2.5 72B",
                         speed_score=0.70, quality_score=0.85,
                         cost_per_token=0.002, context_window=32768,
                         supports_reasoning=True),
            ModelProfile("codellama-34b", "meta", "CodeLlama 34B",
                         speed_score=0.70, quality_score=0.78,
                         cost_per_token=0.001, context_window=16384),
            ModelProfile("deepseek-coder-33b", "deepseek", "DeepSeek Coder 33B",
                         speed_score=0.75, quality_score=0.82,
                         cost_per_token=0.001, context_window=16384),
        ]
        for m in defaults:
            self._models[m.id] = m

    # ------------------------------------------------------------------
    # Model registration
    # ------------------------------------------------------------------

    def register_model(self, profile: ModelProfile) -> None:
        """Register a model with the router."""
        self._models[profile.id] = profile
        logger.debug("Registered model: %s (%s)", profile.id, profile.provider)

    def unregister_model(self, model_id: str) -> bool:
        """Remove a model from the catalog."""
        return self._models.pop(model_id, None) is not None

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        profile = self._models.get(model_id)
        if profile:
            return self._profile_to_dict(profile)
        return None

    def list_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """List all registered models, optionally filtered by provider."""
        models = self._models.values()
        if provider:
            models = [m for m in models if m.provider == provider]
        return [self._profile_to_dict(m) for m in sorted(
            models, key=lambda m: m.quality_score, reverse=True
        )]

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------

    def select(self, requirement: TaskRequirement = None) -> Dict[str, Any]:
        """Select the best model for given requirements."""
        req = requirement or TaskRequirement()
        candidates = list(self._models.values())

        if req.needs_offline:
            candidates = [m for m in candidates if m.offline]
        if req.needs_privacy:
            candidates = [m for m in candidates if m.privacy_level >= 2]
        if req.needs_vision:
            candidates = [m for m in candidates if m.supports_vision]
        if req.needs_tools:
            candidates = [m for m in candidates if m.supports_tools]
        if req.needs_reasoning:
            candidates = [m for m in candidates if m.supports_reasoning]

        candidates = [m for m in candidates if m.context_window >= req.min_context]
        candidates = [m for m in candidates if m.quality_score >= req.min_quality]
        candidates = [m for m in candidates if m.cost_per_token <= req.max_cost_per_token]

        if not candidates:
            fallback = self._fallback(req)
            if fallback:
                return self._result(fallback, req, "fallback")
            return {"error": "No suitable model found", "requirement": str(req)}

        best = max(candidates, key=lambda m: self._score(m, req))
        return self._result(best, req, "matched")

    def select_for_task(self, task_type: str) -> Dict[str, Any]:
        """Convenience: select a model for a common task type."""
        routing_map = {
            "chat": TaskRequirement(speed=True, priority=RoutingPriority.SPEED),
            "reasoning": TaskRequirement(needs_reasoning=True,
                                         min_quality=0.85,
                                         priority=RoutingPriority.QUALITY),
            "coding": TaskRequirement(needs_tools=True,
                                      min_quality=0.80,
                                      priority=RoutingPriority.QUALITY),
            "quick_search": TaskRequirement(priority=RoutingPriority.SPEED,
                                            min_context=4096),
            "research": TaskRequirement(priority=RoutingPriority.QUALITY,
                                        min_context=32000),
            "writing": TaskRequirement(min_quality=0.80,
                                       priority=RoutingPriority.BALANCED),
            "analysis": TaskRequirement(needs_reasoning=True,
                                        min_quality=0.85,
                                        priority=RoutingPriority.QUALITY),
            "planning": TaskRequirement(needs_reasoning=True,
                                        min_context=16000,
                                        priority=RoutingPriority.BALANCED),
            "debugging": TaskRequirement(needs_tools=True,
                                         min_quality=0.80,
                                         priority=RoutingPriority.SPEED),
            "learning": TaskRequirement(priority=RoutingPriority.BALANCED),
            "cheap": TaskRequirement(max_cost_per_token=0.001,
                                     priority=RoutingPriority.COST),
            "private": TaskRequirement(needs_privacy=True,
                                       priority=RoutingPriority.PRIVACY),
        }
        req = routing_map.get(task_type, TaskRequirement())
        return self.select(req)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score(self, model: ModelProfile, req: TaskRequirement) -> float:
        """Score a model against requirements (0.0 - 1.0)."""
        prio = req.priority
        speed_w = 0.25
        quality_w = 0.25
        cost_w = 0.25
        context_w = 0.25

        if prio == RoutingPriority.SPEED:
            speed_w, quality_w, cost_w, context_w = 0.6, 0.15, 0.15, 0.1
        elif prio == RoutingPriority.QUALITY:
            speed_w, quality_w, cost_w, context_w = 0.1, 0.6, 0.15, 0.15
        elif prio == RoutingPriority.COST:
            speed_w, quality_w, cost_w, context_w = 0.15, 0.15, 0.6, 0.1
        elif prio == RoutingPriority.PRIVACY:
            speed_w, quality_w, cost_w, context_w = 0.1, 0.2, 0.2, 0.1
            privacy_score = min(model.privacy_level / 3.0, 1.0)
            return privacy_score * 0.4 + model.quality_score * 0.2 + \
                   model.speed_score * 0.1

        speed_s = model.speed_score * speed_w
        quality_s = model.quality_score * quality_w
        cost_s = (1.0 - min(model.cost_per_token / 0.05, 1.0)) * cost_w
        ctx_ratio = min(model.context_window / max(req.min_context, 1), 2.0) / 2.0
        context_s = ctx_ratio * context_w

        return speed_s + quality_s + cost_s + context_s

    def _fallback(self, req: TaskRequirement) -> Optional[ModelProfile]:
        """Find a fallback model when no exact match exists."""
        candidates = list(self._models.values())
        if not candidates:
            return None
        if req.needs_offline:
            return None
        return max(candidates, key=lambda m: m.quality_score)

    def _result(self, model: ModelProfile, req: TaskRequirement,
                match_type: str) -> Dict[str, Any]:
        return {
            "model": self._profile_to_dict(model),
            "confidence": round(self._score(model, req), 2),
            "match_type": match_type,
            "requirement": {
                "priority": req.priority.value,
                "needs_privacy": req.needs_privacy,
                "needs_offline": req.needs_offline,
                "min_context": req.min_context,
                "needs_reasoning": req.needs_reasoning,
                "needs_vision": req.needs_vision,
            },
        }

    # ------------------------------------------------------------------
    # Privacy & Offline
    # ------------------------------------------------------------------

    def get_private_models(self) -> List[Dict[str, Any]]:
        """Get models suitable for private/local use."""
        return [
            self._profile_to_dict(m) for m in self._models.values()
            if m.privacy_level >= 2 or m.offline
        ]

    def get_offline_models(self) -> List[Dict[str, Any]]:
        """Get models that can run fully offline."""
        return [
            self._profile_to_dict(m) for m in self._models.values()
            if m.offline
        ]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _profile_to_dict(self, profile: ModelProfile) -> Dict[str, Any]:
        return {
            "id": profile.id,
            "provider": profile.provider,
            "name": profile.name,
            "speed_score": profile.speed_score,
            "quality_score": profile.quality_score,
            "cost_per_token": profile.cost_per_token,
            "privacy_level": profile.privacy_level,
            "offline": profile.offline,
            "context_window": profile.context_window,
            "supports_tools": profile.supports_tools,
            "supports_vision": profile.supports_vision,
            "supports_streaming": profile.supports_streaming,
            "supports_reasoning": profile.supports_reasoning,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_models": len(self._models),
            "providers": sorted(set(m.provider for m in self._models.values())),
            "offline_count": sum(1 for m in self._models.values() if m.offline),
            "reasoning_count": sum(1 for m in self._models.values() if m.supports_reasoning),
        }
