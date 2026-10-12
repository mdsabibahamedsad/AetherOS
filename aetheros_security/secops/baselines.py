"""
Behavior baselines for anomaly detection.

The SecOps layer builds deterministic per-actor behavior baselines from bus
events (tool-call rates, network egress, file deletes, resource usage, cost).
A new sample is compared against the baseline with a simple deviation score
(z-score approximation).  Baselines are versioned and can be re-learned;
learning updates require explicit approval (see the learning loop module).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BaselineStats:
    """Deterministic statistics for one behavior key."""

    key: str
    count: int = 0
    total: float = 0.0
    total_sq: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    version: int = 1
    learned_at: float = field(default_factory=time.time)

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.total_sq += value * value
        if self.count == 1:
            self.min_value = self.max_value = value
        else:
            self.min_value = min(self.min_value, value)
            self.max_value = max(self.max_value, value)

    @property
    def mean(self) -> float:
        return (self.total / self.count) if self.count else 0.0

    @property
    def stddev(self) -> float:
        if self.count < 2:
            return 0.0
        variance = max(0.0, (self.total_sq / self.count) - (self.mean ** 2))
        return variance ** 0.5

    def deviation(self, value: float) -> float:
        """Return a normalized deviation score (0-100)."""
        if self.count == 0:
            return 0.0
        if self.stddev == 0.0:
            # Constant baseline: any meaningful change is a deviation.
            if value == self.mean:
                return 0.0
            scale = abs(self.mean) if self.mean else 1.0
            return min(100.0, abs(value - self.mean) / scale * 100.0)
        z = abs(value - self.mean) / self.stddev
        # Map z to a 0-100 score: z=0 -> 0, z=3 -> ~90, z>=5 -> 100.
        score = min(100.0, z / 5.0 * 100.0)
        return round(score, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "count": self.count,
            "mean": round(self.mean, 4),
            "stddev": round(self.stddev, 4),
            "min": self.min_value,
            "max": self.max_value,
            "version": self.version,
            "learned_at": self.learned_at,
        }


class BehaviorBaselines:
    """Per-actor deterministic behavior baselines.

    Usage::

        baselines = BehaviorBaselines()
        baselines.observe("tool_call", actor="agent-1", value=5)
        baselines.observe("tool_call", actor="agent-1", value=7)
        anomaly = baselines.score("tool_call", actor="agent-1", value=50)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._baselines: Dict[str, Dict[str, BaselineStats]] = {}
        self._anomaly_threshold = 70.0  # score above this = anomaly

    def _key(self, behavior: str, actor: str) -> str:
        return f"{behavior}:{actor}"

    def observe(self, behavior: str, *, actor: str = "",
                value: float = 1.0) -> None:
        """Feed a sample into the baseline for behavior+actor."""
        key = self._key(behavior, actor or "unknown")
        with self._lock:
            bucket = self._baselines.setdefault(key, {})
            bucket.setdefault("_", BaselineStats(key=key)).observe(value)

    def score(self, behavior: str, *, actor: str = "",
              value: float = 1.0) -> float:
        """Return the deviation score (0-100) for a sample."""
        key = self._key(behavior, actor or "unknown")
        with self._lock:
            bucket = self._baselines.get(key)
            if not bucket or "_" not in bucket:
                return 0.0
            return bucket["_"].deviation(value)

    def is_anomalous(self, behavior: str, *, actor: str = "",
                     value: float = 1.0,
                     threshold: Optional[float] = None) -> bool:
        thr = threshold if threshold is not None else self._anomaly_threshold
        return self.score(behavior, actor=actor, value=value) >= thr

    # ------------------------------------------------------------------
    # Versioning / learning
    # ------------------------------------------------------------------

    def bump_version(self, behavior: str, actor: str = "") -> bool:
        key = self._key(behavior, actor or "unknown")
        with self._lock:
            bucket = self._baselines.get(key)
            if not bucket or "_" not in bucket:
                return False
            bucket["_"].version += 1
            return True

    def reset(self, behavior: Optional[str] = None, actor: Optional[str] = None) -> int:
        """Reset baselines (optionally scoped). Returns number reset."""
        cleared = 0
        with self._lock:
            if behavior is None:
                cleared = len(self._baselines)
                self._baselines.clear()
                return cleared
            key = self._key(behavior, actor or "unknown")
            if key in self._baselines:
                del self._baselines[key]
                cleared = 1
        return cleared

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            entries = {k: v["_"].to_dict() for k, v in self._baselines.items()
                       if "_" in v}
        return {
            "count": len(entries),
            "baselines": entries,
            "anomaly_threshold": self._anomaly_threshold,
        }

    def set_anomaly_threshold(self, threshold: float) -> None:
        self._anomaly_threshold = max(0.0, min(100.0, threshold))


# Global baselines
_baselines: Optional[BehaviorBaselines] = None


def get_behavior_baselines() -> BehaviorBaselines:
    """Return the process-wide BehaviorBaselines singleton."""
    global _baselines
    if _baselines is None:
        _baselines = BehaviorBaselines()
    return _baselines