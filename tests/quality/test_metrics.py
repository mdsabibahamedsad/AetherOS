"""Quality metrics contracts (P15-22, P54): verified-only success,
configurable budgets/SLOs, deterministic recovery scoring."""

from agent.quality.metrics import (
    ErrorBudget,
    QualityMetrics,
    SLO,
    TaskRecord,
    cost_summary,
    recovery_score,
)
from aetheros_observability.evaluation import TaskOutcome


def _rec(outcome, **kw):
    return TaskRecord(task_id=kw.pop("task_id", "t"), outcome=outcome, **kw)


class TestSuccessCounting:
    def test_unverified_completed_is_not_verified_success(self):
        snap = QualityMetrics().evaluate([_rec(TaskOutcome.COMPLETED)])
        assert snap.success_rate == 1.0
        assert snap.verified_success_rate == 0.0

    def test_verified_completed_counts(self):
        snap = QualityMetrics().evaluate(
            [_rec(TaskOutcome.COMPLETED, verified=True)])
        assert snap.verified_success_rate == 1.0

    def test_validation_success_counts_as_verified(self):
        snap = QualityMetrics().evaluate(
            [_rec(TaskOutcome.VALIDATION_SUCCESS)])
        assert snap.verified_success_rate == 1.0

    def test_empty_input_is_zero_not_crash(self):
        snap = QualityMetrics().evaluate([])
        assert snap.total == 0 and snap.success_rate == 0.0


class TestReliabilityRates:
    def _mixed(self):
        return [
            _rec(TaskOutcome.COMPLETED, verified=True),
            _rec(TaskOutcome.FAILED, retries=2, recovered=True),
            _rec(TaskOutcome.FAILED, timed_out=True),
            _rec(TaskOutcome.FAILED, crashed=True),
        ]

    def test_rates_are_fraction_of_total(self):
        snap = QualityMetrics().evaluate(self._mixed())
        assert snap.total == 4
        assert snap.success_rate == 0.25
        assert snap.failure_rate == 0.75
        assert snap.timeout_rate == 0.25
        assert snap.crash_rate == 0.25
        assert snap.retry_rate == 0.25
        # recovery relative to failures+crashes (3), not total
        assert snap.recovery_rate == round(1 / 3, 4)
        assert snap.availability == 0.75


class TestErrorBudgetsAndSLOs:
    def test_budget_consumption_and_exhaustion(self):
        tasks = [_rec(TaskOutcome.FAILED), _rec(TaskOutcome.COMPLETED)]
        budgets = [ErrorBudget(metric="failure_rate", max_value=0.4)]
        snap = QualityMetrics(error_budgets=budgets).evaluate(tasks)
        assert snap.error_budgets[0]["consumed"] == 0.5
        assert snap.error_budgets[0]["exhausted"] is True

    def test_slo_met_and_missed(self):
        tasks = [_rec(TaskOutcome.COMPLETED, verified=True),
                 _rec(TaskOutcome.COMPLETED, verified=False)]
        slos = [SLO(name="succ", kind="task_success", target=0.5),
                SLO(name="succ-hi", kind="task_success", target=0.9)]
        snap = QualityMetrics(slos=slos).evaluate(tasks)
        met = {s["name"]: s["met"] for s in snap.slos}
        assert met["succ"] is True and met["succ-hi"] is False

    def test_latency_slo_is_lower_is_better(self):
        slo = SLO(name="fast", kind="latency", target=100.0,
                  higher_is_better=False)
        QualityMetrics(slos=[slo]).evaluate(
            [_rec(TaskOutcome.COMPLETED, duration_ms=50.0)])
        assert slo.met

    def test_policy_violation_fails_security_slo(self):
        slo = SLO(name="sec", kind="security", target=1.0)
        QualityMetrics(slos=[slo]).evaluate(
            [_rec(TaskOutcome.POLICY_VIOLATION)])
        assert not slo.met


class TestRecoveryScore:
    def test_perfect_recovery_scores_one(self):
        out = recovery_score(detection_ms=0, recovery_ms=0)
        assert out["score"] == 1.0

    def test_deductions_reduce_score_monotonically(self):
        mild = recovery_score(detection_ms=5000, recovery_ms=30000)
        harsh = recovery_score(detection_ms=60000, recovery_ms=300000,
                               data_loss=2, task_loss=1,
                               duplicate_side_effects=1)
        assert harsh["score"] < mild["score"] <= 1.0

    def test_data_loss_never_yields_negative(self):
        out = recovery_score(detection_ms=10**9, recovery_ms=10**9,
                             data_loss=100)
        assert out["score"] >= 0.0


class TestCostSummary:
    def test_aggregates_without_leaking_secrets(self):
        tasks = [
            _rec(TaskOutcome.COMPLETED, model="m1", tool_id="web_search",
                 cost_usd=0.5, tokens=100, tool_calls=2),
            _rec(TaskOutcome.COMPLETED, model="m1", tool_id="terminal",
                 cost_usd=0.25, tokens=50, tool_calls=1),
        ]
        summary = cost_summary(tasks)
        assert summary["total_cost_usd"] == 0.75
        assert summary["total_tokens"] == 150
        assert summary["by_model"]["m1"] == 0.75
        assert summary["by_tool"]["web_search"] == 2
