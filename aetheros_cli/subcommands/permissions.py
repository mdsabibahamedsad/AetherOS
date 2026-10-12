"""``aetheros permissions`` subcommand parser.

Manage granular permissions for plugins, agents, MCP servers, and automation tasks.
Integrates with aetheros_security.permissions PermissionEngine.
"""

from __future__ import annotations

from typing import Callable


def build_permissions_parser(subparsers, *, cmd_permissions: Callable) -> None:
    """Attach the ``permissions`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "permissions",
        help="Manage granular permissions for plugins, agents, and tasks",
        description=(
            "Zero-Trust permission management. Every plugin, agent, MCP server, "
            "and automation task requires explicit permissions. Permissions follow "
            "the format 'category:action' (e.g. 'filesystem:read', 'network:connect')."
        ),
    )
    sub = parser.add_subparsers(
        dest="permissions_command",
        metavar="<subcommand>",
    )

    # list
    list_p = sub.add_parser(
        "list",
        help="List granted permissions",
        description="Show all currently granted permissions, optionally filtered by requester.",
    )
    list_p.add_argument(
        "requester",
        nargs="?",
        default=None,
        help="Filter by requester name (plugin, agent, etc.)",
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # grant
    grant_p = sub.add_parser(
        "grant",
        help="Grant a permission",
        description="Grant a specific permission to a requester.",
    )
    grant_p.add_argument(
        "permission",
        help="Permission to grant (e.g. 'filesystem:read', 'network:connect')",
    )
    grant_p.add_argument(
        "requester",
        help="Who receives the permission",
    )
    grant_p.add_argument(
        "--duration",
        default="session",
        choices=["once", "session", "hour", "day", "week", "month", "permanent"],
        help="How long the permission lasts (default: session)",
    )
    grant_p.add_argument(
        "--reason",
        default="",
        help="Why the permission was granted",
    )

    # revoke
    revoke_p = sub.add_parser(
        "revoke",
        help="Revoke a permission",
        description="Revoke a specific permission from a requester.",
    )
    revoke_p.add_argument(
        "permission",
        help="Permission to revoke",
    )
    revoke_p.add_argument(
        "requester",
        help="Who loses the permission",
    )

    # revoke-all
    revoke_all_p = sub.add_parser(
        "revoke-all",
        help="Revoke all permissions for a requester",
        description="Revoke every permission granted to a specific requester.",
    )
    revoke_all_p.add_argument(
        "requester",
        help="Who loses all permissions",
    )

    # show
    show_p = sub.add_parser(
        "show",
        help="Show permission details for a requester",
        description="Display all active permissions and their risk levels for a requester.",
    )
    show_p.add_argument(
        "requester",
        help="Requester to show permissions for",
    )

    # request
    request_p = sub.add_parser(
        "request",
        help="Request a permission (interactive)",
        description="Interactively request and approve a permission.",
    )
    request_p.add_argument(
        "permission",
        help="Permission to request",
    )
    request_p.add_argument(
        "requester",
        help="Who is requesting",
    )
    request_p.add_argument(
        "--reason",
        default="",
        help="Why the permission is needed",
    )

    # categories
    cat_p = sub.add_parser(
        "categories",
        help="List available permission categories",
        description="Show all permission categories and their available actions.",
    )
    cat_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # stats
    stats_p = sub.add_parser(
        "stats",
        help="Show permission statistics",
        description="Display permission usage statistics and grant counts.",
    )
    stats_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_permissions)
