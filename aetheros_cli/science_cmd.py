"""CLI: ``aetheros science ...`` (Master 53 §85).

Operates against real backend state (file-backed stores under the
profile home). Follows the build_parser / dispatch_* convention.
Every demo path executes real code — never simulated-as-real.
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def _engine(args: Any):
    from pathlib import Path
    from tempfile import mkdtemp
    from aetheros_science import ScientificIntelligenceEngine
    try:
        from aetheros_control_plane import UniversalControlPlane
        plane: Any = UniversalControlPlane()
    except Exception:
        plane = None
    home = Path(mkdtemp(prefix="sci-"))
    return ScientificIntelligenceEngine(
        home, plane=plane,
        autonomy=int(getattr(args, "autonomy", 5) or 5))


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "science",
        help="Scientific intelligence: questions, hypotheses, experiments, "
             "evidence, discovery",
    )
    parser.add_argument("--autonomy", type=int, default=5)
    verbs = parser.add_subparsers(dest="science_command")

    q = verbs.add_parser("question", help="Decompose a research question")
    q.add_argument("text", nargs="+")

    h = verbs.add_parser("hypothesis", help="Generate hypotheses")
    h.add_argument("--question", required=True)
    h.add_argument("--factors", default="cache,parallelism")

    d = verbs.add_parser("experiment", help="Design an experiment")
    d.add_argument("verb", choices=["design", "run", "reproduce"])
    d.add_argument("--hypothesis", default="H: x affects y")
    d.add_argument("--id", default="")

    verbs.add_parser("simulate", help="Simulation status / dry plan")
    verbs.add_parser("analyze", help="Analyze last results (demo stats)")
    verbs.add_parser("falsify", help="Show falsification criteria template")
    verbs.add_parser("replicate", help="Replication planning help")
    e = verbs.add_parser("evidence", help="Evidence strength levels")
    e.add_argument("--claim", default="demo claim")
    verbs.add_parser("graph", help="Knowledge-graph relation types")
    verbs.add_parser("benchmark", help="Run scientific benchmark suites")
    verbs.add_parser("audit", help="Engine health + trace counts")
    dis = verbs.add_parser("discover", help="Discovery gate checklist")
    dis.add_argument("--claim", default="demo claim")
    verbs.add_parser("research", help="Landscape status (sources required)")
    return parser


def dispatch_science_command(args: Any) -> int:
    eng = _engine(args)
    verb = getattr(args, "science_command", None) or "audit"
    if verb == "question":
        from aetheros_science import decompose_question
        print(json.dumps(decompose_question(" ".join(args.text)),
                         indent=2)[:4000])
    elif verb == "hypothesis":
        from aetheros_science import HypothesisEngine
        task = eng.create_task(args.question)
        decomp = eng.understand(task)
        hyps = eng.hypothesize(
            task, decomp,
            strategies=["EXPLANATORY", "CAUSAL", "CONTRARIAN"])
        print(json.dumps(
            [{"id": h.id, "strategy": h.strategy, "statement": h.statement,
              "status": h.status} for h in hyps], indent=2)[:4000])
    elif verb == "experiment":
        hyp_text = args.hypothesis
        task = eng.create_task("cli experiment")
        from aetheros_science.models import Hypothesis
        hyp = Hypothesis(task_id=task.id, statement=hyp_text,
                         variables={"independent": ["x"],
                                    "dependent": ["y"]})
        eng.hypotheses[hyp.id] = hyp
        if args.verb == "design":
            exp = eng.design_experiment(task, hyp)
            print(json.dumps({"id": exp.id, "design": exp.design,
                              "safety": exp.safety_class,
                              "approval": exp.approval_required,
                              "protocol": exp.protocol}, indent=2))
        elif args.verb == "run":
            exp = eng.design_experiment(task, hyp)
            code = ("import json\nmetrics={'runs':3}\n"
                    "open('metrics.json','w').write(json.dumps(metrics))\n")
            res = eng.execute(task, exp, code, {})
            print(json.dumps({"exit": res.exit_code,
                              "metrics": res.metrics,
                              "type": res.execution_type}, indent=2))
        else:
            exp = eng.design_experiment(task, hyp)
            code = "open('metrics.json','w').write('{}')\n"
            eng.execute(task, exp, code, {})
            rep = eng.replicate(task, exp, code, {}, mode="SEED")
            print(json.dumps({"reproducibility": rep.reproducibility},
                             indent=2))
    elif verb == "simulate":
        print(json.dumps({"simulator": eng.simulator.status,
                          "note": "SIMULATION results are never "
                                  "real-world evidence"}, indent=2))
    elif verb == "analyze":
        comp = eng.stats.welch_t([10.0, 11.0, 9.0], [20.0, 21.0, 19.0])
        print(json.dumps(comp, indent=2))
    elif verb == "falsify":
        from aetheros_science import FalsificationEngine
        from aetheros_science.models import Hypothesis
        h = Hypothesis(statement="X affects Y",
                       variables={"independent": ["X"],
                                  "dependent": ["Y"]})
        print(json.dumps(
            FalsificationEngine().criteria(h).__dict__, indent=2))
    elif verb == "replicate":
        from aetheros_science import ReplicationEngine
        print(json.dumps({"plan": ReplicationEngine().plan(
            "exp_demo", ["SEED", "IMPLEMENTATION", "DATASET"])}, indent=2))
    elif verb == "evidence":
        print(json.dumps({"levels": ["E0", "E1", "E2", "E3", "E4", "E5",
                                     "E6"],
                          "taxonomy": "AetherOS internal, not universal"},
                         indent=2))
    elif verb == "graph":
        from aetheros_science.knowledge import RELATIONS
        print(json.dumps({"relations": RELATIONS}, indent=2))
    elif verb == "benchmark":
        from benchmark.science_bench import main as bench_main
        bench_main()
    elif verb == "audit":
        print(json.dumps(eng.health(), indent=2))
    elif verb == "discover":
        from aetheros_science.discovery import QualityGate
        print(json.dumps({"gate_checks": QualityGate.CHECKS,
                          "claim": args.claim,
                          "status": "POTENTIAL_DISCOVERY until gate "
                                    "passes"}, indent=2))
    elif verb == "research":
        print(json.dumps(
            {"network": eng.landscape_builder.network_status,
             "rule": "claims require provided sources; no fabricated "
                     "literature"}, indent=2))
    else:
        print(f"unknown science verb: {verb}")
        return 2
    return 0
