"""Tests for the additive hardening modules (Steps 58-95).

Covers: reversibility, failure classification, dry-run preview, blast radius,
idempotency, anomaly detection + quarantine, resource locks, intent drift,
and durable receipts — both pure and wired through the ComputerUseManager.
"""

from __future__ import annotations

import pytest

from aetheros_actions.anomaly import AgentQuarantine, AnomalyDetector
from aetheros_actions.blast_radius import EXTERNAL, estimate_blast_radius, plan_blast_radius
from aetheros_actions.dryrun import action_dry_run, plan_dry_run
from aetheros_actions.executor import ActionExecutor
from aetheros_actions.failure import classify_failure, is_retryable
from aetheros_actions.idempotency import IdempotencyRegistry
from aetheros_actions.intent import IntentVerifier
from aetheros_actions.lock import ResourceLockManager
from aetheros_actions.manager import ComputerUseManager
from aetheros_actions.model import (
    Action,
    ActionType,
    FailureKind,
    Reversibility,
    RiskLevel,
)
from aetheros_actions.receipts import build_receipt, run_receipts
from aetheros_actions.reversibility import annotate_plan_actions, classify_reversibility
from aetheros_actions.verifier import ActionVerifier


def _act(action_type=ActionType.CLICK, target="x", **kw) -> Action:
    return Action(action_type=action_type, target=target, **kw)


class _FakeExecutor(ActionExecutor):
    def __init__(self, fail_on=()):
        super().__init__(handler=self._flow)
        self.fail_on = set(fail_on)
        self.calls = []

    def _flow(self, action):
        self.calls.append(action.target)
        if action.target in self.fail_on:
            raise RuntimeError("simulated failure")
        return {"ok": True}


class TestReversibility:
    def test_read_only_is_reversible(self):
        assert classify_reversibility(_act(ActionType.CLICK)) is Reversibility.REVERSIBLE

    def test_app_launch_is_partially_reversible(self):
        assert classify_reversibility(_act(ActionType.APP_LAUNCH)) is Reversibility.PARTIALLY_REVERSIBLE

    def test_app_close_is_irreversible(self):
        assert classify_reversibility(_act(ActionType.APP_CLOSE)).is_irreversible

    def test_upload_is_irreversible(self):
        assert classify_reversibility(_act(ActionType.UPLOAD)) is Reversibility.IRREVERSIBLE

    def test_unknown_kind_conservative(self):
        assert classify_reversibility(_act(ActionType.NAVIGATE)) is Reversibility.PARTIALLY_REVERSIBLE

    def test_annotate_sets_field(self):
        a = _act(ActionType.APP_CLOSE)
        assert annotate_plan_actions([a])[0].reversibility is Reversibility.IRREVERSIBLE


class TestFailureClassification:
    def test_transient(self):
        assert classify_failure("timed out after 30s") is FailureKind.TRANSIENT
        assert is_retryable("connection reset by peer")

    def test_permission(self):
        assert classify_failure("permission denied: not granted") is FailureKind.PERMISSION

    def test_validation(self):
        assert classify_failure("invalid target") is FailureKind.VALIDATION
        assert classify_failure("requires `x`") is FailureKind.VALIDATION

    def test_unavailable(self):
        assert classify_failure("backend unavailable") is FailureKind.UNAVAILABLE

    def test_empty_is_unknown(self):
        assert classify_failure("") is FailureKind.UNKNOWN

    def test_dry_run_action_is_validation(self):
        assert classify_failure("anything", action=_act(dry_run=True)) is FailureKind.VALIDATION


