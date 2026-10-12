"""Tests for aetheros_observability evaluation + cost tracking."""

import pytest

from aetheros_observability.cost import CostTracker, get_cost_tracker
from aetheros_observability.evaluation import (
    EvaluationService,
    TaskEvaluation,
    TaskOutcome,
    get_evaluation_service,
)


class TestEvaluationService:
    def test_record_result_success(self):
        svc = EvaluationService()
        eval_ = svc.record_result(task_id="t1", outcome=TaskOutcome.COMPLETED,
                                  duration_ms=1000, cost_usd=0.1,
                                  tool_usage=4, model_usage=2)
        assert eval_.task_id == "t1"
        assert eval_.outcome == TaskOutcome.COMPLETED
        assert len(svc.records()) == 1

    def test_success_score_and_failure_rate(self):
        svc = EvaluationService()
        svc.record_result(task_id="a", outcome=TaskOutcome.COMPLETED)
        svc.record_result(task_id="b", outcome=TaskOutcome.FAILED)
        svc.record_result(task_id="c", outcome=TaskOutcome.COMPLETED)
        assert svc.success_score() == pytest.approx(2 / 3, abs=0.001)
        assert svc.failure_rate() == pytest.approx(1 / 3, abs=0.001)

    def test_summary(self):
        svc = EvaluationService()
        svc.record_result(task_id="a", outcome=TaskOutcome.COMPLETED,
                          duration_ms=2000, cost_usd=0.05)
        svc.record_result(task_id="b", outcome=TaskOutcome.FAILED,
                          duration_ms=1000, cost_usd=0.01)
        summary = svc.summary()
        assert summary["total"] == 2
        assert summary["avg_latency_ms"] == 1500
        assert summary["total_cost_usd"] == 0.06

    def test_avg_latency(self):
        svc = EvaluationService()
        svc.record_result(task_id="a", outcome=TaskOutcome.COMPLETED,
                          duration_ms=100)
        svc.record_result(task_id="b", outcome=TaskOutcome.COMPLETED,
                          duration_ms=300)
        assert svc.avg_latency_ms() == 200

    def test_total_cost(self):
        svc = EvaluationService()
        svc.record_result(task_id="a", outcome=TaskOutcome.COMPLETED,
                          cost_usd=0.5)
        svc.record_result(task_id="b", outcome=TaskOutcome.FAILED,
                          cost_usd=0.25)
        assert svc.total_cost_usd() == 0.75


class TestCostTracker:
    def test_record_model_call_returns_estimate(self):
        tracker = CostTracker()
        estimate = tracker.record_model_call(
            model="gpt-4o", provider="openai",
            input_tokens=1000, output_tokens=500)
        assert estimate.estimated is True
        assert estimate.amount_usd > 0
        assert estimate.model == "gpt-4o"

    def test_total_cost_accumulates(self):
        tracker = CostTracker()
        tracker.record_model_call(model="gpt-4o", input_tokens=1000,
                                  output_tokens=500)
        tracker.record_model_call(model="gpt-4o", input_tokens=1000,
                                  output_tokens=500)
        assert tracker.total_cost() > 0

    def test_model_cost_aggregation(self):
        tracker = CostTracker()
        tracker.record_model_call(model="model-a", input_tokens=100,
                                  output_tokens=100)
        assert tracker.model_cost("model-a") > 0
        assert tracker.model_cost("unknown-model") == 0.0

    def test_summary_marked_estimated(self):
        tracker = CostTracker()
        tracker.record_model_call(model="gpt-4o", input_tokens=500,
                                  output_tokens=250)
        summary = tracker.summary()
        assert "total_estimated_usd" in summary
        assert "note" in summary


class TestSingletons:
    def test_evaluation_singleton(self):
        assert get_evaluation_service() is get_evaluation_service()

    def test_cost_singleton(self):
        assert get_cost_tracker() is get_cost_tracker()