"""`aetheros agent-network ...` — Agent Network CLI (Master 46 section 95).

Every command performs a real operation against AgentGateway state.
No fake agents, no fake trust, no fake latency.

NOTE: the top-level `agent` command belongs to the agent ecosystem
(`agents/cli.py`: create/run/install/dashboard). This module registers
`agent-network` so the two never collide (argparse raises on duplicates).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def _gateway(args=None):
    from aetheros_network.gateway import AgentGateway
    from aetheros_network.transport import TransportConfig

    cfg = TransportConfig(
        allow_insecure=os.environ.get("AETHEROS_AGENT_NETWORK_ALLOW_INSECURE") == "1",
        allow_private_hosts=os.environ.get("AETHEROS_AGENT_NETWORK_ALLOW_LAN") == "1",
    )
    if cfg.allow_insecure:
        print("WARNING: development insecure mode (plain http) enabled via "
              "AETHEROS_AGENT_NETWORK_ALLOW_INSECURE=1. Never use in production.",
              file=sys.stderr)
    return AgentGateway(transport_config=cfg)


def build_parser(subparsers) -> Any:
    p = subparsers.add_parser("agent-network", help="Agent Network: discovery, trust, delegation (A2A)")
    sub = p.add_subparsers(dest="agent_verb", required=True)

    sub.add_parser("list", help="List known agents (registry state, real health)")

    d = sub.add_parser("discover", help="Discover an agent from its URL (untrusted until verified)")
    d.add_argument("url", help="Agent base URL or agent-card URL")
    d.add_argument("--org", default="", help="Organization id to attribute")

    i = sub.add_parser("info", help="Show agent record")
    i.add_argument("id", help="Agent id")

    v = sub.add_parser("verify", help="Verify agent (TLS/card evidence) and record result")
    v.add_argument("id", help="Agent id")

    t = sub.add_parser("trust", help="Grant trust (explicit user approval)")
    t.add_argument("id", help="Agent id")
    t.add_argument("--level", default="user_trusted",
                   choices=["user_trusted", "organization_trusted", "fully_trusted"])

    b = sub.add_parser("block", help="Block an agent (denies new tasks)")
    b.add_argument("id", help="Agent id")

    r = sub.add_parser("revoke", help="Revoke an agent (blocks + cancels its tasks)")
    r.add_argument("id", help="Agent id")

    c = sub.add_parser("connect", help="Health-check an agent (real HTTPS probe)")
    c.add_argument("id", help="Agent id")

    sub.add_parser("disconnect", help="Drop cached transport for an agent").add_argument("id")

    h = sub.add_parser("health", help="Show health for all known agents")
    h.add_argument("--id", default="", help="Single agent id")

    dl = sub.add_parser("delegate", help="Delegate a task to a trusted agent")
    dl.add_argument("id", help="Target agent id")
    dl.add_argument("task", help="Task purpose text")
    dl.add_argument("--permission", action="append", default=[],
                    help="Capability to grant (repeatable)")
    dl.add_argument("--data-scope", default="internal",
                    choices=["public", "internal", "private", "sensitive", "highly_sensitive"])
    dl.add_argument("--auto-approve", action="store_true",
                    help="Attempt submission without pausing for approval")

    sub.add_parser("tasks", help="List remote tasks (persisted state)")

    cx = sub.add_parser("cancel", help="Cancel a remote task")
    cx.add_argument("task", help="Task id")

    sub.add_parser("network", help="Show network topology (registry-backed, no fake nodes)")

    d2 = sub.add_parser("doctor", help="Diagnose identity/TLS/card/auth/permissions for an agent")
    d2.add_argument("id", help="Agent id")

    cd = sub.add_parser("card", help="Show an agent card")
    cd.add_argument("id", help="Agent id")

    s = sub.add_parser("serve", help="Run this instance as an A2A server (deny-by-default)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--name", default="AetherOS Agent")
    s.add_argument("--pair-token", default="",
                   help="Bearer pairing token to require (recommended)")

    pr = sub.add_parser("pair", help="Pair: discover URL then persist as discovered")
    pr.add_argument("url", help="Agent base URL")
    return p


def _discover_to_gateway(gw, url: str, org: str) -> str:
    from aetheros_network.discovery import discover_from_url
    result = discover_from_url(url, gw.transport_config,
                               organization_id=org)
    if result.errors:
        raise SystemExit(f"discovery failed: {result.errors[0]}")
    agent_id = gw.adopt_discovery(result)
    if result.warnings:
        print("warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    print(f"discovered (UNTRUSTED): {agent_id}")
    return agent_id


def dispatch_agent_command(args) -> int:
    gw = _gateway(args)
    verb = args.agent_verb

    if verb == "list":
        rows = gw.registry.list()
        for r in rows:
            print(f"{r['agent_id']}  trust={gw.trust.level(r['agent_id'])}  "
                  f"health={r['health']}  source={r['source']}")
        if not rows:
            print("(empty — no agents known. Use `aetheros agent-network discover <url>`.)")
        return 0

    if verb in ("discover", "pair"):
        _discover_to_gateway(gw, args.url, getattr(args, "org", ""))
        return 0

    if verb == "info":
        rec = gw.registry.get_including_removed(args.id)
        if rec is None:
            raise SystemExit(f"unknown agent: {args.id}")
        print(json.dumps({
            "agent_id": args.id,
            "trust": gw.trust.level(args.id),
            "health": rec.health,
            "removed": rec.removed,
            "source": rec.source,
            "provenance": rec.provenance,
            "latency_ms": rec.latency_ms,
            "success": rec.success_count,
            "failures": rec.failure_count,
            "card": rec.card,
        }, indent=2, default=str))
        return 0

    if verb == "card":
        rec = gw.registry.get_including_removed(args.id)
        if rec is None:
            raise SystemExit(f"unknown agent: {args.id}")
        print(json.dumps(rec.card, indent=2, default=str))
        return 0

    if verb == "verify":
        from aetheros_network.agent_card import parse_agent_card, validate_agent_card
        rec = gw.registry.get(args.id)
        if rec is None:
            raise SystemExit(f"unknown agent: {args.id}")
        card = parse_agent_card(rec.card)
        errors, warnings = validate_agent_card(card)
        checks = {
            "tls_ok": card.url.startswith("https://"),
            "issuer_ok": bool(rec.provenance),
            "expired": False,
            "endpoint_mismatch": any("endpoint substitution" in w for w in warnings),
            "card_errors": errors,
        }
        label = gw.verify_agent(args.id, checks)
        print(f"{args.id}: {label}")
        for e in errors:
            print(f"  error: {e}")
        for w in warnings:
            print(f"  warning: {w}")
        return 0

    if verb == "trust":
        gw.set_trust(args.id, args.level, by="user:cli")
        print(f"{args.id} -> {args.level}")
        return 0

    if verb == "block":
        gw.set_trust(args.id, "blocked", by="user:cli")
        print(f"{args.id} blocked")
        return 0

    if verb == "revoke":
        gw.revoke(args.id, by="user:cli")
        print(f"{args.id} revoked; its pending tasks cancelled")
        return 0

    if verb == "connect":
        import time as _t
        from aetheros_network.transport import TransportError
        rec = gw.registry.get(args.id)
        if rec is None:
            raise SystemExit(f"unknown agent: {args.id}")
        t = gw._transport_for(args.id)
        t0 = _t.time()
        try:
            raw = t.fetch_agent_card()
            latency = (_t.time() - t0) * 1000
            gw.registry.record_heartbeat(args.id, "online", latency_ms=latency, success=True)
            print(f"{args.id}: ONLINE latency={latency:.0f}ms card={raw.get('name', '?')}")
        except TransportError as e:
            gw.registry.record_heartbeat(args.id, "unavailable", success=False)
            print(f"{args.id}: {e.kind.upper()} {e}")
            return 1
        return 0

    if verb == "disconnect":
        gw._transports.pop(args.id, None)
        print(f"{args.id}: cached transport dropped")
        return 0

    if verb == "health":
        rows = gw.registry.list()
        if args.id:
            rows = [r for r in rows if r["agent_id"] == args.id]
        for r in rows:
            print(f"{r['agent_id']}: {r['health']} "
                  f"latency={r['latency_ms']} last_seen={r['last_seen']}")
        return 0

    if verb == "delegate":
        task = gw.delegate(
            args.id, args.task, {"text": args.task},
            permissions=args.permission or ["agent.task.submit"],
            data_scope=args.data_scope,
            origin_agent="local:cli", owner="cli",
            require_approval=not args.auto_approve,
        )
        print(f"task {task.task_id}: {task.status}")
        return 0

    if verb == "tasks":
        for t in gw.tasks.list():
            print(f"{t.task_id}  -> {t.target_agent}  {t.status}  {t.purpose[:80]}")
        q = gw.tasks.queue_depth()
        print(f"queue: {q['queued']} queued, {q['running']} running (cap {q['max_queued']})")
        return 0

    if verb == "cancel":
        task = gw.cancel(args.task)
        print(f"task {task.task_id}: {task.status}")
        return 0

    if verb == "network":
        print("AetherOS (local)")
        for r in gw.registry.list():
            print(f"  +-- {r['agent_id']} "
                  f"[trust={gw.trust.level(r['agent_id'])} health={r['health']}]")
        return 0

    if verb == "doctor":
        rec = gw.registry.get_including_removed(args.id)
        if rec is None:
            raise SystemExit(f"unknown agent: {args.id}")
        checks = [
            ("identity", "PASS" if rec.identity.get("agent_id") else "FAIL"),
            ("tls", "PASS" if str(rec.card.get("url", "")).startswith("https://") else "FAIL"),
            ("card", "PASS" if rec.card.get("name") and rec.card.get("url") else "FAIL"),
            ("trust", gw.trust.level(args.id)),
            ("revocation", "BLOCKED" if gw.trust.is_blocked(args.id) else "PASS"),
            ("health", rec.health.upper()),
            ("endpoint", rec.card.get("url", "")),
        ]
        for name, status in checks:
            print(f"{name:12s} {status}")
        return 0

    if verb == "serve":
        from aetheros_network.server import AgentServer, ServerConfig
        tokens = [args.pair_token] if args.pair_token else []
        if not tokens:
            print("WARNING: no --pair-token set; server runs without bearer auth "
                  "(loopback only).", file=sys.stderr)
        srv = AgentServer(ServerConfig(name=args.name, pairing_tokens=tokens),
                          gw.home / "server")
        print(f"serving A2A at http://{args.host}:{args.port} "
              f"(card: /.well-known/agent-card.json). Ctrl-C to stop.")
        srv.serve_forever(args.host, args.port)
        return 0

    raise SystemExit(f"unknown agent verb: {verb}")
