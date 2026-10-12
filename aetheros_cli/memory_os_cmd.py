"""``aetheros memory-os`` — user control surface for the unified memory
layer (Master 18 P19, P62-65).

Footprint Ladder rung 2: CLI command; no new model tools. State lives in
``<AETHEROS_HOME>/memory_os/memory_os.db`` (profile-aware).
"""

from __future__ import annotations

import argparse
import json
import sys

from agent.memory_os.models import MemoryStatus, MemoryType


def _manager():
    from agent.memory_os.manager import MemoryManager

    return MemoryManager()


def _user_ctx(args) -> "AccessContext":  # noqa: F821
    from agent.memory_os.security import AccessContext

    return AccessContext.user(actor_id=getattr(args, "owner", None) or "default",
                              project_id=getattr(args, "project", "") or "")


def cmd_status(args) -> int:
    m = _manager()
    print(json.dumps(m.stats(), indent=2))
    print("controls:", json.dumps(m.controls.to_dict()))
    return 0


def cmd_remember(args) -> int:
    from agent.memory_os.models import MemoryType, MemoryScope, Sensitivity, SourceType

    m = _manager()
    outcome = m.remember(
        args.content,
        type_=MemoryType(args.type),
        scope=MemoryScope(args.scope),
        sensitivity=Sensitivity(getattr(args, "sensitivity", "internal")),
        source_type=SourceType.USER_EXPLICIT,
        project_id=args.project or "",
        semantic_key=args.key or "",
        tags=args.tag or [],
        actor="cli",
        channel="cli",
        explicit=True,
        ctx=_user_ctx(args),
    )
    print(json.dumps({
        "memory_id": outcome.item.memory_id,
        "status": outcome.effective_status.value,
        "needs_confirmation": outcome.needs_confirmation,
        "merged_into": outcome.merged_into,
    }, indent=2))
    return 0


def cmd_search(args) -> int:
    m = _manager()
    res = m.search(args.query, _user_ctx(args), top_k=args.top_k,
                   project_id=args.project)
    if args.json:
        print(json.dumps([{
            "memory_id": h.item.memory_id,
            "type": h.item.type.value,
            "content": h.item.content,
            "score": h.score,
            "explanation": h.explanation(),
        } for h in res.hits], indent=2))
    else:
        for h in res.hits:
            print(f"[{h.score:.2f}] ({h.item.memory_id}) {h.item.type.value}: "
                  f"{h.item.summary or h.item.content[:90]}")
            print(f"         {h.explanation()}")
    if not res.hits:
        print("(no stored memory matched — nothing to fabricate)")
    return 0


