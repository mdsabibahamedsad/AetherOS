"""Phase 2H — RecoveryManager tests: bounded retries, no retry storms.

Covers: destructive-action protection (never hammer HIGH/CRITICAL), transient
retry bounds, run-attempt budget, reobserve hook, failure bookkeeping, and
record_success reset. Uses retry_interval=0 everywhere (no sleeps).
"""

from __future__ import annotations

from aetheros_actions.model import Action, ActionType, RiskLevel
from aetheros_actions.recovery import RecoveryManager
from aetheros_actions.state import ComputerUseState


def _act(risk: RiskLevel = RiskLevel.LOW, at: ActionType = ActionType.CLICK, target: str = "b") -> Action:
    return Action(action_type=at, target=target, risk_level=risk)


class TestDestructiveProtection:
    def test_high_never_retried_by_default(self):
        r = RecoveryManager(retry_interval=0)
        d = r.should_retry(_act(risk=RiskLevel.HIGH), attempts_used=0)
        assert not d.should_retry
        assert d.state is ComputerUseState.FAILED
        assert "destructive" in d.reason

    def test_critical_never_retried_by_default(self):
        r = RecoveryManager(retry_interval=0)
        d = r.should_retry(_act(risk=RiskLevel.CRITICAL), attempts_used=0)
        assert not d.should_retry

    def test_destructive_with_explicit_budget(self):
        r = RecoveryManager(max_destructive_retries=1, retry_interval=0)
        d = r.should_retry(_act(risk=RiskLevel.HIGH), attempts_used=0)
        assert d.should_retry
        d2 = r.should_retry(_act(risk=RiskLevel.HIGH), attempts_used=1)
        assert not d2.should_retry

    def test_low_risk_retried_within_budget(self):
        r = RecoveryManager(max_retries=2, retry_interval=0)
        assert r.should_retry(_act(), 0).should_retry
        assert r.should_retry(_act(), 1).should_retry
        assert not r.should_retry(_act(), 2).should_retry

    def test_run_budget_caps_total_attempts(self):
        r = RecoveryManager(max_retries=50, max_run_attempts=4, retry_interval=0)
        d = r.should_retry(_act(), attempts_used=4)
        assert not d.should_retry
        assert "run retry budget" in d.reason


class TestRecoveryBehaviors:
    def test_reobserve_hook_invoked(self):
        calls = []
        r = RecoveryManager(retry_interval=0, reobserve=lambda: calls.append(1))
        r.should_retry(_act(), 0)
        assert calls == [1]

    def test_reobserve_exception_swallowed(self):
        def boom():
            raise RuntimeError("observer crashed")

        r = RecoveryManager(retry_interval=0, reobserve=boom)
        assert r.should_retry(_act(), 0).should_retry

    def test_failures_recorded_by_type(self):
        r = RecoveryManager(retry_interval=0)
        r.should_retry(_act(at=ActionType.CLICK), 0)
        r.should_retry(_act(at=ActionType.TYPE), 0)
        assert r.state.count("CLICK") == 1
        assert r.state.count("TYPE") == 1
        assert r.state.count("SCROLL") == 0

    def test_record_success_resets_retry_accounting(self):
        r = RecoveryManager(retry_interval=0)
        r.should_retry(_act(), 0)
        assert r.state.retries_used == 0  # retries_used only increments on success-path bookkeeping
        r.state.retries_used = 3
        r.record_success()
        assert r.state.retries_used == 0

    def test_snapshot_shape(self):
        r = RecoveryManager(retry_interval=0)
        r.should_retry(_act(), 0)
        snap = r.snapshot()
        assert snap["failures"] == 1
        assert "retries_used" in snap
        assert snap["last_failure_ts"] > 0

    def test_max_run_attempts_minimum_one(self):
        r = RecoveryManager(max_run_attempts=0, retry_interval=0)
        assert r.max_run_attempts >= 1

    def test_retry_interval_clamped_non_negative(self):
        r = RecoveryManager(retry_interval=-5)
        assert r.retry_interval >= 0.0

    def test_recovery_decision_to_dict(self):
        r = RecoveryManager(retry_interval=0)
        d = r.should_retry(_act(), 0)
        assert d.to_dict()["should_retry"] is True
        assert d.to_dict()["state"] == "RECOVERING"