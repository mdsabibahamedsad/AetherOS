"""Trend tracking + deterioration alerts (P93-94)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TrendPoint:
    ts: float
    value: float


@dataclass
class TrendAlert:
    metric: str
    kind: str              # deterioration | spike | anomaly
    detail: str
    at: float = field(default_factory=time.time)


class TrendTracker:
    """Append-only metric series with deterioration detection.

    Deterioration = the recent-window mean is worse than the prior-window
    mean by more than ``threshold`` (direction-aware per metric).
    """

    def __init__(self, *,
                 lower_is_better: Dict[str, bool] = None,
                 deterioration_threshold: float = 0.10,
                 min_points: int = 4):
        self.series: Dict[str, List[TrendPoint]] = {}
        self.lower_is_better = dict(lower_is_better or {
            "latency_p95_ms": True,
            "error_rate": True,
            "cost_usd": True,
            "failure_rate": True,
        })
        self.threshold = deterioration_threshold
        self.min_points = min_points
        self.alerts: List[TrendAlert] = []

    def record(self, metric: str, value: float,
               at: Optional[float] = None) -> Optional[TrendAlert]:
        point = TrendPoint(ts=at if at is not None else time.time(),
                           value=value)
        self.series.setdefault(metric, []).append(point)
        alert = self._check(metric)
        if alert:
            self.alerts.append(alert)
        return alert

    def _check(self, metric: str) -> Optional[TrendAlert]:
        pts = self.series.get(metric, [])
        if len(pts) < self.min_points:
            return None
        half = len(pts) // 2
        prior = [p.value for p in pts[:-half]]
        recent = [p.value for p in pts[-half:]]
        prior_mean = sum(prior) / len(prior)
        recent_mean = sum(recent) / len(recent)
        if prior_mean == 0:
            return None
        change = (recent_mean - prior_mean) / abs(prior_mean)
        worse = change > self.threshold if self.lower_is_better.get(metric) \
            else change < -self.threshold
        if worse:
            return TrendAlert(
                metric=metric, kind="deterioration",
                detail=f"recent mean {recent_mean:.3f} vs prior "
                       f"{prior_mean:.3f} ({change:+.1%})",
            )
        return None

    def latest(self, metric: str) -> Optional[TrendPoint]:
        pts = self.series.get(metric, [])
        return pts[-1] if pts else None

    def summary(self) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for metric, pts in self.series.items():
            values = [p.value for p in pts]
            out[metric] = {
                "points": len(values),
                "first": values[0],
                "latest": values[-1],
            }
        return out
