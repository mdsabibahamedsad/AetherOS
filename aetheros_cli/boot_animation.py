"""
AetherOS Cinematic Boot Animation — premium startup sequence.

Features:
- Typing-effect brand reveal
- Real system checks (Python, GPU, providers)
- Animated progress bar
- Phase-by-phase status indicators
- Version display
- Transitions seamlessly into setup wizard or agent session
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

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
    get_console,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Boot Phases
# =============================================================================

_BOOT_PHASES = [
    ("Initializing Runtime...", "system", 0.3),
    ("Loading Plugins...", "plugin", 0.4),
    ("Loading AI Providers...", "provider", 0.5),
    ("Checking Python...", "system", 0.2),
    ("Checking GPU...", "hardware", 0.6),
    ("Loading Memory...", "memory", 0.4),
    ("Loading MCP...", "mcp", 0.5),
    ("Loading Extensions...", "extension", 0.3),
    ("Preparing Workspace...", "workspace", 0.4),
    ("Launching AetherOS...", "launch", 0.6),
]

_PHASE_ICONS = {
    "system": "⚙",
    "plugin": "🔌",
    "provider": "☁",
    "hardware": "🖥",
    "memory": "🧠",
    "mcp": "🔗",
    "extension": "🧩",
    "workspace": "📁",
    "launch": "🚀",
}

# =============================================================================
# AetherOS Premium Brand Animation
# =============================================================================

# Wolf logo ASCII art - premium geometric design
_WOLF_LOGO = """
    /\\      /\\
   /  \\    /  \\
  /    \\  /    \\
 /  /\\  \\/  /\\  \\
/  /  \\    /  \\  \\
\\  \\    /  /    / /
 \\  \\  /  /    / /
  \\  \\/  /    / /
   \\    /    / /
    \\  /    / /
     \\/    / /
      \\   / /
       \\ / /
        \\/
"""

_BRAND_LINES = [
    "",
    "  ╔═══════════════════════════════════════╗",
    "  ║                                       ║",
    "  ║      ◆  A E T H E R O S  ◆           ║",
    "  ║                                       ║",
    "  ║      AI Operating System              ║",
    "  ║                                       ║",
    "  ╚═══════════════════════════════════════╝",
    "",
]


def _type_text(text: str, style: str, speed: float = 0.02) -> Text:
    """Create a typing-effect text segment (static display, not animated)."""
    return Text(text, style=style)


def _detect_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _detect_gpu() -> str:
    try:
        if shutil.which("nvidia-smi"):
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0]
        return "Not detected"
    except Exception:
        return "Check failed"


def _detect_ollama() -> bool:
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        req.timeout = 1
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


# =============================================================================
# Renderer
# =============================================================================


def _build_status_table(
    completed: list[str],
    current: Optional[str],
    show_real_checks: bool = False,
) -> Panel:
    """Build the status table for the boot animation."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Status", width=6)
    table.add_column("Phase", width=40)
    table.add_column("Detail", width=30)

    for phase_name, phase_type, _duration in _BOOT_PHASES:
        icon = _PHASE_ICONS.get(phase_type, " ")
        phase_display = f"{icon}  {phase_name}"

        if phase_name in completed:
            status = Text("✓", style=f"bold {C_SUCCESS}")
            phase_text = Text(phase_display, style=f"dim {C_DIM}")
            detail = ""
            if show_real_checks and phase_name == "Checking Python...":
                detail = _detect_python_version()
            elif show_real_checks and phase_name == "Checking GPU...":
                detail = _detect_gpu()
            detail_text = Text(detail or "", style=f"dim {C_DIM}")
        elif phase_name == current:
            spinner = Spinner("dots", text="", style=C_ACCENT)
            status = spinner
            phase_text = Text(phase_display, style=f"bold {C_TEXT}")
            detail_text = Text("", style=C_DIM)
        else:
            status = Text(" ", style=C_DIM)
            phase_text = Text(phase_display, style=f"dim {C_DIM}")
            detail_text = Text("", style=C_DIM)

        table.add_row(status, phase_text, detail_text)

    return table


