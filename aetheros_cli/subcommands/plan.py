"""``aetheros plan`` subcommand parser for the Aether Intelligence Engine.

Extracted from ``aetheros_cli/main.py:main()`` pattern (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_plan_parser(subparsers, *, cmd_plan: Callable) -> None:
    """Attach the ``plan`` subcommand to ``subparsers``."""
    plan_parser = subparsers.add_parser(
        "plan",
        help="Plan tasks, decompose goals, and execute long-term plans",
        description=(
            "Intelligent task planning and goal decomposition. "
            "Break down complex goals into actionable steps, "
            "identify dependencies, and track long-term execution.\n\n"
            "Subcommands:\n"
            "  create     Create a new plan from a goal or task description\n"
            "  list       List active and recent plans\n"
            "  show       Show detailed plan breakdown\n"
            "  execute    Execute the next steps in a plan\n"
            "  status     Show plan execution status\n"
            "  refine     Refine or update an existing plan\n"
        ),
    )
    plan_sub = plan_parser.add_subparsers(dest="plan_command", metavar="<subcommand>")

    # create
    create_parser = plan_sub.add_parser(
        "create", help="Create a new plan from a goal or task description"
    )
    create_parser.add_argument("goal", help="The goal or task to plan")
    create_parser.add_argument(
        "--steps", type=int, default=0,
        help="Number of steps to generate (default: auto)",
    )
    create_parser.add_argument(
        "--context", help="Additional context for planning",
    )
    create_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # list
    list_parser = plan_sub.add_parser(
        "list", aliases=["ls"], help="List active and recent plans"
    )
    list_parser.add_argument(
        "--all", action="store_true", help="Show all plans including completed",
    )
    list_parser.add_argument(
        "--limit", type=int, default=10, help="Number of plans to show",
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # show
    show_parser = plan_sub.add_parser(
        "show", help="Show detailed plan breakdown"
    )
    show_parser.add_argument("plan_id", help="Plan ID to show")
    show_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # execute
    execute_parser = plan_sub.add_parser(
        "execute", aliases=["exec"], help="Execute the next steps in a plan"
    )
    execute_parser.add_argument("plan_id", help="Plan ID to execute")
    execute_parser.add_argument(
        "--step", type=int, default=None,
        help="Specific step number to execute (default: next pending)",
    )
    execute_parser.add_argument(
        "--all", action="store_true",
        help="Execute all pending steps (use with caution)",
    )

    # status
    status_parser = plan_sub.add_parser(
        "status", help="Show plan execution status"
    )
    status_parser.add_argument("plan_id", nargs="?", help="Plan ID (default: active plan)")
    status_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # refine
    refine_parser = plan_sub.add_parser(
        "refine", help="Refine or update an existing plan"
    )
    refine_parser.add_argument("plan_id", help="Plan ID to refine")
    refine_parser.add_argument(
        "--feedback", help="Feedback to incorporate",
    )
    refine_parser.add_argument(
        "--add-step", help="Add a new step to the plan",
    )
    refine_parser.add_argument(
        "--reorder", help="Reorder steps (comma-separated indices)",
    )

    plan_parser.set_defaults(func=cmd_plan)
