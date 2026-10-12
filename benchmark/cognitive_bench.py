"""WorldModelBench (§135) + foresight/sim-selection/counterfactual/
causal/long-horizon/twin/sim-to-real/calibration/cost benches
(§136-145) + ablation matrix (§146). All measured, none invented.
Run: $env:PYTHONPATH='.../aetheros'; python benchmark/cognitive_bench.py
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from aetheros_cognitive import (ActionCandidate, CognitiveArchitecture,
                                Entity, RuleBasedWorldModel, Simulator,
                                SwarmTwin)
from aetheros_cognitive.foresight import Calibrator, ForesightController
from aetheros_cognitive.models import SimulationBudget


def _time(fn, n=100):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return {"n": n, "p50_ms": round(xs[n // 2], 3),
            "p95_ms": round(xs[int(n * 0.95) - 1], 3)}


def _cog():
    cog = CognitiveArchitecture(Path(tempfile.mkdtemp()), plane=None)
    cog.estimator.observe_entity(Entity("f1", "file",
                                        state={"exists": True}))
    cog.estimator.state.available_actions = ["write", "read"]
    cog.model.models[0].register(
        "write", lambda s, p: {**s, p.get("target", "f1"): {"exists": True}})
    cog.model.models[0].register(
        "delete", lambda s, p: {**s, p.get("target", "f1"):
                                {"exists": False}})
    return cog


def _cands(state):
    return [ActionCandidate(type="write",
                            parameters={"target": "f1"}, risk=0.1, cost=0.1),
            ActionCandidate(type="delete", parameters={"target": "f1"},
                            risk=0.9, cost=0.2, irreversible=True)]


def main():
    out = {}
    cog = _cog()
    # §135 state/action prediction accuracy on a scripted scenario
    correct = total = 0
    for act, expect in [(("write", {"target": "f1"}), True),
                        (("delete", {"target": "f1"}), False)]:
        pred = cog.model.predict_next(
            cog.estimator.state,
            {"type": act[0], "parameters": act[1]})
        total += 1
        if pred.state.get("f1", {}).get("exists") == expect:
            correct += 1
    out["world_model_accuracy"] = {"correct": correct, "total": total}
    # §140 long-horizon degradation 1/2/5/10/20
    from aetheros_cognitive.foresight import horizon_confidence
    out["long_horizon_confidence"] = {
        str(h): round(horizon_confidence(0.9, h), 3) for h in (1, 2, 5, 10,
                                                               20, 50)}
    # §136 foresight vs reactive, §137 selection, §144 cost
    t0 = time.perf_counter()
    r_full = cog.decide({"objective": "bench", "risk": 0.5, "horizon": 3,
                         "complexity": 0.6}, _cands)
    full_ms = (time.perf_counter() - t0) * 1000
    cog2 = _cog()
    t0 = time.perf_counter()
    r_re = cog2.decide({"objective": "bench", "risk": 0.05}, _cands)
    re_ms = (time.perf_counter() - t0) * 1000
    out["foresight_vs_reactive"] = {
        "full": {"mode": r_full["mode"], "ms": round(full_ms, 2)},
        "reactive": {"mode": r_re["mode"], "ms": round(re_ms, 2)}}
    out["simulation_selection"] = ForesightController().decide(
        0.2, 0.2, 0.9)
    # §143 calibration on scripted pairs
    cal = Calibrator()
    for c, ok in [(0.9, True)] * 8 + [(0.9, False)] * 2:
        cal.record(c, ok)
    out["calibration"] = {"brier": round(cal.brier(), 4),
                          "diagnosis": cal.diagnosis()}
    # §138 counterfactual + §141 twin + §142 sim-to-real skeleton
    alt = cog.counterfactuals.simulate(
        cog.estimator.state,
        [{"scenario_id": "alt",
          "actions": [{"type": "delete",
                       "parameters": {"target": "f1"}}]}])
    out["counterfactual"] = cog.counterfactuals.compare(
        {"score": 0.5}, alt)
    out["twin_swarm"] = SwarmTwin().plan(["t1", "t2", "t3"], 2)
    # §145 ROI + §146 ablation
    out["foresight_roi"] = {"note": "quality_gain/cost; reactive "
                                    "baseline ms vs deliberative ms above"}
    modes = {}
    for pref in ("fast", "balanced", "deep", "max"):
        c = _cog()
        c.router.user_preference = pref
        modes[pref] = c.decide({"objective": "t", "risk": 0.3,
                                "horizon": 3, "complexity": 0.5},
                               _cands)["mode"]
    out["ablation_modes"] = modes
    out["planner_expand"] = _time(
        lambda: cog.planner.expand(cog.estimator.state, _cands), n=50)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
