"""Master 52 test matrix (§196): world state, entities, relations,
causal, prediction, simulation, counterfactual, foresight, reality,
errors, twins, versions, stale plans, firewall."""
from __future__ import annotations

import pytest

from aetheros_cognitive import (ActionCandidate, CognitiveArchitecture,
                                CounterfactualEngine, Entity, ForesightController,
                                Planner, RealityChecker, RepositoryTwin,
                                RuleBasedWorldModel, SideEffectFirewall,
                                Simulator, StateEstimator, WorldState)
from aetheros_cognitive.causal import CausalModel
from aetheros_cognitive.foresight import Calibrator, horizon_confidence
from aetheros_cognitive.models import SimulationBudget
from aetheros_cognitive.reality import (WorldModelUpdater, classify_error,
                                        toctou_recheck)
from aetheros_cognitive.router import CognitiveRouter
from aetheros_cognitive.twins import (A2ATwin, AutomationTwin, BrowserTwin,
                                      MCPTwin, SwarmTwin)
from aetheros_cognitive.world_models import (GraphDynamicsWorldModel,
                                             HybridWorldModel, LLMWorldModel,
                                             ModelEnsemble,
                                             SimulationUnavailable,
                                             StateTransitionWorldModel)


def _ws():
    est = StateEstimator()
    est.observe_entity(Entity("f1", "file", state={"exists": True}))
    est.observe_entity(Entity("agent1", "agent", state={"idle": True}))
    est.state.available_actions = ["read", "write"]
    return est


def _model():
    m = RuleBasedWorldModel()
    m.register("write", lambda s, p: {**s, p.get("target", "f1"): {
        "exists": True, "content": p.get("content", "")}})
    m.register("delete", lambda s, p: {**s, p.get("target", "f1"): {
        "exists": False}})
    return m


# -- world state -------------------------------------------------------------
def test_observe_conflict_and_unknown():
    est = _ws()
    est.observe_entity(Entity("f1", "file", state={"exists": False}),
                       source="direct")
    assert est.state.entities["f1"].state == {"exists": False}
    est.mark_unknown("f1", reason="sensor lost")
    assert est.state.entities["f1"].provenance == "unknown"
    assert "sensor lost" in est.state.known_unknowns


def test_snapshot_restore_and_staleness():
    est = _ws()
    sid = est.snapshot()
    est.observe_entity(Entity("f1", "file", state={"exists": False}),
                       source="direct")
    est.restore(sid)
    assert est.state.entities["f1"].state == {"exists": True}
    est.observe_entity(Entity("tmp", "file", state={}), ttl_s=-1.0)
    assert est.refresh_stale("tmp") is True


def test_relationship_neighbors():
    est = _ws()
    est.relate("agent1", "uses", "f1")
    assert len(est.neighbors("f1")) == 1


# -- world models ---------------------------------------------------------------
def test_rule_model_known_and_unknown_action():
    m = _model()
    st = _ws().state
    known = m.predict_next(st, {"type": "delete",
                                "parameters": {"target": "f1"}})
    assert known.state["f1"] == {"exists": False}
    assert known.confidence.combined() > 0.3
    unknown = m.predict_next(st, {"type": "teleport", "parameters": {}})
    assert unknown.confidence.combined() < 0.3  # honest low confidence
    assert unknown.provenance["rule"] is False


def test_transition_table_learn_and_predict():
    t = StateTransitionWorldModel()
    p0 = t.predict_next(_ws().state, {"type": "boot"})
    assert p0.provenance["known"] is False
    t.learn("default", "boot", "ready")
    p1 = t.predict_next(_ws().state, {"type": "boot"})
    assert p1.state == {"mode": "ready"}


def test_graph_dynamics_affection_set():
    est = _ws()
    est.relate("f1", "depends_on", "lib1")
    g = GraphDynamicsWorldModel()
    p = g.predict_next(est.state, {"type": "x",
                                   "parameters": {"target": "f1"}},
                       horizon=1)
    assert set(p.state["affected"]) == {"f1", "lib1"}


