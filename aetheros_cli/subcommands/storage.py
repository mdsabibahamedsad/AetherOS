"""``aetheros storage`` / ``aetheros backup``-plus / ``aetheros recovery`` /
``aetheros sync`` / ``aetheros data`` subcommand parsers (Master 61 §107).

Thin argparse wiring over the canonical ``aetheros_data.api`` backend.
Every command reports real backend state; nothing is faked.
"""

from __future__ import annotations

from typing import Callable


def build_storage_parser(subparsers, *, cmd_storage: Callable) -> None:
    sp = subparsers.add_parser(
        "storage",
        help="Canonical data-layer status and integrity",
        description="Storage health, database stats, integrity and retention state.",
    )
    sp.add_argument("storage_action", nargs="?", default="status",
                    choices=["status", "check", "integrity"])
    sp.set_defaults(func=cmd_storage)


def build_recovery_parser(subparsers, *, cmd_recovery: Callable) -> None:
    sp = subparsers.add_parser(
        "recovery",
        help="Crash recovery and reconciliation",
        description="Interrupted tasks, stale leases, unknown side effects.",
    )
    sp.add_argument("recovery_action", nargs="?", default="status",
                    choices=["status", "reconcile"])
    sp.set_defaults(func=cmd_recovery)


def build_sync_parser(subparsers, *, cmd_sync: Callable) -> None:
    sp = subparsers.add_parser(
        "sync",
        help="Offline-first sync status and controls",
        description="Sync is not backup. Shows devices, queue, conflicts.",
    )
    sp.add_argument("sync_action", nargs="?", default="status",
                    choices=["status", "pause", "resume"])
    sp.set_defaults(func=cmd_sync)


def build_data_parser(subparsers, *, cmd_data: Callable) -> None:
    sp = subparsers.add_parser(
        "data",
        help="Portable export/import, migration, integrity",
        description="Versioned export/import with validation; imports never grant authority.",
    )
    sp.add_argument("data_action", nargs="?", default="integrity",
                    choices=["export", "import", "migrate", "integrity"])
    sp.add_argument("--dest", default=None)
    sp.add_argument("--path", default=None)
    sp.add_argument("--authorize", action="store_true")
    sp.set_defaults(func=cmd_data)
