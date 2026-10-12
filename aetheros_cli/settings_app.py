"""
AetherOS Settings Application — browse and edit all configuration sections.

Provides a tabbed/browsed interface for exploring and modifying every aspect
of AetherOS configuration. Reuses the existing SetupStep classes and wizard
loop from ``setup_wizard`` for editing individual sections.

Sections:
  - Profile (name, username, language, timezone, theme)
  - AI Providers
  - API Configuration
  - Default Models
  - Workspace
  - Tools
  - Automation
  - Integrations (connected services)
  - Memory
  - Privacy
  - Connected Services Hub
"""

from __future__ import annotations

import copy
import logging
import time
from pathlib import Path
from typing import Any

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_cli.config import (
    ensure_aetheros_home,
    get_config_path,
    get_env_value,
    load_config,
    save_config,
    save_env_value,
)
from aetheros_cli.setup_renderer import (
    C_ACCENT,
    C_BORDER,
    C_CARD_BG,
    C_CYAN,
    C_DIM,
    C_ERROR,
    C_NAV_BG,
    C_PURPLE,
    C_SECTION_BG,
    C_SUCCESS,
    C_TEXT,
    C_WARN,
    STEP_ICONS,
    clear,
    get_console,
    icon,
    make_card,
    make_keyboard_hints,
    make_nav_bar,
    make_section_card,
    make_step_progress,
)
from aetheros_cli.setup_wizard import (
    SetupCheckpoint,
    _get_key,
    _AI_PROVIDERS,
    _LOCAL_PROVIDERS,
    _CONNECTABLE_SERVICES,
    _TOOLS,
    _AUTOMATION_OPTIONS,
    _MEMORY_OPTIONS,
    _PRIVACY_OPTIONS,
    _WORKSPACE_PRESETS,
    _PROFILE_LANGUAGES,
    _THEMES,
    _PURPOSES,
    _EXPERIENCE_LEVELS,
    _API_CONFIG_PROVIDERS,
    _MODEL_CATEGORIES,
)
from aetheros_constants import get_aetheros_home, display_aetheros_home

logger = logging.getLogger(__name__)


# =============================================================================
# Settings Application
# =============================================================================

SETTINGS_SECTIONS = [
    ("profile", "Profile", "👤", "Name, language, timezone, theme"),
    ("providers", "AI Providers", "☁", "Add, remove, or configure AI providers"),
    ("api_keys", "API Keys", "🔑", "Manage API keys for cloud services"),
    ("models", "Default Models", "🤖", "Preferred models for each task"),
    ("workspace", "Workspace", "📁", "Project directories and workspace paths"),
    ("tools", "Tools", "🛠", "Enable/disable agent tools"),
    ("automation", "Automation", "⚡", "Background agents, cron, notifications"),
    ("integrations", "Integrations", "🔌", "Connected services and platforms"),
    ("memory", "Memory", "🧠", "Memory configuration"),
    ("privacy", "Privacy", "🔒", "Privacy, sync, and update preferences"),
    ("services_hub", "Services Hub", "🔗", "Manage all connected services"),
]