def test_llm_unavailable_is_honest():
    with pytest.raises(SimulationUnavailable):
        LLMWorldModel().predict_next(_ws().state, {"type": "x"})


def test_hybrid_disables_after_repeated_failure():
    h = HybridWorldModel([RuleBasedWorldModel()])
    for _ in range(5):
        h.record_failure()
    assert h.disabled is True
    with pytest.raises(SimulationUnavailable):
        h.predict_next(_ws().state, {"type": "x"})


def test_ensemble_disagreement():
    e = ModelEnsemble([_model(), GraphDynamicsWorldModel()])
    preds = e.predict_all(_ws().state, {"type": "write",
                                        "parameters": {"target": "f1"}})
    assert len(preds) == 2
    assert isinstance(ModelEnsemble.disagrees(preds), bool)


# -- simulator / firewall ----------------------------------------------------------
def test_firewall_blocks_unsimulated_tool():
    fw = SideEffectFirewall()
    fw.declare_safe("read", lambda a: {"ok": True})
    assert fw.call("read", {}) == {"ok": True}
    with pytest.raises(SimulationUnavailable):
        fw.call("pay_invoice", {"amount": 999})
    assert fw.attempts_blocked == 1


def test_rollout_budget_truncates():
    sim = Simulator(_model())
    b = sim.rollout(_ws().state, [{"type": "write",
                                   "parameters": {"target": "f1"}}] * 10,
                    SimulationBudget(max_depth=2))
    assert b.outcome.get("truncated") is True


def test_monte_carlo_frequencies_sum():
    sim = Simulator(_model())
    branches = sim.monte_carlo(_ws().state, [[{"type": "write",
                                               "parameters": {
                                                   "target": "f1"}}]],
                               SimulationBudget(), rollouts_per_set=4)
    assert len(branches) == 4
    assert all(0.0 <= br.frequency <= 1.0 for br in branches)


# -- planner --------------------------------------------------------------------------
def _cands(state):
    return [ActionCandidate(type="write",
                            parameters={"target": "f1", "content": "hi"},
                            risk=0.1, cost=0.1, reversibility=0.9),
            ActionCandidate(type="delete", parameters={"target": "f1"},
                            risk=0.9, cost=0.2, irreversible=True,
                            reversibility=0.0)]


def test_planner_prefers_safe_and_prunes_policy():
    sim = Simulator(_model())
    pl = Planner(sim, goal_test=lambda s: 1.0 if s.get("f1") else 0.0)
    pl.policy_check = lambda a: "denied" if a["type"] == "delete" else None
    ranked = pl.best_first(_ws().state, _cands)
    assert ranked and ranked[0]["candidate"].type == "write"
    assert pl.pruned == 1
    assert [r["candidate"].type for r in pl.mcts(
        _ws().state, _cands, iterations=6)]


def test_preconditions_checked():
    sim = Simulator(_model())
    pl = Planner(sim)
    cands = [ActionCandidate(type="write", parameters={},
                             preconditions=["nonexistent-thing"])]
    assert pl.expand(_ws().state, lambda _s: cands) == []


# -- foresight / calibration ---------------------------------------------------------------
def test_foresight_decisions():
    fc = ForesightController()
    assert fc.decide(0.1, 0.1, 1.0)["decision"] == "do_not_simulate"
    assert fc.decide(0.9, 0.9, 0.1)["decision"] == "ask_user"
    assert fc.decide(0.7, 0.5, 0.9)["decision"] == "simulate_deep"
    assert horizon_confidence(0.9, 10) < horizon_confidence(0.9, 1)


def test_calibration_brier():
    cal = Calibrator()
    assert cal.brier() is None
    for _ in range(10):
        cal.record(0.9, True)
    assert cal.brier() < 0.05
    assert cal.diagnosis()
    assert len(cal.reliability()) == 5


