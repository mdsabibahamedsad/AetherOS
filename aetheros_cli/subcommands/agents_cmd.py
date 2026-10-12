"""``aetheros agents`` subcommand parser for the Aether Intelligence Engine.

Extracted from ``aetheros_cli/main.py:main()`` pattern (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_agents_parser(subparsers, *, cmd_agents: Callable) -> None:
    """Attach the ``agents`` subcommand to ``subparsers``."""
    agents_parser = subparsers.add_parser(
        "agents",
        help="Manage and monitor specialized AI agents",
        description=(
            "Monitor and manage the AetherOS multi-agent system.\n\n"
            "13 specialized agents are available:\n"
            "  Planner, Researcher, Coder, Reviewer, Debugger, Tester,\n"
            "  Writer, Browser, Automation, Security, Knowledge, Voice,\n"
            "  Coordinator\n\n"
            "Subcommands:\n"
            "  list         List all available agents\n"
            "  status       Show agent system status\n"
            "  coordinate   Plan which agents to use for a goal\n"
            "  logs         View agent activity logs\n"
            "  history      Show agent execution history\n"
        ),
    )
    agents_sub = agents_parser.add_subparsers(dest="agents_command", metavar="<subcommand>")

    # list
    list_parser = agents_sub.add_parser(
        "list", aliases=["ls"],
        help="List all available agents",
    )
    list_parser.add_argument(
        "--role", help="Filter by agent role",
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # status
    status_parser = agents_sub.add_parser(
        "status", help="Show agent system status"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # coordinate
    coordinate_parser = agents_sub.add_parser(
        "coordinate", aliases=["coord"],
        help="Plan which agents to use for a goal",
    )
    coordinate_parser.add_argument("goal", help="The goal to coordinate agents for")
    coordinate_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # logs
    logs_parser = agents_sub.add_parser(
        "logs", help="View agent activity logs"
    )
    logs_parser.add_argument(
        "name", nargs="?", help="Agent name (default: all agents)",
    )
    logs_parser.add_argument(
        "--limit", type=int, default=50, help="Number of log entries (default: 50)",
    )
    logs_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # history
    history_parser = agents_sub.add_parser(
        "history", help="Show agent execution history"
    )
    history_parser.add_argument(
        "name", nargs="?", help="Agent name (default: all agents)",
    )
    history_parser.add_argument(
        "--limit", type=int, default=20, help="Number of entries (default: 20)",
    )
    history_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    agents_parser.set_defaults(func=cmd_agents)