def cmd_show(args) -> int:
    m = _manager()
    item = m.get(args.id, _user_ctx(args))
    if item is None:
        print("not found or not authorized", file=sys.stderr)
        return 1
    payload = item.to_row() | {
        "tags": item.tags,
        "provenance": item.provenance.to_dict(),
        "metadata": item.metadata,
        "versions": m.store.versions(item.memory_id),
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_list(args) -> int:
    m = _manager()
    types = [args.type] if args.type else None
    items = m.list(_user_ctx(args), types=types, limit=args.limit)
    for i in items:
        print(f"({i.memory_id}) [{i.status.value}] {i.type.value}: "
              f"{i.summary or i.content[:80]}")
    if not items:
        print("(empty)")
    return 0


def cmd_forget(args) -> int:
    m = _manager()
    ctx = _user_ctx(args)
    ids: list = []
    if args.id and args.id != "all":
        ids = [args.id]
    elif args.query:
        res = m.search(args.query, ctx, top_k=max(1, args.limit))
        ids = [h.item.memory_id for h in res.hits]
    if args.id == "all" and not args.yes:
        print("refusing to forget everything without --yes", file=sys.stderr)
        return 1
    if args.id == "all":
        ids = [i.memory_id for i in m.list(ctx)]
    n = 0
    for mid in ids:
        d = m.forget(mid, ctx)
        n += 1 if d.get("deleted") else 0
        print(f"{mid}: deleted={d.get('deleted')}")
    print(f"forgot {n} memory item(s)")
    return 0


def cmd_candidates(args) -> int:
    m = _manager()
    ctx = _user_ctx(args)
    cands = m.list(ctx, statuses=[MemoryStatus.CANDIDATE])
    if args.approve or args.deny:
        target = args.approve or args.deny
        item = m.confirm_candidate(target, ctx, approve=bool(args.approve))
        print(f"{target}: {'approved' if item else 'denied/absent'}")
        return 0
    for c in cands:
        print(f"({c.memory_id}) {c.type.value}: {c.summary or c.content[:80]}")
    if not cands:
        print("(no candidates awaiting approval)")
    return 0


def cmd_correct(args) -> int:
    m = _manager()
    item = m.update(args.id, args.content, _user_ctx(args), note="correction")
    if item is None:
        print("not found or not authorized", file=sys.stderr)
        return 1
    print(f"updated {item.memory_id} -> v{item.version}")
    return 0


def cmd_feedback(args) -> int:
    from agent.memory_os.models import FeedbackKind

    m = _manager()
    item = m.store.get_item(args.id)
    if item is None:
        print("not found", file=sys.stderr)
        return 1
    m.lifecycle.apply_feedback(item, FeedbackKind(args.kind))
    print(f"feedback recorded on {item.memory_id}")
    return 0


def cmd_link(args) -> int:
    from agent.memory_os.models import RelationshipType

    m = _manager()
    edge = m.link("entity", args.src, RelationshipType(args.rel), "entity",
                  args.dst, confidence=0.7)
    print(f"edge {edge['edge_id']} created")
    return 0


def cmd_graph(args) -> int:
    m = _manager()
    sg = m.graph.subgraph("entity", args.entity, depth=min(3, max(1, args.depth)))
    print(json.dumps(sg, indent=2, default=str))
    return 0


def cmd_export(args) -> int:
    m = _manager()
    result = m.export_items(args.path, _user_ctx(args), fmt=args.format)
    print(json.dumps(result, indent=2))
    return 0


def cmd_import(args) -> int:
    m = _manager()
    stats = m.import_items(args.path, _user_ctx(args),
                           approve_all=bool(args.approve_all))
    print(json.dumps(stats, indent=2))
    return 0


def cmd_backup(args) -> int:
    m = _manager()
    result = m.backup(args.path, encrypt=bool(args.encrypt))
    print(json.dumps(result, indent=2))
    return 0


def cmd_restore(args) -> int:
    m = _manager()
    result = m.restore(args.path, replace=bool(args.replace))
    print(json.dumps(result, indent=2))
    return 0


def cmd_maintenance(args) -> int:
    m = _manager()
    report = m.run_maintenance(dry_run=bool(args.dry_run))
    print(json.dumps(report, indent=2))
    return 0


def cmd_private_mode(args) -> int:
    m = _manager()
    if args.on_off == "on":
        m.controls.private_mode = True
    elif args.on_off == "off":
        m.controls.private_mode = False
    print(f"private mode: {'ON' if m.controls.private_mode else 'OFF'} "
          "(process-local toggle; set per session)")
    return 0


def cmd_audit(args) -> int:
    m = _manager()
    entries = m.audit_entries(limit=args.limit)
    for e in entries:
        print(f"#{e['seq']} {e['action']:<10} actor={e['actor']} "
              f"target={e['target']} {json.dumps(e['detail'])}")
    ok = m.audit_integrity()
    print(f"chain-integrity: {'OK' if ok else 'TAMPERED'}")
    return 0 if ok else 1


def register_memory_os_subparser(subparsers) -> None:
    p = subparsers.add_parser(
        "memory-os", help="unified memory layer: remember/search/forget/graph"
    )
    p.add_argument("--owner", default="default")
    p.add_argument("--project", default="")
    sub = p.add_subparsers(dest="memory_os_cmd")

    sub.add_parser("status").set_defaults(func=cmd_status)

    rp = sub.add_parser("remember")
    rp.add_argument("content")
    rp.add_argument("--type", default="semantic",
                    choices=[t.value for t in MemoryType])
    rp.add_argument("--scope", default="user",
                    choices=["session", "task", "project", "user",
                             "organization"])
    rp.add_argument("--sensitivity", default="internal",
                    choices=["public", "internal", "sensitive"])
    rp.add_argument("--key", default="", help="semantic key for conflicts")
    rp.add_argument("--tag", action="append")
    rp.set_defaults(func=cmd_remember)

    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("--top-k", type=int, default=8)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    hp = sub.add_parser("show")
    hp.add_argument("id")
    hp.set_defaults(func=cmd_show)

    lp = sub.add_parser("list")
    lp.add_argument("--type", default="")
    lp.add_argument("--limit", type=int, default=50)
    lp.set_defaults(func=cmd_list)

    fp = sub.add_parser("forget")
    fp.add_argument("id", nargs="?", default="")
    fp.add_argument("--query", default="")
    fp.add_argument("--limit", type=int, default=5)
    fp.add_argument("--yes", action="store_true")
    fp.set_defaults(func=cmd_forget)

    cp = sub.add_parser("candidates")
    cp.add_argument("--approve", default="")
    cp.add_argument("--deny", default="")
    cp.set_defaults(func=cmd_candidates)

    kp = sub.add_parser("correct")
    kp.add_argument("id")
    kp.add_argument("content")
    kp.set_defaults(func=cmd_correct)

    gp = sub.add_parser("feedback")
    gp.add_argument("id")
    gp.add_argument("kind", choices=["useful", "incorrect", "outdated",
                                     "irrelevant", "private"])
    gp.set_defaults(func=cmd_feedback)

    ep = sub.add_parser("link")
    ep.add_argument("src")
    ep.add_argument("rel")
    ep.add_argument("dst")
    ep.set_defaults(func=cmd_link)

    gg = sub.add_parser("graph")
    gg.add_argument("entity")
    gg.add_argument("--depth", type=int, default=1)
    gg.set_defaults(func=cmd_graph)

    xp = sub.add_parser("export")
    xp.add_argument("path")
    xp.add_argument("--format", default="json",
                    choices=["json", "jsonl", "md", "csv"])
    xp.set_defaults(func=cmd_export)

    ip = sub.add_parser("import")
    ip.add_argument("path")
    ip.add_argument("--approve-all", action="store_true")
    ip.set_defaults(func=cmd_import)

    bp = sub.add_parser("backup")
    bp.add_argument("path")
    bp.add_argument("--encrypt", action="store_true")
    bp.set_defaults(func=cmd_backup)

    rsp = sub.add_parser("restore")
    rsp.add_argument("path")
    rsp.add_argument("--replace", action="store_true")
    rsp.set_defaults(func=cmd_restore)

    mp = sub.add_parser("maintenance")
    mp.add_argument("--dry-run", action="store_true")
    mp.set_defaults(func=cmd_maintenance)

    pp = sub.add_parser("private-mode")
    pp.add_argument("on_off", choices=["on", "off"])
    pp.set_defaults(func=cmd_private_mode)

    ap = sub.add_parser("audit")
    ap.add_argument("--limit", type=int, default=30)
    ap.set_defaults(func=cmd_audit)


def main(args) -> int:
    func = getattr(args, "func", None)
    if func is None:
        cmd_status(args)
        return 0
    return func(args)