# -- reality ------------------------------------------------------------------
def test_expect_check_and_actions():
    rc = RealityChecker()
    rc.expect("a1", {"file": "exists"})
    err = rc.check("a1", {"file": "exists"})
    assert err.severity == "minor" and not err.difference
    rc.expect("a2", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6})
    err2 = rc.check("a2", {"a": 0, "b": 0, "c": 0, "d": 0, "e": 0,
                           "f": 0})
    assert err2.severity == "critical"
    assert rc.action_for(err2) == "stop"
    assert toctou_recheck(lambda: 3, 2) is True
    assert toctou_recheck(lambda: 2, 2) is False
    assert WorldModelUpdater().update({"trust": 0.8}, err2)["trust"] < 0.8


# -- counterfactual / causal -----------------------------------------------------
def test_counterfactual_compare_and_explain():
    sim = Simulator(_model())
    ce = CounterfactualEngine(sim)
    scs = ce.generate(_ws().state, [[{"type": "write",
                                      "parameters": {"target": "f1"}}]])
    sims = ce.simulate(_ws().state, scs)
    cmp_ = ce.compare({"score": 0.0}, sims)
    assert cmp_["would_change"] is True
    assert "PREDICTIONS" in ce.explain_difference({"score": 0.0,
                                                   "branch": sims[0][
                                                       "branch"]}, sims[0])


def test_causal_correlation_not_causation():
    cm = CausalModel()
    cm.hypothesize("rain", "outage")
    cm.add_evidence("rain", "outage", "observation", "log-1")
    assert cm.edges["rain→outage"].status == "HYPOTHESIS"  # still!
    cm.add_evidence("rain", "outage", "intervention", "do() test")
    assert cm.edges["rain→outage"].status == "VALIDATED"
    res = cm.intervene("x", "y", lambda on: True)  # no contrast
    assert res["validated"] is False
    cm.downgrade("rain", "outage", reason="failed replication")
    assert cm.edges["rain→outage"].status == "HYPOTHESIS"


# -- twins ----------------------------------------------------------------
def test_repository_twin_overlay_not_real(tmp_path):
    real = tmp_path / "repo"
    real.mkdir()
    (real / "a.txt").write_text("real", encoding="utf-8")
    twin = RepositoryTwin(real)
    out = twin.apply_simulated({"type": "write_file",
                                "parameters": {"path": "b.txt",
                                               "content": "sim"}})
    assert out["simulated"] is True
    assert not (real / "b.txt").exists()  # real untouched
    assert twin.apply_simulated({"type": "nope"})["simulated"] is False


def test_browser_automation_swarm_a2a_mcp_twins():
    bt = BrowserTwin()
    bt.open_tab("t1", "https://x.example")
    assert bt.apply_simulated({"type": "navigate",
                               "parameters": {"url": "https://y.example",
                                              "tab": "t1"}})["simulated"]
    assert bt.apply_simulated({"type": "navigate",
                               "parameters": {
                                   "tab": "ghost"}})["simulated"] is False
    at = AutomationTwin({"steps": ["a", "b"]})
    dry = at.apply_simulated({"type": "dry_run"})
    assert dry["side_effects"] == "none — dry run only"
    plan = SwarmTwin().plan([f"t{i}" for i in range(9)], 3)
    assert plan["waves"] == 3 and plan["simulated"] is True
    assert A2ATwin().predict_peer()["reliability"] is None  # honest I-don't-know
    hist = A2ATwin([{"ok": True, "latency_ms": 10},
                    {"ok": False, "latency_ms": 50}])
    assert hist.predict_peer()["reliability"] == 0.5
    mt = MCPTwin({"echo": lambda a: a})
    assert mt.apply_simulated({"tool": "echo"})["simulated"] is True
    assert "SIMULATION_UNAVAILABLE" in mt.apply_simulated(
        {"tool": "real_pay"})["reason"]


# -- router ----------------------------------------------------------------
def test_router_modes_and_degradation():
    r = CognitiveRouter()
    assert r.select(0.05, 0.05, 1, 0.1)["mode"] == "reactive"
    assert r.select(0.9, 0.9, 8, 0.9)["mode"] == "deliberative"
    assert r.select(0.2, 0.2, 1, 0.1,
                    world_model_available=False)["degraded"] is True
    assert CognitiveRouter.degrade("deliberative") == "simulative"
    assert CognitiveRouter("max").select(0.0, 0.0, 1, 0.0)["mode"] \
        == "deliberative"
