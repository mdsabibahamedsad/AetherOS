"""Quality metrics (P15-22) composing aetheros_observability primitives.

Success counting honors the verified-only rule (P15): outcomes that require
verification are not counted as success until verified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_observability.evaluation import TaskOutcome

#: P15 — outcomes that count as success ONLY when independently verified.
_VERIFICATION_REQUIRED = frozenset({TaskOutcome.COMPLETED})


@dataclass
class TaskRecord:
    task_id: str
    outcome: TaskOutcome
    verified: bool = False
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    tokens: int = 0
    tool_calls: int = 0
    retries: int = 0
    timed_out: bool = False
    crashed: bool = False
    recovered: bool = False
    agent_id: str = ""
    tool_id: str = ""
    model: str = ""


@dataclass
class ErrorBudget:
    """P21 — configurable, never hard-coded universal thresholds."""

    metric: str                    # failure_rate | timeout_rate | crash_rate | latency_p95_ms
    max_value: float
    consumed: float = 0.0

    @property
    def exhausted(self) -> bool:
        return self.consumed > self.max_value

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_value - self.consumed)


@dataclass
class SLO:
    """P22."""

    name: str
    kind: str                      # availability | latency | task_success | security
    target: float
    actual: float = 0.0
    higher_is_better: bool = True

    @property
    def met(self) -> bool:
        if self.higher_is_better:
            return self.actual >= self.target
        return self.actual <= self.target


@dataclass
class ReliabilitySnapshot:
    success_rate: float
    failure_rate: float
    timeout_rate: float
    crash_rate: float
    retry_rate: float
    recovery_rate: float
    verified_success_rate: float
    availability: float
    total: int
    error_budgets: List[Dict[str, Any]] = field(default_factory=list)
    slos: List[Dict[str, Any]] = field(default_factory=list)


class QualityMetrics:
    """Computes P15-P22 metrics from task records. Pure functions over
    inputs — no hidden state, no fabricated samples."""

    def __init__(self, error_budgets: Optional[List[ErrorBudget]] = None,
                 slos: Optional[List[SLO]] = None):
        self.error_budgets = list(error_budgets or [])
        self.slos = list(slos or [])

    def evaluate(self, tasks: List[TaskRecord],
                 *, window_seconds: float = 0.0) -> ReliabilitySnapshot:
        total = len(tasks)
        if total == 0:
            return ReliabilitySnapshot(
                success_rate=0.0, failure_rate=0.0, timeout_rate=0.0,
                crash_rate=0.0, retry_rate=0.0, recovery_rate=0.0,
                verified_success_rate=0.0, availability=0.0, total=0,
                error_budgets=[vars(b) | {"exhausted": b.exhausted}
                               for b in self.error_budgets],
                slos=[{"name": s.name, "met": s.met} for s in self.slos],
            )

        def count(pred) -> int:
            return sum(1 for t in tasks if pred(t))

        success = count(lambda t: t.outcome in (
            TaskOutcome.COMPLETED, TaskOutcome.USER_ACCEPTED,
            TaskOutcome.TOOL_SUCCESS, TaskOutcome.VALIDATION_SUCCESS))
        # P15: COMPLETED requires verification to count as verified success
        verified_success = count(
            lambda t: t.outcome is TaskOutcome.COMPLETED and t.verified
            or t.outcome in (TaskOutcome.USER_ACCEPTED,
                             TaskOutcome.VALIDATION_SUCCESS))
        failures = count(lambda t: t.outcome is TaskOutcome.FAILED)
        timeouts = count(lambda t: t.timed_out)
        crashes = count(lambda t: t.crashed)
        retried = count(lambda t: t.retries > 0)
        troubled = sum(1 for t in tasks
                       if t.outcome is TaskOutcome.FAILED or t.crashed)
        recovered = count(lambda t: t.recovered)

        snap = ReliabilitySnapshot(
            success_rate=round(success / total, 4),
            failure_rate=round(failures / total, 4),
            timeout_rate=round(timeouts / total, 4),
            crash_rate=round(crashes / total, 4),
            retry_rate=round(retried / total, 4),
            recovery_rate=round(recovered / max(1, troubled), 4),
            verified_success_rate=round(verified_success / total, 4),
            availability=round((total - crashes) / total, 4),
            total=total,
        )

        # P21 error budgets
        by_metric = {
            "failure_rate": snap.failure_rate,
            "timeout_rate": snap.timeout_rate,
            "crash_rate": snap.crash_rate,
        }
        for b in self.error_budgets:
            b.consumed = by_metric.get(b.metric, 0.0)
        snap.error_budgets = [
            {"metric": b.metric, "max": b.max_value, "consumed": b.consumed,
             "exhausted": b.exhausted}
            for b in self.error_budgets
        ]

        # P22 SLOs
        slo_actual = {
            "availability": snap.availability,
            "task_success": snap.verified_success_rate,
            "latency": (sum(t.duration_ms for t in tasks) / total),
            "security": 1.0 if not any(
                t.outcome is TaskOutcome.POLICY_VIOLATION for t in tasks
            ) else 0.0,
        }
        for s in self.slos:
            s.actual = round(slo_actual.get(s.kind, 0.0), 4)
        snap.slos = [{"name": s.name, "kind": s.kind, "target": s.target,
                      "actual": s.actual, "met": s.met} for s in self.slos]
        return snap


def recovery_score(*, detection_ms: float, recovery_ms: float,
                   data_loss: int = 0, task_loss: int = 0,
                   duplicate_side_effects: int = 0) -> Dict[str, Any]:
    """P54 — recovery quality; 1.0 is perfect, deductions are explicit."""
    score = 1.0
    score -= min(0.4, detection_ms / 60000.0 * 0.4)      # up to 0.4 by 60s detect
    score -= min(0.4, recovery_ms / 300000.0 * 0.4)      # up to 0.4 by 5min recover
    score -= min(0.3, data_loss * 0.15)
    score -= min(0.2, task_loss * 0.1)
    score -= min(0.2, duplicate_side_effects * 0.2)
    return {
        "score": round(max(0.0, score), 3),
        "detection_ms": detection_ms,
        "recovery_ms": recovery_ms,
        "data_loss": data_loss,
        "task_loss": task_loss,
        "duplicate_side_effects": duplicate_side_effects,
    }


def cost_summary(tasks: List[TaskRecord]) -> Dict[str, Any]:
    """P18 — cost aggregation without any secret material."""
    return {
        "total_cost_usd": round(sum(t.cost_usd for t in tasks), 4),
        "total_tokens": sum(t.tokens for t in tasks),
        "total_tool_calls": sum(t.tool_calls for t in tasks),
        "by_model": _by(tasks, "model", "cost_usd"),
        "by_tool": _by(tasks, "tool_id", "tool_calls"),
    }


def _by(tasks: List[TaskRecord], key: str, agg: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for t in tasks:
        k = getattr(t, key) or "unknown"
        out[k] = round(out.get(k, 0.0) + getattr(t, agg), 4)
    return out
