"""``aetheros learn`` subcommand parser for the Aether Intelligence Engine.

Handles user-approved learning of coding style, workflow, tools,
commands, workspace habits, and frequently used prompts.
"""

from __future__ import annotations

from typing import Callable


def build_learn_parser(subparsers, *, cmd_learn: Callable) -> None:
    """Attach the ``learn`` subcommand to ``subparsers``."""
    learn_parser = subparsers.add_parser(
        "learn",
        help="Manage user-approved learning and preferences",
        description=(
            "AetherOS learns from your usage patterns — but only with your "
            "explicit approval. Never learns automatically.\n\n"
            "Subcommands:\n"
            "  observe    Record a learning observation\n"
            "  list       Show observations pending approval\n"
            "  approve    Approve a learning observation\n"
            "  reject     Reject a learning observation\n"
            "  learned    Show learned patterns\n"
            "  summary    Show learning summary\n"
        ),
    )
    learn_sub = learn_parser.add_subparsers(dest="learn_command", metavar="<subcommand>")

    # observe
    observe_parser = learn_sub.add_parser(
        "observe", help="Record a learning observation"
    )
    observe_parser.add_argument(
        "category",
        choices=["coding_style", "workflow", "favorite_tools", "common_commands",
                 "workspace_habits", "frequent_prompts", "generic"],
        help="Category of the observation",
    )
    observe_parser.add_argument("observation", help="What was observed")
    observe_parser.add_argument(
        "--pattern", help="Extracted pattern or rule",
    )
    observe_parser.add_argument(
        "--context", help="Context where the observation was made",
    )
    observe_parser.add_argument(
        "--approve", action="store_true",
        help="Auto-approve this observation (requires learning opt-in)",
    )
    observe_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # list
    list_parser = learn_sub.add_parser(
        "list", aliases=["ls"],
        help="Show observations pending approval",
    )
    list_parser.add_argument(
        "--category",
        choices=["coding_style", "workflow", "favorite_tools", "common_commands",
                 "workspace_habits", "frequent_prompts", "generic"],
        help="Filter by category",
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # approve
    approve_parser = learn_sub.add_parser(
        "approve", help="Approve a learning observation"
    )
    approve_parser.add_argument(
        "sample_id", nargs="?", help="Sample ID to approve",
    )
    approve_parser.add_argument(
        "--all", action="store_true", help="Approve all pending observations",
    )
    approve_parser.add_argument(
        "--category",
        choices=["coding_style", "workflow", "favorite_tools", "common_commands",
                 "workspace_habits", "frequent_prompts", "generic"],
        help="Filter by category (with --all)",
    )

    # reject
    reject_parser = learn_sub.add_parser(
        "reject", help="Reject a learning observation"
    )
    reject_parser.add_argument(
        "sample_id", nargs="?", help="Sample ID to reject",
    )
    reject_parser.add_argument(
        "--all", action="store_true", help="Reject all pending observations",
    )
    reject_parser.add_argument(
        "--category",
        choices=["coding_style", "workflow", "favorite_tools", "common_commands",
                 "workspace_habits", "frequent_prompts", "generic"],
        help="Filter by category (with --all)",
    )

    # learned
    learned_parser = learn_sub.add_parser(
        "learned", aliases=["patterns"],
        help="Show learned patterns",
    )
    learned_parser.add_argument(
        "--category",
        choices=["coding_style", "workflow", "favorite_tools", "common_commands",
                 "workspace_habits", "frequent_prompts", "generic"],
        help="Filter by category",
    )
    learned_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # summary
    summary_parser = learn_sub.add_parser(
        "summary", help="Show learning summary"
    )
    summary_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    learn_parser.set_defaults(func=cmd_learn)
