"""CLI for the Universal Control Plane — ``aetheros governance …``.

Thin argparse surface over :mod:`aetheros_control_plane`. All verbs
operate against real backend state (in-process plane + persisted
policy). Follows the ``build_parser`` / ``dispatch_*`` convention used
by kanban/marketplace/media.
"""

from __future__ import annotations

import argparse
from typing import Any


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "governance",
        help="Universal control plane: identity, trust, policy, audit",
    )
    verbs = parser.add_subparsers(dest="governance_command")

    p = verbs.add_parser("policy-check", help="Evaluate a capability/resource")
    p.add_argument("--cap", default="filesystem.read")
    p.add_argument("--resource", default="/workspace/project")
    p.add_argument("--tenant", default="default")

    verbs.add_parser("health", help="Control-plane health + audit integrity")
    verbs.add_parser("audit-verify", help="Verify audit hash chain")

    e = verbs.add_parser("emergency-stop", help="Halt execution by scope")
    e.add_argument("--scope", default="global",
                   choices=["action", "task", "agent", "swarm",
                            "all_autonomous", "all_remote", "global"])
    e.add_argument("--target", default="")
    e.add_argument("--reason", default="manual operator stop")
    e.add_argument("--resume", action="store_true")

    q = verbs.add_parser("quarantine", help="Hold/release/list quarantine")
    q.add_argument("verb", choices=["hold", "release", "list"], nargs="?",
                   default="list")
    q.add_argument("--identity", default="")
    q.add_argument("--reason", default="manual")

    s = verbs.add_parser("simulate",
                         help="Dry-run: what happens if agent X does Y?")
    s.add_argument("--cap", required=True)
    s.add_argument("--resource", default="*")
    s.add_argument("--data-class", default="internal")
    return parser


def dispatch_governance_command(args: Any) -> int:
    from aetheros_control_plane.cli import main as cp_main

    verb = getattr(args, "governance_command", None) or "health"
    if verb == "policy-check":
        return cp_main(["policy", "check", "--cap", args.cap,
                        "--resource", args.resource, "--tenant",
                        args.tenant])
    if verb == "health":
        return cp_main(["health"])
    if verb == "audit-verify":
        return cp_main(["audit", "verify"])
    if verb == "emergency-stop":
        cmd = ["emergency-stop", "--scope", args.scope,
               "--target", args.target, "--reason", args.reason]
        if args.resume:
            cmd.append("--resume")
        return cp_main(cmd)
    if verb == "quarantine":
        cmd = ["quarantine", args.verb]
        if args.identity:
            cmd += ["--identity", args.identity]
        if args.reason:
            cmd += ["--reason", args.reason]
        return cp_main(cmd)
    if verb == "simulate":
        return cp_main(["policy", "simulate", "--cap", args.cap,
                        "--resource", args.resource])
    print(f"unknown governance verb: {verb}")
    return 2