class SettingsApp:
    """Interactive settings browser and editor."""

    def __init__(self):
        self.config: dict = {}
        self._running = True
        self._cursor = 0

    def run(self) -> None:
        """Run the settings application."""
        ensure_aetheros_home()
        self.config = load_config()

        try:
            self._main_loop()
        except KeyboardInterrupt:
            pass

    def _main_loop(self) -> None:
        """Main settings browser loop."""
        while self._running:
            clear()
            self._render_browser()
            key = _get_key()
            self._handle_browser_input(key)

    def _render_browser(self) -> None:
        """Render the settings section browser."""
        heading = make_step_progress(1, 1, "Settings", "Configure your AetherOS system")
        get_console().print(heading)
        get_console().print()

        # Build section cards
        cards = []
        for i, (section_id, name, section_icon, desc) in enumerate(SETTINGS_SECTIONS):
            status, summary = self._get_section_status(section_id)
            sel = "▸ " if i == self._cursor else "  "
            card = Panel(
                Group(
                    Text(f"{sel}{section_icon}  {name}", style=f"bold {C_TEXT}" if i == self._cursor else C_DIM),
                    Text(f"       {desc}", style=C_DIM),
                    Text(f"       Status: ", style=C_DIM) + Text(status, style=f"bold {C_SUCCESS if 'Ready' in status else C_WARN}"),
                ),
                border_style=C_ACCENT if i == self._cursor else C_BORDER,
                padding=(0, 1),
                box=box.ROUNDED,
            )
            cards.append(card)

        # Display in columns (2 columns)
        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="left", width=50)
        grid.add_column(justify="left", width=50)

        for i in range(0, len(cards), 2):
            if i + 1 < len(cards):
                grid.add_row(cards[i], cards[i + 1])
            else:
                grid.add_row(cards[i], Text(""))

        get_console().print(
            Panel(
                grid,
                border_style="#484f58",
                padding=(1, 1),
                box=box.ROUNDED,
            )
        )
        get_console().print()

        hints = [
            ("↑↓", "Navigate"),
            ("Enter", "Open section"),
            ("Esc", "Exit settings"),
        ]
        get_console().print(make_keyboard_hints(hints))

    def _get_section_status(self, section_id: str) -> tuple[str, str]:
        """Get the status and summary for a settings section."""
        if section_id == "profile":
            onboarding = self.config.get("onboarding", {})
            if onboarding.get("profile_build"):
                return ("Ready", "Name configured")
            return ("Not set", "Not configured")
        elif section_id == "providers":
            providers = self.config.get("onboarding", {}).get("selected_providers", [])
            if providers:
                return ("Ready", f"{len(providers)} provider(s)")
            return ("Not set", "No providers configured")
        elif section_id == "api_keys":
            count = sum(1 for _, _, var, _ in _API_CONFIG_PROVIDERS if get_env_value(var))
            if count > 0:
                return ("Ready", f"{count} key(s) configured")
            return ("Not set", "No API keys configured")
        elif section_id == "workspace":
            cwd = self.config.get("terminal", {}).get("cwd")
            if cwd:
                return ("Ready", cwd)
            return ("Default", "Using default workspace")
        elif section_id == "tools":
            tools = self.config.get("onboarding", {}).get("tools", [])
            return ("Ready" if tools else "Default", f"{len(tools)} tool(s)")
        elif section_id == "automation":
            auto = self.config.get("onboarding", {}).get("automation", [])
            return ("Ready" if auto else "Default", f"{len(auto)} feature(s)")
        elif section_id == "integrations":
            services = self.config.get("onboarding", {}).get("connected_services", [])
            return ("Ready" if services else "Not set", f"{len(services)} service(s)")
        elif section_id == "privacy":
            priv = self.config.get("onboarding", {}).get("privacy", [])
            return ("Ready" if priv else "Default", f"{len(priv)} option(s)")
        elif section_id == "memory":
            mem = self.config.get("onboarding", {}).get("memory", [])
            return ("Ready" if mem else "Default", f"{len(mem)} type(s)")
        elif section_id == "models":
            return ("Ready", "Configured via providers")
        elif section_id == "services_hub":
            return ("Open", "Manage connections")
        return ("Unknown", "")

    def _handle_browser_input(self, key: str) -> None:
        """Handle keyboard input in browser mode."""
        if key == "cancel":
            self._running = False
        elif key == "up":
            self._cursor = max(0, self._cursor - 1)
        elif key == "down":
            self._cursor = min(len(SETTINGS_SECTIONS) - 1, self._cursor + 1)
        elif key in ("confirm", "right"):
            section_id = SETTINGS_SECTIONS[self._cursor][0]
            self._open_section(section_id)

    def _open_section(self, section_id: str) -> None:
        """Open a settings section for editing."""
        if section_id == "profile":
            self._edit_profile()
        elif section_id == "providers":
            self._edit_providers()
        elif section_id == "api_keys":
            self._edit_api_keys()
        elif section_id == "models":
            self._edit_models()
        elif section_id == "workspace":
            self._edit_workspace()
        elif section_id == "tools":
            self._edit_tools()
        elif section_id == "automation":
            self._edit_automation()
        elif section_id == "integrations":
            self._edit_integrations()
        elif section_id == "memory":
            self._edit_memory()
        elif section_id == "privacy":
            self._edit_privacy()
        elif section_id == "services_hub":
            self._open_services_hub()

    def _show_saved_banner(self) -> None:
        """Show a brief 'Saved' confirmation."""
        get_console().print(
            Panel(
                Align.center(Text("✓  Settings saved", style=f"bold {C_SUCCESS}")),
                border_style=C_SUCCESS,
                padding=(0, 2),
                box=box.ROUNDED,
            )
        )
        time.sleep(0.5)

    # ── Section Editors ──────────────────────────────────────────────

    def _edit_profile(self) -> None:
        """Edit profile settings."""
        onboarding = self.config.setdefault("onboarding", {})
        display_cfg = self.config.setdefault("display", {})

        fields = [
            ("Name", onboarding.get("profile_name", ""), "Enter your name"),
            ("Username", onboarding.get("profile_username", ""), "Enter a username"),
            ("Language", onboarding.get("profile_language", "en"), "Language code"),
            ("Timezone", onboarding.get("profile_timezone", "UTC"), "Timezone"),
            ("Theme", display_cfg.get("skin", "default"), "Theme name"),
        ]

        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Edit Profile", "Name, language, timezone, theme")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Label", width=16)
            table.add_column("Value", width=50)

            for i, (label, value, _) in enumerate(fields):
                style = f"bold {C_ACCENT}" if i == cursor else C_DIM
                val_style = f"bold {C_TEXT}" if i == cursor else C_DIM
                cursor_mark = " ▸" if i == cursor else ""
                table.add_row(
                    Text(f"  {label}{cursor_mark}", style=style),
                    Text(str(value) if value else "(not set)", style=val_style),
                )

            get_console().print(
                Panel(
                    table,
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Edit field"),
                    ("Esc", "Back to settings"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(fields) - 1, cursor + 1)
            elif key == "confirm":
                # Edit the selected field
                label, current, placeholder = fields[cursor]
                from prompt_toolkit import PromptSession
                from prompt_toolkit.styles import Style as PtStyle
                pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
                session = PromptSession(style=pt_style)
                try:
                    value = session.prompt(
                        f"  {C_ACCENT}▸{C_DIM}  {label}: ",
                        default=current,
                    )
                    if value:
                        field_keys = [
                            ("profile_name", "profile_name"),
                            ("profile_username", "profile_username"),
                            ("profile_language", "profile_language"),
                            ("profile_timezone", "profile_timezone"),
                            ("skin", "skin"),
                        ]
                        key_name, config_key = field_keys[cursor]
                        if config_key == "skin":
                            display_cfg["skin"] = value
                        else:
                            onboarding[config_key] = value
                        fields[cursor] = (label, value, placeholder)
                        save_config(self.config)
                except (EOFError, KeyboardInterrupt):
                    pass

    def _edit_providers(self) -> None:
        """Edit AI providers selection."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("selected_providers", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Edit AI Providers", "Select your AI providers")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Provider", width=24)
            table.add_column("Tag", width=14)

            for i, (key, name, tag) in enumerate(_AI_PROVIDERS):
                checked = "◉" if key in selected else "○"
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(f"[{tag}]", style=f"dim {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_ACCENT,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["selected_providers"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_AI_PROVIDERS) - 1, cursor + 1)
            elif key == " ":
                key_name = _AI_PROVIDERS[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["selected_providers"] = list(selected)
                save_config(self.config)
                editing = False

    def _edit_api_keys(self) -> None:
        """Edit API keys."""
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Edit API Keys", "Configure API keys for providers")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Provider", width=16)
            table.add_column("Status", width=40)

            for i, (key, name, env_var, placeholder) in enumerate(_API_CONFIG_PROVIDERS):
                existing = get_env_value(env_var) or ""
                status = f"{'*' * 20}{existing[-4:]}" if len(existing) > 8 else "(not configured)"
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                cursor_mark = " ▸" if i == cursor else ""
                table.add_row(
                    Text(f"  {name}{cursor_mark}", style=style),
                    Text(status, style=C_CYAN if existing else C_DIM),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_WARN,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Edit key"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_API_CONFIG_PROVIDERS) - 1, cursor + 1)
            elif key == "confirm":
                key_name, name, env_var, placeholder = _API_CONFIG_PROVIDERS[cursor]
                existing = get_env_value(env_var) or ""
                from prompt_toolkit import PromptSession
                from prompt_toolkit.styles import Style as PtStyle
                pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
                session = PromptSession(style=pt_style)
                try:
                    value = session.prompt(
                        f"  {C_ACCENT}▸{C_DIM}  {name} API Key ({placeholder}): ",
                        default=existing,
                        is_password=True,
                    )
                    if value:
                        save_env_value(env_var, value)
                except (EOFError, KeyboardInterrupt):
                    pass

    def _edit_models(self) -> None:
        """Show model configuration info."""
        clear()
        progress = make_step_progress(1, 1, "Default Models", "Model preferences per task")
        get_console().print(progress)
        get_console().print()

        table = Table.grid(padding=(0, 2))
        table.add_column("Role", width=18)
        table.add_column("Suggested Models", width=50)
        for role, label, examples in _MODEL_CATEGORIES:
            table.add_row(
                Text(f"  {label}", style=f"bold {C_TEXT}"),
                Text(examples, style=C_DIM),
            )

        get_console().print(
            Panel(
                Group(
                    table,
                    Text(""),
                    Text("  Use 'aetheros model' to set your default model.", style=f"dim {C_DIM}"),
                ),
                border_style=C_PURPLE,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        get_console().print()
        get_console().print(make_keyboard_hints([("Any key", "Back")]))
        _get_key()

    def _edit_workspace(self) -> None:
        """Edit workspace settings."""
        onboarding = self.config.setdefault("onboarding", {})
        terminal = self.config.setdefault("terminal", {})
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Workspace", "Choose your workspace directory")
            get_console().print(progress)
            get_console().print()

            presets = [
                ("projects", "Projects Folder", str(Path.home() / "aetheros-projects")),
                ("downloads", "Downloads", str(Path.home() / "Downloads")),
                ("documents", "Documents", str(Path.home() / "Documents")),
                ("custom", "Custom Folder", terminal.get("cwd", str(Path.home()))),
            ]

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Folder", width=20)
            table.add_column("Path", width=40)

            for i, (key, name, path) in enumerate(presets):
                sel = "◉" if i == cursor else "○"
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"  {sel}", style=style),
                    Text(name, style=style),
                    Text(path, style=f"dim {C_DIM}"),
                )

            get_console().print(
                Panel(
                    table,
                    border_style=C_ACCENT,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Enter", "Select"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(presets) - 1, cursor + 1)
            elif key == "confirm":
                key_name, _, path = presets[cursor]
                onboarding["workspace"] = key_name
                onboarding["workspace_path"] = path
                if key_name == "projects":
                    terminal["cwd"] = str(Path.home() / "aetheros-projects")
                elif key_name == "custom":
                    terminal["cwd"] = path
                else:
                    terminal["cwd"] = str(Path.home() / key_name.capitalize())
                save_config(self.config)
                editing = False

    def _edit_tools(self) -> None:
        """Edit tools selection."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("tools", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Tools", "Enable the tools you need")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Tool", width=18)
            table.add_column("Description", width=40)

            for i, (key, name, desc) in enumerate(_TOOLS):
                checked = "◉" if key in selected else "○"
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_ACCENT,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["tools"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_TOOLS) - 1, cursor + 1)
            elif key == " ":
                key_name = _TOOLS[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["tools"] = list(selected)
                save_config(self.config)
                editing = False

    def _edit_automation(self) -> None:
        """Edit automation settings."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("automation", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Automation", "Configure automation capabilities")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Feature", width=24)
            table.add_column("Description", width=40)

            for i, (key, name, desc) in enumerate(_AUTOMATION_OPTIONS):
                checked = "◉" if key in selected else "○"
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_CYAN,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["automation"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_AUTOMATION_OPTIONS) - 1, cursor + 1)
            elif key == " ":
                key_name = _AUTOMATION_OPTIONS[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["automation"] = list(selected)
                save_config(self.config)
                editing = False

    def _edit_integrations(self) -> None:
        """Edit connected services."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("connected_services", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Integrations", "Connect your accounts and services")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Service", width=24)
            table.add_column("Category", width=14)
            table.add_column("Status", width=16)

            for i, (key, name, cat, serv_icon) in enumerate(_CONNECTABLE_SERVICES):
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                status = "✓ Connected" if key in selected else "○ Connect"
                table.add_row(
                    Text(f"{sel} {serv_icon}", style=style),
                    Text(name, style=style),
                    Text(cat, style=f"dim {C_DIM}"),
                    Text(status, style=f"bold {C_SUCCESS}" if key in selected else C_DIM),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_ACCENT,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["connected_services"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_CONNECTABLE_SERVICES) - 1, cursor + 1)
            elif key == " ":
                key_name = _CONNECTABLE_SERVICES[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["connected_services"] = list(selected)
                save_config(self.config)
                editing = False

    def _edit_memory(self) -> None:
        """Edit memory settings."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("memory", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Memory", "Configure how AetherOS remembers")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Memory Type", width=24)
            table.add_column("Description", width=40)

            for i, (key, name, desc) in enumerate(_MEMORY_OPTIONS):
                checked = "◉" if key in selected else "○"
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_PURPLE,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["memory"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_MEMORY_OPTIONS) - 1, cursor + 1)
            elif key == " ":
                key_name = _MEMORY_OPTIONS[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["memory"] = list(selected)
                save_config(self.config)
                editing = False

    def _edit_privacy(self) -> None:
        """Edit privacy settings."""
        onboarding = self.config.setdefault("onboarding", {})
        selected = set(onboarding.get("privacy", []))
        cursor = 0
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, "Privacy", "Configure privacy and data preferences")
            get_console().print(progress)
            get_console().print()

            table = Table.grid(padding=(0, 2))
            table.add_column("Sel", width=4)
            table.add_column("Option", width=24)
            table.add_column("Description", width=40)

            for i, (key, name, desc) in enumerate(_PRIVACY_OPTIONS):
                checked = "◉" if key in selected else "○"
                sel = "▸" if i == cursor else " "
                style = f"bold {C_TEXT}" if i == cursor else C_DIM
                table.add_row(
                    Text(f"{sel} {checked}", style=style),
                    Text(name, style=style),
                    Text(desc, style=f"italic {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(table, Text("")),
                    border_style=C_WARN,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()
            get_console().print(
                make_keyboard_hints([
                    ("↑↓", "Navigate"),
                    ("Space", "Toggle"),
                    ("Enter", "Save & back"),
                    ("Esc", "Back"),
                ])
            )

            key = _get_key()
            if key == "cancel":
                onboarding["privacy"] = list(selected)
                save_config(self.config)
                editing = False
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(_PRIVACY_OPTIONS) - 1, cursor + 1)
            elif key == " ":
                key_name = _PRIVACY_OPTIONS[cursor][0]
                if key_name in selected:
                    selected.discard(key_name)
                else:
                    selected.add(key_name)
            elif key == "confirm":
                onboarding["privacy"] = list(selected)
                save_config(self.config)
                editing = False

    def _open_services_hub(self) -> None:
        """Open the services hub for managing connected services."""
        from aetheros_cli.services_hub import ServicesHub
        hub = ServicesHub(self.config)
        hub.run()


# =============================================================================
# Entry Point
# =============================================================================

def run_settings_app() -> None:
    """Launch the settings application."""
    app = SettingsApp()
    app.run()
