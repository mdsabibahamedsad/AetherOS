"""``aetheros reliability`` subcommand parser.

Extracted into a parser module following the same pattern as ``cron.py`` and
``doctor.py``: the handler is injected via ``cmd_reliability`` so this module
does not import ``main`` (cycle avoidance).
"""

from __future__ import annotations

from typing import Callable


def build_reliability_parser(subparsers, *, cmd_reliability: Callable) -> None:
    """Attach the ``reliability`` subcommand (and sub-actions) to ``subparsers``."""
    reliability_parser = subparsers.add_parser(
        "reliability",
        help="Reliability & self-healing: status, watchdog, backup/restore, modes",
        description=(
            "Inspect and control the AetherOS reliability layer: recovery "
            "state, watchdog, recovery journal, backups, Safe/Recovery modes, "
            "diagnostics and SLA metrics."
        ),
    )
    reliability_sub = reliability_parser.add_subparsers(dest="reliability_command")

    # reliability status
    reliability_sub.add_parser(
        "status", help="Show reliability status (mode, state, watchdog, backups)"
    )

    # reliability health
    reliability_sub.add_parser(
        "health", help="Show component health and operating mode"
    )

    # reliability watchdog
    watchdog = reliability_sub.add_parser(
        "watchdog", help="Watchdog status and control"
    )
    watchdog_sub = watchdog.add_subparsers(dest="watchdog_action")
    watchdog_sub.add_parser("status", help="Watchdog status")
    watchdog_sub.add_parser("start", help="Start the watchdog")
    watchdog_sub.add_parser("stop", help="Stop the watchdog")
    watchdog_reset = watchdog_sub.add_parser(
        "reset", help="Reset a crash-looped component"
    )
    watchdog_reset.add_argument("component", help="Component id to reset")

    # reliability journal
    journal = reliability_sub.add_parser(
        "journal", help="Recovery journal inspection"
    )
    journal.add_argument(
        "--recent", type=int, default=20, help="Show N most recent operations"
    )
    journal.add_argument(
        "--pending", action="store_true", help="Show only unfinished operations"
    )

    # reliability backup
    backup = reliability_sub.add_parser(
        "backup", help="Create / list / verify / prune reliability backups"
    )
    backup.add_argument(
        "--label", default="", help="Label for the backup"
    )
    backup.add_argument("--list", action="store_true", help="List backups")
    backup.add_argument("--verify", metavar="BACKUP_ID", help="Verify a backup")
    backup.add_argument(
        "--prune", type=int, metavar="KEEP", help="Keep newest KEEP, delete older"
    )

    # reliability restore (deliberately interactive + confirm-gated)
    restore = reliability_sub.add_parser(
        "restore", help="Restore a backup (preview, then confirmed restore)"
    )
    restore.add_argument("backup_id", help="Backup id to restore")
    restore.add_argument(
        "--scope", choices=("config", "state", "full"), default="full",
        help="What to restore (default: full)",
    )
    restore.add_argument(
        "--dry-run", action="store_true",
        help="Preview only — show what would change, restore nothing",
    )
    restore.add_argument(
        "--yes", action="store_true",
        help="Skip the confirmation prompt (dangerous)",
    )

    # reliability safe-mode / recovery-mode
    safe = reliability_sub.add_parser(
        "safe-mode", help="Enter / exit Safe Mode"
    )
    safe.add_argument(
        "action", choices=("enter", "exit"), help="enter or exit Safe Mode"
    )
    safe.add_argument("--reason", default="", help="Reason (audited)")

    recovery = reliability_sub.add_parser(
        "recovery-mode", help="Enter / exit Recovery Mode"
    )
    recovery.add_argument(
        "action", choices=("enter", "exit"), help="enter or exit Recovery Mode"
    )
    recovery.add_argument("--reason", default="", help="Reason (audited)")

    # reliability diagnostics
    diag = reliability_sub.add_parser(
        "diagnostics", help="Export a redacted reliability diagnostics bundle"
    )
    diag.add_argument(
        "--output", default="", help="Output file path (default: stdout JSON)"
    )

    # reliability sla
    reliability_sub.add_parser(
        "sla", help="Recovery SLA metrics (MTTR, success rates)"
    )

    # reliability spof
    reliability_sub.add_parser(
        "spof", help="Single points of failure audit for the reliability layer"
    )

    # reliability lkg
    lkg = reliability_sub.add_parser(
        "lkg", help="Last-known-good config status"
    )
    lkg.add_argument(
        "--update", action="store_true",
        help="Update last-known-good from the current config (if valid)",
    )

    reliability_parser.set_defaults(func=cmd_reliability)