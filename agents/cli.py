"""CLI command handlers for the agent ecosystem.

Implements the command logic for:
  aetheros agents          — list all agents
  aetheros agent create    — interactive 11-step wizard
  aetheros agent run       — start an agent session
  aetheros agent install   — install marketplace agent
  aetheros marketplace     — browse marketplace
  aetheros agent export    — export agent config
  aetheros agent import    — import agent config
  aetheros agent backup    — backup all agents
  aetheros agent restore   — restore from backup
  aetheros agent dashboard — live dashboard
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from rich import box as rich_box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aetheros_cli.setup_renderer import (
    C_ACCENT, C_BORDER, C_CYAN, C_DIM, C_ERROR, C_PURPLE,
    C_SUCCESS, C_TEXT, C_WARN, get_console,
)
from agents.manager import AgentManager
from agents.marketplace import (
    MARKETPLACE_CATEGORIES,
    get_marketplace_catalog, get_featured_agents, install_from_marketplace,
    get_installed_marketplace_agents,
)
from agents.wizard import run_agent_wizard
from agents.runtime import AgentRuntime
from agents.dashboard import show_agent_dashboard, run_live_dashboard, build_agent_card, build_agent_table
from agents import store

logger = logging.getLogger(__name__)


# ── Agent Manager ─────────────────────────────────────────────────


def cmd_agents(args: Any) -> None:
    """List all registered agents."""
    mgr = AgentManager()
    agents = mgr.list(include_disabled=True)

    console = get_console()
    console.clear()

    console.print(
        Panel(
            Align.center(
                Group(
                    Text(f"  ◆  Agents ({len(agents)})  ◆  ", style=f"bold {C_PURPLE}"),
                    Text("  Manage your AI agent ecosystem", style=C_DIM),
                ),
                vertical="middle",
            ),
            border_style=C_PURPLE,
            padding=(1, 4),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    if not agents:
        console.print(Text("  No agents created yet.", style=C_DIM))
        console.print(Text("  Create one with:  aetheros agent create", style=C_ACCENT))
        console.print()
        return

    # Cards view
    cards = [build_agent_card(a) for a in agents]
    console.print(
        Panel(
            Group(Text("  Grid View", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # Table view
    console.print(
        Panel(
            Group(Text("  List View", style=f"bold {C_TEXT}"), Text(""), build_agent_table(agents)),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()


def cmd_agent_create(args: Any) -> None:
    """Create a new agent via the interactive wizard."""
    console = get_console()
    console.clear()

    agent = run_agent_wizard()
    if agent:
        console.print()
        console.print(f"  [{C_SUCCESS}]✓[/]  Agent '{agent.name}' created (id: {agent.id})")
    else:
        console.print(f"  [{C_WARN}]⚠[/]  Agent creation cancelled")


def cmd_agent_run(args: Any) -> None:
    """Run an agent."""
    mgr = AgentManager()
    agent_id = args.agent_id if hasattr(args, 'agent_id') and args.agent_id else args.name_or_id

    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if not agent:
        get_console().print(f"  [{C_ERROR}]✗[/]  Agent '{agent_id}' not found")
        return

    goal = " ".join(args.goal) if hasattr(args, 'goal') and args.goal else "Help me with a task."

    runtime = AgentRuntime()
    runtime.start()

    try:
        instance = runtime.start_agent(agent.id, goal=goal)
        get_console().print(f"  [{C_SUCCESS}]●[/]  Running agent '{agent.name}' (session: {instance.session_id})")
    except RuntimeError as e:
        if "already running" in str(e):
            get_console().print(f"  [{C_WARN}]⚠[/]  Agent '{agent.name}' is already running")
        else:
            get_console().print(f"  [{C_ERROR}]✗[/]  {e}")
    except Exception as e:
        get_console().print(f"  [{C_ERROR}]✗[/]  Failed to run agent: {e}")
    finally:
        runtime.stop()


def cmd_agent_install(args: Any) -> None:
    """Install an agent from the marketplace."""
    package_id = args.package_id if hasattr(args, 'package_id') and args.package_id else args.name_or_id

    console = get_console()
    console.print(f"  [{C_DIM}]Installing '{package_id}' from marketplace...[/]")

    agent = install_from_marketplace(package_id)
    if agent:
        console.print(f"  [{C_SUCCESS}]✓[/]  Installed '{agent.name}' (id: {agent.id})")
    else:
        console.print(f"  [{C_ERROR}]✗[/]  Package '{package_id}' not found in marketplace")


def cmd_agent_export(args: Any) -> None:
    """Export an agent configuration."""
    mgr = AgentManager()
    agent_id = args.agent_id if hasattr(args, 'agent_id') and args.agent_id else args.name_or_id

    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if not agent:
        get_console().print(f"  [{C_ERROR}]✗[/]  Agent '{agent_id}' not found")
        return

    output = args.output if hasattr(args, 'output') and args.output else None
    try:
        path = mgr.export_agent(agent.id, output)
        get_console().print(f"  [{C_SUCCESS}]✓[/]  Exported to {path}")
    except Exception as e:
        get_console().print(f"  [{C_ERROR}]✗[/]  Export failed: {e}")


def cmd_agent_import(args: Any) -> None:
    """Import an agent configuration."""
    mgr = AgentManager()
    source = args.path if hasattr(args, 'path') and args.path else args.name_or_id

    console = get_console()
    console.print(f"  [{C_DIM}]Importing agent from {source}...[/]")

    try:
        agent = mgr.import_agent(source)
        console.print(f"  [{C_SUCCESS}]✓[/]  Imported '{agent.name}' (id: {agent.id})")
    except Exception as e:
        console.print(f"  [{C_ERROR}]✗[/]  Import failed: {e}")


def cmd_agent_delete(args: Any) -> None:
    """Delete an agent."""
    mgr = AgentManager()
    agent_id = args.agent_id if hasattr(args, 'agent_id') and args.agent_id else args.name_or_id

    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if not agent:
        get_console().print(f"  [{C_ERROR}]✗[/]  Agent '{agent_id}' not found")
        return

    mgr.delete(agent.id)
    get_console().print(f"  [{C_SUCCESS}]✓[/]  Deleted agent '{agent.name}'")


def cmd_agent_duplicate(args: Any) -> None:
    """Duplicate an agent."""
    mgr = AgentManager()
    agent_id = args.agent_id if hasattr(args, 'agent_id') and args.agent_id else args.name_or_id

    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if not agent:
        get_console().print(f"  [{C_ERROR}]✗[/]  Agent '{agent_id}' not found")
        return

    new_name = args.new_name if hasattr(args, 'new_name') and args.new_name else ""
    duplicate = mgr.duplicate(agent.id, new_name)
    if duplicate:
        get_console().print(f"  [{C_SUCCESS}]✓[/]  Duplicated as '{duplicate.name}' (id: {duplicate.id})")


def cmd_agent_backup(args: Any) -> None:
    """Backup all agent configurations."""
    mgr = AgentManager()
    output = args.output if hasattr(args, 'output') and args.output else None
    path = mgr.backup(output)
    get_console().print(f"  [{C_SUCCESS}]✓[/]  Backup saved to {path}")


def cmd_agent_restore(args: Any) -> None:
    """Restore agents from a backup."""
    mgr = AgentManager()
    source = args.path if hasattr(args, 'path') and args.path else args.name_or_id

    console = get_console()
    console.print(f"  [{C_DIM}]Restoring agents from {source}...[/]")

    agents = mgr.restore(source)
    console.print(f"  [{C_SUCCESS}]✓[/]  Restored {len(agents)} agents")


def cmd_agent_info(args: Any) -> None:
    """Show detailed information about an agent."""
    mgr = AgentManager()
    agent_id = args.agent_id if hasattr(args, 'agent_id') and args.agent_id else args.name_or_id

    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if not agent:
        get_console().print(f"  [{C_ERROR}]✗[/]  Agent '{agent_id}' not found")
        return

    console = get_console()
    console.clear()

    avatar = agent.avatar
    info = Table.grid(padding=(0, 2))
    info.add_column("Field", width=18, style=f"bold {C_DIM}")
    info.add_column("Value", width=50)

    info.add_row(f"{avatar.icon}  Agent", f"[bold {avatar.color}]{agent.name}[/]")
    info.add_row("ID", agent.id)
    info.add_row("Description", agent.description or "—")
    info.add_row("")
    info.add_row("Role", agent.role.replace("_", " ").title())
    info.add_row("Personality", agent.personality.replace("_", " ").title())
    info.add_row("Reasoning", agent.reasoning.title())
    info.add_row("Memory", agent.memory_scope.replace("_", " ").title())
    info.add_row("")
    info.add_row("Provider", agent.provider or "Default")
    info.add_row("Temperature", str(agent.temperature))
    info.add_row("Max Iterations", str(agent.max_iterations))
    if agent.models:
        info.add_row("Models", ", ".join(f"{k}: {v}" for k, v in agent.models.items()))
    if agent.fallback_providers:
        info.add_row("Fallbacks", ", ".join(p.provider for p in agent.fallback_providers))
    info.add_row("")
    info.add_row("Tools", ", ".join(agent.tools) or "None")
    info.add_row("Permissions", ", ".join(p.replace("_", " ").title() for p in agent.permissions))
    if agent.knowledge_sources:
        info.add_row("Knowledge", ", ".join(k.type for k in agent.knowledge_sources))
    if agent.skills:
        info.add_row("Skills", ", ".join(agent.skills))
    if agent.mcp_servers:
        info.add_row("MCP", ", ".join(agent.mcp_servers))
    if agent.prompt:
        info.add_row("Prompt", agent.prompt[:80] + ("..." if len(agent.prompt) > 80 else ""))
    info.add_row("")
    info.add_row("Status", agent.status.upper())
    info.add_row("Sessions", str(agent.metrics.sessions_run))
    m = agent.metrics
    info.add_row("Total Tokens", f"{m.total_tokens:,}" if m.total_tokens else "0")
    info.add_row("Version", str(agent.version))
    info.add_row("Created", agent.created_at)
    info.add_row("Updated", agent.updated_at)

    console.print(
        Panel(
            Group(Text("  Agent Details", style=f"bold {C_PURPLE}"), Text(""), info),
            border_style=C_PURPLE,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()


def cmd_agent_dashboard(args: Any) -> None:
    """Show the agent dashboard."""
    runtime = AgentRuntime()
    runtime.start()

    if hasattr(args, 'live') and args.live:
        run_live_dashboard(runtime=runtime)
    else:
        show_agent_dashboard(runtime=runtime)

    runtime.stop()


# ── Marketplace ────────────────────────────────────────────────────


def cmd_marketplace(args: Any) -> None:
    """Browse the agent marketplace."""
    console = get_console()
    console.clear()

    category = args.category if hasattr(args, 'category') and args.category else None

    console.print(
        Panel(
            Align.center(
                Group(
                    Text("  ◆  Agent Marketplace  ◆  ", style=f"bold {C_PURPLE}"),
                    Text("  Discover and install AI agents", style=C_DIM),
                ),
                vertical="middle",
            ),
            border_style=C_PURPLE,
            padding=(1, 4),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # Categories
    if not category:
        cat_grid = Table.grid(padding=(0, 2))
        cat_grid.add_column("Category", width=22)
        cat_grid.add_column("Count", width=6)
        cat_grid.add_column("Featured", width=40)

        for key, label in MARKETPLACE_CATEGORIES.items():
            agents = get_marketplace_catalog(key)
            featured = [a for a in agents if a.get("featured")]
            featured_names = ", ".join(a["name"][:20] for a in featured[:3])
            cat_grid.add_row(
                Text(f"  {label}", style=C_TEXT),
                Text(str(len(agents)), style=f"bold {C_CYAN}"),
                Text(featured_names, style=C_DIM),
            )
        cat_grid.add_row(Text(""))
        cat_grid.add_row(Text(f"  Total: {len(get_marketplace_catalog())} agents", style=f"bold {C_PURPLE}"))

        console.print(
            Panel(
                Group(
                    Text("  Categories", style=f"bold {C_TEXT}"),
                    Text(""),
                    cat_grid,
                ),
                border_style=C_BORDER,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )
        console.print()

    # Featured agents
    featured = get_featured_agents()
    if featured:
        cards = []
        for agent in featured:
            card = Table.grid(padding=(0, 1))
            card.add_row(Text(f"  ★  {agent['name']}", style=f"bold {C_GOLD if C_GOLD else C_ACCENT}"))
            card.add_row(Text(f"       {agent.get('description', '')[:50]}...", style=C_DIM))
            card.add_row(
                Text(f"       ⭐ {agent.get('rating', 0)}  │  {agent.get('installs', 0):,} installs  │  v{agent.get('version', '')}",
                     style=C_DIM)
            )
            cards.append(Panel(card, border_style=C_GOLD if C_GOLD else C_ACCENT, padding=(0, 1), box=rich_box.ROUNDED))

        console.print(
            Panel(
                Group(
                    Text("  Featured Agents", style=f"bold {C_TEXT}"),
                    Text(""),
                    Columns(cards, equal=False, expand=False),
                ),
                border_style=C_BORDER,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )
        console.print()

    # Installed agents
    installed = get_installed_marketplace_agents()
    if installed:
        inst_table = Table.grid(padding=(0, 2))
        inst_table.add_column("Package", width=20)
        inst_table.add_column("Version", width=10)
        inst_table.add_column("Installed", width=20)
        for pkg in installed:
            inst_table.add_row(
                Text(f"  {pkg['name']}", style=C_TEXT),
                Text(f"v{pkg['version']}", style=C_DIM),
                Text(pkg['installed_at'][:10] if pkg.get('installed_at') else "", style=C_DIM),
            )
        console.print(
            Panel(
                Group(
                    Text("  Installed from Marketplace", style=f"bold {C_TEXT}"),
                    Text(""),
                    inst_table,
                ),
                border_style=C_BORDER,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )
        console.print()


# ── Agent subcommand parsing ───────────────────────────────────────


def build_agent_subparser(subparsers) -> None:
    """Build argparse subcommand tree for agent commands."""
    # `aetheros agent <subcommand>`
    agent_parser = subparsers.add_parser("agent", help="Manage AI agents")
    agent_sub = agent_parser.add_subparsers(dest="agent_command", required=True)

    p_create = agent_sub.add_parser("create", help="Create a new agent (interactive wizard)")
    p_create.set_defaults(func=cmd_agent_create)

    p_run = agent_sub.add_parser("run", help="Run an agent")
    p_run.add_argument("name_or_id", help="Agent name or ID")
    p_run.add_argument("goal", nargs="*", help="Task description")
    p_run.set_defaults(func=cmd_agent_run)

    p_install = agent_sub.add_parser("install", help="Install agent from marketplace")
    p_install.add_argument("name_or_id", help="Package name or ID")
    p_install.set_defaults(func=cmd_agent_install)

    p_export = agent_sub.add_parser("export", help="Export agent configuration")
    p_export.add_argument("name_or_id", help="Agent name or ID")
    p_export.add_argument("-o", "--output", help="Output file path")
    p_export.set_defaults(func=cmd_agent_export)

    p_import = agent_sub.add_parser("import", help="Import agent configuration")
    p_import.add_argument("path", help="Path to agent JSON file")
    p_import.set_defaults(func=cmd_agent_import)

    p_info = agent_sub.add_parser("info", help="Show agent details")
    p_info.add_argument("name_or_id", help="Agent name or ID")
    p_info.set_defaults(func=cmd_agent_info)

    p_delete = agent_sub.add_parser("delete", help="Delete an agent")
    p_delete.add_argument("name_or_id", help="Agent name or ID")
    p_delete.set_defaults(func=cmd_agent_delete)

    p_dup = agent_sub.add_parser("duplicate", help="Duplicate an agent")
    p_dup.add_argument("name_or_id", help="Agent name or ID")
    p_dup.add_argument("-n", "--new-name", help="New agent name")
    p_dup.set_defaults(func=cmd_agent_duplicate)

    p_dash = agent_sub.add_parser("dashboard", help="Show agent dashboard")
    p_dash.add_argument("--live", action="store_true", help="Live-updating dashboard")
    p_dash.set_defaults(func=cmd_agent_dashboard)

    p_backup = agent_sub.add_parser("backup", help="Backup all agents")
    p_backup.add_argument("-o", "--output", help="Output zip path")
    p_backup.set_defaults(func=cmd_agent_backup)

    p_restore = agent_sub.add_parser("restore", help="Restore agents from backup")
    p_restore.add_argument("path", help="Path to backup zip")
    p_restore.set_defaults(func=cmd_agent_restore)

    # `aetheros agents` — shortcut for listing
    agents_parser = subparsers.add_parser("agents", help="List all agents")
    agents_parser.set_defaults(func=cmd_agents)

    # Marketplace subcommand under `aetheros agent marketplace`
    p_market = agent_sub.add_parser("marketplace", help="Browse the agent marketplace")
    p_market.add_argument("-c", "--category", help="Filter by category")
    p_market.set_defaults(func=cmd_marketplace)
