"""``aetheros capsule`` subcommand parser (Master 58 §77).

Capsule runtime: create, inspect, pause, resume, checkpoint, restore,
migrate, quarantine, destroy, replay, benchmark — plus permissions,
resources, trace, preview, simulate, diff, profiles, isolation, and gc.
"""

from __future__ import annotations

from typing import Callable


def build_capsule_parser(subparsers, *, cmd_capsule: Callable) -> None:
    """Attach the ``capsule`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "capsule",
        help="Manage agent capsules (isolated execution environments)",
        description=(
            "Create, inspect, and control Agent Capsules. Every agent "
            "workload runs inside an explicit, resource-bounded, "
            "authority-bounded capsule governed by the Kernel."
        ),
    )
    sub = parser.add_subparsers(dest="capsule_command", metavar="<subcommand>")

    sub.add_parser("list", aliases=["ls"], help="List capsules").add_argument(
        "--json", action="store_true", help="Output in JSON format")

    create_p = sub.add_parser("create", help="Create a capsule")
    create_p.add_argument("objective", help="Task objective for the capsule agent")
    create_p.add_argument("--profile", default="standard",
                          help="Capsule profile (default: standard)")
    create_p.add_argument("--actor", default="human", help="Intent actor")
    create_p.add_argument("--parent", default=None, help="Parent capsule id")
    create_p.add_argument("--start", action="store_true", help="Start after provisioning")
    create_p.add_argument("--json", action="store_true", help="Output in JSON format")

    for name in ("inspect", "permissions", "resources", "trace"):
        p = sub.add_parser(name, help=f"Show capsule {name}")
        p.add_argument("id", help="Capsule id")
        p.add_argument("--json", action="store_true", help="Output in JSON format")

    for name in ("pause", "resume"):
        p = sub.add_parser(name, help=f"{name.capitalize()} a capsule")
        p.add_argument("id", help="Capsule id")

    cp = sub.add_parser("checkpoint", help="Checkpoint a capsule")
    cp.add_argument("id", help="Capsule id")

    rp = sub.add_parser("restore", help="Restore a capsule snapshot")
    rp.add_argument("snapshot", help="Snapshot integrity hash")

    mg = sub.add_parser("migrate", help="Migrate a capsule (requires --force)")
    mg.add_argument("id", help="Capsule id")
    mg.add_argument("--destination", default="local", help="Migration target")
    mg.add_argument("--force", action="store_true", help="Authorize migration")

    q = sub.add_parser("quarantine", help="Quarantine a capsule (requires --force)")
    q.add_argument("id", help="Capsule id")
    q.add_argument("--reason", default="operator", help="Quarantine reason")
    q.add_argument("--force", action="store_true", help="Authorize quarantine")

    d = sub.add_parser("destroy", help="Destroy a capsule (requires --force)")
    d.add_argument("id", help="Capsule id")
    d.add_argument("--mode", default="graceful",
                   choices=["graceful", "immediate", "forced", "emergency"])
    d.add_argument("--force", action="store_true", help="Authorize destruction")

    r = sub.add_parser("replay", help="Replay capsule actions (observe-only default)")
    r.add_argument("id", help="Capsule id")
    r.add_argument("--mode", default="observe_only",
                   choices=["observe_only", "simulation", "dry_run"])

    pv = sub.add_parser("preview", help="Preview a capsule before launching")
    pv.add_argument("objective", help="Task objective")
    pv.add_argument("--profile", default="standard", help="Capsule profile")

    sm = sub.add_parser("simulate", help="Ask: would this capsule be allowed to do X?")
    sm.add_argument("id", help="Capsule id")
    sm.add_argument("capability", help="Capability to test")
    sm.add_argument("--url", default=None, help="Optional URL input")

    df = sub.add_parser("diff", help="Compare two capsules")
    df.add_argument("a", help="First capsule id")
    df.add_argument("b", help="Second capsule id")

    sub.add_parser("profiles", help="List capsule profiles")
    sub.add_parser("isolation", help="Show isolation capability detection")
    sub.add_parser("benchmark", help="Run the capsule benchmark suite")

    gc = sub.add_parser("gc", help="Garbage-collect expired capsules")
    gc.add_argument("--dry-run", action="store_true", help="Report only")
    gc.add_argument("--force", action="store_true", help="Authorize collection")

    sub.add_parser("leaks", help="Scan for orphan processes/mounts/reservations")

    parser.set_defaults(func=cmd_capsule)
