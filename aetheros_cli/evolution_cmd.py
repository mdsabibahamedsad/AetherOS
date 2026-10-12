"""CLI: ``aetheros evolution …`` (§136) + ``aetheros eval …`` /
``aetheros trace …`` / ``aetheros failures …`` / ``aetheros lessons …``
/ ``aetheros experiment …`` / ``aetheros candidate …`` aliases.

Operates against real backend state (file-backed stores under the
profile home). Follows the build_parser / dispatch_* convention.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _engine(args: Any):
    from aetheros_constants import get_aetheros_home
    from aetheros_self_improvement import SelfImprovementEngine
    try:
        from aetheros_control_plane import UniversalControlPlane
        plane: Any = UniversalControlPlane()
    except Exception:
        plane = None
    return SelfImprovementEngine(get_aetheros_home() / "intelligence",
                                 plane=plane,
                                 tenant=getattr(args, "tenant", "default"))


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "evolution",
        help="Self-evolving intelligence: evals, failures, lessons, "
             "experiments, candidates",
    )
    parser.add_argument("--tenant", default="default")
    verbs = parser.add_subparsers(dest="evolution_command")

    verbs.add_parser("health", help="Store counts + drift + scorecards")

    t = verbs.add_parser("traces", help="List recent traces")
    t.add_argument("--limit", type=int, default=5)

    verbs.add_parser("failures", help="Failure hotspots + clusters")

    verbs.add_parser("lessons", help="List lessons")

    d = verbs.add_parser("drift", help="Observe a metric for drift")
    d.add_argument("--kind", default="latency")
    d.add_argument("--metric", required=True)
    d.add_argument("--value", type=float, required=True)

    p = verbs.add_parser("purge", help="Enforce trace retention")
    p.add_argument("--days", type=float, default=30.0)
    return parser


def build_eval_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "eval", help="Run evaluation suites (offline, budgeted)")
    parser.add_argument("--tenant", default="default")
    verbs = parser.add_subparsers(dest="eval_command")
    verbs.add_parser("capability", help="Run built-in capability suite")
    verbs.add_parser("regression", help="Run built-in regression suite")
    verbs.add_parser("security", help="Run built-in security suite")
    c = verbs.add_parser("compare", help="Compare two stored results")
    c.add_argument("--a", default="")
    c.add_argument("--b", default="")
    return parser


def dispatch_evolution_command(args: Any) -> int:
    eng = _engine(args)
    verb = getattr(args, "evolution_command", None) or "health"
    if verb == "health":
        store = eng.traces
        print(json.dumps({
            "traces": len(store.list(eng.tenant, limit=10000)),
            "failures": len(eng.failures.failures),
            "lessons": len(eng.lessons.lessons),
            "experiments": len(eng.runner.experiments),
            "deployments": len(eng.deploy.deployments),
            "drift_events": len(eng.drift.events),
            "autonomy": eng.autonomy.value}, indent=2))
    elif verb == "traces":
        print(json.dumps(eng.traces.list(eng.tenant,
                                         limit=args.limit), indent=2)[:4000])
    elif verb == "failures":
        print(json.dumps({"hotspots": eng.failures.hotspots(),
                          "clusters": eng.failures.cluster()}, indent=2))
    elif verb == "lessons":
        print(json.dumps(
            [{k: v for k, v in lesson.__dict__.items()}
             for lesson in eng.lessons.lessons.values()], indent=2,
            default=str)[:4000])
    elif verb == "drift":
        ev = eng.drift.observe(args.kind, args.metric, args.value)
        print(json.dumps({"drift": ev.__dict__ if ev else None},
                         indent=2, default=str))
    elif verb == "purge":
        print(json.dumps({"removed": eng.traces.purge_older_than(
            eng.tenant, args.days)}))
    else:
        print(f"unknown evolution verb: {verb}")
        return 2
    return 0


def dispatch_eval_command(args: Any) -> int:
    from aetheros_self_improvement.suites import run_suite
    eng = _engine(args)
    suite = getattr(args, "eval_command", None) or "capability"
    if suite == "compare":
        print(json.dumps({"a": args.a, "b": args.b,
                          "note": "stored-result diff not yet persisted; "
                                  "run suites to produce results"}))
        return 0
    result = run_suite(eng, suite)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("hard_gate_failures", 0) == 0 else 1
