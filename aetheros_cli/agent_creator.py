"""
AetherOS Agent Creator — define your AI agent's identity and preferences.

Interactive wizard for naming your agent, choosing its personality,
conversation style, reasoning level, and coding preferences.
All settings are stored in config.yaml and editable later.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from rich import box as rich_box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_cli.config import ensure_aetheros_home, load_config, save_config
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
from aetheros_cli.setup_wizard import _get_key

logger = logging.getLogger(__name__)

# =============================================================================
# Agent Identity Options
# =============================================================================

AGENT_NAMES = [
    "Aether",
    "Nova",
    "Atlas",
    "Friday",
    "Jarvis",
    "Echo",
    "Neo",
    "Onyx",
    "Sage",
    "Luna",
    "Orion",
    "Pixel",
    "Raven",
    "Spark",
    "Zephyr",
]

PERSONALITIES = [
    ("professional", "Professional", "Formal, precise, and business-oriented"),
    ("friendly", "Friendly", "Warm, approachable, and conversational"),
    ("technical", "Technical", "Detailed, precise, and technically focused"),
    ("researcher", "Researcher", "Analytical, thorough, and evidence-based"),
    ("developer", "Developer", "Code-focused with practical engineering insights"),
    ("creative", "Creative", "Imaginative, exploratory, and design-oriented"),
    ("minimal", "Minimal", "Brief, direct, and to the point"),
    ("custom", "Custom", "Define your own personality"),
]

CONVERSATION_STYLES = [
    ("concise", "Concise", "Short, direct answers — get to the point"),
    ("balanced", "Balanced", "Thorough but not verbose — the default"),
    ("detailed", "Detailed", "Comprehensive explanations with full context"),
]

REASONING_LEVELS = [
    ("fast", "Fast", "Quick responses for simple tasks"),
    ("balanced", "Balanced", "Standard reasoning — good for most tasks"),
    ("deep", "Deep Thinking", "Extended reasoning for complex problems"),
]

CODING_PREFERENCES = [
    ("python", "Python", "General-purpose, data science, AI/ML"),
    ("javascript", "JavaScript", "Web development, Node.js, full-stack"),
    ("typescript", "TypeScript", "Type-safe JavaScript, web apps"),
    ("rust", "Rust", "Systems programming, performance-critical"),
    ("go", "Go", "Cloud services, microservices, backends"),
    ("java", "Java", "Enterprise, Android, large-scale systems"),
    ("csharp", "C#", ".NET, game dev, enterprise applications"),
    ("cpp", "C++", "Systems, game dev, high-performance computing"),
]

# =============================================================================
# Agent Creator Wizard
# =============================================================================


class AgentCreator:
    """Interactive agent creation wizard."""

    def __init__(self, config: dict):
        self.config = config
        self._running = True
        self._step = 0

        # Agent state
        self._agent_name = "Aether"
        self._personality = "professional"
        self._conversation_style = "balanced"
        self._reasoning_level = "balanced"
        self._coding_prefs: set[str] = set()
        self._custom_name_mode = False
        self._cursor = 0

    def run(self) -> dict:
        """Run the agent creator wizard. Returns agent config dict."""
        self._step = 0
        self._show_intro()

        steps = [
            self._step_name,
            self._step_personality,
            self._step_style,
            self._step_reasoning,
            self._step_coding,
        ]

        for step_fn in steps:
            self._cursor = 0
            step_fn()
            if not self._running:
                break

        return self._build_config()

    def _show_intro(self) -> None:
        """Show the agent creation intro screen."""
        clear()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text("◆  Create Your AI Agent  ◆", style=f"bold {C_PURPLE}"),
                        Text(""),
                        Text("Your personal AI companion needs a name and personality.", style=C_TEXT),
                        Text("You can change all of this later in Settings.", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_PURPLE,
                padding=(2, 4),
                box=rich_box.ROUNDED,
            )
        )
        get_console().print()
        get_console().print(make_keyboard_hints([("Enter", "Start"), ("Esc", "Skip")]))

        key = _get_key()
        if key == "cancel":
            self._running = False

    def _render_progress(self) -> None:
        """Render step progress header."""
        progress = make_step_progress(
            min(self._step + 1, 5), 5,
            "Create Agent",
            f"Step {min(self._step + 1, 5)} of 5"
        )
        get_console().print(progress)
        get_console().print()

    # ── Step 1: Agent Name ──────────────────────────────────────────

    def _step_name(self) -> None:
        """Choose or enter an agent name."""
        self._step = 0
        self._custom_name_mode = False

        while self._running:
            clear()
            self._render_progress()

            # Name cards in a grid
            cards = []
            name_grid = Table.grid(padding=(0, 2))
            name_grid.add_column("Sel", width=4)
            name_grid.add_column("Name", width=60)

            for i, name in enumerate(AGENT_NAMES):
                sel = "◉" if name == self._agent_name and not self._custom_name_mode else "○"
                if i == self._cursor and not self._custom_name_mode:
                    sel = "▸ ◉" if name == self._agent_name else "▸ ○"
                style_text = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                name_grid.add_row(
                    Text(sel, style=f"bold {C_ACCENT}" if i == self._cursor else C_DIM),
                    Text(name, style=style_text),
                )

            # Custom name option at the bottom
            custom_indicator = "◉" if self._custom_name_mode else "○"
            custom_sel = "▸" if len(AGENT_NAMES) <= self._cursor else " "
            custom_style = f"bold {C_TEXT}" if self._custom_name_mode or len(AGENT_NAMES) <= self._cursor else C_DIM
            name_grid.add_row(
                Text(f"{custom_sel} {custom_indicator}", style=custom_style),
                Text(f"Custom: {self._agent_name}" if self._custom_name_mode else "Custom name", style=custom_style),
            )

            get_console().print(
                Panel(
                    Group(
                        Text("  Choose your agent's name:", style=f"bold {C_TEXT}"),
                        Text(""),
                        name_grid,
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Select"),
                    ("C", "Custom name"),
                    ("Esc", "Skip"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                self._running = False
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(AGENT_NAMES), self._cursor + 1)
            elif key == "c" or key == "C":
                self._custom_name_mode = True
                self._prompt_custom_name()
            elif key == "confirm":
                if self._cursor < len(AGENT_NAMES):
                    self._agent_name = AGENT_NAMES[self._cursor]
                    self._custom_name_mode = False
                    return
                else:
                    self._custom_name_mode = True
                    self._prompt_custom_name()
                    return

    def _prompt_custom_name(self) -> None:
        """Prompt for a custom agent name."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)

        get_console().print()
        get_console().print(
            Panel(
                Align.center(Text("Enter a name for your AI agent:", style=C_TEXT)),
                border_style=C_PURPLE,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )

        try:
            value = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Agent name: ", default=self._agent_name)
            if value.strip():
                self._agent_name = value.strip()
        except (EOFError, KeyboardInterrupt):
            pass

    # ── Step 2: Personality ─────────────────────────────────────────

    def _step_personality(self) -> None:
        """Choose agent personality."""
        self._step = 1

        while self._running:
            clear()
            self._render_progress()

            cards = []
            for i, (key, name, desc) in enumerate(PERSONALITIES):
                sel = name == self._personality
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {name}", style=style))
                card.add_row(Text(f"       {desc}", style=f"dim {C_DIM}"))
                cards.append(
                    Panel(
                        card,
                        border_style=border,
                        padding=(0, 1),
                        box=rich_box.ROUNDED,
                    )
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Choose your agent's personality:", style=f"bold {C_TEXT}"),
                        Text(""),
                        Columns(cards, equal=False, expand=False),
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Select"),
                    ("Esc", "Skip"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                idx = max(0, [k for k, _, _ in PERSONALITIES].index(self._personality) - 1)
                self._personality = PERSONALITIES[idx][0]
            elif key == "down":
                keys = [k for k, _, _ in PERSONALITIES]
                idx = min(len(keys) - 1, keys.index(self._personality) + 1)
                self._personality = PERSONALITIES[idx][0]
            elif key == "confirm":
                if self._personality == "custom":
                    self._prompt_custom_personality()
                return

    def _prompt_custom_personality(self) -> None:
        """Prompt for a custom personality description."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)

        get_console().print(
            Panel(
                Align.center(Text("Describe your desired personality:", style=C_TEXT)),
                border_style=C_PURPLE,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )

        try:
            value = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Personality description: ")
            if value.strip():
                self.config.setdefault("agent", {})["custom_personality"] = value.strip()
        except (EOFError, KeyboardInterrupt):
            pass

    # ── Step 3: Conversation Style ──────────────────────────────────

    def _step_style(self) -> None:
        """Choose conversation style."""
        self._step = 2

        while self._running:
            clear()
            self._render_progress()

            cards = []
            for i, (key, name, desc) in enumerate(CONVERSATION_STYLES):
                sel = key == self._conversation_style
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {name}", style=style))
                card.add_row(Text(f"       {desc}", style=f"dim {C_DIM}"))
                cards.append(
                    Panel(
                        card,
                        border_style=border,
                        padding=(0, 1),
                        box=rich_box.ROUNDED,
                    )
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Choose your conversation style:", style=f"bold {C_TEXT}"),
                        Text(""),
                        Columns(cards, equal=False, expand=False),
                    ),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Select"),
                    ("Esc", "Skip"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                idx = max(0, [k for k, _, _ in CONVERSATION_STYLES].index(self._conversation_style) - 1)
                self._conversation_style = CONVERSATION_STYLES[idx][0]
            elif key == "down":
                keys = [k for k, _, _ in CONVERSATION_STYLES]
                idx = min(len(keys) - 1, keys.index(self._conversation_style) + 1)
                self._conversation_style = CONVERSATION_STYLES[idx][0]
            elif key == "confirm":
                return

    # ── Step 4: Reasoning Level ─────────────────────────────────────

    def _step_reasoning(self) -> None:
        """Choose reasoning level."""
        self._step = 3

        while self._running:
            clear()
            self._render_progress()

            cards = []
            for i, (key, name, desc) in enumerate(REASONING_LEVELS):
                sel = key == self._reasoning_level
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {name}", style=style))
                card.add_row(Text(f"       {desc}", style=f"dim {C_DIM}"))
                cards.append(
                    Panel(
                        card,
                        border_style=border,
                        padding=(0, 1),
                        box=rich_box.ROUNDED,
                    )
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Choose reasoning effort:", style=f"bold {C_TEXT}"),
                        Text(""),
                        Columns(cards, equal=False, expand=False),
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Select"),
                    ("Esc", "Skip"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                idx = max(0, [k for k, _, _ in REASONING_LEVELS].index(self._reasoning_level) - 1)
                self._reasoning_level = REASONING_LEVELS[idx][0]
            elif key == "down":
                keys = [k for k, _, _ in REASONING_LEVELS]
                idx = min(len(keys) - 1, keys.index(self._reasoning_level) + 1)
                self._reasoning_level = REASONING_LEVELS[idx][0]
            elif key == "confirm":
                return

    # ── Step 5: Coding Preferences ──────────────────────────────────

    def _step_coding(self) -> None:
        """Choose coding language preferences (multi-select)."""
        self._step = 4

        # Default preselect based on common choices
        if not self._coding_prefs:
            self._coding_prefs.add("python")
            self._coding_prefs.add("javascript")

        while self._running:
            clear()
            self._render_progress()

            lang_table = Table.grid(padding=(0, 2))
            lang_table.add_column("Sel", width=4)
            lang_table.add_column("Language", width=16)
            lang_table.add_column("Use Case", width=40)

            for i, (key, name, desc) in enumerate(CODING_PREFERENCES):
                checked = "◉" if key in self._coding_prefs else "○"
                sel = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                lang_table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Select your preferred programming languages:", style=f"bold {C_TEXT}"),
                        Text("  (These influence code generation suggestions)", style=f"dim {C_DIM}"),
                        Text(""),
                        lang_table,
                    ),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Done"),
                    ("Esc", "Skip"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(CODING_PREFERENCES) - 1, self._cursor + 1)
            elif key == " ":
                lang = CODING_PREFERENCES[self._cursor][0]
                if lang in self._coding_prefs:
                    self._coding_prefs.discard(lang)
                else:
                    self._coding_prefs.add(lang)
            elif key == "confirm":
                return

    # ── Build Config ────────────────────────────────────────────────

    def _build_config(self) -> dict:
        """Build the agent config dict from selections."""
        agent_cfg = self.config.setdefault("agent", {})

        identity = {
            "name": self._agent_name,
            "personality": self._personality,
            "conversation_style": self._conversation_style,
            "reasoning_level": self._reasoning_level,
            "coding_preferences": list(self._coding_prefs),
            "created": True,
        }

        # Map reasoning levels to the internal config
        reasoning_map = {
            "fast": None,
            "balanced": "medium",
            "deep": "high",
        }
        reasoning = reasoning_map.get(self._reasoning_level)
        if reasoning:
            agent_cfg["reasoning_effort"] = reasoning

        # Map conversation style
        verbosity_map = {
            "concise": 0,
            "balanced": 1,
            "detailed": 2,
        }
        agent_cfg["verbosity"] = verbosity_map.get(self._conversation_style, 1)

        # Store full agent identity
        agent_cfg["identity"] = identity
        self.config.setdefault("onboarding", {})["agent_created"] = True

        # Persist
        save_config(self.config)

        return identity


# =============================================================================
# Entry Point
# =============================================================================


def run_agent_creator(config: dict | None = None) -> dict:
    """Launch the agent creator wizard.

    Returns the created agent identity dict.
    """
    if config is None:
        config = load_config()

    ensure_aetheros_home()
    creator = AgentCreator(config)
    return creator.run()
