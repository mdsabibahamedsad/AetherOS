"""
AetherOS Premium Setup Renderer — OS-installer-grade UI components.

Shared rendering utilities for the setup wizard, settings app, and
services hub. Provides a consistent premium look: rounded panels,
accent-colored cards, progress indicators, navigation bars, and
keyboard shortcut displays.
"""

from __future__ import annotations

import logging
from typing import Any

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)

# =============================================================================
# Brand Color Palette — premium OS installer aesthetic
# =============================================================================

C_ACCENT = "#58a6ff"
C_SUCCESS = "#3fb950"
C_WARN = "#d29922"
C_ERROR = "#f85149"
C_PURPLE = "#bc8cff"
C_CYAN = "#39d2c0"
C_TEXT = "#e6edf3"
C_DIM = "#8b949e"
C_BORDER = "#30363d"
C_BORDER_LIGHT = "#484f58"
C_NAV_BG = "#21262d"
C_SECTION_BG = "#161b22"
C_CARD_BG = "#0d1117"
C_GOLD = "#ffd700"
C_CORAL = "#ff6b6b"
C_MINT = "#56d4b0"

# =============================================================================
# ANSI helpers (for non-Rich contexts)
# =============================================================================

A_BOLD = "\033[1m"
A_DIM = "\033[2m"
A_RST = "\033[0m"
A_BLUE = "\033[38;2;88;166;255m"
A_GRAY = "\033[38;2;139;148;158m"
A_WHITE = "\033[38;2;230;237;243m"
A_CYAN = "\033[38;2;57;210;192m"
A_PURPLE = "\033[38;2;188;140;255m"
A_GREEN = "\033[38;2;63;185;80m"
A_YELLOW = "\033[38;2;210;153;34m"
A_RED = "\033[38;2;248;81;73m"

# =============================================================================
# Step icon registry
# =============================================================================

STEP_ICONS = {
    "welcome": "◆",
    "profile": "👤",
    "purpose": "🎯",
    "experience": "📊",
    "ai_providers": "☁",
    "local_detection": "🖥",
    "api_config": "🔑",
    "default_models": "🤖",
    "connect_services": "🔌",
    "automation": "⚡",
    "tools": "🛠",
    "memory": "🧠",
    "privacy": "🔒",
    "workspace": "📁",
    "review": "📋",
    "finish": "🎉",
    "settings": "⚙",
    "services": "🔗",
}


def icon(name: str) -> str:
    return STEP_ICONS.get(name, "◇")


# =============================================================================
# Console helpers
# =============================================================================

_console_cache: dict[int, Console] = {}


def get_console(*, highlight: bool = False, width: int | None = None) -> Console:
    key = id(0)
    if key not in _console_cache:
        _console_cache[key] = Console(highlight=highlight, width=width)
    return _console_cache[key]


def clear() -> None:
    get_console().clear()


# =============================================================================
# Style factories
# =============================================================================


def dim(text: str) -> str:
    return f"[dim]{text}[/dim]"


def bold(text: str) -> str:
    return f"[bold]{text}[/bold]"


def accent(text: str) -> str:
    return f"[{C_ACCENT}]{text}[/{C_ACCENT}]"


def green(text: str) -> str:
    return f"[{C_SUCCESS}]{text}[/{C_SUCCESS}]"


def yellow(text: str) -> str:
    return f"[{C_WARN}]{text}[/{C_WARN}]"


def red(text: str) -> str:
    return f"[{C_ERROR}]{text}[/{C_ERROR}]"


def purple(text: str) -> str:
    return f"[{C_PURPLE}]{text}[/{C_PURPLE}]"


def cyan(text: str) -> str:
    return f"[{C_CYAN}]{text}[/{C_CYAN}]"


def text(text: str) -> str:
    return f"[{C_TEXT}]{text}[/{C_TEXT}]"


# =============================================================================
# Premium OS-installer Layout Components
# =============================================================================


