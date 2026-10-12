"""Cost tracking — estimated cost aggregation for agents, missions, models.

Cost estimation delegates to the existing AetherOS pricing engine
(``agent.usage_pricing.estimate_usage_cost``) and is always clearly marked
``ESTIMATED`` unless exact provider billing data exists.  Cost figures are
never presented as exact billing.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from aetheros_observability.metrics import get_unified_metrics


@dataclass
class CostEstimate:
    """A single cost estimate — always ESTIMATED unless ``exact`` is true."""

    amount_usd: float = 0.0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    cached_cost_usd: float = 0.0
    estimated: bool = True
    currency: str = "USD"
    model: str = ""
    provider: str = ""
    status: str = "estimated"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount_usd": round(self.amount_usd, 6),
            "input_cost_usd": round(self.input_cost_usd, 6),
            "output_cost_usd": round(self.output_cost_usd, 6),
            "cached_cost_usd": round(self.cached_cost_usd, 6),
            "estimated": self.estimated,
            "currency": self.currency,
            "model": self.model,
            "provider": self.provider,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class CostTracker:
    """Aggregates per-model, per-agent, per-mission estimated costs."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._model_costs: Dict[str, float] = defaultdict(float)
        self._agent_costs: Dict[str, float] = defaultdict(float)
        self._mission_costs: Dict[str, float] = defaultdict(float)
        self._session_costs: Dict[str, float] = defaultdict(float)
        self._calls: Dict[str, int] = defaultdict(int)

    def estimate(
        self,
        *,
        model: str,
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> CostEstimate:
        """Estimate cost for a model call using the canonical pricing engine."""
        try:
            from agent.usage_pricing import CanonicalUsage, estimate_usage_cost
            usage = CanonicalUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
            )
            result = estimate_usage_cost(model, usage, provider=provider or None)
            amount = float(result.amount_usd) if result.amount_usd is not None else 0.0
            status = result.status
            # A real (non-unknown) result is authoritative; when the pricing
            # engine has no entry for the model it reports "unknown" and we
            # fall back to our rough estimator so cost is never silently zero.
            if status == "unknown" or amount <= 0.0:
                amount = _fallback_cost(input_tokens, output_tokens,
                                        cache_read_tokens + cache_write_tokens)
                status = "estimated"
            estimated = status == "estimated"
        except Exception:
            amount = _fallback_cost(input_tokens, output_tokens, cache_read_tokens)
            status = "estimated"
            estimated = True

        est = CostEstimate(
            amount_usd=amount,
            input_cost_usd=_allocated(amount, input_tokens, output_tokens,
                                      cache_read_tokens + cache_write_tokens),
            output_cost_usd=_allocated(amount, output_tokens, input_tokens,
                                       cache_read_tokens + cache_write_tokens),
            cached_cost_usd=_allocated(amount, cache_read_tokens + cache_write_tokens,
                                       input_tokens + output_tokens, 0),
            estimated=estimated,
            model=model,
            provider=provider,
            status=status,
        )
        return est

    def record_model_call(
        self,
        *,
        model: str,
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        agent_id: str = "",
        mission_id: str = "",
        session_id: str = "",
    ) -> CostEstimate:
        """Record a model call and aggregate its estimated cost."""
        est = self.estimate(
            model=model, provider=provider, input_tokens=input_tokens,
            output_tokens=output_tokens, cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )
        key = f"{model}" if not provider else f"{provider}/{model}"
        with self._lock:
            self._model_costs[key] += est.amount_usd
            self._calls[key] += 1
            if agent_id:
                self._agent_costs[agent_id] += est.amount_usd
            if mission_id:
                self._mission_costs[mission_id] += est.amount_usd
            if session_id:
                self._session_costs[session_id] += est.amount_usd
        get_unified_metrics().increment(
            "aetheros.cost.estimated_usd", est.amount_usd,
            {"model": model or "unknown", "provider": provider or "unknown"},
        )
        return est

    def model_cost(self, model: str, provider: str = "") -> float:
        key = f"{model}" if not provider else f"{provider}/{model}"
        with self._lock:
            return round(self._model_costs.get(key, 0.0), 6)

    def agent_cost(self, agent_id: str) -> float:
        with self._lock:
            return round(self._agent_costs.get(agent_id, 0.0), 6)

    def mission_cost(self, mission_id: str) -> float:
        with self._lock:
            return round(self._mission_costs.get(mission_id, 0.0), 6)

    def session_cost(self, session_id: str) -> float:
        with self._lock:
            return round(self._session_costs.get(session_id, 0.0), 6)

    def total_cost(self) -> float:
        with self._lock:
            return round(sum(self._model_costs.values()), 6)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_estimated_usd": round(sum(self._model_costs.values()), 6),
                "models": {
                    k: {"cost_usd": round(v, 6), "calls": self._calls.get(k, 0)}
                    for k, v in sorted(self._model_costs.items(), key=lambda kv: -kv[1])
                },
                "agents": {k: round(v, 6) for k, v in self._agent_costs.items()},
                "missions": {k: round(v, 6) for k, v in self._mission_costs.items()},
                "sessions": {k: round(v, 6) for k, v in self._session_costs.items()},
                "note": "All amounts are ESTIMATED unless provider billing data exists.",
            }


def _fallback_cost(input_tokens: int, output_tokens: int, cached_tokens: int) -> float:
    """Rough USD fallback when the pricing engine is unavailable."""
    return (input_tokens / 1_000_000 * 2.5) + (output_tokens / 1_000_000 * 10.0) + \
           (cached_tokens / 1_000_000 * 0.3)


def _allocated(total: float, this: int, *others: int) -> float:
    denom = this + sum(others)
    if denom <= 0 or total == 0:
        return 0.0
    return round(total * (this / denom), 6)


_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Return the process-wide CostTracker singleton."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker