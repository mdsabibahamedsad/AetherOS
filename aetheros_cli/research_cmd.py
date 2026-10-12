"""``aetheros research`` — evidence-backed deep research CLI.

Footprint Ladder rung 2: capability ships as a CLI command guided by the
``research`` skill; no new core model tools are registered. State lives in
``<AETHEROS_HOME>/research/research.db`` (profile-aware).
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def _print_event(event: dict) -> None:
    kind = event.get("kind", "")
    detail = str(event.get("detail", ""))[:100]
    if kind == "phase":
        print(f"┊ {event.get('state', '')} {detail}".rstrip(), file=sys.stderr)
    elif kind == "search":
        print(f"┊ searching: {detail}", file=sys.stderr)
    elif kind == "reading":
        print(f"┊ reading: {detail}", file=sys.stderr)
    elif kind == "warning":
        print(f"┊ WARNING: {detail}", file=sys.stderr)


def _engine(store=None):
    from agent.research.engine import ResearchEngine

    return ResearchEngine(store=store, on_event=_print_event)


def _load_store():
    from agent.research.store import ResearchStore

    return ResearchStore()


def _emit_task_json(task, store) -> None:
    payload = task.to_dict()
    payload["usage"] = store.usage(task.research_id)
    print(json.dumps(payload, indent=2, default=str))


def _depth(value: str):
    from agent.research.models import ResearchDepth

    try:
        return ResearchDepth(value.lower())
    except ValueError:
        raise SystemExit(
            f"invalid depth '{value}' (choose quick|standard|deep|exhaustive)"
        )


def cmd_start(args) -> int:
    store = _load_store()
    engine = _engine(store)
    task = engine.start(
        query=args.query,
        depth=_depth(args.depth),
        sources_allowed=args.allow.split(",") if args.allow else None,
        sources_blocked=args.block.split(",") if args.block else None,
        deadline_seconds=args.deadline,
    )
    if not args.no_run:
        task = engine.run(
            task.research_id,
            report_format=getattr(args, "format", None) or "deep",
            remember=bool(getattr(args, "remember", False)),
        )
    if args.json:
        _emit_task_json(task, store)
    else:
        print(f"research_id: {task.research_id}")
        print(f"status:      {task.status.value}")
        if task.error:
            print(f"error:       {task.error}")
    if task.status.value == "FAILED":
        return 2
    if args.no_run or task.status.value == "COMPLETED":
        return 0
    return 1


def cmd_run(args) -> int:
    store = _load_store()
    engine = _engine(store)
    task = engine.run(
        args.id,
        report_format=getattr(args, "format", None) or "deep",
        remember=bool(getattr(args, "remember", False)),
    )
    if args.json:
        _emit_task_json(task, store)
    else:
        print(f"status: {task.status.value}")
    return 0 if task.status.value == "COMPLETED" else 1


def cmd_pause(args) -> int:
    store = _load_store()
    engine = _engine(store)
    ok = engine.pause(args.id)
    print("pause requested" if ok else f"cannot pause {args.id} (missing or terminal)")
    return 0 if ok else 1


def cmd_ingest(args) -> int:
    store = _load_store()
    engine = _engine(store)
    try:
        result = engine.add_local_document(args.id, args.path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def cmd_mcp_evidence(args) -> int:
    store = _load_store()
    engine = _engine(store)
    result = engine.add_mcp_evidence(args.id, args.server, args.tool, args.text)
    print(json.dumps(result, indent=2))
    return 0


def cmd_graph(args) -> int:
    store = _load_store()
    graph = store.load_graph(args.id)
    if not graph.entities:
        print("no knowledge graph yet (run a task first)")
        return 1
    data = graph.to_dict()
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    for e in data["entities"]:
        aliases = f" (aka {', '.join(e['aliases'])})" if e["aliases"] else ""
        print(f"[{e['etype']}] {e['name']}{aliases} conf={e['confidence']:.2f}")
    for r in data["edges"]:
        names = {x["entity_id"]: x["name"] for x in data["entities"]}
        print(f"  {names.get(r['src_id'], r['src_id'])} --{r['relation']}--> "
              f"{names.get(r['dst_id'], r['dst_id'])} conf={r['confidence']:.2f}")
    return 0


def cmd_eval(args) -> int:
    store = _load_store()
    from agent.research.reports import (
        ReportContext,
        citation_coverage,
        quality_metric,
    )
    from agent.research.adversarial import detect_bias

    task = store.get_task(args.id)
    if not task:
        print(f"unknown research id: {args.id}", file=sys.stderr)
        return 2
    ctx = ReportContext(
        task=task,
        sources=store.list_sources(args.id),
        claims=store.list_claims(args.id),
        contradictions=store.list_contradictions(args.id),
        usage=store.usage(args.id),
    )
    payload = {
        "citation_coverage": citation_coverage(ctx.claims),
        "quality": quality_metric(ctx),
        "bias": detect_bias(ctx.sources, ctx.claims).__dict__,
        "usage": ctx.usage,
        "duplicate_events": sum(
            1 for e in store.get_events(args.id) if e["kind"] == "duplicate"
        ),
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_schedule(args) -> int:
    from agent.research.scheduler_bridge import cancel_scheduled, schedule_research

    if args.off:
        ok = cancel_scheduled(args.id)
        print("monitor removed" if ok else "no monitor job found")
        return 0 if ok else 1
    task = _load_store().get_task(args.id)
    if not task:
        print(f"unknown research id: {args.id}", file=sys.stderr)
        return 2
    job = schedule_research(args.id, task.user_query, every=args.every,
                            deliver=args.deliver)
    print(json.dumps(job if isinstance(job, dict) else {"job": str(job)}, indent=2, default=str)[:800])
    return 0


def cmd_list(_args) -> int:
    store = _load_store()
    tasks = store.list_tasks()
    if not tasks:
        print("no research tasks")
        return 0
    print(f"{'ID':<14} {'STATUS':<13} {'DEPTH':<11} QUERY")
    for t in tasks:
        print(f"{t.research_id:<14} {t.status.value:<13} {t.depth.value:<11} {t.user_query[:60]}")
    return 0


def cmd_show(args) -> int:
    store = _load_store()
    task = store.get_task(args.id)
    if not task:
        print(f"unknown research id: {args.id}", file=sys.stderr)
        return 2
    transitions = store.get_transitions(args.id)
    sources = store.list_sources(args.id)
    claims = store.list_claims(args.id)
    if args.json:
        print(
            json.dumps(
                {
                    "task": task.to_dict(),
                    "transitions": [t.to_dict() for t in transitions],
                    "sources": [s.to_dict() for s in sources],
                    "claims": [
                        c.to_dict() for c in claims if args.claims or c.has_evidence
                    ],
                    "usage": store.usage(args.id),
                },
                indent=2,
                default=str,
            )
        )
        return 0
    print(f"query:   {task.user_query}")
    print(f"id:      {task.research_id}")
    print(f"status:  {task.status.value}  depth={task.depth.value} confidence={task.confidence}")
    print(f"states:  {' -> '.join(t.to_status for t in transitions)}")
    quarantined = sum(1 for s in sources if s.quarantined)
    print(f"sources: {len(sources)} ({quarantined} quarantined)")
    statuses: dict = {}
    for c in claims:
        statuses[c.status.value] = statuses.get(c.status.value, 0) + 1
    if statuses:
        print("claims:  " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    for s in sources[:10]:
        flag = " [QUARANTINED]" if s.quarantined else ""
        print(f"  - [{s.source_type.value}] {s.title or s.url}{flag}")
        print(f"    {s.url}")
    if len(sources) > 10:
        print(f"  ... and {len(sources) - 10} more")
    return 0


def cmd_report(args) -> int:
    store = _load_store()
    task = store.get_task(args.id)
    if not task:
        print(f"unknown research id: {args.id}", file=sys.stderr)
        return 2
    fmt = getattr(args, "format", None)
    if fmt and fmt != "deep":
        engine = _engine(store)
        text, _warnings = engine.render_report(task, fmt=fmt)
        print(text)
        return 0
    if not task.final_report:
        print("report not generated yet (task not COMPLETED)", file=sys.stderr)
        return 1
    print(task.final_report)
    return 0


def cmd_cancel(args) -> int:
    engine = _engine(_load_store())
    ok = engine.cancel(args.id)
    print("cancelled" if ok else f"cannot cancel {args.id} (missing or terminal)")
    return 0 if ok else 1


def register_research_subparser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "research",
        help="Evidence-backed web research with citations and provenance.",
        description=(
            "Run multi-query web research through the configured search/extract "
            "backends (`aetheros tools`). Produces source-normalized, "
            "deduplicated, injection-screened evidence with validated "
            "citations. Interrupted tasks resume without duplicating work."
        ),
        epilog=(
            "Examples:\n"
            '  aetheros research start "what changed in MCP spec 2026"\n'
            '  aetheros research start --depth quick "xai grok api pricing"\n'
            "  aetheros research list\n"
            "  aetheros research show <id> --json\n"
            "  aetheros research report <id>\n"
            "  aetheros research cancel <id>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subs = parser.add_subparsers(dest="research_command")

    p_start = subs.add_parser("start", help="Create and run a new research task")
    p_start.add_argument("query", help="Research question")
    p_start.add_argument("--depth", default="standard",
                         choices=["quick", "standard", "deep", "exhaustive"])
    p_start.add_argument("--format", default="deep",
                         choices=["deep", "brief", "executive", "comparison",
                                  "timeline", "decision_memo"])
    p_start.add_argument("--allow", default=None,
                         help="Comma-separated registrable domains allowlist")
    p_start.add_argument("--block", default=None,
                         help="Comma-separated registrable domains denylist")
    p_start.add_argument("--deadline", type=float, default=None,
                         help="Wall-clock budget in seconds")
    p_start.add_argument("--no-run", action="store_true",
                         help="Plan only; run later via `research resume`")
    p_start.add_argument("--remember", action="store_true",
                         help="Opt-in: write strongest findings to memory "
                              "with provenance metadata")
    p_start.add_argument("--json", action="store_true")
    p_start.set_defaults(func=lambda a: sys.exit(cmd_start(a)))

    p_resume = subs.add_parser("resume", aliases=["run"],
                               help="Resume/run an existing research task")
    p_resume.add_argument("id")
    p_resume.add_argument("--format", default=None,
                          choices=["deep", "brief", "executive", "comparison",
                                   "timeline", "decision_memo"])
    p_resume.add_argument("--remember", action="store_true")
    p_resume.add_argument("--json", action="store_true")
    p_resume.set_defaults(func=lambda a: sys.exit(cmd_run(a)))

    p_pause = subs.add_parser("pause", help="Pause a running task at the next step boundary")
    p_pause.add_argument("id")
    p_pause.set_defaults(func=lambda a: sys.exit(cmd_pause(a)))

    p_ingest = subs.add_parser("ingest",
                               help="Ingest a local document as private evidence")
    p_ingest.add_argument("id")
    p_ingest.add_argument("path")
    p_ingest.set_defaults(func=lambda a: sys.exit(cmd_ingest(a)))

    p_mcp = subs.add_parser("mcp-evidence",
                            help="Record MCP tool output as untrusted evidence")
    p_mcp.add_argument("id")
    p_mcp.add_argument("server")
    p_mcp.add_argument("tool")
    p_mcp.add_argument("text")
    p_mcp.set_defaults(func=lambda a: sys.exit(cmd_mcp_evidence(a)))

    p_graph = subs.add_parser("graph", aliases=["kg"],
                              help="Show the research knowledge graph")
    p_graph.add_argument("id")
    p_graph.add_argument("--json", action="store_true")
    p_graph.set_defaults(func=lambda a: sys.exit(cmd_graph(a)))

    p_eval = subs.add_parser("eval",
                             help="Print citation-coverage/quality/bias metrics")
    p_eval.add_argument("id")
    p_eval.set_defaults(func=lambda a: sys.exit(cmd_eval(a)))

    p_sched = subs.add_parser("schedule",
                              help="Recurring monitor job via the cron scheduler")
    p_sched.add_argument("id")
    p_sched.add_argument("--every", default="1d")
    p_sched.add_argument("--deliver", default=None)
    p_sched.add_argument("--off", action="store_true",
                         help="Remove the monitor job instead")
    p_sched.set_defaults(func=lambda a: sys.exit(cmd_schedule(a)))

    p_list = subs.add_parser("list", aliases=["ls"], help="List research tasks")
    p_list.set_defaults(func=lambda a: sys.exit(cmd_list(a)))

    p_show = subs.add_parser("show", help="Show one research task's state")
    p_show.add_argument("id")
    p_show.add_argument("--claims", action="store_true",
                        help="Include unevidenced claims in --json output")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=lambda a: sys.exit(cmd_show(a)))

    p_report = subs.add_parser("report", help="Print the final markdown report")
    p_report.add_argument("id")
    p_report.add_argument("--format", default=None,
                          choices=["deep", "brief", "executive", "comparison",
                                   "timeline", "decision_memo"])
    p_report.set_defaults(func=lambda a: sys.exit(cmd_report(a)))

    p_cancel = subs.add_parser("cancel", help="Cancel a running/paused task")
    p_cancel.add_argument("id")
    p_cancel.set_defaults(func=lambda a: sys.exit(cmd_cancel(a)))

    parser.set_defaults(func=lambda a: (
        parser.print_help(),
        sys.exit(2),
    ))
    return parser
