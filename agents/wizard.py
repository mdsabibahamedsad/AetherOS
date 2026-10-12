"""11-step interactive agent creation wizard — Rich-powered CLI experience."""

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

from aetheros_cli.setup_renderer import (
    C_ACCENT, C_BORDER, C_CARD_BG, C_CYAN, C_DIM, C_ERROR,
    C_PURPLE, C_SUCCESS, C_TEXT, C_WARN,
    clear, get_console, make_keyboard_hints, make_step_progress,
)
from agents.models import (
    AGENT_ROLE_LABELS, AgentAvatar, AgentConfig, AgentRole,
    AVAILABLE_PERMISSIONS, AVAILABLE_TOOLS,
    MEMORY_LABELS, MemoryScope, PERSONALITY_LABELS, Personality,
    REASONING_LABELS, ReasoningLevel,
)
from agents.manager import AgentManager
from agents import store

logger = logging.getLogger(__name__)

# =============================================================================
# Wizard color constants (not imported from setup_renderer for independence)
# =============================================================================

C_GOLD = "#ffd700"
C_ORANGE = "#ff9f43"
C_TEAL = "#00d2d3"
C_PINK = "#fd79a8"
C_INDIGO = "#6c5ce7"
C_GREEN = "#00b894"
C_RED = "#ff6b6b"


# =============================================================================
# Avatar presets
# =============================================================================

AVATAR_PRESETS = [
    ("🤖", "Robot", C_ACCENT),
    ("🧠", "Brain", C_PURPLE),
    ("⚡", "Lightning", C_GOLD),
    ("🦊", "Fox", C_GOLD),
    ("🐉", "Dragon", C_CYAN),
    ("🦅", "Eagle", C_ACCENT),
    ("🦋", "Butterfly", C_PURPLE),
    ("🌟", "Star", C_GOLD),
    ("🎯", "Target", C_SUCCESS),
    ("🔮", "Crystal", C_PURPLE),
    ("⚙", "Gear", C_DIM),
    ("🛡", "Shield", C_ACCENT),
    ("🎭", "Theater", C_PURPLE),
    ("🌊", "Wave", C_CYAN),
    ("🔥", "Fire", C_GOLD),
    ("💎", "Diamond", C_CYAN),
]

AVATAR_COLORS = [
    "#58a6ff", "#bc8cff", "#3fb950", "#d29922", "#f85149",
    "#39d2c0", "#ff6b6b", "#56d4b0", "#ffd700", "#ff9f43",
    "#00d2d3", "#a29bfe", "#fd79a8", "#6c5ce7", "#00b894",
]


def _resolve_color(color: str) -> str:
    mapper = {
        "C_ACCENT": C_ACCENT, "C_PURPLE": C_PURPLE, "C_CYAN": C_CYAN,
        "C_SUCCESS": C_SUCCESS, "C_GOLD": C_GOLD, "C_DIM": C_DIM,
        "C_ERROR": C_ERROR, "C_WARN": C_WARN,
        "#58a6ff": "#58a6ff", "#bc8cff": "#bc8cff", "#3fb950": "#3fb950",
        "#d29922": "#d29922", "#f85149": "#f85149", "#39d2c0": "#39d2c0",
        "#ff6b6b": "#ff6b6b", "#56d4b0": "#56d4b0", "#ffd700": "#ffd700",
        "#ff9f43": "#ff9f43", "#00d2d3": "#00d2d3", "#a29bfe": "#a29bfe",
        "#fd79a8": "#fd79a8", "#6c5ce7": "#6c5ce7", "#00b894": "#00b894",
    }
    return mapper.get(color, color)


# =============================================================================
# Wizard Engine
# =============================================================================


