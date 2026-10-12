"""
Model Manager — model routing, selection, and resource management.

Models become schedulable resources. The Kernel understands capabilities,
reasoning level, context size, modalities, latency, cost, and privacy.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from kernel.core.types import (
    ResourceBudget,
    DataClassification,
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Model capabilities."""
    TEXT = "text"
    REASONING = "reasoning"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    TOOL_USE = "tool_use"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"


class ModelProvider(Enum):
    """Model provider types."""
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


@dataclass
class ModelProfile:
    """Model capability profile."""
    model_id: str
    name: str
    provider: ModelProvider
    base_url: str = ""
    capabilities: List[ModelCapability] = field(default_factory=list)
    context_window: int = 4096
    max_output_tokens: int = 4096
    supports_vision: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_streaming: bool = True
    reasoning_level: str = "standard"  # standard, high, deep
    latency_class: str = "normal"  # fast, normal, slow
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    privacy_level: DataClassification = DataClassification.INTERNAL
    local: bool = False
    gpu_memory_mb: int = 0
    availability: float = 1.0  # 0.0 to 1.0
    health: str = "healthy"  # healthy, degraded, down
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelSelection:
    """Model selection criteria."""
    required_capabilities: List[ModelCapability] = field(default_factory=list)
    preferred_capabilities: List[ModelCapability] = field(default_factory=list)
    max_cost_per_1k: float = float('inf')
    max_latency: str = "slow"  # fast, normal, slow
    min_context_window: int = 0
    required_reasoning: str = "standard"
    privacy_requirement: DataClassification = DataClassification.PUBLIC
    prefer_local: bool = False
    exclude_providers: List[ModelProvider] = field(default_factory=list)
    exclude_models: List[str] = field(default_factory=list)


class IModelProvider:
    """Interface for model providers."""
    def get_models(self) -> List[ModelProfile]: ...
    def complete(self, model_id: str, messages: List[Dict], **kwargs) -> Any: ...
    def estimate_cost(self, model_id: str, messages: List[Dict]) -> float: ...
    def check_health(self, model_id: str) -> bool: ...


