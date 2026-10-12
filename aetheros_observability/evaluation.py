"""Agent / task evaluation framework.

Defines measurable task outcomes and records them for regression and
quality evaluation.  Subjective quality is never treated as objective
truth — each outcome maps to a well-defined signal.
"""

from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TaskOutcome(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    USER_ACCEPTED = "user_accepted"
    USER_REJECTED = "user_rejected"
    TOOL_SUCCESS = "tool_success"
    VALIDATION_SUCCESS = "validation_success"
    POLICY_VIOLATION = "policy_violation"


#: Outcomes that count as "success" for the success-score.
_SUCCESS_OUTCOMES = frozenset(
    {
        TaskOutcome.COMPLETED,
        TaskOutcome.USER_ACCEPTED,
        TaskOutcome.TOOL_SUCCESS,
        TaskOutcome.VALIDATION_SUCCESS,
    }
)


@dataclass
class TaskEvaluation:
    task_id: str
    outcome: TaskOutcome
    agent_id: str = ""
    mission_id: str = ""
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    error_type: str = ""
    tool_usage: int = 0
    model_usage: int = 0
    user_feedback: float = 0.0      # 0..1, 0 = none recorded
    policy_violation: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "outcome": self.outcome.value,
            "agent_id": self.agent_id,
            "mission_id": self.mission_id,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
            "error_type": self.error_type,
            "tool_usage": self.tool_usage,
            "model_usage": self.model_usage,
            "user_feedback": self.user_feedback,
            "policy_violation": self.policy_violation,
            "timestamp": self.timestamp,
        }


class EvaluationService:
    """Records task outcomes and computes success scores (Step 49-51).

    Usage::

        es = get_evaluation_service()
        es.record(TaskEvaluation(task_id="t1", outcome=TaskOutcome.COMPLETED))
        print(es.success_score())
        print(es.summary())
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: List[TaskEvaluation] = []
        self._max_records = 5000

    def record(self, evaluation: TaskEvaluation) -> None:
        with self._lock:
            self._records.append(evaluation)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

    def record_result(
        self,
        *,
        task_id: str,
        outcome: TaskOutcome,
        agent_id: str = "",
        mission_id: str = "",
        duration_ms: float = 0.0,
        cost_usd: float = 0.0,
        error_type: str = "",
        tool_usage: int = 0,
        model_usage: int = 0,
        user_feedback: float = 0.0,
        policy_violation: str = "",
    ) -> TaskEvaluation:
        evaluation = TaskEvaluation(
            task_id=task_id, outcome=outcome, agent_id=agent_id,
            mission_id=mission_id, duration_ms=duration_ms,
            cost_usd=cost_usd, error_type=error_type,
            tool_usage=tool_usage, model_usage=model_usage,
            user_feedback=user_feedback, policy_violation=policy_violation,
        )
        self.record(evaluation)
        return evaluation

    def success_score(self, *, agent_id: str = "",
                      mission_id: str = "") -> float:
        """Return the success ratio (0..1) for a scope."""
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        if not records:
            return 1.0
        successes = sum(1 for r in records if r.outcome in _SUCCESS_OUTCOMES)
        return round(successes / len(records), 4)

    def failure_rate(self, *, agent_id: str = "", mission_id: str = "") -> float:
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        if not records:
            return 0.0
        failures = sum(1 for r in records
                       if r.outcome in (TaskOutcome.FAILED, TaskOutcome.POLICY_VIOLATION))
        return round(failures / len(records), 4)

    def avg_latency_ms(self, *, agent_id: str = "", mission_id: str = "") -> float:
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        if not records:
            return 0.0
        return round(sum(r.duration_ms for r in records) / len(records), 2)

    def total_cost_usd(self, *, agent_id: str = "", mission_id: str = "") -> float:
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        return round(sum(r.cost_usd for r in records), 6)

    def summary(self, *, agent_id: str = "", mission_id: str = "") -> Dict[str, Any]:
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        outcome_counts: Dict[str, int] = {}
        for r in records:
            outcome_counts[r.outcome.value] = outcome_counts.get(r.outcome.value, 0) + 1
        return {
            "total": len(records),
            "success_score": self.success_score(agent_id=agent_id, mission_id=mission_id),
            "failure_rate": self.failure_rate(agent_id=agent_id, mission_id=mission_id),
            "avg_latency_ms": self.avg_latency_ms(agent_id=agent_id, mission_id=mission_id),
            "total_cost_usd": self.total_cost_usd(agent_id=agent_id, mission_id=mission_id),
            "by_outcome": outcome_counts,
            "policy_violations": sum(1 for r in records if r.outcome == TaskOutcome.POLICY_VIOLATION),
        }

    def records(self, *, agent_id: str = "", mission_id: str = "",
                limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            records = self._filtered(agent_id, mission_id)
        return [r.to_dict() for r in records[-limit:]]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def _filtered(self, agent_id: str, mission_id: str) -> List[TaskEvaluation]:
        records = self._records
        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]
        if mission_id:
            records = [r for r in records if r.mission_id == mission_id]
        return records


_evaluation_service: Optional[EvaluationService] = None


def get_evaluation_service() -> EvaluationService:
    """Return the process-wide EvaluationService singleton."""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service