class TestDryRun:
    def test_action_dry_run_impact(self):
        imp = action_dry_run(_act(ActionType.APP_CLOSE, target="app"))
        assert imp.irreversible
        assert imp.action_type == "APP_CLOSE"
        assert imp.target == "app"

    def test_plan_dry_run_counts(self):
        prev = plan_dry_run("close apps", [
            _act(ActionType.APP_CLOSE, target="a", risk_level=RiskLevel.HIGH),
            _act(ActionType.CLICK, target="b", risk_level=RiskLevel.LOW),
        ])
        assert prev.irreversible_count == 1
        assert prev.high_risk_count == 1
        assert prev.destructive_count == 1
        assert len(prev.impacts) == 2
        assert "no changes made" in prev.message

    def test_empty_plan_message(self):
        assert "empty" in plan_dry_run("goal", []).message

    def test_manager_dry_run_executes_nothing(self):
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "click it", [
            {"action": "CLICK", "target": "btn", "parameters": {}},
        ], dry_run=True)
        assert report.ok
        assert report.preview is not None
        assert len(report.preview["impact"]) == 1
        assert report.steps == []
        assert ex.calls == []


class TestBlastRadius:
    def test_upload_reaches_external(self):
        assert estimate_blast_radius(_act(ActionType.UPLOAD)).scope == EXTERNAL

    def test_plan_aggregates_worst_scope(self):
        agg = plan_blast_radius([
            _act(ActionType.CLICK),
            _act(ActionType.UPLOAD),
        ])
        assert agg.scope == EXTERNAL
        assert agg.affected_count == 2

    def test_unknown_kind_assumes_worst(self):
        from aetheros_actions.blast_radius import SYSTEM
        assert estimate_blast_radius(_act(ActionType.OPEN)).scope != SYSTEM


class TestIdempotency:
    def test_registry_dedup(self):
        reg = IdempotencyRegistry()
        assert reg.check_and_record("k", "a1", session_id="s1")
        assert not reg.check_and_record("k", "a2", session_id="s1")
        assert reg.check_and_record("k", "a3", session_id="s2")
        assert reg.seen("k", session_id="s1")

    def test_manager_skips_second_run(self):
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        step = {"action": "CLICK", "target": "btn", "parameters": {},
                "idempotency_key": "dedup-1"}
        r1 = man.run_plan(s, "click once", [step])
        assert r1.ok and ex.calls == ["btn"]
        r2 = man.run_plan(s, "click once", [step])
        assert r2.ok
        assert ex.calls == ["btn"]  # not executed a second time
        assert r2.steps[0].result.message.startswith("already executed")


class TestAnomalyAndQuarantine:
    def _clock(self):
        t = [0.0]

        def now():
            return t[0]
        return t, now

    def test_detector_mass_modification(self):
        t, now = self._clock()
        det = AnomalyDetector(repeated_destructive_threshold=2, now=now)
        det.record(_act(ActionType.APP_CLOSE))
        assert det.detect(agent_id="ag") is None
        det.record(_act(ActionType.APP_CLOSE))
        info = det.detect(agent_id="ag")
        assert info is not None
        assert info.kind == "repeated_destructive"

    def test_detector_rapid_clicks(self):
        t, now = self._clock()
        det = AnomalyDetector(rapid_click_threshold=3, now=now)
        for _ in range(3):
            det.record(_act(ActionType.CLICK))
            t[0] += 0.5
        assert det.detect().kind == "rapid_clicks"

    def test_quarantine_revocations(self):
        q = AgentQuarantine()
        q.quarantine_agent("ag", "anomaly", evidence=[{"kind": "test"}])
        assert q.is_quarantined("ag")
        assert "computer_control" in q.revocations("ag")
        assert q.evidence("ag")[0]["kind"] == "test"
        assert q.unquarantine("ag")

    def test_manager_quarantines_on_anomaly(self):
        t, now = self._clock()
        det = AnomalyDetector(repeated_destructive_threshold=1, now=now)
        q = AgentQuarantine()
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, anomaly_detector=det, quarantine=q,
                                 confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "close one app", [
            {"action": "APP_CLOSE", "target": "app", "parameters": {}},
        ])
        assert not report.ok
        assert q.is_quarantined("ag")
        assert report.steps[0].verification.verdict.value == "FAIL"

    def test_quarantined_agent_blocked_next_run(self):
        q = AgentQuarantine()
        q.quarantine_agent("ag", "past anomaly")
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, quarantine=q, confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "click it", [
            {"action": "CLICK", "target": "btn", "parameters": {}},
        ])
        assert not report.ok
        assert ex.calls == []
        assert "quarantined" in report.steps[0].decision.reason


