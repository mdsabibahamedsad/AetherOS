"""`aetheros quality` — Master 20 quality/release-gate CLI surface.

Read-only reporting over the agent.quality engines plus the documented
known-issue seed. Gate/scorecard evaluation consumes an explicit JSON file
of measured gate inputs; missing input means the gate is reported as never
evaluated (BLOCK), never fabricated.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from agent.quality.benchmarks import BaselineStore
from agent.quality.gates import GATE_NAMES, GateInput, ReleaseGateEngine
from agent.quality.knowledge import KnownIssuesDatabase, seed_documented_issues


def build_quality_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "quality",
        help="Quality engine: gates, scorecards, baselines, known issues",
        description=(
            "Master 20 evaluation layer. Reports release gates, the "
            "release scorecard, recorded baselines and known issues.\n\n"
            "`gate`/`scorecard` read measured gate inputs from a JSON file "
            "({\"gate\": ..., \"checks_passed\": N, ...}[...]); gates "
            "without input are reported as never evaluated."
        ),
    )
    sub = parser.add_subparsers(dest="quality_action")

    sub.add_parser("status", help="Overview of the quality subsystem")
    sub.add_parser("baselines", help="List recorded evaluation baselines")
    sub.add_parser("known-issues", help="List known issues (seeded + open)")
    gate_p = sub.add_parser("gate", help="Evaluate the seven release gates")
    gate_p.add_argument("inputs", nargs="?", default=None,
                        help="Path to gate-inputs JSON (optional)")
    card_p = sub.add_parser("scorecard",
                            help="Print the full release scorecard JSON")
    card_p.add_argument("inputs", nargs="?", default=None,
                        help="Path to gate-inputs JSON (optional)")

    parser.set_defaults(func=cmd_quality)


def _load_gate_inputs(path: str) -> List[GateInput]:
    if not path:
        return []
    with open(path, "r", encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict):
        raw = [raw]
    return [GateInput(gate=item["gate"],
                      checks_passed=int(item.get("checks_passed", 0)),
                      checks_failed=int(item.get("checks_failed", 0)),
                      critical_failures=int(
                          item.get("critical_failures", 0)),
                      details=str(item.get("details", "")))
            for item in raw]


def _print_gates(scorecard) -> None:
    for g in scorecard.gates:
        line = f"  {g.gate:<14} {g.status.value:<6}"
        if g.blocking_reason:
            line += f"  ({g.blocking_reason})"
        elif g.details:
            line += f"  {g.details}"
        print(line)


def cmd_quality(args: argparse.Namespace) -> None:
    action = getattr(args, "quality_action", None)

    if action in ("gate", "scorecard"):
        from agent.quality.models import GateStatus

        inputs = _load_gate_inputs(getattr(args, "inputs", None))
        scorecard = ReleaseGateEngine().evaluate(
            inputs, version=getattr(args, "version", "") or "unspecified")
        if action == "scorecard":
            print(json.dumps(scorecard.to_dict(), indent=2))
            return
        print(f"Release gates ({scorecard.version}):")
        _print_gates(scorecard)
        blocking = [g for g in scorecard.gates
                    if g.status is GateStatus.BLOCK]
        verdict = "BLOCKED" if blocking else "READY"
        print(f"\nVerdict: {verdict}")
        sys.exit(1 if blocking else 0)

    if action == "baselines":
        store = BaselineStore()
        rows = store.all()
        if not rows:
            print(f"No baselines recorded yet.")
            print(f"  Record one via agent.quality.BaselineStore "
                  f"(stored under ~/.aetheros/quality/baselines.json)")
            return
        print(f"{len(rows)} baseline(s):")
        for b in rows:
            n = len(b.metrics)
            print(f"  {b.baseline_id}  {b.label:<18} v{b.version}  "
                  f"{n} metric(s)")
        return

    if action == "known-issues":
        db = KnownIssuesDatabase()
        seed_documented_issues(db)
        open_issues = db.open_issues()
        print(f"{len(open_issues)} open known issue(s) "
              f"(documented pre-existing clusters):")
        for i in open_issues:
            print(f"  [{i.severity:^8}] {i.issue_id}: {i.title}")
            print(f"             workaround: {i.workaround}")
        return

    # status overview
    db = KnownIssuesDatabase()
    seed_documented_issues(db)
    store = BaselineStore()
    print("Aetheros quality engine (Master 20)")
    print(f"  gates defined:     {len(GATE_NAMES)} "
          f"({', '.join(GATE_NAMES)})")
    print(f"  baselines stored:  {len(store.all())}")
    print(f"  open known issues: {len(db.open_issues())}")
    print("\nNext:")
    print("  aetheros quality gate <inputs.json>   evaluate release gates")
    print("  aetheros quality scorecard <inputs>   full scorecard JSON")
    print("  aetheros quality known-issues         pre-existing clusters")