def make_header(title: str, subtitle: str = "", icon_str: str = "") -> Panel:
    """Premium installer header with brand mark, title, and subtitle."""
    content = Table.grid(padding=(0, 1))
    content.add_column(justify="center")
    title_text = Text()
    if icon_str:
        title_text.append(f"{icon_str}  ", style=f"bold {C_PURPLE}")
    title_text.append(title, style=f"bold {C_TEXT}")
    content.add_row(title_text)
    if subtitle:
        content.add_row(Text(subtitle, style=f"italic {C_DIM}"))
    return Panel(
        Align.center(content),
        border_style=C_PURPLE,
        padding=(1, 4),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )


def make_step_progress(
    current: int,
    total: int,
    title: str,
    subtitle: str = "",
) -> Panel:
    """OS-installer progress bar showing Step X/Y with percentage."""
    pct = int((current / total) * 100)
    filled = int((current / total) * 20)
    bar = f"[{'█' * filled}{'░' * (20 - filled)}]"

    progress_table = Table.grid(padding=(0, 2))
    progress_table.add_column("Label", justify="left", width=14)
    progress_table.add_column("Bar", justify="center", width=28)
    progress_table.add_column("Title", justify="right", width=40)

    label = Text(f"Step {current}/{total}", style=f"bold {C_CYAN}")
    bar_text = Text(f"{bar}  {pct}%", style=f"bold {C_ACCENT}")
    title_col = Text(title, style=f"bold {C_TEXT}")

    progress_table.add_row(label, bar_text, title_col)

    if subtitle:
        progress_table.add_row(
            Text(""),
            Text(""),
            Text(subtitle, style=f"italic {C_DIM}"),
        )

    return Panel(
        progress_table,
        border_style=C_BORDER_LIGHT,
        padding=(0, 1),
        box=box.ROUNDED,
        style=f"on {C_SECTION_BG}",
    )


def make_nav_bar(
    can_back: bool = True,
    can_next: bool = True,
    can_skip: bool = False,
    can_save: bool = True,
    step_name: str = "",
) -> Panel:
    """Premium navigation bar with all supported keyboard shortcuts."""
    nav_table = Table.grid(padding=(0, 2))
    nav_table.add_column("Group", justify="center", width=80)

    def btn(label: str, key: str, active: bool) -> str:
        if not active:
            return f"[dim]{label}[/dim]"
        return f"[bold {C_ACCENT}]{label}[/bold {C_ACCENT}]  [dim]{key}[/dim]"

    parts = []
    parts.append(btn("◀  Back", "←", can_back))
    parts.append("   ")
    parts.append(btn("Next  ▶", "Enter", can_next))

    if can_skip:
        parts.extend(["   ", btn("Skip  ⏭", "S", True)])

    parts.extend(
        [
            "  │  ",
            btn("💾  Save", "Ctrl+S", can_save),
            "   ",
            btn("✖  Cancel", "Esc", True),
        ]
    )

    # Mode indicator
    parts.append("  │  ")
    parts.append(f"[dim]Tab[/dim] next  [dim]Shift+Tab[/dim] prev")

    nav_table.add_row("".join(parts))
    return Panel(
        nav_table,
        border_style=C_NAV_BG,
        padding=(0, 1),
        box=box.ROUNDED,
        style=f"on {C_NAV_BG}",
    )


def make_card(
    title: str,
    body: RenderableType,
    accent: str = C_ACCENT,
    icon_str: str = "",
    subtitle: str = "",
    width: int | None = None,
) -> Panel:
    """Premium card with title, optional icon, and rounded border."""
    title_parts = []
    if icon_str:
        title_parts.append(f"{icon_str} ")
    title_parts.append(title)
    full_title = "".join(title_parts)

    return Panel(
        body,
        title=f"[bold {accent}]{full_title}[/bold {accent}]"
        + (f"\n[italic {C_DIM}]{subtitle}[/italic {C_DIM}]" if subtitle else ""),
        title_align="left",
        border_style=accent,
        padding=(1, 2),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
        width=width,
    )