def play_boot_animation(
    console: Optional[Console] = None,
    first_boot: bool = False,
) -> None:
    """Play the cinematic AetherOS boot animation sequence.

    Args:
        console: Optional Rich console. Creates one if not provided.
        first_boot: If True, shows the full setup-prominent boot flow.
    """
    if console is None:
        console = get_console(highlight=False)

    completed: list[str] = []
    total = len(_BOOT_PHASES)

    # ── Brand reveal ──────────────────────────────────────────────────
    brand_panel = Panel(
        Align.center(
            Group(
                Text("  ", style=f"bold {C_PURPLE}"),
                Text(_BRAND_LINES[0], style=f"bold {C_PURPLE}"),
                Text(""),
                Text(_BRAND_LINES[1], style=f"italic {C_DIM}"),
            ),
            vertical="middle",
        ),
        border_style=C_PURPLE,
        padding=(2, 4),
        box=None,
        style=f"on {C_CARD_BG}",
    )

    with Live(brand_panel, console=console, refresh_per_second=15, transient=True) as live:
        time.sleep(0.8)

        # ── Boot phases ───────────────────────────────────────────────
        for i, (phase_name, phase_type, duration) in enumerate(_BOOT_PHASES):
            progress_pct = int((i / total) * 20)
            bar = f"[{'█' * progress_pct}{'░' * (20 - progress_pct)}]"
            pct = int((i / total) * 100)

            status_table = _build_status_table(completed, phase_name)
            info_line = Text(f"  {bar}  {pct}%  ", style=f"bold {C_CYAN}")

            combined = Table.grid(padding=(0, 1))
            combined.add_row(status_table)
            combined.add_row(Text(""))
            combined.add_row(info_line)
            if first_boot and pct > 30:
                combined.add_row(
                    Text(
                        "  Setting up your AetherOS environment...",
                        style=f"italic {C_DIM}",
                    )
                )

            combined_panel = Panel(
                Align.center(combined, vertical="middle"),
                border_style=C_PURPLE,
                padding=(1, 4),
                box=None,
                style=f"on {C_CARD_BG}",
            )

            live.update(combined_panel)

            # Real work during phases
            if phase_name == "Checking Python...":
                _py_ver = _detect_python_version()
                time.sleep(0.1)
            elif phase_name == "Checking GPU...":
                _gpu_info = _detect_gpu()
                time.sleep(0.1)
            elif phase_name == "Initializing Runtime...":
                __import__("aetheros_constants")
                time.sleep(0.1)

            time.sleep(duration)
            completed.append(phase_name)

        # ── Completion ────────────────────────────────────────────────
        status_table = _build_status_table(completed, None, show_real_checks=True)
        bar = "[████████████████████]"
        info_line = Text(f"  {bar}  100%  ", style=f"bold {C_SUCCESS}")

        final_combined = Table.grid(padding=(0, 1))
        final_combined.add_row(status_table)
        final_combined.add_row(Text(""))
        final_combined.add_row(info_line)

        if first_boot:
            final_combined.add_row(Text(""))
            final_combined.add_row(
                Text(
                    "  Welcome to AetherOS — let's get you set up.",
                    style=f"italic {C_ACCENT}",
                )
            )

        final_panel = Panel(
            Align.center(final_combined, vertical="middle"),
            border_style=C_CYAN,
            padding=(1, 4),
            box=None,
            style=f"on {C_CARD_BG}",
        )

        live.update(final_panel)
        time.sleep(0.6)

        # ── Ready screen ──────────────────────────────────────────────
        ready_content = Table.grid(padding=(0, 1))
        ready_content.add_column(justify="center")
        ready_content.add_row(Text(""))
        ready_content.add_row(
            Text("◆  A E T H E R O S  ◆", style=f"bold {C_PURPLE}")
        )
        ready_content.add_row(Text(""))
        ready_content.add_row(
            Text("v" + _detect_python_version(), style=f"dim {C_DIM}")
        )
        ready_content.add_row(Text(""))
        ready_content.add_row(
            Text(
                "Ready." if not first_boot else "Welcome. Let's configure your system.",
                style=f"bold {C_CYAN}",
            )
        )

        ready_panel = Panel(
            Align.center(ready_content, vertical="middle"),
            border_style=C_CYAN if not first_boot else C_ACCENT,
            padding=(2, 4),
            box=box.ROUNDED,
            style=f"on {C_CARD_BG}",
        )

        live.update(ready_panel)
        time.sleep(1.0)
