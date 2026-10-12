"""`aetheros benchmark` CLI (P71-72): list / run / compare / report /
leaderboard / export / verify. Integrated into the existing argparse tree
without touching any other command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESULTS_DIR_DEFAULT = "benchmark/results"


def build_benchmark_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "benchmark",
        help="Universal agent benchmark lab (Master 21)",
        description=(
            "Reproducible head-to-head agent benchmarks. Detection and "
            "reporting are free; real task runs cost tokens and execute "
            "only with --allow-live."
        ),
    )
    sub = parser.add_subparsers(dest="benchmark_action")

    sub.add_parser("list", help="List agents (health), categories, dataset")
    sub.add_parser("verify", help="Validate dataset + result artifacts")

    run_p = sub.add_parser("run", help="Run a suite for an agent")
    run_p.add_argument("--agent", required=True,
                       help="aetheros|hermes|openclaw|openhands|claude-code|codex")
    run_p.add_argument("--suite", default="all",
                       help="'all' or a category name or comma-list")
    run_p.add_argument("--tasks", default="", help="comma-separated task_ids")
    run_p.add_argument("--repeats", type=int, default=None,
                       help="override per-task repetition count")
    run_p.add_argument("--results-dir", default=RESULTS_DIR_DEFAULT)
    run_p.add_argument("--allow-live", action="store_true",
                       help="REQUIRED to execute real model-backed runs "
                            "(spends tokens)")

    cmp_p = sub.add_parser("compare", help="AetherOS vs baseline deltas")
    cmp_p.add_argument("--baseline", default="hermes")
    cmp_p.add_argument("--results-dir", default=RESULTS_DIR_DEFAULT)

    rep_p = sub.add_parser("report", help="Generate markdown reports")
    rep_p.add_argument("--results-dir", default=RESULTS_DIR_DEFAULT)
    rep_p.add_argument("--out", default="AETHEROS_BENCHMARK_REPORT.md")

    lb_p = sub.add_parser("leaderboard", help="Print the local leaderboard")
    lb_p.add_argument("--results-dir", default=RESULTS_DIR_DEFAULT)

    exp_p = sub.add_parser("export", help="Export results JSON+JSONL paths")
    exp_p.add_argument("--results-dir", default=RESULTS_DIR_DEFAULT)

    parser.set_defaults(func=cmd_benchmark)


def cmd_benchmark(args: argparse.Namespace) -> None:
    action = getattr(args, "benchmark_action", None)
    if action == "list":
        _cmd_list()
    elif action == "verify":
        _cmd_verify(args)
    elif action == "run":
        _cmd_run(args)
    elif action == "compare":
        _cmd_compare(args)
    elif action == "report":
        _cmd_report(args)
    elif action == "leaderboard":
        _cmd_leaderboard(args)
    elif action == "export":
        _cmd_export(args)
    else:
        print("usage: aetheros benchmark {list,verify,run,compare,"
              "report,leaderboard,export}")


def _cmd_list() -> None:
    from benchmark.adapters import all_adapters
    from benchmark.dataset import category_balance, load_tasks

    print(f"{'agent':<12} {'health':<16} version")
    for name, adapter in all_adapters().items():
        h = adapter.health_check()
        print(f"{name:<12} {h.status:<16} {h.version}")
    tasks = load_tasks()
    cats = category_balance(tasks)
    print(f"\ndataset: {len(tasks)} tasks across {len(cats)} categories")
    for cat, n in cats.items():
        print(f"  {cat}: {n}")


def _cmd_verify(args) -> None:
    from benchmark.dataset import verify_dataset
    report = verify_dataset()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["ok"] else 1)


def _cmd_run(args) -> None:
    from benchmark.controller import BenchmarkController
    categories = None
    if args.suite != "all":
        categories = [c.strip() for c in args.suite.split(",")]
    task_ids = [t.strip() for t in args.tasks.split(",")] \
        if args.tasks else None
    ctrl = BenchmarkController(Path(args.results_dir))
    manifest = ctrl.run_suite(
        args.agent, categories=categories, task_ids=task_ids,
        repeats_override=args.repeats, allow_live=args.allow_live)
    print(json.dumps(manifest, indent=2, default=str))
    if not args.allow_live:
        print("\nNOTE: recorded BLOCKED rows (live execution disabled). "
              "Re-run with --allow-live to spend tokens on real runs.")


def _cmd_compare(args) -> None:
    from benchmark.comparison import HeadToHead
    ctrl = _controller(args.results_dir)
    results = ctrl.load_results()
    try:
        table = HeadToHead("aetheros", args.baseline,
                           results).table()
    except ValueError as exc:
        print(f"INSUFFICIENT EVIDENCE: {exc}")
        sys.exit(2)
    print(json.dumps(table, indent=2, default=str))
    if table["fairness_flags"]:
        print("FAIRNESS_WARNINGS present; comparison labeled "
              "NOT_DIRECTLY_COMPARABLE.", file=sys.stderr)


def _cmd_report(args) -> None:
    from benchmark.reports import ReportBuilder
    md = ReportBuilder(Path(args.results_dir)).full_report()
    Path(args.out).write_text(md, encoding="utf-8")
    print(f"report written: {args.out}")


def _cmd_leaderboard(args) -> None:
    from benchmark.reports import ReportBuilder
    print(ReportBuilder(Path(args.results_dir)).leaderboard_md())


def _cmd_export(args) -> None:
    rd = Path(args.results_dir)
    jsonl = rd / "results.jsonl"
    if not jsonl.exists():
        print("no results.jsonl yet — nothing exported")
        return
    out = {"results_jsonl": str(jsonl),
           "traces_dir": str(rd / "traces"),
           "manifests": sorted(p.name for p in rd.glob("manifest-*.json"))}
    print(json.dumps(out, indent=2))


def _controller(results_dir: str):
    from benchmark.controller import BenchmarkController
    return BenchmarkController(Path(results_dir))
