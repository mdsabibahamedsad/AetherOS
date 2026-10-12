"""``aetheros knowledge`` subcommand parser for the Aether Intelligence Engine.

Extracted from ``aetheros_cli/main.py:main()`` pattern (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_knowledge_parser(subparsers, *, cmd_knowledge: Callable) -> None:
    """Attach the ``knowledge`` subcommand to ``subparsers``."""
    knowledge_parser = subparsers.add_parser(
        "knowledge",
        help="Query and manage the knowledge graph and semantic search",
        description=(
            "Access the AetherOS knowledge engine.\n\n"
            "Query the knowledge graph, run semantic and hybrid searches,\n"
            "and manage document relationships.\n\n"
            "Subcommands:\n"
            "  search     Semantic or hybrid search across knowledge\n"
            "  graph      Show knowledge graph connections\n"
            "  entities   List entities in the knowledge graph\n"
            "  stats      Show knowledge engine statistics\n"
        ),
    )
    knowledge_sub = knowledge_parser.add_subparsers(dest="knowledge_command", metavar="<subcommand>")

    # search
    search_parser = knowledge_sub.add_parser(
        "search", aliases=["s"],
        help="Semantic or hybrid search across knowledge",
    )
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--mode", choices=["semantic", "hybrid", "keyword"], default="hybrid",
        help="Search mode (default: hybrid)",
    )
    search_parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)",
    )
    search_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # graph
    graph_parser = knowledge_sub.add_parser(
        "graph", help="Show knowledge graph connections"
    )
    graph_parser.add_argument(
        "entity", nargs="?", help="Entity to show connections for",
    )
    graph_parser.add_argument(
        "--depth", type=int, default=2, help="Graph traversal depth (default: 2)",
    )
    graph_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # entities
    entities_parser = knowledge_sub.add_parser(
        "entities", aliases=["e"],
        help="List entities in the knowledge graph",
    )
    entities_parser.add_argument(
        "--type", help="Filter by entity type",
    )
    entities_parser.add_argument(
        "--limit", type=int, default=20, help="Max entities (default: 20)",
    )
    entities_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    # stats
    stats_parser = knowledge_sub.add_parser(
        "stats", help="Show knowledge engine statistics"
    )
    stats_parser.add_argument(
        "--json", action="store_true", help="Output as JSON",
    )

    knowledge_parser.set_defaults(func=cmd_knowledge)
