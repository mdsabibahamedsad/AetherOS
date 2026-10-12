"""``aetheros audit`` subcommand parser.

View and manage the security audit log.
Integrates with aetheros_security.audit AuditLogger.
"""

from __future__ import annotations

from typing import Callable


def build_audit_parser(subparsers, *, cmd_audit: Callable) -> None:
    """Attach the ``audit`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "audit",
        help="View and manage security audit logs",
        description=(
            "Access the tamper-evident audit log system. Recorded events include "
            "permission grants/denials, plugin installations, workflow executions, "
            "automation actions, security events, and authentication events."
        ),
    )
    sub = parser.add_subparsers(
        dest="audit_command",
        metavar="<subcommand>",
    )

    # view / recent
    view_p = sub.add_parser(
        "view",
        aliases=["recent"],
        help="View recent audit log entries",
        description="Display the most recent audit log entries.",
    )
    view_p.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of entries to show (default: 50)",
    )
    view_p.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        default=None,
        help="Filter by severity level",
    )
    view_p.add_argument(
        "--event-type",
        default=None,
        help="Filter by event type (e.g. 'permission_granted', 'auth_failure')",
    )
    view_p.add_argument(
        "--user",
        default=None,
        help="Filter by user/source name",
    )
    view_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # search
    search_p = sub.add_parser(
        "search",
        help="Search audit log entries",
        description="Search audit log entries with filters.",
    )
    search_p.add_argument(
        "--event-type",
        default=None,
        help="Filter by event type",
    )
    search_p.add_argument(
        "--user",
        default=None,
        help="Filter by user",
    )
    search_p.add_argument(
        "--start-time",
        type=float,
        default=None,
        help="Start timestamp (Unix epoch)",
    )
    search_p.add_argument(
        "--end-time",
        type=float,
        default=None,
        help="End timestamp (Unix epoch)",
    )
    search_p.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum entries to return (default: 100)",
    )

    # export
    export_p = sub.add_parser(
        "export",
        help="Export audit log to file",
        description="Export the full audit log to a JSON file.",
    )
    export_p.add_argument(
        "output",
        help="Output file path (.json)",
    )

    # stats
    stats_p = sub.add_parser(
        "stats",
        help="Show audit log statistics",
        description="Display audit log statistics including event type and severity counts.",
    )
    stats_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # events
    events_p = sub.add_parser(
        "events",
        help="List available event types",
        description="Show all available audit event types.",
    )
    events_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_audit)