class ModelManager:
    """
    Manages model routing, selection, and resource allocation.
    
    Models are schedulable resources with capabilities, costs, and constraints.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Model registry
        self._models: Dict[str, ModelProfile] = {}
        self._providers: Dict[str, IModelProvider] = {}
        
        # Selection policies
        self._selection_policies: List[Callable[[ModelSelection, List[ModelProfile]], Optional[ModelProfile]]] = []
        
        # Usage tracking
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        
        # Register default selection policy
        self._register_default_policy()

    def _register_default_policy(self) -> None:
        """Register default model selection policy."""
        self._selection_policies.append(self._default_selection_policy)

    def register_provider(
        self,
        name: str,
        provider: IModelProvider,
    ) -> None:
        """Register a model provider."""
        with self._lock:
            self._providers[name] = provider
            
            # Load models from provider
            try:
                models = provider.get_models()
                for model in models:
                    self._models[model.model_id] = model
            except Exception as exc:
                logger.error("Failed to load models from provider %s: %s", name, exc)

        logger.info("ModelManager: registered provider %s", name)

        if self.event_bus:
            self.event_bus.emit("model.provider.registered", {
                "provider": name,
            })

    def register_model(self, model: ModelProfile) -> None:
        """Register a model directly."""
        with self._lock:
            self._models[model.model_id] = model

        if self.event_bus:
            self.event_bus.emit("model.registered", {
                "model_id": model.model_id,
                "provider": model.provider.value,
            })

    def select_model(self, selection: ModelSelection) -> Optional[ModelProfile]:
        """Select the best model for the given criteria."""
        with self._lock:
            candidates = list(self._models.values())

        # Filter by health
        candidates = [m for m in candidates if m.health == "healthy"]

        # Filter by availability: a model is never claimed available unless
        # its provider reports availability > 0 (unconfigured providers
        # register 0.0 and are excluded here, not silently offered).
        candidates = [m for m in candidates if (m.availability or 0.0) > 0.0]

        # Filter by excluded providers/models
        if selection.exclude_providers:
            candidates = [m for m in candidates if m.provider not in selection.exclude_providers]
        if selection.exclude_models:
            candidates = [m for m in candidates if m.model_id not in selection.exclude_models]

        # Filter by required capabilities
        for cap in selection.required_capabilities:
            candidates = [m for m in candidates if cap in m.capabilities]

        # Filter by context window
        if selection.min_context_window > 0:
            candidates = [m for m in candidates if m.context_window >= selection.min_context_window]

        # Filter by cost
        if selection.max_cost_per_1k < float('inf'):
            candidates = [m for m in candidates 
                         if m.cost_per_1k_input <= selection.max_cost_per_1k 
                         and m.cost_per_1k_output <= selection.max_cost_per_1k]

        # Filter by latency
        latency_order = {"fast": 0, "normal": 1, "slow": 2}
        max_latency = latency_order.get(selection.max_latency, 2)
        candidates = [m for m in candidates if latency_order.get(m.latency_class, 1) <= max_latency]

        # Filter by privacy
        privacy_order = {
            DataClassification.PUBLIC: 0,
            DataClassification.INTERNAL: 1,
            DataClassification.PRIVATE: 2,
            DataClassification.CONFIDENTIAL: 3,
            DataClassification.SECRET: 4,
            DataClassification.HIGHLY_SENSITIVE: 5,
        }
        req_privacy = privacy_order.get(selection.privacy_requirement, 0)
        # A model must be cleared for data AT LEAST as sensitive as the
        # requirement (>=, not <=): a PUBLIC-cleared model must never be
        # offered SECRET work.
        candidates = [m for m in candidates if privacy_order.get(m.privacy_level, 0) >= req_privacy]

        # Filter by reasoning level
        reasoning_order = {"standard": 0, "high": 1, "deep": 2}
        req_reasoning = reasoning_order.get(selection.required_reasoning, 0)
        candidates = [m for m in candidates if reasoning_order.get(m.reasoning_level, 0) >= req_reasoning]

        if not candidates:
            return None

        # Apply selection policies
        for policy in self._selection_policies:
            result = policy(selection, candidates)
            if result:
                return result

        # Fallback: first candidate
        return candidates[0]

    def _default_selection_policy(
        self,
        selection: ModelSelection,
        candidates: List[ModelProfile],
    ) -> Optional[ModelProfile]:
        """Default selection policy: prefer local, then preferred capabilities, then cost."""
        # Prefer local if requested
        if selection.prefer_local:
            local = [m for m in candidates if m.local]
            if local:
                candidates = local

        # Score by preferred capabilities
        if selection.preferred_capabilities:
            def score(model: ModelProfile) -> int:
                return sum(1 for cap in selection.preferred_capabilities if cap in model.capabilities)
            candidates.sort(key=score, reverse=True)

        # Then by cost (lower is better)
        candidates.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)

        return candidates[0] if candidates else None

    def register_selection_policy(self, policy: Callable) -> None:
        """Register a custom model selection policy."""
        self._selection_policies.append(policy)

    def get_model(self, model_id: str) -> Optional[ModelProfile]:
        """Get a model profile."""
        with self._lock:
            return self._models.get(model_id)

    def list_models(
        self,
        provider: ModelProvider = None,
        capability: ModelCapability = None,
        local_only: bool = False,
    ) -> List[ModelProfile]:
        """List models with optional filters."""
        with self._lock:
            models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if capability:
            models = [m for m in models if capability in m.capabilities]

        if local_only:
            models = [m for m in models if m.local]

        return models

    def estimate_cost(self, model_id: str, messages: List[Dict]) -> float:
        """Estimate cost for a model call."""
        model = self.get_model(model_id)
        if not model:
            return 0.0

        provider = self._providers.get(model.provider.value)
        if provider:
            try:
                return provider.estimate_cost(model_id, messages)
            except Exception as exc:
                logger.error("Cost estimation failed: %s", exc)

        # Fallback: rough estimate
        input_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
        return (input_tokens / 1000) * model.cost_per_1k_input

    def record_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        """Record model usage for metrics."""
        with self._lock:
            if model_id not in self._usage_stats:
                self._usage_stats[model_id] = {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_latency_ms": 0,
                    "errors": 0,
                    "first_used": _now(),
                    "last_used": _now(),
                }
            
            stats = self._usage_stats[model_id]
            stats["total_calls"] += 1
            stats["total_input_tokens"] += input_tokens
            stats["total_output_tokens"] += output_tokens
            stats["total_latency_ms"] += latency_ms
            if not success:
                stats["errors"] += 1
            stats["last_used"] = _now()

    def get_usage_stats(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a model."""
        with self._lock:
            return self._usage_stats.get(model_id)

    def check_health(self, model_id: str) -> bool:
        """Check model health."""
        model = self.get_model(model_id)
        if not model:
            return False

        provider = self._providers.get(model.provider.value)
        if provider:
            try:
                return provider.check_health(model_id)
            except Exception:
                pass

        return model.health == "healthy"

    def update_model_health(self, model_id: str, health: str) -> bool:
        """Update model health status."""
        with self._lock:
            model = self._models.get(model_id)
            if not model:
                return False
            model.health = health
            return True

    def get_stats(self) -> Dict[str, Any]:
        """Get model manager statistics."""
        with self._lock:
            total = len(self._models)
            by_provider: Dict[str, int] = {}
            by_capability: Dict[str, int] = {}
            local_count = 0
            healthy = 0

            for model in self._models.values():
                by_provider[model.provider.value] = by_provider.get(model.provider.value, 0) + 1
                for cap in model.capabilities:
                    by_capability[cap.value] = by_capability.get(cap.value, 0) + 1
                if model.local:
                    local_count += 1
                if model.health == "healthy":
                    healthy += 1

        return {
            "total_models": total,
            "by_provider": by_provider,
            "by_capability": by_capability,
            "local_models": local_count,
            "healthy_models": healthy,
            "providers": list(self._providers.keys()),
        }

    def shutdown(self) -> None:
        """Shutdown the model manager."""
        logger.info("ModelManager: shutting down")
        with self._lock:
            self._models.clear()
            self._providers.clear()
            self._usage_stats.clear()