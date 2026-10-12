"""Quality object contracts (P2, P5, P7, P11-12, P24, P83): risk
classification is upgrade-only, proposals demand evidence + rollback,
CRITICAL/HIGH always require human approval."""

import dataclasses

import pytest

from agent.quality.models import (
    CRITICAL_COMPONENTS,
    SAFE_AUTO_FIX_KINDS,
    Baseline,
    Candidate,
    ChangeProposal,
    ChangeRisk,
    Experiment,
    GateResult,
    GateStatus,
    Hypothesis,
    KnownIssue,
    MetricResult,
    ReleaseScorecard,
    RolloutStage,
    RolloutState,
    RunStatus,
    classify_change_risk,
)


class TestRiskClassification:
    def test_critical_component_escalates(self):
        assert classify_change_risk(["installer"]) is ChangeRisk.CRITICAL

    def test_upgrade_only_never_downgrades(self):
        assert classify_change_risk(
            ["security"], described_risk="LOW") is ChangeRisk.CRITICAL

    def test_benign_components_stay_as_described(self):
        assert classify_change_risk(
            ["docs"], described_risk="TRIVIAL") is ChangeRisk.TRIVIAL

    def test_invalid_description_falls_back_to_low(self):
        assert classify_change_risk([], "nonsense") is ChangeRisk.LOW


class TestChangeProposal:
    def _kwargs(self, **over):
        base = dict(
            description="formatting: reflow imports",
            reason="lint drift",
            components=["docs"],
            expected_benefit="clean lint",
            evidence=["lint output ref 123"],
            rollback_plan="git revert",
            author="quality-engine",
        )
        base.update(over)
        return base

    def test_missing_evidence_rejected_at_construction(self):
        with pytest.raises(ValueError, match="evidence"):
            ChangeProposal(**self._kwargs(evidence=[]))

    def test_missing_rollback_plan_rejected(self):
        with pytest.raises(ValueError, match="rollback_plan"):
            ChangeProposal(**self._kwargs(rollback_plan=""))

    def test_critical_component_forces_human_approval(self):
        p = ChangeProposal(**self._kwargs(components=["authentication"]))
        assert p.risk is ChangeRisk.CRITICAL
        assert p.requires_human_approval

    def test_non_allowlisted_change_requires_human_approval(self):
        p = ChangeProposal(**self._kwargs())  # not marked auto_applicable
        assert p.requires_human_approval

    def test_serialization_roundtrip_shape(self):
        d = ChangeProposal(**self._kwargs()).to_dict()
        assert d["risk"] == "LOW"
        for field_name in ("description", "reason", "components",
                           "expected_benefit", "evidence", "rollback_plan"):
            assert field_name in d


class TestEvaluationRun:
    def test_mandatory_provenance_fields(self):
        run = dataclasses.replace(
            Baseline.create("production", "1.0", {"m": 1.0}))  # smoke ctor
        del run
        run = Experiment(
            hypothesis=Hypothesis(
                problem="p", statement="s", expected_improvement="e",
                metric="latency", risk="r", measurement_method="bench",
                rollback_condition="regression > 10%"),
            baseline_id="b", candidate_id="c", environment="local")
        d = run.to_dict()
        assert d["status"] == "pending"
        assert d["hypothesis"]["rollback_condition"]

    def test_executed_gate_blocks_uncompleted_runs(self):
        from agent.quality.models import EvaluationRun as ER
        pending = ER(target="t", version="v", environment="e", dataset="d")
        done = ER(target="t", version="v", environment="e", dataset="d",
                  status=RunStatus.COMPLETED)
        assert not pending.executed()
        assert done.executed()


class TestGateAndScorecardSemantics:
    def test_any_block_means_not_ready(self):
        sc = ReleaseScorecard(version="x", gates=[
            GateResult(gate="FUNCTIONAL", status=GateStatus.PASS),
            GateResult(gate="SECURITY", status=GateStatus.BLOCK),
        ])
        assert not sc.ready
        d = sc.to_dict()
        assert d["ready"] is False
        assert d["gates"][1]["status"] == "BLOCK"

    def test_all_pass_is_ready(self):
        sc = ReleaseScorecard(version="x", gates=[
            GateResult(gate=n, status=GateStatus.PASS) for n in
            ("FUNCTIONAL", "SECURITY")])
        assert sc.ready


class TestConstantsAreClosedSets:
    def test_safe_autofix_allowlist_matches_policy_examples(self):
        assert SAFE_AUTO_FIX_KINDS == frozenset({
            "formatting", "regenerate_derived_index",
            "restart_failed_worker", "clear_safe_cache",
        })

    def test_critical_components_cover_security_boundaries(self):
        for comp in ("security", "authorization", "credentials",
                     "permission_policy", "sandbox", "data_migration"):
            assert comp in CRITICAL_COMPONENTS


class TestRolloutStateModel:
    def test_stage_progression_values(self):
        st = RolloutState(version="9.9")
        assert st.stage is RolloutStage.NONE
        st.stage = RolloutStage.CANARY
        assert st.to_dict()["stage"] == "canary"


class TestBaselineCandidate:
    def test_baseline_metrics_snapshot(self):
        b = Baseline.create("previous-release", "2.3.1",
                            {"p95_latency_ms": 120.0})
        assert b.metrics["p95_latency_ms"] == 120.0

    def test_candidate_tracks_dependency_changes(self):
        c = Candidate(candidate_id="cand-1", commit="abc1234",
                      dependency_changes=["httpx>=0.28.1,<1"])
        assert c.dependency_changes and c.commit == "abc1234"

    def test_metric_result_directions(self):
        m = MetricResult(name="latency", value=90.0, baseline_value=100.0,
                         delta=-10.0, direction="improved")
        assert m.direction in ("improved", "regressed", "unchanged", "new")


def test_known_issue_defaults_open():
    ki = KnownIssue(issue_id="KI-X", title="t", severity="high",
                    workaround="w")
    assert ki.status == "open"