def make_info_card(
    title: str,
    items: list[tuple[str, str]],
    accent: str = C_ACCENT,
) -> Panel:
    """Key-value information card."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Key", width=20)
    table.add_column("Value", width=50)
    for key, val in items:
        table.add_row(
            Text(f"  {key}", style=f"bold {accent}"),
            Text(str(val), style=C_TEXT),
        )
    return make_card(title, table, accent)


def make_checklist(
    items: list[tuple[str, str, str]],
    selected: set[str],
    cursor: int = 0,
    columns: int = 1,
) -> Panel:
    """Multi-column checklist with selection indicators."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Sel", width=4)
    table.add_column("Item", width=60)
    table.add_column("Description", width=40)

    for i, (key, label, desc) in enumerate(items):
        checked = "◉" if key in selected else "○"
        sel = "▸" if i == cursor else " "
        style = f"bold {C_TEXT}" if i == cursor else C_DIM
        table.add_row(
            Text(f"{sel} {checked}", style=style),
            Text(label, style=style),
            Text(desc, style=f"italic {C_DIM}"),
        )

    return table


def make_selection_list(
    items: list[tuple[str, str]],
    selected_index: int = 0,
    multi: bool = False,
    selected_items: set[str] | None = None,
    filter_text: str = "",
) -> Table:
    """Filterable selection list for pickers."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Sel", width=4)
    table.add_column("Item", width=50)

    filtered = items
    if filter_text:
        filtered = [
            (k, v)
            for k, v in items
            if filter_text.lower() in k.lower()
            or filter_text.lower() in v.lower()
        ]

    for i, (key, label) in enumerate(filtered):
        if multi:
            checked = "◉" if (selected_items and key in selected_items) else "○"
        else:
            checked = "▸" if i == selected_index else " "
        style = f"bold {C_TEXT}" if i == selected_index else C_DIM
        table.add_row(Text(checked, style=style), Text(label, style=style))

    if filter_text:
        table.add_row(
            Text(""),
            Text(f"  filter: {filter_text}", style=f"italic {C_DIM}"),
        )

    return table


def make_status_indicator(status: str, label: str) -> Text:
    """Colored status indicator."""
    status_map = {
        "connected": (C_SUCCESS, "✓"),
        "disconnected": (C_DIM, "○"),
        "error": (C_ERROR, "✗"),
        "warning": (C_WARN, "⚠"),
        "loading": (C_ACCENT, "⟳"),
        "detected": (C_SUCCESS, "✓"),
        "not_found": (C_DIM, "✗"),
        "enabled": (C_SUCCESS, "◉"),
        "disabled": (C_DIM, "○"),
    }
    color, sym = status_map.get(status, (C_DIM, "?"))
    return Text(f"  {sym} {label}", style=f"bold {color}")


def make_divider(text: str = "", style: str = C_DIM) -> Rule:
    """Styled divider."""
    return Rule(
        text,
        style=Style(color=style, dim=True),
        characters="─",
    )


def make_keyboard_hints(hints: list[tuple[str, str]]) -> Panel:
    """Keyboard shortcut hints bar."""
    parts = []
    for i, (key, desc) in enumerate(hints):
        if i > 0:
            parts.append("  ")
        parts.append(f"[dim]{key}[/dim] [bold {C_DIM}]{desc}[/bold {C_DIM}]")

    height = (len(parts) // 6) + 1 if parts else 1
    return Panel(
        Text("  " + "  ·  ".join(parts) if parts else ""),
        border_style=C_BORDER,
        padding=(0, 1),
        box=box.SIMPLE,
        style=f"on {C_NAV_BG}",
    )


def make_success_screen(
    title: str,
    message: str,
    details: list[str] | None = None,
) -> Panel:
    """Premium success/completion screen."""
    content = Table.grid(padding=(0, 1))
    content.add_column(justify="center")
    content.add_row(Text(""))
    content.add_row(Text(f"◆  {title}  ◆", style=f"bold {C_SUCCESS}"))
    content.add_row(Text(""))
    content.add_row(Text(message, style=C_TEXT))
    if details:
        content.add_row(Text(""))
        for d in details:
            content.add_row(Text(f"  {d}", style=C_DIM))
    content.add_row(Text(""))
    return Panel(
        Align.center(content),
        border_style=C_SUCCESS,
        padding=(2, 4),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )


def make_error_screen(
    title: str,
    message: str,
    hint: str = "",
) -> Panel:
    """Premium error screen."""
    content = Table.grid(padding=(0, 1))
    content.add_column(justify="center")
    content.add_row(Text(""))
    content.add_row(Text(f"✗  {title}  ✗", style=f"bold {C_ERROR}"))
    content.add_row(Text(""))
    content.add_row(Text(message, style=C_TEXT))
    if hint:
        content.add_row(Text(""))
        content.add_row(Text(hint, style=f"italic {C_DIM}"))
    content.add_row(Text(""))
    return Panel(
        Align.center(content),
        border_style=C_ERROR,
        padding=(2, 4),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )


def make_section_card(
    section_name: str,
    section_icon: str,
    summary: str,
    status: str,
    accent: str = C_ACCENT,
) -> Panel:
    """Settings section card for browser view."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Info", width=60)

    icon_str = icon(section_name) or section_icon
    name_label = section_name.replace("_", " ").title()

    status_colors = {
        "configured": C_SUCCESS,
        "partial": C_WARN,
        "pending": C_DIM,
        "skipped": C_DIM,
    }
    sc = status_colors.get(status, C_DIM)

    table.add_row(
        Text(f"  {icon_str}  {name_label}", style=f"bold {C_TEXT}")
    )
    table.add_row(
        Text(f"     {summary}", style=dim(C_DIM))
    )
    table.add_row(
        Text(f"     Status: ", style=C_DIM)
        + Text(status.replace("_", " ").title(), style=f"bold {sc}")
    )

    return Panel(
        table,
        border_style=accent if status == "configured" else C_BORDER,
        padding=(0, 1),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )


