"""Monitoring (Phase L, §52-53, §121, §124, §150-155): drift detection,
eval health/saturation, metric-integrity checks, scorecards (never one
misleading score, §150), trends, learning velocity, regression rate.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .models import DriftEvent, TrialResult


class DriftDetector:
    def __init__(self, rel_threshold: float = 0.2):
        self.rel_threshold = rel_threshold
        self.baselines: Dict[str, float] = {}
        self.events: List[DriftEvent] = []

    def set_baseline(self, metric: str, value: float) -> None:
        self.baselines[metric] = value

    def observe(self, kind: str, metric: str, value: float) -> Optional[DriftEvent]:
        base = self.baselines.get(metric)
        if base is None:
            self.baselines[metric] = value
            return None
        denom = abs(base) if base else 1.0
        if abs(value - base) / denom >= self.rel_threshold:
            ev = DriftEvent(kind=kind, metric=metric, baseline=base,
                            observed=value, threshold=self.rel_threshold)
            self.events.append(ev)
            return ev
        return None


def eval_health(success_rates: List[float]) -> Dict[str, Any]:
    """Saturation: a suite at ~100% stops measuring improvement (§53)."""
    if not success_rates:
        return {"pass_rate": 0.0, "saturated": False}
    mean = statistics.mean(success_rates)
    return {"pass_rate": round(mean, 4),
            "saturated": mean >= 0.98,
            "stale": False,
            "recommendation": "retire to regression; add capability tasks"
            if mean >= 0.98 else "healthy"}


def metric_integrity(before: Dict[str, Any],
                     after: Dict[str, Any]) -> Dict[str, Any]:
    """§121: metric improved but real outcome degraded?"""
    metric_up = after.get("target_metric", 0) > before.get("target_metric", 0)
    outcome_down = after.get("success_rate", 1) < before.get("success_rate", 1)
    gaming = bool(metric_up and outcome_down)
    return {"gaming_suspected": gaming,
            "detail": "target metric up while success down" if gaming
            else "consistent"}


class Scorecards:
    """Multi-dimensional scorecards (§101-105, §150). No single score."""

    @staticmethod
    def model(trials: List[TrialResult]) -> Dict[str, Any]:
        n = len(trials)
        return {"trials": n,
                "success_rate": sum(t.passed for t in trials) / n if n
                else 0.0,
                "mean_latency_ms": round(statistics.mean(
                    [t.latency_ms for t in trials]), 2) if trials else 0.0,
                "total_tokens": sum(t.tokens for t in trials),
                "tool_calls": sum(t.tool_calls for t in trials)}

    @staticmethod
    def trends(snapshots: List[Dict[str, float]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key in {k for s in snapshots for k in s}:
            vals = [s[key] for s in snapshots if key in s]
            out[key] = {"first": vals[0], "last": vals[-1],
                        "delta": round(vals[-1] - vals[0], 4)}
        return out

    @staticmethod
    def regression_rate(introduced: int, resolved: int) -> Dict[str, Any]:
        flag = introduced > resolved
        return {"introduced": introduced, "resolved": resolved,
                "net": introduced - resolved,
                "flagged": flag,
                "note": "creates more regressions than it fixes"
                if flag else "healthy"}
