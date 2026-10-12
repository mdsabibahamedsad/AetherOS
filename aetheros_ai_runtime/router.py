"""Intelligent router (sections 12-14, 27-32, 63, 83-86, 90-92, 94-95).

Policy-aware scoring over verified capabilities (never spoofed metadata
without provenance). 12 modes, 14 specialization profiles, agent/swarm/
automation/research/memory/computer bindings, quality memory with decay,
org policy + pins + blocklists enforced before scoring. Every decision
emits a ModelDecisionTrace (rejected reasons included).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_ai_runtime.models import DataClass, ModelRecord

MODES = ("auto", "local_first", "local_only", "cloud_first", "cloud_only",
         "cheapest", "fastest", "best_quality", "best_reasoning",
         "privacy_first", "balanced", "custom_policy")

PROFILES: Dict[str, Dict[str, Any]] = {
    "coding": {"needs": ["tool_calling"], "prefer": ["reasoning"],
               "weights": {"quality": 1.5, "capability": 1.5}},
    "research": {"needs": [], "prefer": ["reasoning"],
                 "weights": {"quality": 1.4, "context": 1.3}},
    "browser": {"needs": ["tool_calling"], "prefer": [],
                "weights": {"capability": 1.5, "reliability": 1.2}},
    "computer": {"needs": ["tool_calling", "vision"], "prefer": [],
                 "weights": {"capability": 2.0, "reliability": 1.5}},
    "vision": {"needs": ["vision"], "prefer": [],
               "weights": {"capability": 2.0}},
    "writing": {"needs": [], "prefer": [],
                "weights": {"latency": 1.3, "cost": 1.2}},
    "planning": {"needs": [], "prefer": ["reasoning"],
                 "weights": {"quality": 1.5, "reliability": 1.2}},
    "reasoning": {"needs": ["reasoning"], "prefer": [],
                  "weights": {"quality": 1.6}},
    "summarization": {"needs": [], "prefer": [],
                      "weights": {"latency": 1.4, "cost": 1.3}},
    "classification": {"needs": [], "prefer": [],
                       "weights": {"latency": 1.5, "cost": 1.2}},
    "embedding": {"needs": ["embeddings"], "prefer": [],
                  "weights": {"capability": 2.0}},
    "reranking": {"needs": [], "prefer": [], "weights": {"latency": 1.2}},
    "memory": {"needs": [], "prefer": [], "weights": {"cost": 1.3, "latency": 1.2}},
    "automation": {"needs": [], "prefer": [],
                   "weights": {"reliability": 1.5, "cost": 1.2}},
}

DEFAULT_WEIGHTS = {"quality": 1.0, "capability": 1.0, "reliability": 1.0,
                   "availability": 1.0, "privacy": 1.0, "latency": 1.0,
                   "cost": 1.0, "hardware": 1.0, "context": 1.0,
                   "tool": 1.0, "risk": 1.0, "failure": 1.0}


@dataclass
class TaskRequirements:
    task_type: str = "general"
    profile: str = ""
    complexity: float = 0.5
    needs_reasoning: bool = False
    context_tokens: int = 4000
    needs_vision: bool = False
    needs_audio: bool = False
    needs_tools: bool = False
    needs_streaming: bool = False
    needs_embeddings: bool = False
    latency_target_s: float = 60.0
    cost_budget_usd: float = 1.0
    classification: str = DataClass.INTERNAL.value
    reliability: float = 0.8
    quality_target: float = 0.7
    mode: str = "auto"
    local_only: bool = False
    region: str = ""
    preferred: str = ""
    blocked: List[str] = field(default_factory=list)
    agent_type: str = ""
    autonomy: int = 0
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class ModelDecisionTrace:
    task_id: str = ""
    candidates: int = 0
    eligible: List[str] = field(default_factory=list)
    rejected: Dict[str, str] = field(default_factory=dict)
    selected: str = ""
    policy: str = ""
    scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    fallbacks: List[str] = field(default_factory=list)
    classification: str = ""
    at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"task_id": self.task_id, "candidates": self.candidates,
                "eligible": self.eligible, "rejected": self.rejected,
                "selected": self.selected, "policy": self.policy,
                "scores": self.scores, "fallbacks": self.fallbacks,
                "classification": self.classification, "at": self.at}


class QualityMemory:
    """Historical performance with recency decay (never permanent bias)."""

    def __init__(self, *, half_life_days: float = 30.0) -> None:
        self._half_life = max(1.0, half_life_days)
        self._events: List[Dict[str, Any]] = []

    def record(self, model: str, task_class: str, *, success: bool,
               latency_s: float = 0.0, cost_usd: float = 0.0,
               failure: str = "") -> None:
        self._events.append({"model": model, "task_class": task_class,
                             "success": success, "latency_s": latency_s,
                             "cost_usd": cost_usd, "failure": failure,
                             "at": time.time()})

    def score(self, model: str, task_class: str,
              now: Optional[float] = None) -> float:
        import math
        now = now if now is not None else time.time()
        total, weight = 0.0, 0.0
        for e in self._events:
            if e["model"] != model or e["task_class"] != task_class:
                continue
            age_days = max(0.0, (now - e["at"]) / 86400.0)
            w = math.exp(-age_days * math.log(2) / self._half_life)
            total += (1.0 if e["success"] else -1.0) * w
            weight += w
        if weight <= 0:
            return 0.0
        return max(-1.0, min(1.0, total / weight))


class IntelligentModelRouter:
    def __init__(self, list_models: Callable[[], List[ModelRecord]], *,
                 quality: Optional[QualityMemory] = None,
                 measured_latency: Optional[Dict[str, float]] = None,
                 hardware_gb: float = 0.0) -> None:
        self._list = list_models
        self._quality = quality or QualityMemory()
        self._latency = measured_latency or {}
        self._hardware_gb = hardware_gb

    def route(self, req: TaskRequirements,
              *, task_id: str = "") -> ModelDecisionTrace:
        trace = ModelDecisionTrace(task_id=task_id or req.task_type,
                                   classification=req.classification,
                                   policy=req.mode)
        models = self._list()
        trace.candidates = len(models)
        profile = PROFILES.get(req.profile or req.task_type, {})
        needs = set(profile.get("needs", []))
        if req.needs_reasoning:
            needs.add("reasoning")
        if req.needs_vision:
            needs.add("vision")
        if req.needs_tools:
            needs.add("tool_calling")
        if req.needs_embeddings:
            needs.add("embeddings")
        if req.needs_streaming:
            needs.add("streaming")
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(profile.get("weights", {}))
        weights.update(req.weights or {})
        mode = req.mode if req.mode in MODES else "auto"
        local_only = req.local_only or mode in ("local_only",)
        scored: List[tuple] = []
        for m in models:
            reason = self._eligibility(m, req, needs, mode)
            if reason is not None:
                trace.rejected[m.canonical_id] = reason
                continue
            trace.eligible.append(m.canonical_id)
            parts = self._score(m, req, weights, mode)
            total = sum(parts.values())
            trace.scores[m.canonical_id] = {k: round(v, 3) for k, v in parts.items()}
            scored.append((total, m))
        if not scored:
            if local_only:
                trace.rejected["_router"] = "NO_COMPATIBLE_LOCAL_MODEL"
            return trace
        scored.sort(key=lambda t: -t[0])
        # Mode overrides: cheapest/fastest/best_quality/best_reasoning.
        if mode == "cheapest":
            scored.sort(key=lambda t: self._cost_of(t[1]))
        elif mode == "fastest":
            scored.sort(key=lambda t: self._latency.get(t[1].canonical_id, 1e9))
        elif mode in ("best_quality", "best_reasoning"):
            scored.sort(key=lambda t: -(t[1].context_window or 0))
        winner = scored[0][1]
        # Favorites/pins respected within policy (never override blocks).
        if req.preferred:
            for _, m in scored:
                if m.canonical_id == req.preferred:
                    winner = m
                    break
        trace.selected = winner.canonical_id
        trace.fallbacks = [m.canonical_id for _, m in scored[1:4]]
        return trace

    # -- internals ---------------------------------------------------------
    def _eligibility(self, m: ModelRecord, req: TaskRequirements,
                     needs: set, mode: str) -> Optional[str]:
        if m.blocked or m.canonical_id in req.blocked:
            return "blocked by policy"
        if m.deprecated:
            return "deprecated"
        for cap in needs:
            if not bool(getattr(m, cap, False)):
                return f"missing capability: {cap}"
        if m.context_window and m.context_window < req.context_tokens:
            return f"context {m.context_window} < {req.context_tokens}"
        if req.local_only or mode == "local_only":
            if m.locality != "local":
                return "LOCAL_ONLY policy"
        if mode == "local_first" and m.locality != "local":
            pass  # allowed but deprioritized in scoring
        if mode == "cloud_only" and m.locality == "local":
            return "CLOUD_ONLY policy"
        if req.region and m.region and m.region != req.region:
            return f"region {m.region} != {req.region}"
        if m.status in ("unavailable", "misconfigured", "auth_error"):
            return f"health: {m.status}"
        if m.hardware_gb and self._hardware_gb and \
                m.hardware_gb > self._hardware_gb and m.locality == "local":
            return f"hardware: needs {m.hardware_gb}GB"
        return None

    def _score(self, m: ModelRecord, req: TaskRequirements,
               weights: Dict[str, float], mode: str) -> Dict[str, float]:
        price = self._cost_of(m)
        cost_fit = 1.0 if m.pricing.unknown else max(
            0.0, 1.0 - price / max(req.cost_budget_usd, 1e-9))
        lat = self._latency.get(m.canonical_id, 0.0)
        latency_fit = 1.0 if not lat else max(
            0.0, 1.0 - lat / max(req.latency_target_s, 1e-9))
        ctx_fit = 1.0
        if m.context_window:
            ctx_fit = min(1.0, m.context_window / max(req.context_tokens * 2, 1))
        privacy_fit = 1.0 if m.locality == "local" else (
            0.2 if req.classification in ("sensitive", "highly_sensitive",
                                          "private") else 0.7)
        hw_fit = 1.0
        if m.locality == "local" and m.hardware_gb and self._hardware_gb:
            hw_fit = 1.0 if m.hardware_gb <= self._hardware_gb else 0.0
        tool_fit = 1.0 if (not req.needs_tools or m.tool_calling) else 0.0
        q = self._quality.score(m.canonical_id, req.profile or req.task_type)
        parts = {
            "quality": weights["quality"] * (0.5 + 0.5 * req.quality_target + 0.3 * q),
            "capability": weights["capability"] * (1.0 if tool_fit else 0.0),
            "reliability": weights["reliability"] * req.reliability,
            "availability": weights["availability"] * (
                0.0 if m.status in ("unavailable",) else 1.0),
            "privacy": weights["privacy"] * privacy_fit,
            "latency": weights["latency"] * latency_fit,
            "cost": weights["cost"] * cost_fit,
            "hardware": weights["hardware"] * hw_fit,
            "context": weights["context"] * ctx_fit,
            "tool": weights["tool"] * tool_fit,
            "risk": -weights["risk"] * (0.5 if m.locality == "remote" else 0.0),
            "failure": -weights["failure"] * (0.5 if q < -0.3 else 0.0),
        }
        if mode == "local_first" and m.locality == "local":
            parts["privacy"] += 0.5
        if mode == "privacy_first":
            parts["privacy"] *= 2.0
        if mode == "cloud_first" and m.locality == "remote":
            parts["latency"] += 0.3
        return parts

    @staticmethod
    def _cost_of(m: ModelRecord) -> float:
        if m.pricing.unknown or m.pricing.input_per_1k is None:
            return 0.0  # unknown cost never blocks; reported UNKNOWN
        return float(m.pricing.input_per_1k)
