"""Agent dashboard — status monitoring, metrics, and real-time display."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from rich import box as rich_box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_cli.setup_renderer import (
    C_ACCENT, C_BORDER, C_CYAN, C_DIM, C_ERROR, C_GOLD,
    C_PURPLE, C_SUCCESS, C_TEXT, C_WARN, get_console,
)
from agents.models import AgentConfig, AgentStatus
from agents.runtime import AgentRuntime
from agents import store

logger = logging.getLogger(__name__)


def build_agent_card(config: AgentConfig, instance: Any = None) -> Panel:
    """Build a Rich Panel card for an agent."""
    avatar_icon = config.avatar.icon or "🤖"
    avatar_color = config.avatar.color or C_ACCENT

    status_colors = {
        AgentStatus.IDLE.value: C_DIM,
        AgentStatus.RUNNING.value: C_SUCCESS,
        AgentStatus.BUSY.value: C_GOLD,
        AgentStatus.ERROR.value: C_ERROR,
        AgentStatus.STOPPED.value: C_DIM,
    }
    status_color = status_colors.get(config.status, C_DIM)

    status_label = config.status.upper() if config.status else "IDLE"
    if instance and instance.current_task:
        status_label = f"RUNNING: {instance.current_task[:40]}"

    card = Table.grid(padding=(0, 1))
    card.add_column("Field", style=C_DIM, width=14)
    card.add_column("Value", width=40)

    card.add_row(Text(f"{avatar_icon}  {config.name}", style=f"bold {avatar_color}"), Text(""))
    card.add_row(Text(""))
    card.add_row("Status", Text(status_label, style=f"bold {status_color}"))
    card.add_row("Role", config.role.replace("_", " ").title())
    card.add_row("Model", config.models.get("reasoning", config.models.get("coding", "auto")))
    card.add_row("Memory", config.memory_scope.replace("_", " ").title())
    card.add_row("Tools", ", ".join(config.tools[:4]) + ("..." if len(config.tools) > 4 else ""))

    if config.metrics.sessions_run > 0:
        metrics = config.metrics
        card.add_row(Text(""))
        card.add_row("Sessions", str(metrics.sessions_run))
        token_str = f"{metrics.total_tokens:,}" if metrics.total_tokens else "0"
        card.add_row("Tokens", token_str)

    border = status_color if config.status == AgentStatus.RUNNING.value else C_BORDER
    return Panel(
        card,
        border_style=border,
        padding=(1, 2),
        box=rich_box.ROUNDED,
    )


def build_agent_table(agents: list[AgentConfig], instances: dict[str, Any] | None = None) -> Table:
    """Build a table view of all agents."""
    table = Table(
        border_style=C_BORDER,
        header_style=f"bold {C_TEXT}",
        box=rich_box.SIMPLE,
    )
    table.add_column("", width=3)
    table.add_column("Name", width=20)
    table.add_column("Role", width=18)
    table.add_column("Status", width=12)
    table.add_column("Model", width=24)
    table.add_column("Tools", width=22)
    table.add_column("Sessions", width=8)

    for agent in agents:
        avatar = agent.avatar.icon or "🤖"
        status_icons = {
            AgentStatus.IDLE.value: "○",
            AgentStatus.RUNNING.value: "●",
            AgentStatus.BUSY.value: "◉",
            AgentStatus.ERROR.value: "✗",
            AgentStatus.STOPPED.value: "⊘",
        }
        status_icon = status_icons.get(agent.status, "○")
        status_colors = {
            AgentStatus.IDLE.value: C_DIM,
            AgentStatus.RUNNING.value: C_SUCCESS,
            AgentStatus.BUSY.value: C_GOLD,
            AgentStatus.ERROR.value: C_ERROR,
            AgentStatus.STOPPED.value: C_DIM,
        }
        s_color = status_colors.get(agent.status, C_DIM)

        tools_str = ", ".join(agent.tools[:3]) + ("..." if len(agent.tools) > 3 else "")
        model_str = agent.models.get("reasoning", agent.models.get("coding", "auto"))
        sessions_str = str(agent.metrics.sessions_run) if agent.metrics.sessions_run else "—"

        table.add_row(
            Text(avatar),
            Text(agent.name, style=f"bold {C_TEXT}"),
            Text(agent.role.replace("_", " ").title()),
            Text(f"{status_icon} {agent.status}", style=f"bold {s_color}"),
            Text(model_str, style=C_DIM),
            Text(tools_str, style=C_DIM),
            Text(sessions_str),
        )

    return table


def show_agent_dashboard(console: Console | None = None, runtime: AgentRuntime | None = None) -> None:
    """Display the agent dashboard with live status."""
    console = console or get_console()
    agents = store.list_agents()
    instances = runtime.list_all_instances() if runtime else {}
    instance_map = {i.config.id: i for i in instances} if instances else {}

    clear_screen()
    console.print()

    # Header
    console.print(
        Panel(
            Align.center(
                Group(
                    Text("  ◆  Agent Dashboard  ◆  ", style=f"bold {C_PURPLE}"),
                    Text(f"  {len(agents)} agents registered — {len(instances)} running", style=C_DIM),
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
        console.print(Text("  No agents created yet. Create one with /agent create", style=C_DIM))
        console.print()
        return

    # Grid view (cards)
    cards = [build_agent_card(a, instance_map.get(a.id)) for a in agents]
    console.print(
        Panel(
            Group(Text("  Agents", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # Table view
    console.print(
        Panel(
            Group(Text("  All Agents", style=f"bold {C_TEXT}"), Text(""), build_agent_table(agents, instance_map)),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()


def clear_screen() -> None:
    """Clear the terminal screen."""
    import os
    os.system("cls" if os.name == "nt" else "clear")


def run_live_dashboard(console: Console | None = None, runtime: AgentRuntime | None = None,
                       refresh_interval: float = 2.0) -> None:
    """Run a live-updating agent dashboard."""
    console = console or get_console()

    try:
        with Live(refresh_per_second=1 / refresh_interval, console=console) as live:
            while True:
                agents = store.list_agents()
                instances = runtime.list_all_instances() if runtime else {}
                instance_map = {i.config.id: i for i in instances} if instances else {}

                cards = [build_agent_card(a, instance_map.get(a.id)) for a in agents]
                table = build_agent_table(agents, instance_map)

                layout = Table.grid(padding=(0, 1))
                layout.add_column()

                layout.add_row(
                    Panel(
                        Align.center(
                            Text("  ◆  Agent Dashboard (Live)  ◆  ", style=f"bold {C_PURPLE}"),
                            vertical="middle",
                        ),
                        border_style=C_PURPLE,
                        padding=(1, 4),
                        box=rich_box.ROUNDED,
                    )
                )
                if cards:
                    layout.add_row(Columns(cards, equal=False, expand=False))
                layout.add_row(Text(""))
                layout.add_row(
                    Panel(table, border_style=C_BORDER, padding=(1, 2), box=rich_box.ROUNDED)
                )

                live.update(layout)
                time.sleep(refresh_interval)

    except KeyboardInterrupt:
        pass
