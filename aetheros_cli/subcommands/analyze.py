"""``aetheros analyze`` subcommand parser for the Aether Intelligence Engine.

Extracted from ``aetheros_cli/main.py:main()`` pattern (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_analyze_parser(subparsers, *, cmd_analyze: Callable) -> None:
    """Attach the ``analyze`` subcommand to ``subparsers``."""
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze projects for architecture, quality, and risks",
        description=(
            "Deep analysis of repositories and projects.\n\n"
            "Understands architecture, dependencies, code quality, security\n"
            "risks, performance issues, and technical debt.\n\n"
            "Subcommands:\n"
            "  project     Analyze an entire project directory\n"
            "  file        Analyze a single file in depth\n"
            "  research    Multi-source research on a topic\n"
            "  knowledge   Query the knowledge graph\n"
            "  repository  Deep repository understanding (Developer AI)\n"
            "  document    Generate documentation\n"
            "  tests       Generate test scaffolding\n"
            "  refactor    Get refactoring suggestions\n"
            "  status      Show analysis status\n"
        ),
    )
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_command", metavar="<subcommand>")

    # project
    project_parser = analyze_sub.add_parser(
        "project", aliases=["p"],
        help="Analyze an entire project directory",
    )
    project_parser.add_argument("path", help="Path to the project directory")
    project_parser.add_argument(
        "--full", action="store_true",
        help="Full deep analysis (may take longer)",
    )
    project_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # file
    file_parser = analyze_sub.add_parser(
        "file", aliases=["f"],
        help="Analyze a single file in depth",
    )
    file_parser.add_argument("path", help="Path to the file")
    file_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # research
    research_parser = analyze_sub.add_parser(
        "research", aliases=["rs"],
        help="Multi-source research on a topic",
    )
    research_parser.add_argument("topic", help="Research topic or question")
    research_parser.add_argument(
        "--sources", nargs="+",
        default=["web", "docs", "github", "knowledge", "files"],
        help="Sources to search (web, docs, github, knowledge, files)",
    )
    research_parser.add_argument(
        "--deep", type=int, default=1, choices=[1, 2, 3],
        help="Deep research depth level (1-3)",
    )
    research_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # knowledge
    knowledge_parser = analyze_sub.add_parser(
        "knowledge", aliases=["k"],
        help="Query the knowledge graph",
    )
    knowledge_parser.add_argument("query", help="Knowledge graph query")
    knowledge_parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)",
    )
    knowledge_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # repository
    repo_parser = analyze_sub.add_parser(
        "repository", aliases=["repo"],
        help="Deep repository understanding (Developer AI)",
    )
    repo_parser.add_argument("path", help="Path to the repository")
    repo_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # document
    doc_parser = analyze_sub.add_parser(
        "document", aliases=["docs"],
        help="Generate documentation",
    )
    doc_parser.add_argument("path", help="Path to file or project")
    doc_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # tests
    tests_parser = analyze_sub.add_parser(
        "tests", help="Generate test scaffolding"
    )
    tests_parser.add_argument("path", help="Path to source file")
    tests_parser.add_argument(
        "--framework", default="pytest",
        help="Test framework (default: pytest)",
    )
    tests_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # refactor
    refactor_parser = analyze_sub.add_parser(
        "refactor", help="Get refactoring suggestions"
    )
    refactor_parser.add_argument("path", help="Path to file or project")
    refactor_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # status
    status_parser = analyze_sub.add_parser(
        "status", help="Show analysis engine status"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    analyze_parser.set_defaults(func=cmd_analyze)
