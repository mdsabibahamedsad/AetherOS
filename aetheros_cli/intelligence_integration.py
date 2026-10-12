"""
Phase 14 Aether Intelligence Engine — Integration Helper

This module provides the registration hooks that main.py and web_server.py
call to attach all intelligence subcommands and API routes.

CLI usage in main.py::

    from aetheros_cli.intelligence_integration import register_intelligence_subcommands
    register_intelligence_subcommands(subparsers)

Web API usage in web_server.py::

    from aetheros_cli.intelligence_integration import register_intelligence_api_routes
    register_intelligence_api_routes(app)
"""

from __future__ import annotations

import argparse
import sys


def register_intelligence_subcommands(subparsers: argparse.Action) -> None:
    """Attach all Phase 14 intelligence subcommands to the top-level parser."""
    from aetheros_cli.subcommands.plan import build_plan_parser
    from aetheros_cli.subcommands.think import build_think_parser
    from aetheros_cli.subcommands.analyze import build_analyze_parser
    from aetheros_cli.subcommands.agents_cmd import build_agents_parser
    from aetheros_cli.subcommands.knowledge_cmd import build_knowledge_parser
    from aetheros_cli.subcommands.learn import build_learn_parser
    from aetheros_cli.intelligence_cmds import (
        cmd_plan,
        cmd_think,
        cmd_analyze,
        cmd_agents,
        cmd_knowledge,
        cmd_learn,
    )

    build_plan_parser(subparsers, cmd_plan=cmd_plan)
    build_think_parser(subparsers, cmd_think=cmd_think)
    build_analyze_parser(subparsers, cmd_analyze=cmd_analyze)
    build_agents_parser(subparsers, cmd_agents=cmd_agents)
    build_knowledge_parser(subparsers, cmd_knowledge=cmd_knowledge)
    build_learn_parser(subparsers, cmd_learn=cmd_learn)


def register_intelligence_api_routes(app) -> None:
    """Attach web intelligence API routes to a FastAPI application."""
    from aetheros_cli.web_intelligence_api import register_routes
    register_routes(app)


# Convenience: list registered commands when run directly.
if __name__ == "__main__":
    print("Phase 14 Aether Intelligence Engine — registered subparsers:")
    for name in ("plan", "think", "analyze", "agents", "knowledge", "learn"):
        print(f"  aetheros {name}")
    print()
    print("Web API routes prefix: /api/intelligence/*")
    print()
    print("Subsystems:")
    for sub in ("planning", "reasoning", "context", "model_router", "local_ai",
                "learning", "developer_ai", "workflow_ai", "automation_ai",
                "research", "project_understanding", "explainability"):
        print(f"  aetheros_intelligence.{sub}")
    print()
    print("Specialized Agents:")
    from agents.specialized import list_specialized_agents
    for a in list_specialized_agents():
        print(f"  {a['icon']} {a['role']:15s} {a['name']}")
