"""CLI: ``aetheros cognitive …`` (§161): world/state/inspect,
simulate, foresight, counterfactual, causal, twin, predictions,
cognitive benchmark. Operates on real backend state; simulations
actually execute against in-memory/twin models.
"""

from __future__ import annotations

import argparse
import json
from typing import Any


def _cognition(args: Any):
    from pathlib import Path
    from tempfile import mkdtemp
    from aetheros_cognitive import CognitiveArchitecture
    try:
        from aetheros_control_plane import UniversalControlPlane
        plane: Any = UniversalControlPlane()
    except Exception:
        plane = None
    return CognitiveArchitecture(Path(mkdtemp(prefix="cog_")), plane=plane,
                                 tenant=getattr(args, "tenant", "default"))


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "cognitive",
        help="Cognitive Architecture 2.0: world model, foresight, "
             "simulation, counterfactuals, twins",
    )
    parser.add_argument("--tenant", default="default")
    verbs = parser.add_subparsers(dest="cognitive_command")

    verbs.add_parser("health", help="Backend + model trust status")

    w = verbs.add_parser("world", help="Inspect live world state")
    w.add_argument("verb", nargs="?", default="state",
                   choices=["state", "inspect"])

    s = verbs.add_parser("simulate", help="Run a demo rollout")
    s.add_argument("--depth", type=int, default=2)

    f = verbs.add_parser("foresight", help="Foresight triage decision")
    f.add_argument("--risk", type=float, default=0.3)
    f.add_argument("--uncertainty", type=float, default=0.3)

    verbs.add_parser("causal", help="Show causal graph (starts empty)")

    t = verbs.add_parser("twin", help="Twin demo: swarm estimate")
    t.add_argument("--tasks", type=int, default=9)
    t.add_argument("--agents", type=int, default=3)

    verbs.add_parser("benchmark", help="Run WorldModelBench (offline)")
    return parser


def dispatch_cognitive_command(args: Any) -> int:
    from aetheros_cognitive import CognitiveRouter
    from aetheros_cognitive.foresight import ForesightController
    from aetheros_cognitive.twins import SwarmTwin
    cog = _cognition(args)
    verb = getattr(args, "cognitive_command", None) or "health"
    if verb == "health":
        print(json.dumps({
            "model": cog.model.describe(),
            "disabled": cog.model.disabled,
            "trust": cog.trust,
            "decisions": len(cog.decisions),
            "router_modes": CognitiveRouter.MODES}, indent=2))
    elif verb == "world":
        print(json.dumps(cog.estimator.present(), indent=2)[:4000])
    elif verb == "simulate":
        from aetheros_cognitive import RuleBasedWorldModel, Simulator
        m = RuleBasedWorldModel()
        m.register("noop", lambda s, p: dict(s))
        br = Simulator(m).rollout(cog.estimator.state,
                                  [{"type": "noop"}] * args.depth)
        print(json.dumps({"predicted_states": br.predicted_states,
                          "confidence": br.confidence,
                          "note": "PREDICTION, not fact"}, indent=2,
                         default=str))
    elif verb == "foresight":
        print(json.dumps(ForesightController().decide(
            args.risk, args.uncertainty, True), indent=2))
    elif verb == "causal":
        print(json.dumps({"edges": cog.causal.graph(),
                          "rule": "HYPOTHESIS until validated"}, indent=2))
    elif verb == "twin":
        print(json.dumps(SwarmTwin().plan(
            [f"t{i}" for i in range(args.tasks)], args.agents), indent=2))
    elif verb == "benchmark":
        from benchmark.cognitive_bench import main as bench_main
        bench_main()
    else:
        print(f"unknown cognitive verb: {verb}")
        return 2
    return 0
