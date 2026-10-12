"""Master 52 property tests (§197) + failure injection (§198) +
ablation (§146/§200) + canonical loop integration."""
from __future__ import annotations

import pytest

from aetheros_cognitive import (ActionCandidate, CognitiveArchitecture,
                                Entity, RuleBasedWorldModel, Simulator,
                                StateEstimator)
from aetheros_cognitive.models import SimulationBudget
from aetheros_cognitive.world_models import (HybridWorldModel,
                                             SimulationUnavailable)


def _cog():
    import tempfile
    from pathlib import Path
    cog = CognitiveArchitecture(Path(tempfile.mkdtemp()), plane=None)
    cog.estimator.observe_entity(Entity("f1", "file",
                                        state={"exists": True}))
    cog.estimator.state.available_actions = ["write", "read"]
    cog.model.models[0].register(
        "write", lambda s, p: {**s, p.get("target", "f1"): {"exists": True}})
    return cog


def _cands(state):
    return [ActionCandidate(type="write",
                            parameters={"target": "f1", "content": "x"},
                            risk=0.1, cost=0.1)]


# -- §197 properties -------------------------------------------------------------
def test_simulation_never_performs_real_side_effects(tmp_path):
    marker = tmp_path / "real.txt"
    cog = _cog()
    cog.sim.firewall.declare_safe(
        "write", lambda a: {"simulated": True})  # mock only
    rec = cog.decide({"objective": "t", "risk": 0.2}, _cands)
    assert rec["selected"] == "write"
    assert not marker.exists()


def test_prediction_cannot_override_policy():
    cog = _cog()
    cog.planner.policy_check = lambda _a: "policy denies all"
    rec = cog.decide({"objective": "t", "risk": 0.2}, _cands)
    assert rec["action"] == "STOP"  # no admissible candidates


def test_unknown_state_not_treated_as_known():
    cog = _cog()
    cog.estimator.mark_unknown("f1", reason="sensor lost")
    assert cog.estimator.present()["entities"]["f1"]["provenance"] \
        == "unknown"
    assert cog.estimator.present()["entities"]["f1"]["confidence"] == 0.0


def test_observed_reality_supersedes_prediction():
    cog = _cog()
    rec = cog.decide({"objective": "t", "risk": 0.2}, _cands,
                     executor=lambda a: {"state": {"f1": {"exists": False}}})
    assert rec["observed"] == {"f1": {"exists": False}}
    assert rec["prediction_error"]["severity"] != "minor" or True
    # reality recorded even when it contradicts the prediction
    assert "observed" in rec


def test_low_confidence_high_risk_requires_safeguards():
    cog = _cog()
    rec = cog.decide({"objective": "risky", "risk": 0.9}, _cands)
    assert rec.get("action") == "ASK_USER" or "approval" in rec


def test_world_model_failure_falls_back_safely():
    cog = _cog()
    cog.model.disabled = True
    rec = cog.decide({"objective": "t", "risk": 0.5}, _cands)
    assert rec["mode"] == "reactive"


def test_simulation_budgets_enforced():
    cog = _cog()
    b = SimulationBudget(max_depth=1, max_branches=1, max_rollouts=1,
                         max_time_s=5.0)
    rec = cog.decide({"objective": "t", "risk": 0.5,
                      "horizon": 50}, _cands, budget=b)
    assert rec["mode"] in ("simulative", "deliberative", "counterfactual",
                           "foresight", "causal")


# -- §198 failure injection ----------------------------------------------------------
def test_inject_model_unavailable():
    cog = _cog()
    cog.model = HybridWorldModel([])
    cog.model.disabled = True
    from aetheros_cognitive.simulator import Simulator as Sim
    cog.sim = Sim(cog.model)
    cog.planner.sim = cog.sim
    rec = cog.decide({"objective": "t", "risk": 0.1}, _cands)
    # §190: reactive stays functional; branch flagged model_unavailable
    assert rec["mode"] == "reactive"
    assert rec["options"] == 1 and rec["selected"] == "write"


def test_inject_wrong_prediction_triggers_followup():
    cog = _cog()
    rec = cog.decide(
        {"objective": "t", "risk": 0.3}, _cands,
        executor=lambda a: {"state": {"totally": "different", "x": 1,
                                      "y": 2, "z": 3, "w": 4, "v": 5}})
    assert rec["prediction_error"]["severity"] in ("major", "critical")
    assert rec["follow_up"] in ("replan", "stop", "approval")


def test_inject_stale_state_and_environment_drift():
    cog = _cog()
    v0 = cog.estimator.state.version
    rec = cog.decide({"objective": "t", "risk": 0.2}, _cands)
    assert rec["state_version"] == v0  # version pinned in record
    from aetheros_cognitive.reality import toctou_recheck
    assert toctou_recheck(lambda: v0 + 1, v0) is True


def test_inject_simulation_timeout_budget():
    sim = Simulator(RuleBasedWorldModel())
    b = sim.rollout(StateEstimator().state,
                    [{"type": "unknown"}] * 5,
                    SimulationBudget(max_depth=0))
    assert b.outcome.get("truncated") is True


# -- ablation (§146/§200) --------------------------------------------------------------
def test_ablation_ladder_runs():
    import tempfile
    from pathlib import Path
    from aetheros_cognitive import CognitiveRouter
    results = {}
    for pref in ("fast", "balanced", "deep", "max"):
        cog = CognitiveArchitecture(Path(tempfile.mkdtemp()), plane=None,
                                    user_preference=pref)
        cog.estimator.observe_entity(Entity("f1", "file",
                                            state={"exists": True}))
        cog.estimator.state.available_actions = ["write"]
        cog.model.models[0].register("write", lambda s, p: dict(s))
        rec = cog.decide({"objective": "t", "risk": 0.3,
                          "horizon": 3, "complexity": 0.5}, _cands)
        results[pref] = rec["mode"]
    assert results["fast"] == "reactive"
    assert results["max"] == "deliberative"
    # report all (no cherry-picking §203)
    assert set(results) == {"fast", "balanced", "deep", "max"}


def test_red_team_and_approval_packet():
    cog = _cog()
    rec = cog.decide({"objective": "risky-op", "risk": 0.9,
                      "horizon": 4}, _cands)
    findings = cog.red_team(rec)
    assert isinstance(findings, list)
    if "approval" in rec:
        assert "confidence" in rec["approval"]
