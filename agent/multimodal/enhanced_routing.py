"""Enhanced Model Routing for the Multimodal OS (Phase 4 of Master Prompt 10).

Selects a model for a task based on modality, quality, latency, cost, privacy,
availability, context and tool support — integrating MASTER 6 routing concepts
with the multimodal capability detector (Phase 3).

No large/expensive model is used when a smaller suitable one suffices; a
privacy-first strategy prefers local processing; a circuit breaker avoids
hammering failing providers.

This router is a library. It is not wired into run_agent's hot loop.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agent.multimodal.capability_detector import CapabilityDetector, CapabilityType, ModelCapability
from agent.multimodal.media_abstraction import MediaObject

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    QUALITY_FIRST = "quality_first"
    COST_FIRST = "cost_first"
    SPEED_FIRST = "speed_first"
    BALANCED = "balanced"
    LOCAL_FIRST = "local_first"
    PRIVACY_FIRST = "privacy_first"


class FallbackReason(Enum):
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    TIMEOUT = "timeout"
    QUALITY_UNACCEPTABLE = "quality_unacceptable"
    COST_EXCEEDED = "cost_exceeded"


@dataclass
class RoutingPreference:
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    max_cost_per_request: Optional[float] = None
    max_latency_seconds: Optional[float] = None
    min_quality_score: float = 0.0
    prefer_local: bool = False
    require_privacy: bool = False
    allowed_providers: List[str] = field(default_factory=list)
    blocked_providers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    selected_model: ModelCapability
    routing_strategy: RoutingStrategy
    fallback_chain: List[ModelCapability] = field(default_factory=list)
    estimated_cost: Optional[float] = None
    estimated_latency: Optional[float] = None
    confidence_score: float = 1.0
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ModelPerformanceMetrics:
    provider: str
    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency: float = 0.0
    total_cost: float = 0.0
    error_rate: float = 0.0
    quality_score: float = 1.0

    def update_success(self, latency: float, cost: float, quality: float = 1.0) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        if self.average_latency == 0:
            self.average_latency = latency
        else:
            self.average_latency = (
                self.average_latency * (self.successful_requests - 1) + latency
            ) / self.successful_requests
        self.total_cost += cost
        if self.quality_score == 1.0:
            self.quality_score = quality
        else:
            self.quality_score = (self.quality_score * (self.successful_requests - 1) + quality) / self.successful_requests

    def update_failure(self) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests else 0.0


# Cost heuristics in USD per 1K input tokens (order-of-magnitude only).
_PROVIDER_COST_PER_K = {
    "openai": 0.003, "anthropic": 0.003, "google": 0.00125, "xai": 0.003,
    "mistral": 0.0002, "groq": 0.0002, "deepseek": 0.0003, "openrouter": 0.002,
    "ollama": 0.0, "local": 0.0,
}


class EnhancedModelRouter:
    """Model selection with adaptive strategy, fallback chain and circuit breaker."""

    def __init__(
        self,
        capability_detector: Optional[CapabilityDetector] = None,
        providers: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
    ) -> None:
        self.capability_detector = capability_detector or CapabilityDetector()
        self.providers = providers or ["anthropic", "openai", "gemini", "ollama", "openrouter"]
        self.models = models or []
        self._routing_history: List[RoutingDecision] = []
        self._performance_metrics: Dict[Tuple[str, str], ModelPerformanceMetrics] = {}
        self._circuit_breaker: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # -- public API ---------------------------------------------------------
    def route_request(
        self,
        capability: CapabilityType,
        media_objects: Optional[List[MediaObject]] = None,
        task_description: str = "",
        preferences: Optional[RoutingPreference] = None,
        input_size_estimate: int = 1000,
    ) -> RoutingDecision:
        prefs = preferences or RoutingPreference()

        candidates = self._collect_candidates(capability)
        candidates = self._filter_by_preferences(candidates, prefs)
        if not candidates:
            raise ValueError(f"No available models for capability: {capability.value}")

        selected = self._select_best(candidates, prefs, input_size_estimate)
        fallback = self._build_fallback_chain(candidates, prefs, selected, input_size_estimate)

        decision = RoutingDecision(
            selected_model=selected,
            routing_strategy=prefs.strategy,
            fallback_chain=fallback,
            estimated_cost=self._estimate_cost(selected, input_size_estimate),
            estimated_latency=self._estimate_latency(selected),
            confidence_score=self._calculate_confidence(selected, prefs),
            reasoning=self._reasoning(selected, prefs, capability),
        )
        self._routing_history.append(decision)
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-500:]
        return decision

    def record_result(
        self,
        provider: str,
        model: str,
        success: bool,
        latency: float,
        cost: float = 0.0,
        quality: float = 1.0,
    ) -> None:
        """Feed observed results back so the router adapts (Phase 50)."""
        key = (provider, model)
        perf = self._performance_metrics.setdefault(key, ModelPerformanceMetrics(provider, model))
        if success:
            perf.update_success(latency, cost, quality)
        else:
            perf.update_failure()
        # Circuit breaker: 5 consecutive failures -> open for 60s
        cb = self._circuit_breaker.setdefault(
            key, {"failure_count": 0, "state": "closed", "next_attempt_time": 0.0}
        )
        if success:
            cb["failure_count"] = 0
            cb["state"] = "closed"
        else:
            cb["failure_count"] += 1
            if cb["failure_count"] >= 5:
                cb["state"] = "open"
                cb["next_attempt_time"] = time.time() + 60.0
        if cb["state"] == "open" and time.time() >= cb["next_attempt_time"]:
            cb["state"] = "half-open"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "routing_history_count": len(self._routing_history),
            "performance": {
                f"{k[0]}:{k[1]}": {
                    "total_requests": v.total_requests,
                    "success_rate": v.successful_requests / v.total_requests if v.total_requests else 0.0,
                    "average_latency": round(v.average_latency, 3),
                    "error_rate": round(v.error_rate, 3),
                }
                for k, v in self._performance_metrics.items()
            },
            "circuit_breakers": {
                f"{k[0]}:{k[1]}": v["state"] for k, v in self._circuit_breaker.items()
            },
        }

    # -- internals ----------------------------------------------------------
    def _collect_candidates(self, capability: CapabilityType) -> List[ModelCapability]:
        candidates: List[ModelCapability] = []
        for provider in self.providers:
            if self.models:
                for model in self.models:
                    profile = self.capability_detector.detect(provider, model)
                    if profile.supports(capability):
                        candidates.append(profile)
            else:
                # Try a small, well-known default per provider for each modality.
                defaults = _DEFAULT_MODELS.get(provider, [])
                for model in defaults:
                    profile = self.capability_detector.detect(provider, model)
                    if profile.supports(capability):
                        candidates.append(profile)
        return candidates

    def _filter_by_preferences(
        self, candidates: List[ModelCapability], prefs: RoutingPreference
    ) -> List[ModelCapability]:
        filtered: List[ModelCapability] = []
        for m in candidates:
            if prefs.allowed_providers and m.provider not in prefs.allowed_providers:
                continue
            if m.provider in prefs.blocked_providers:
                continue
            if prefs.require_privacy and not self._is_local_provider(m.provider):
                continue
            key = (m.provider, m.model)
            if key in self._circuit_breaker and self._circuit_breaker[key]["state"] == "open":
                continue
            perf = self._performance_metrics.get(key)
            if perf is not None and prefs.min_quality_score > 0 and perf.quality_score < prefs.min_quality_score:
                continue
            if perf is not None and perf.error_rate > 0.5:
                continue
            filtered.append(m)
        return filtered

    def _select_best(
        self, candidates: List[ModelCapability], prefs: RoutingPreference, input_size_estimate: int
    ) -> ModelCapability:
        def score(m: ModelCapability) -> float:
            cost = self._estimate_cost(m, input_size_estimate) or 0.0
            latency = self._estimate_latency(m) or 1.0
            is_local = 1.0 if self._is_local_provider(m.provider) else 0.0
            if prefs.strategy == RoutingStrategy.COST_FIRST:
                return -cost
            if prefs.strategy == RoutingStrategy.SPEED_FIRST:
                return -latency
            if prefs.strategy == RoutingStrategy.LOCAL_FIRST:
                return is_local * 10 - latency
            if prefs.strategy == RoutingStrategy.PRIVACY_FIRST:
                return is_local * 100 - latency
            if prefs.strategy == RoutingStrategy.QUALITY_FIRST:
                return -cost + latency * 0.001  # cheapest capable wins among capable
            # BALANCED: prefer local, then lower cost, then speed
            return is_local * 5 - cost * 100 - latency
        return max(candidates, key=score)

    def _build_fallback_chain(
        self,
        candidates: List[ModelCapability],
        prefs: RoutingPreference,
        selected: ModelCapability,
        input_size_estimate: int,
    ) -> List[ModelCapability]:
        others = [m for m in candidates if (m.provider, m.model) != (selected.provider, selected.model)]
        others.sort(key=lambda m: self._estimate_cost(m, input_size_estimate) or 0.0)
        return others[:3]

    def _estimate_cost(self, m: ModelCapability, input_tokens: int) -> Optional[float]:
        per_k = _PROVIDER_COST_PER_K.get(m.provider.lower())
        if per_k is None:
            return None
        return round(per_k * (input_tokens / 1000.0), 6)

    def _estimate_latency(self, m: ModelCapability) -> Optional[float]:
        perf = self._performance_metrics.get((m.provider, m.model))
        if perf is not None and perf.average_latency > 0:
            return round(perf.average_latency, 3)
        base = {"anthropic": 3.0, "openai": 2.5, "gemini": 1.5, "openrouter": 4.0, "ollama": 1.0}.get(
            m.provider.lower(), 3.0
        )
        return base

    def _calculate_confidence(self, m: ModelCapability, prefs: RoutingPreference) -> float:
        score = 1.0
        perf = self._performance_metrics.get((m.provider, m.model))
        if perf is not None:
            score *= max(0.1, 1.0 - perf.error_rate)
        if m.source == "heuristics":
            score *= 0.8
        if prefs.require_privacy and not self._is_local_provider(m.provider):
            score *= 0.5
        return round(max(0.0, min(1.0, score)), 3)

    @staticmethod
    def _is_local_provider(provider: str) -> bool:
        return provider.lower() in ("ollama", "local")

    def _reasoning(self, m: ModelCapability, prefs: RoutingPreference, cap: CapabilityType) -> str:
        bits = [f"selected {m.provider}:{m.model} for {cap.value}"]
        bits.append(f"strategy={prefs.strategy.value}")
        bits.append(f"capability_source={m.source}")
        if prefs.require_privacy:
            bits.append("privacy_required=True")
        return "; ".join(bits)


_DEFAULT_MODELS: Dict[str, List[str]] = {
    "anthropic": ["claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", "claude-sonnet-4-5"],
    "openai": ["gpt-4.1", "gpt-4o", "gpt-4o-mini"],
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    "xai": ["grok-4", "grok-3"],
    "mistral": ["mistral-large-latest"],
    "groq": ["llama-3.3-70b-versatile"],
    "deepseek": ["deepseek-chat"],
    "openrouter": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
    "ollama": ["llama3.2", "llama3.2-vision", "llava"],
}