class TestResourceLocks:
    def test_exclusive_acquire(self):
        lm = ResourceLockManager()
        assert lm.acquire("mouse", "a")
        assert not lm.acquire("mouse", "b")
        assert lm.held_by("mouse") == "a"
        assert lm.release_all("a") == 1
        assert lm.acquire("mouse", "b")

    def test_manager_denies_conflicting_holder(self):
        lm = ResourceLockManager()
        lm.acquire("mouse", "other-session")
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, lock_manager=lm,
                                 confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "click it", [
            {"action": "CLICK", "target": "btn", "parameters": {}},
        ])
        assert not report.ok
        assert ex.calls == []
        assert "resource" in report.steps[0].decision.reason

    def test_lock_released_after_success(self):
        lm = ResourceLockManager()
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, lock_manager=lm,
                                 confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        man.run_plan(s, "click it", [
            {"action": "CLICK", "target": "btn", "parameters": {}},
        ])
        assert lm.held_by("mouse") is None


class TestIntentDrift:
    def test_goal_with_no_signal_not_drifted(self):
        iv = IntentVerifier()
        check = iv.check("", [_act(ActionType.CLICK)])
        assert not check.drifted

    def test_destructive_step_outside_goal_drifts(self):
        iv = IntentVerifier()
        check = iv.check("read my inbox", [
            _act(ActionType.UPLOAD, target="/tmp/random.bin"),
        ])
        assert check.drifted
        assert check.reasons

    def test_aligned_step_not_drifted(self):
        iv = IntentVerifier()
        check = iv.check("upload report", [
            _act(ActionType.UPLOAD, target="report.pdf", reason="upload report"),
        ])
        assert not check.drifted

    def test_manager_warns_on_drift(self):
        man = ComputerUseManager()
        s = man.create_session(agent_id="ag")
        verdict = man.plan(s, "read my inbox", [
            {"action": "UPLOAD", "target": "/tmp/random.bin"},
        ])
        assert verdict.ok
        assert any("intent drift" in w for w in verdict.warnings)

    def test_manager_blocks_when_opted_in(self):
        man = ComputerUseManager(block_on_intent_drift=True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "read my inbox", [
            {"action": "UPLOAD", "target": "/tmp/random.bin"},
        ])
        assert not report.ok
        assert any("intent drift blocked" in w for w in report.warnings)
        assert report.steps[0].decision.reason == "intent drift blocked"


class TestReceipts:
    def test_build_receipt_correlates(self):
        a = _act(ActionType.APP_CLOSE, target="app", agent_id="ag", session_id="s1")
        rec = build_receipt(a, decision="ALLOW", ok=False, error="timed out",
                            trace_id="t1")
        assert rec.trace_id == "t1"
        assert rec.failure_kind == FailureKind.TRANSIENT.value
        assert rec.reversibility == Reversibility.IRREVERSIBLE.value
        assert rec.ok is False

    def test_receipts_built_after_run(self):
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "click it", [
            {"action": "CLICK", "target": "btn", "parameters": {}},
        ], trace_id="trace-abc")
        assert report.trace_id == "trace-abc"
        assert len(report.receipts) == 1
        assert report.receipts[0]["traceId"] == "trace-abc"
        assert report.receipts[0]["target"] == "btn"
        assert report.receipts[0]["actionId"] == report.steps[0].action.action_id

    def test_receipts_for_denied_steps(self):
        from aetheros_actions.model import TrustSource
        ex = _FakeExecutor()
        man = ComputerUseManager(executor=ex, confirm_callback=lambda d: True)
        s = man.create_session(agent_id="ag")
        report = man.run_plan(s, "type from page", [
            {"action": "TYPE", "target": "field", "parameters": {"text": "x"}},
        ], source=TrustSource.WEB_CONTENT)
        assert not report.ok
        assert report.receipts[0]["decision"] == "DENY"