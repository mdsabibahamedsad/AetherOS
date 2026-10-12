"""
``aetheros marketplace`` subcommand parser — marketplace commands.
"""

from __future__ import annotations

from typing import Callable


def build_marketplace_parser(subparsers, *, cmd_marketplace: Callable) -> None:
    """Attach the marketplace subcommand to subparsers."""
    parser = subparsers.add_parser(
        "marketplace",
        aliases=["market", "mkt"],
        help="Extension marketplace — discover, search, install extensions",
        description="AetherOS Extension Marketplace — find, install, and manage extensions.",
    )
    mkt_subparsers = parser.add_subparsers(dest="marketplace_action")

    # marketplace search
    search_parser = mkt_subparsers.add_parser(
        "search", help="Search the marketplace for extensions"
    )
    search_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_parser.add_argument(
        "--kind", "-k", choices=[
            "tool", "agent", "workflow", "memory", "model",
            "voice", "notification", "enterprise",
        ],
        help="Filter by extension kind",
    )
    search_parser.add_argument(
        "--category", "-c", help="Filter by category"
    )
    search_parser.add_argument(
        "--publisher", "-p", help="Filter by publisher"
    )
    search_parser.add_argument(
        "--verified", action="store_true", help="Only verified extensions"
    )
    search_parser.add_argument(
        "--sort", choices=["relevance", "downloads", "rating", "updated"],
        default="relevance", help="Sort order (default: relevance)",
    )
    search_parser.add_argument(
        "--limit", "-l", type=int, default=20, help="Max results (default: 20)"
    )
    search_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # marketplace install
    install_parser = mkt_subparsers.add_parser(
        "install", help="Install an extension from the marketplace"
    )
    install_parser.add_argument(
        "source",
        help="Extension name, Git URL, owner/repo, or .aep file path",
    )
    install_parser.add_argument(
        "--force", "-f", action="store_true",
        help="Reinstall if already installed",
    )

    # marketplace update
    update_parser = mkt_subparsers.add_parser(
        "update", help="Update installed extensions"
    )
    update_parser.add_argument(
        "name", nargs="?", default="",
        help="Extension name to update (omit to check all)",
    )

    # marketplace remove
    remove_parser = mkt_subparsers.add_parser(
        "remove", aliases=["rm", "uninstall"],
        help="Remove an installed extension",
    )
    remove_parser.add_argument("name", help="Extension name to remove")

    # marketplace list
    list_parser = mkt_subparsers.add_parser(
        "list", aliases=["ls"], help="List installed extensions"
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # marketplace info
    info_parser = mkt_subparsers.add_parser(
        "info", help="Show detailed info about an extension"
    )
    info_parser.add_argument("name", help="Extension name")
    info_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # marketplace popular
    popular_parser = mkt_subparsers.add_parser(
        "popular", help="Show popular extensions"
    )
    popular_parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Number to show"
    )

    # marketplace top-rated
    top_parser = mkt_subparsers.add_parser(
        "top-rated", help="Show top-rated extensions"
    )
    top_parser.add_argument("--limit", "-l", type=int, default=10)

    # marketplace sources
    mkt_subparsers.add_parser(
        "sources", help="List configured marketplace sources"
    )

    # marketplace refresh
    mkt_subparsers.add_parser(
        "refresh", help="Refresh the extension cache"
    )

    parser.set_defaults(func=cmd_marketplace)