class AgentWizard:
    """11-step interactive agent creation wizard."""

    def __init__(self):
        self.mgr = AgentManager()
        self._config = AgentConfig()
        self._cursor = 0
        self._multi_cursor: set[int] = set()
        self._running = True
        self._step_index = 0
        self._selected_avatar = 0
        self._selected_color = 0
        self._custom_value = ""

        # For multi-select tools/permissions
        self._selected_tools: set[int] = set()
        self._selected_permissions: set[int] = set()
        self._selected_knowledge: set[int] = set()
        self._selected_skills: set[int] = set()

    def run(self) -> AgentConfig | None:
        store.init_db()
        self._show_intro()

        steps = [
            self._step_name_avatar,
            self._step_role,
            self._step_personality,
            self._step_reasoning,
            self._step_providers,
            self._step_models,
            self._step_memory,
            self._step_knowledge,
            self._step_tools,
            self._step_permissions,
            self._step_review,
        ]

        for i, step_fn in enumerate(steps):
            self._step_index = i
            self._cursor = 0
            if not self._running:
                break
            step_fn()
            if not self._running:
                break

        if self._running:
            return self._finalize()
        return None

    def _show_intro(self) -> None:
        clear()
        console = get_console()
        console.print(
            Panel(
                Align.center(
                    Group(
                        Text("◆  Create an AI Agent  ◆", style=f"bold {C_PURPLE}"),
                        Text(""),
                        Text("Design your agent's identity, abilities, and permissions.", style=C_TEXT),
                        Text("11 quick steps — everything editable later.", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_PURPLE,
                padding=(2, 4),
                box=rich_box.ROUNDED,
            )
        )
        console.print()
        console.print(make_keyboard_hints([("Enter", "Start"), ("Esc", "Cancel")]))
        from aetheros_cli.setup_wizard import _get_key
        key = _get_key()
        if key == "cancel":
            self._running = False

    def _progress(self) -> None:
        get_console().print(make_step_progress(self._step_index + 1, 11, "Create Agent", f"Step {self._step_index + 1} of 11"))
        get_console().print()

    # ── Step 1: Name + Avatar ───────────────────────────────────────

    def _step_name_avatar(self) -> None:
        self._progress()
        console = get_console()

        prompt_shown = False
        while self._running and not prompt_shown:
            clear()
            self._progress()
            console.print(
                Panel(
                    Align.center(
                        Text("What should your agent be called?", style=f"bold {C_TEXT}"),
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            console.print()
            from aetheros_cli.setup_wizard import _get_key
            console.print(make_keyboard_hints([("Enter", "Accept name"), ("Esc", "Cancel")]))

            from prompt_toolkit import PromptSession
            from prompt_toolkit.styles import Style as PtStyle
            pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
            session = PromptSession(style=pt_style)
            try:
                value = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Name: ", default=self._config.name)
                if value.strip():
                    self._config.name = value.strip()
                    prompt_shown = True
            except (EOFError, KeyboardInterrupt):
                self._running = False
                return

        # Avatar icon selection
        while self._running:
            clear()
            self._progress()

            icon_grid = Table.grid(padding=(0, 2))
            icon_grid.add_column("Sel", width=4)
            icon_grid.add_column("Icon", width=6)
            icon_grid.add_column("Name", width=16)

            icons_per_row = 4
            for i, (emoji, label, _) in enumerate(AVATAR_PRESETS):
                sel = "◉" if i == self._selected_avatar else "○"
                pointer = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                icon_grid.add_row(
                    Text(f"{pointer} {sel}", style=style),
                    Text(emoji),
                    Text(label, style=style),
                )

            color_row = Table.grid(padding=(0, 2))
            color_row.add_column("Sel", width=4)
            color_row.add_column("Color", width=8)
            color_row.add_column("Preview", width=20)
            for i, color in enumerate(AVATAR_COLORS):
                sel = "◉" if i == self._selected_color else "○"
                pointer = "▸" if i + len(AVATAR_PRESETS) == self._cursor else " "
                if i + len(AVATAR_PRESETS) != self._cursor:
                    pointer = " "
                block = f"■■■■■"

            console.print(
                Panel(
                    Group(
                        Text(f"  Agent: {self._config.name}", style=f"bold {C_TEXT}"),
                        Text(""),
                        Text("  Choose an avatar icon:", style=C_DIM),
                        Text(""),
                        icon_grid,
                        Text(""),
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            console.print()
            console.print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(AVATAR_PRESETS) - 1, self._cursor + 1)
            elif key == "confirm":
                self._selected_avatar = self._cursor
                self._config.avatar = AgentAvatar(
                    icon=AVATAR_PRESETS[self._cursor][0],
                    color=AVATAR_COLORS[self._selected_color],
                )
                return

    # ── Step 2: Role ────────────────────────────────────────────────

    def _step_role(self) -> None:
        roles = list(AGENT_ROLE_LABELS.items())
        while self._running:
            clear()
            self._progress()

            cards = []
            for i, (role, label) in enumerate(roles):
                sel = role.value == self._config.role
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {label}", style=style))
                cards.append(Panel(card, border_style=border, padding=(0, 1), box=rich_box.ROUNDED))

            get_console().print(
                Panel(
                    Group(Text("  Choose your agent's role:", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                vals = [r.value for r, _ in roles]
                idx = max(0, vals.index(self._config.role) - 1)
                self._config.role = roles[idx][0].value
            elif key == "down":
                vals = [r.value for r, _ in roles]
                idx = min(len(vals) - 1, vals.index(self._config.role) + 1)
                self._config.role = roles[idx][0].value
            elif key == "confirm":
                if self._config.role == "custom":
                    self._prompt_custom_role()
                return

    def _prompt_custom_role(self) -> None:
        from aetheros_cli.setup_wizard import _get_key
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)
        get_console().print()
        try:
            value = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Custom role: ")
            self._config.role_custom = value.strip()
        except (EOFError, KeyboardInterrupt):
            pass

    # ── Step 3: Personality ─────────────────────────────────────────

    def _step_personality(self) -> None:
        personalities = list(PERSONALITY_LABELS.items())
        while self._running:
            clear()
            self._progress()

            cards = []
            for i, (p, label) in enumerate(personalities):
                sel = p.value == self._config.personality
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {label}", style=style))
                cards.append(Panel(card, border_style=border, padding=(0, 1), box=rich_box.ROUNDED))

            get_console().print(
                Panel(
                    Group(Text("  Choose your agent's personality:", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                vals = [p.value for p, _ in personalities]
                idx = max(0, vals.index(self._config.personality) - 1)
                self._config.personality = personalities[idx][0].value
            elif key == "down":
                vals = [p.value for p, _ in personalities]
                idx = min(len(vals) - 1, vals.index(self._config.personality) + 1)
                self._config.personality = personalities[idx][0].value
            elif key == "confirm":
                if self._config.personality == "custom":
                    self._prompt_custom_personality()
                return

    def _prompt_custom_personality(self) -> None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)
        get_console().print()
        try:
            value = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Personality description: ")
            self._config.personality_custom = value.strip()
        except (EOFError, KeyboardInterrupt):
            pass

    # ── Step 4: Reasoning ───────────────────────────────────────────

    def _step_reasoning(self) -> None:
        levels = list(REASONING_LABELS.items())
        while self._running:
            clear()
            self._progress()

            cards = []
            for i, (r, label) in enumerate(levels):
                sel = r.value == self._config.reasoning
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {label}", style=style))
                cards.append(Panel(card, border_style=border, padding=(0, 1), box=rich_box.ROUNDED))

            get_console().print(
                Panel(
                    Group(Text("  Reasoning Level:", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                vals = [r.value for r, _ in levels]
                idx = max(0, vals.index(self._config.reasoning) - 1)
                self._config.reasoning = levels[idx][0].value
            elif key == "down":
                vals = [r.value for r, _ in levels]
                idx = min(len(vals) - 1, vals.index(self._config.reasoning) + 1)
                self._config.reasoning = levels[idx][0].value
            elif key == "confirm":
                return

    # ── Step 5: Providers ───────────────────────────────────────────

    def _step_providers(self) -> None:
        from aetheros_cli.config import load_config
        hermes_config = load_config()
        available_providers = self._detect_providers(hermes_config)

        while self._running:
            clear()
            self._progress()

            provider_table = Table.grid(padding=(0, 2))
            provider_table.add_column("Sel", width=4)
            provider_table.add_column("Provider", width=20)
            provider_table.add_column("Model", width=30)

            for i, (prov, model) in enumerate(available_providers):
                sel = "◉" if prov == self._config.provider else "○"
                pointer = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                provider_table.add_row(
                    Text(f"{pointer} {sel}", style=style),
                    Text(prov, style=style),
                    Text(model, style=f"dim {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Choose AI Provider:", style=f"bold {C_TEXT}"),
                        Text("  Select primary and fallback providers", style=f"dim {C_DIM}"),
                        Text(""),
                        provider_table,
                    ),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("F", "Add fallback"), ("Esc", "Skip")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(available_providers) - 1, self._cursor + 1)
            elif key == "confirm":
                if self._cursor < len(available_providers):
                    self._config.provider = available_providers[self._cursor][0]
                    self._config.models["reasoning"] = available_providers[self._cursor][1]
                    return
            elif key == "f" or key == "F":
                if self._cursor < len(available_providers):
                    from agents.models import ProviderConfig
                    prov = available_providers[self._cursor]
                    self._config.fallback_providers.append(
                        ProviderConfig(provider=prov[0], model=prov[1])
                    )
                    get_console().print(f"  [{C_SUCCESS}]✓[/]  Added {prov[0]} as fallback")
                    time.sleep(0.5)

    def _detect_providers(self, hermes_config: dict) -> list[tuple[str, str]]:
        providers = []
        # Primary model
        model = hermes_config.get("model", {}).get("name", "")
        provider = hermes_config.get("model", {}).get("provider", "")
        if model:
            providers.append((provider or "default", model))
        # Check for other configured providers
        from aetheros_cli.config import OPTIONAL_ENV_VARS
        for var_name, meta in OPTIONAL_ENV_VARS.items():
            if meta.get("category") == "provider":
                prov_name = var_name.replace("_API_KEY", "").replace("_API_BASE", "").lower()
                key_val = hermes_config.get("env", {}).get(var_name, "")
                if key_val:
                    pname = var_name.replace("_API_KEY", "").replace("_KEY", "").title()
                    providers.append((pname, f"{pname} model"))
        if not providers:
            providers.append(("default", "Configured in settings"))
        return providers

    # ── Step 6: Models ──────────────────────────────────────────────

    def _step_models(self) -> None:
        model_types = [
            ("coding", "Coding", "Code generation & editing"),
            ("reasoning", "Reasoning", "Complex problem-solving"),
            ("vision", "Vision", "Image analysis"),
            ("fast", "Fast", "Quick responses"),
            ("offline", "Offline", "Local models"),
        ]

        while self._running:
            clear()
            self._progress()

            model_table = Table.grid(padding=(0, 2))
            model_table.add_column("Type", width=14)
            model_table.add_column("Description", width=28)
            model_table.add_column("Model", width=30)

            for key, label, desc in model_types:
                current = self._config.models.get(key, "auto")
                model_table.add_row(
                    Text(f"  {label}", style=f"bold {C_TEXT}"),
                    Text(desc, style=C_DIM),
                    Text(current, style=C_CYAN),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Model Configuration:", style=f"bold {C_TEXT}"),
                        Text("  Assign models to different capabilities", style=f"dim {C_DIM}"),
                        Text(""),
                        model_table,
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                Panel(
                    Align.center(
                        Text("Type a model override (e.g. 'gpt-4o') or press Enter to use defaults", style=C_DIM),
                    ),
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("Enter", "Use defaults & continue"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "confirm":
                return

    # ── Step 7: Memory ──────────────────────────────────────────────

    def _step_memory(self) -> None:
        scopes = list(MEMORY_LABELS.items())
        while self._running:
            clear()
            self._progress()

            cards = []
            for i, (m, label) in enumerate(scopes):
                sel = m.value == self._config.memory_scope
                border = C_ACCENT if sel else C_BORDER
                style = f"bold {C_TEXT}" if sel else C_DIM
                indicator = "◉" if sel else "○"
                card = Table.grid(padding=(0, 1))
                card.add_row(Text(f"  {indicator}  {label}", style=style))
                cards.append(Panel(card, border_style=border, padding=(0, 1), box=rich_box.ROUNDED))

            get_console().print(
                Panel(
                    Group(Text("  Memory Scope:", style=f"bold {C_TEXT}"), Text(""), Columns(cards, equal=False, expand=False)),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Enter", "Select"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                vals = [m.value for m, _ in scopes]
                idx = max(0, vals.index(self._config.memory_scope) - 1)
                self._config.memory_scope = scopes[idx][0].value
            elif key == "down":
                vals = [m.value for m, _ in scopes]
                idx = min(len(vals) - 1, vals.index(self._config.memory_scope) + 1)
                self._config.memory_scope = scopes[idx][0].value
            elif key == "confirm":
                return

    # ── Step 8: Knowledge ───────────────────────────────────────────

    def _step_knowledge(self) -> None:
        knowledge_types = [
            ("folder", "📁  Folder", "Attach a directory of documents"),
            ("markdown", "📝  Markdown", "One or more .md files"),
            ("pdf", "📄  PDF", "PDF documents"),
            ("git", "🔗  Git Repository", "Clone and index a repo"),
            ("website", "🌐  Website", "Crawl and index a website"),
            ("database", "🗄  Database", "Connect to a database"),
        ]

        while self._running:
            clear()
            self._progress()

            ktable = Table.grid(padding=(0, 2))
            ktable.add_column("Sel", width=4)
            ktable.add_column("Type", width=20)
            ktable.add_column("Description", width=40)

            for i, (key, label, desc) in enumerate(knowledge_types):
                checked = "◉" if i in self._selected_knowledge else "○"
                pointer = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                ktable.add_row(
                    Text(f"{pointer} {checked}", style=style),
                    Text(label, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Knowledge Sources:", style=f"bold {C_TEXT}"),
                        Text("  Select sources your agent can reference", style=f"dim {C_DIM}"),
                        Text(""),
                        ktable,
                    ),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Space", "Toggle"), ("Enter", "Continue"), ("Esc", "Skip")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(knowledge_types) - 1, self._cursor + 1)
            elif key == " ":
                if self._cursor in self._selected_knowledge:
                    self._selected_knowledge.discard(self._cursor)
                else:
                    self._selected_knowledge.add(self._cursor)
            elif key == "confirm":
                return

    # ── Step 9: Tools ───────────────────────────────────────────────

    def _step_tools(self) -> None:
        tool_list = list(enumerate(AVAILABLE_TOOLS))
        if not self._selected_tools:
            self._selected_tools = {0, 2, 7}  # Preselect filesystem, python, web_search

        while self._running:
            clear()
            self._progress()

            tool_table = Table.grid(padding=(0, 2))
            tool_table.add_column("Sel", width=4)
            tool_table.add_column("Tool", width=18)
            tool_table.add_column("Capability", width=40)

            tool_descriptions = {
                "filesystem": "Read, write, and manage files",
                "browser": "Navigate and interact with web pages",
                "python": "Execute Python code",
                "docker": "Container management",
                "git": "Version control operations",
                "github": "GitHub API integration",
                "terminal": "Shell command execution",
                "web_search": "Search the internet",
                "ocr": "Extract text from images",
                "vision": "Analyze images and video",
                "voice": "Speech recognition and synthesis",
                "email": "Send and receive emails",
                "calendar": "Manage calendar events",
                "mcp": "Model Context Protocol servers",
                "computer_use": "Control the desktop GUI",
            }

            for i, tool in enumerate(AVAILABLE_TOOLS):
                checked = "◉" if i in self._selected_tools else "○"
                pointer = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                desc = tool_descriptions.get(tool, "")
                tool_table.add_row(
                    Text(f"{pointer} {checked}", style=style),
                    Text(tool.replace("_", " ").title(), style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Enable Tools:", style=f"bold {C_TEXT}"),
                        Text("  Select which tools your agent can use", style=f"dim {C_DIM}"),
                        Text(""),
                        tool_table,
                    ),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Space", "Toggle"), ("Enter", "Continue"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(AVAILABLE_TOOLS) - 1, self._cursor + 1)
            elif key == " ":
                if self._cursor in self._selected_tools:
                    self._selected_tools.discard(self._cursor)
                else:
                    self._selected_tools.add(self._cursor)
            elif key == "confirm":
                self._config.tools = [AVAILABLE_TOOLS[i] for i in sorted(self._selected_tools)]
                return

    # ── Step 10: Permissions ────────────────────────────────────────

    def _step_permissions(self) -> None:
        perm_list = list(enumerate(AVAILABLE_PERMISSIONS))
        if not self._selected_permissions:
            self._selected_permissions = {0, 3}  # Preselect read_files, internet_access

        perm_descriptions = {
            "read_files": "Read any file on the system",
            "write_files": "Create and modify files",
            "execute_terminal": "Run shell commands",
            "internet_access": "Access websites and APIs",
            "install_packages": "Install software packages",
            "git_push": "Push to git repositories",
            "docker": "Manage Docker containers",
            "system_commands": "Execute system-level commands",
            "ask_before_dangerous": "Prompt before risky actions",
        }

        while self._running:
            clear()
            self._progress()

            perm_table = Table.grid(padding=(0, 2))
            perm_table.add_column("Sel", width=4)
            perm_table.add_column("Permission", width=22)
            perm_table.add_column("Description", width=36)

            for i, perm in enumerate(AVAILABLE_PERMISSIONS):
                checked = "◉" if i in self._selected_permissions else "○"
                pointer = "▸" if i == self._cursor else " "
                style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
                desc = perm_descriptions.get(perm, "")
                perm_table.add_row(
                    Text(f"{pointer} {checked}", style=style),
                    Text(perm.replace("_", " ").title(), style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(
                        Text("  Permissions:", style=f"bold {C_TEXT}"),
                        Text("  Grant capabilities to your agent", style=f"dim {C_DIM}"),
                        Text(""),
                        perm_table,
                    ),
                    border_style=C_GOLD,
                    padding=(1, 2),
                    box=rich_box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(make_keyboard_hints([("↑↓", "Navigate"), ("Space", "Toggle"), ("Enter", "Continue"), ("Esc", "Cancel")]))

            from aetheros_cli.setup_wizard import _get_key
            key = _get_key()
            if key == "cancel":
                return
            elif key == "up":
                self._cursor = max(0, self._cursor - 1)
            elif key == "down":
                self._cursor = min(len(AVAILABLE_PERMISSIONS) - 1, self._cursor + 1)
            elif key == " ":
                if self._cursor in self._selected_permissions:
                    self._selected_permissions.discard(self._cursor)
                else:
                    self._selected_permissions.add(self._cursor)
            elif key == "confirm":
                self._config.permissions = [AVAILABLE_PERMISSIONS[i] for i in sorted(self._selected_permissions)]
                return

    # ── Step 11: Review ─────────────────────────────────────────────

    def _step_review(self) -> None:
        clear()
        self._progress()

        console = get_console()
        avatar = self._config.avatar

        review = Table.grid(padding=(0, 2))
        review.add_column("Field", width=18, style=f"bold {C_DIM}")
        review.add_column("Value", width=50)

        role_label = AGENT_ROLE_LABELS.get(
            next((r for r in AgentRole if r.value == self._config.role), None),
            self._config.role_custom or self._config.role,
        )
        personality_label = PERSONALITY_LABELS.get(
            next((p for p in Personality if p.value == self._config.personality), None),
            self._config.personality_custom or self._config.personality,
        )
        reasoning_label = REASONING_LABELS.get(
            next((r for r in ReasoningLevel if r.value == self._config.reasoning), None),
            self._config.reasoning,
        )
        memory_label = MEMORY_LABELS.get(
            next((m for m in MemoryScope if m.value == self._config.memory_scope), None),
            self._config.memory_scope,
        )

        review.add_row(
            f"{avatar.icon}  Agent",
            f"[bold {avatar.color}]{self._config.name}[/]",
        )
        review.add_row("")
        review.add_row("Role", role_label)
        review.add_row("Personality", personality_label)
        review.add_row("Reasoning", reasoning_label)
        review.add_row("Memory", memory_label)
        review.add_row("")
        review.add_row("Provider", self._config.provider or "Default")
        review.add_row("Model", self._config.models.get("reasoning", "auto"))
        review.add_row("Temperature", str(self._config.temperature))
        review.add_row("")
        review.add_row("Tools", ", ".join(self._config.tools))
        review.add_row("Permissions", ", ".join(p.replace("_", " ").title() for p in self._config.permissions))
        if self._config.fallback_providers:
            review.add_row("Fallbacks", ", ".join(p.provider for p in self._config.fallback_providers))
        if self._config.description:
            review.add_row("Description", self._config.description[:60])

        console.print(
            Panel(
                Group(
                    Text("  Review Your Agent", style=f"bold {C_PURPLE}"),
                    Text(""),
                    review,
                ),
                border_style=C_PURPLE,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )
        console.print()
        console.print(make_keyboard_hints([("Enter", "Create Agent"), ("Esc", "Cancel")]))

        from aetheros_cli.setup_wizard import _get_key
        key = _get_key()
        if key == "cancel":
            self._running = False

    # ── Finalize ────────────────────────────────────────────────────

    def _finalize(self) -> AgentConfig:
        console = get_console()

        # Prompt for description
        from aetheros_cli.setup_wizard import _get_key
        console.print()
        console.print(
            Panel(
                Align.center(Text("Add a short description (optional):", style=C_DIM)),
                border_style=C_BORDER,
                padding=(1, 2),
                box=rich_box.ROUNDED,
            )
        )
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)
        try:
            desc = session.prompt(f"  {C_ACCENT}▸{C_DIM}  Description: ")
            if desc.strip():
                self._config.description = desc.strip()
        except (EOFError, KeyboardInterrupt):
            pass

        result = self.mgr.create(self._config)
        console.print()
        console.print(
            Panel(
                Align.center(
                    Group(
                        Text("◆  Agent Created  ◆", style=f"bold {C_SUCCESS}"),
                        Text(""),
                        Text(f"{result.avatar.icon}  {result.name}", style=f"bold {result.avatar.color}"),
                        Text(result.role.replace("_", " ").title(), style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_SUCCESS,
                padding=(2, 4),
                box=rich_box.ROUNDED,
            )
        )
        console.print()
        time.sleep(0.5)
        return result


def run_agent_wizard() -> AgentConfig | None:
    """Run the 11-step agent creation wizard."""
    from agents import store
    store.init_db()
    wizard = AgentWizard()
    return wizard.run()