# =============================================================================
# Full-screen layout builders
# =============================================================================


def build_full_screen(
    progress: Panel,
    content: Panel,
    nav: Panel,
    hints: Panel | None = None,
    sidebar: Panel | None = None,
) -> Layout:
    """Build a full-screen OS-installer layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="progress", size=4),
        Layout(name="main"),
        Layout(name="nav", size=3),
    )

    layout["progress"].update(progress)
    layout["nav"].update(nav)

    if sidebar:
        layout["main"].split_row(
            Layout(name="content", ratio=3),
            Layout(name="sidebar", ratio=1),
        )
        layout["main"]["content"].update(content)
        layout["main"]["sidebar"].update(sidebar)
    else:
        layout["main"].update(content)

    return layout


# =============================================================================
# Loading / Spinner utilities
# =============================================================================


def make_loading_panel(
    message: str, spinner_name: str = "dots"
) -> Panel:
    """Loading indicator panel."""
    spinner = Spinner(spinner_name, text=message, style=C_ACCENT)
    return Panel(
        Align.center(spinner),
        border_style=C_BORDER,
        padding=(2, 4),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )


# =============================================================================
# Confirmation dialogs
# =============================================================================


def confirm_dialog(
    title: str,
    message: str,
    confirm_label: str = "Y",
    cancel_label: str = "N",
) -> Panel:
    """Standard confirmation dialog box."""
    content = Table.grid(padding=(0, 1))
    content.add_column(justify="center")
    content.add_row(Text(message, style=C_WARN))
    content.add_row(Text(""))
    content.add_row(
        Text(
            f"  Press {confirm_label} to confirm, {cancel_label} to cancel",
            style=f"dim {C_DIM}",
        )
    )
    return Panel(
        Align.center(content),
        title=f"[bold {C_WARN}]{title}[/bold {C_WARN}]",
        border_style=C_WARN,
        padding=(1, 3),
        box=box.ROUNDED,
        style=f"on {C_CARD_BG}",
    )
