"""
AetherOS First Launch — welcome dashboard and enhanced terminal home.

Shown when a user starts AetherOS for the first time after initialization.
Provides quick access to: Continue Session, New Project, Open Workspace,
Create Agent, Import Repository, Connect Services, and Settings.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from rich import box as rich_box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_constants import display_aetheros_home, get_aetheros_home
from aetheros_cli.setup_renderer import (
    C_ACCENT,
    C_BORDER,
    C_CARD_BG,
    C_CYAN,
    C_DIM,
    C_ERROR,
    C_PURPLE,
    C_SUCCESS,
    C_TEXT,
    C_WARN,
    clear,
    get_console,
    icon,
    make_card,
    make_keyboard_hints,
    make_nav_bar,
    make_step_progress,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Welcome Dashboard
# =============================================================================


def show_welcome_dashboard(config: dict) -> None:
    """Display the first-launch welcome dashboard.

    Shows after setup wizard + initialization flow complete. Provides
    quick action cards for common startup tasks.
    """
    from aetheros_cli.setup_wizard import _get_key
    console = get_console()
    clear()

    agent_identity = config.get("agent", {}).get("identity", {})
    agent_name = agent_identity.get("name", "Aether")

    # ── Header ──────────────────────────────────────────────────────

    header = Table.grid(padding=(0, 1))
    header.add_column(justify="center")
    header.add_row(Text(""))
    header.add_row(
        Text(f"  ◆  Welcome to AetherOS, {agent_name}  ◆  ", style=f"bold {C_PURPLE}")
    )
    header.add_row(Text(""))
    header.add_row(
        Text("Your autonomous AI operating system is ready.", style=C_TEXT)
    )
    header.add_row(Text(""))

    console.print(
        Panel(
            Align.center(header, vertical="middle"),
            border_style=C_PURPLE,
            padding=(1, 4),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # ── Quick Actions ────────────────────────────────────────────────

    actions = [
        ("1", "Continue Session", "Resume your last conversation", C_ACCENT),
        ("2", "Start New Project", "Create a new project workspace", C_CYAN),
        ("3", "Open Workspace", "Browse ~/AetherOS/Projects", C_PURPLE),
        ("4", "Create Agent", "Set up a new AI agent", C_SUCCESS),
        ("5", "Import Repository", "Clone a Git repository", C_ACCENT),
        ("6", "Connect Services", "Link Telegram, Discord, etc.", C_CYAN),
        ("7", "Settings", "Configure AetherOS", C_TEXT),
    ]

    action_cards = []
    for num, label, desc, color in actions:
        card = Table.grid(padding=(0, 1))
        card.add_row(Text(f"  {num}.  {label}", style=f"bold {color}"))
        card.add_row(Text(f"       {desc}", style=f"dim {C_DIM}"))
        action_cards.append(
            Panel(
                card,
                border_style=C_BORDER,
                padding=(0, 1),
                box=rich_box.ROUNDED,
            )
        )

    console.print(
        Panel(
            Group(
                Text("  Quick Actions", style=f"bold {C_TEXT}"),
                Text(""),
                Columns(action_cards, equal=False, expand=False),
            ),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # ── System Status ────────────────────────────────────────────────

    aetheros_home = get_aetheros_home()
    workspace = Path.home() / "AetherOS"

    status_rows = [
        ("Agent", agent_name, C_ACCENT),
        ("Workspace", str(workspace) if workspace.exists() else "Not created", C_TEXT if workspace.exists() else C_DIM),
        ("AETHEROS_HOME", str(display_aetheros_home()), C_DIM),
        ("Config", "Ready", C_SUCCESS),
    ]
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column("Label", width=14, style=C_TEXT)
    status_table.add_column("Value", width=50)
    for label, value, style in status_rows:
        status_table.add_row(Text(f"  {label}:", style=style), Text(value, style=style))

    console.print(
        Panel(
            Group(
                Text("  System Status", style=f"bold {C_TEXT}"),
                Text(""),
                status_table,
            ),
            border_style=C_BORDER,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    # ── Footer ──────────────────────────────────────────────────────

    console.print(
        make_keyboard_hints([
            ("Enter", "Default: Continue Session"),
            ("1-7", "Select action"),
            ("Esc", "Skip to terminal"),
        ])
    )

    # ── Handle selection ────────────────────────────────────────────

    while True:
        key = _get_key()
        if key in ("confirm", "1") or not key:
            _action_continue_session(config)
            return
        elif key == "2":
            _action_new_project(console)
            return
        elif key == "3":
            _action_open_workspace(console)
            return
        elif key == "4":
            _action_create_agent(config)
            return
        elif key == "5":
            _action_import_repo(console)
            return
        elif key == "6":
            _action_connect_services(console)
            return
        elif key == "7":
            _action_settings(console)
            return
        elif key == "cancel":
            return


# =============================================================================
# Action Handlers
# =============================================================================


def _action_continue_session(config: dict) -> None:
    """Proceed to normal terminal session."""
    pass  # Just returns — caller handles the transition


def _action_new_project(console: Console) -> None:
    """Create a new project in the workspace."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.styles import Style as PtStyle
    pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
    session = PromptSession(style=pt_style)

    console.print()
    console.print(
        Panel(
            Align.center(Text("Create a New Project", style=f"bold {C_ACCENT}")),
            border_style=C_ACCENT,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    try:
        name = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Project name: ")
        if name.strip():
            workspace = Path.home() / "AetherOS" / "Projects" / name.strip()
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "README.md").write_text(f"# {name.strip()}\n\nProject created by AetherOS.\n")
            console.print()
            console.print(f"  [{C_SUCCESS}]✓[/]  Project created: {workspace}")
            time.sleep(1.5)
    except (EOFError, KeyboardInterrupt):
        pass


def _action_open_workspace(console: Console) -> None:
    """Display the workspace directory contents."""
    workspace = Path.home() / "AetherOS"

    console.print()
    console.print(
        Panel(
            Align.center(Text(f"AetherOS Workspace", style=f"bold {C_CYAN}")),
            border_style=C_CYAN,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    if workspace.exists():
        _print_tree(console, workspace, 0)
    else:
        console.print(f"  [{C_WARN}]⚠[/]  Workspace not found at {workspace}")

    console.print()
    console.print(f"  [{C_DIM}]Press any key to continue...[/]")
    from aetheros_cli.setup_wizard import _get_key
    _get_key()


def _print_tree(console: Console, path: Path, level: int = 0, max_depth: int = 2) -> None:
    """Print an indented directory tree."""
    if level > max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for entry in entries:
            if entry.name.startswith("."):
                continue
            indent = "  " * (level + 1)
            if entry.is_dir():
                console.print(f"  {indent}📁  {C_CYAN}{entry.name}{C_DIM}/")
                _print_tree(console, entry, level + 1, max_depth)
            else:
                console.print(f"  {indent}📄  {C_DIM}{entry.name}")
    except PermissionError:
        pass


def _action_create_agent(config: dict) -> None:
    """Launch the agent creator wizard."""
    console = get_console()
    console.print()
    console.print(f"  [{C_PURPLE}]◈[/]  Launching Agent Creator...")
    time.sleep(0.5)

    from aetheros_cli.agent_creator import run_agent_creator
    identity = run_agent_creator(config)
    if identity:
        console.print()
        console.print(f"  [{C_SUCCESS}]✓[/]  Agent '{identity.get('name', 'Aether')}' created")
        time.sleep(1.5)


def _action_import_repo(console: Console) -> None:
    """Import a Git repository."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.styles import Style as PtStyle
    pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
    session = PromptSession(style=pt_style)

    console.print()
    console.print(
        Panel(
            Align.center(Text("Import a Repository", style=f"bold {C_ACCENT}")),
            border_style=C_ACCENT,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()

    try:
        url = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Git URL: ")
        if url.strip():
            import subprocess
            workspace = Path.home() / "AetherOS" / "Projects"
            workspace.mkdir(parents=True, exist_ok=True)
            name = url.strip().split("/")[-1].replace(".git", "")
            target = workspace / name

            console.print(f"  [{C_DIM}]Cloning into {target}...[/]")
            try:
                subprocess.run(["git", "clone", url.strip(), str(target)], check=True, timeout=120)
                console.print(f"  [{C_SUCCESS}]✓[/]  Repository cloned: {target}")
            except subprocess.CalledProcessError:
                console.print(f"  [{C_ERROR}]✗[/]  Failed to clone repository")
            except subprocess.TimeoutExpired:
                console.print(f"  [{C_ERROR}]✗[/]  Clone timed out")

            time.sleep(1.5)
    except (EOFError, KeyboardInterrupt):
        pass


def _action_connect_services(console: Console) -> None:
    """Prompt user to connect external services."""
    console.print()
    console.print(
        Panel(
            Align.center(
                Group(
                    Text("Connect External Services", style=f"bold {C_CYAN}"),
                    Text(""),
                    Text("Run this later with:", style=C_DIM),
                    Text("  aetheros setup  →  Connect Services", style=C_TEXT),
                ),
                vertical="middle",
            ),
            border_style=C_CYAN,
            padding=(2, 4),
            box=rich_box.ROUNDED,
        )
    )
    console.print()
    from aetheros_cli.setup_wizard import _get_key
    console.print(f"  [{C_DIM}]Press any key to continue...[/]")
    _get_key()


def _action_settings(console: Console) -> None:
    """Launch the settings app."""
    console.print()
    console.print(f"  [{C_ACCENT}⚙[/]  Opening Settings...")
    time.sleep(0.5)
    try:
        from aetheros_cli.settings_app import run_settings_app
        from aetheros_cli.config import load_config
        cfg = load_config()
        run_settings_app(cfg)
    except Exception as e:
        console.print(f"  [{C_ERROR}]✗[/]  Failed to open Settings: {e}")
        time.sleep(1.5)


# =============================================================================
# Enhanced Terminal Home
# =============================================================================


def detect_first_launch(config: dict) -> bool:
    """Check if this is a first launch after initialization."""
    onboarding = config.get("onboarding", {})
    return not onboarding.get("dashboard_shown", False)


def mark_dashboard_shown(config: dict) -> None:
    """Mark the welcome dashboard as shown."""
    config.setdefault("onboarding", {})["dashboard_shown"] = True
    from aetheros_cli.config import save_config
    save_config(config)


def build_enhanced_terminal_home(
    console: "Console",
    model: str,
    cwd: str,
    session_id: str | None = None,
    context_length: int | None = None,
    config: dict | None = None,
) -> None:
    """Build an enhanced terminal home with system status sections.

    This extends the minimal banner with live status info.
    """
    from aetheros_cli.banner import (
        _skin_color,
        format_banner_version_label,
        get_update_result,
        prefetch_update_check,
    )

    dim = _skin_color("banner_dim", "#8b949e")
    accent = _skin_color("banner_accent", "#58a6ff")
    text_color = _skin_color("banner_text", "#e6edf3")

    model_short = model.split("/")[-1] if "/" in model else model
    if model_short.endswith(".gguf"):
        model_short = model_short[:-5]
    if len(model_short) > 40:
        model_short = model_short[:37] + "..."

    ctx_str = str(context_length) if context_length else "?"
    version_label = format_banner_version_label()

    agent_name = "Aether"
    personality = "professional"
    if config:
        identity = config.get("agent", {}).get("identity", {})
        agent_name = identity.get("name", "Aether")
        personality = identity.get("personality", "professional")

    personality_labels = {
        "professional": "Professional", "friendly": "Friendly",
        "technical": "Technical", "researcher": "Researcher",
        "developer": "Developer", "creative": "Creative",
        "minimal": "Minimal", "custom": "Custom",
    }
    personality_label = personality_labels.get(personality, personality)

    # ── Title block ─────────────────────────────────────────────────

    console.print()
    console.print(f"[bold {text_color}]AetherOS  —  {agent_name}[/]")
    version_style = f"dim {dim}"
    console.print(f"[{version_style}]Autonomous AI Operating System  {version_label}[/]")
    console.print()

    # ── Status sections ─────────────────────────────────────────────

    sections = [
        ("Project", cwd),
        ("Agent", f"{agent_name}  ({personality_label})"),
        ("Model", model_short),
        ("Context", f"{ctx_str} tokens"),
    ]

    b_sec_accent = f"[{accent}]"
    r_sec_reset = f"[/]"
    b_sec_text = f"[{text_color}]"

    for label, value in sections:
        console.print(f"{b_sec_accent}{label}{r_sec_reset}")
        console.print(f"{b_sec_text}{value}{r_sec_reset}")

    if session_id:
        console.print(f"[dim {dim}]Session: {session_id}[/]")

    # ── Update check ────────────────────────────────────────────────

    try:
        behind = get_update_result(timeout=0.3)
        if behind is not None and behind != 0:
            if behind > 0:
                commits_word = "commit" if behind == 1 else "commits"
                console.print(f"[dim {dim}]{behind} {commits_word} behind — update available[/]")
            else:
                console.print(f"[dim {dim}]update available[/]")
    except Exception:
        pass

    console.print()
    try:
        from aetheros_cli.skin_engine import get_active_prompt_symbol
        symbol = get_active_prompt_symbol(">")
        console.print(f"[{dim}]Ready.[/]")
    except Exception:
        console.print(f"[{dim}]Ready.[/]")

    console.print()
