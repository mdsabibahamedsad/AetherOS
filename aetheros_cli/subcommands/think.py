"""``aetheros think`` subcommand parser for the Aether Intelligence Engine.

Extracted from ``aetheros_cli/main.py:main()`` pattern (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_think_parser(subparsers, *, cmd_think: Callable) -> None:
    """Attach the ``think`` subcommand to ``subparsers``."""
    think_parser = subparsers.add_parser(
        "think",
        help="Run the reasoning pipeline on a problem or question",
        description=(
            "Apply AetherOS reasoning capabilities to any problem.\n\n"
            "Uses chain-of-thought reasoning, self-critique, verification,\n"
            "and alternative generation to produce thorough answers.\n\n"
            "Subcommands:\n"
            "  reason     Reason about a question or problem\n"
            "  reflect    Reflect on a completed action or outcome\n"
            "  explain    Get an explanation for a recommendation\n"
            "  status     Show reasoning pipeline status\n"
        ),
    )
    think_sub = think_parser.add_subparsers(dest="think_command", metavar="<subcommand>")

    # reason
    reason_parser = think_sub.add_parser(
        "reason", aliases=["r"],
        help="Reason about a question or problem using the pipeline",
    )
    reason_parser.add_argument("question", help="The question or problem to reason about")
    reason_parser.add_argument(
        "--strategy", choices=["cot", "critique", "verify", "all"],
        default="all",
        help="Reasoning strategy to use (default: all)",
    )
    reason_parser.add_argument(
        "--context", help="Additional context for reasoning",
    )
    reason_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # reflect
    reflect_parser = think_sub.add_parser(
        "reflect", help="Reflect on a completed action or outcome"
    )
    reflect_parser.add_argument("goal", help="What was attempted")
    reflect_parser.add_argument(
        "outcome", nargs="?", choices=["success", "partial", "failure"],
        default="success",
        help="Outcome of the action",
    )
    reflect_parser.add_argument(
        "--success", action="append", default=[], help="What went well",
    )
    reflect_parser.add_argument(
        "--failure", action="append", default=[], help="What went wrong",
    )
    reflect_parser.add_argument(
        "--lesson", action="append", default=[], help="Lessons learned",
    )
    reflect_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # explain
    explain_parser = think_sub.add_parser(
        "explain", help="Get an explanation for a recommendation or decision"
    )
    explain_parser.add_argument("decision", help="The decision or recommendation to explain")
    explain_parser.add_argument(
        "--confidence", type=float, default=None,
        help="Confidence score (0.0 - 1.0)",
    )
    explain_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # status
    status_parser = think_sub.add_parser(
        "status", help="Show reasoning pipeline status"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    think_parser.set_defaults(func=cmd_think)
