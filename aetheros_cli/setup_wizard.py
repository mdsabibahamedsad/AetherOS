"""
AetherOS Premium Setup Wizard — operating-system-grade installer.

16-step wizard with full keyboard navigation, autosave, resume,
edit-anywhere review, Tab/Shift+Tab field navigation, and premium
OS-installer-grade Rich rendering using the shared setup renderer.

Reuses existing setup section functions from ``aetheros_cli.setup``
for provider configuration, terminal backend, TTS, gateway, tools,
and agent settings.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt as RichPrompt

from aetheros_cli.colors import Colors, color
from aetheros_cli.config import (
    DEFAULT_CONFIG,
    OPTIONAL_ENV_VARS,
    ensure_aetheros_home,
    get_config_path,
    get_env_path,
    get_env_value,
    load_config,
    save_config,
    save_env_value,
    remove_env_value,
)
from aetheros_cli.setup_renderer import (
    C_ACCENT,
    C_BORDER,
    C_BORDER_LIGHT,
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
    confirm_dialog,
    get_console,
    icon,
    make_card,
    make_keyboard_hints,
    make_nav_bar,
    make_step_progress,
    make_success_screen,
    make_error_screen,
)
from aetheros_constants import get_aetheros_home, display_aetheros_home

logger = logging.getLogger(__name__)


_CHECKPOINT_FILE = "setup_checkpoint.json"


# =============================================================================
# Terminal helpers
# =============================================================================


def _dim(text: str) -> str:
    return f"[dim]{text}[/dim]"


def _bold(text: str) -> str:
    return f"[bold]{text}[/bold]"


def _accent(text: str) -> str:
    return f"[{C_ACCENT}]{text}[/{C_ACCENT}]"


def _green(text: str) -> str:
    return f"[{C_SUCCESS}]{text}[/{C_SUCCESS}]"


def _yellow(text: str) -> str:
    return f"[{C_WARN}]{text}[/{C_WARN}]"


def _red(text: str) -> str:
    return f"[{C_ERROR}]{text}[/{C_ERROR}]"


def _purple(text: str) -> str:
    return f"[{C_PURPLE}]{text}[/{C_PURPLE}]"


def _cyan(text: str) -> str:
    return f"[{C_CYAN}]{text}[/{C_CYAN}]"


def _select_from_list(
    items: list[tuple[str, str]],
    selected_index: int = 0,
    filter_text: str = "",
    multi: bool = False,
    selected_items: set[str] | None = None,
) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column("Sel", width=4)
    table.add_column("Item", width=50)

    filtered = items
    if filter_text:
        filtered = [
            (k, v)
            for k, v in items
            if filter_text.lower() in k.lower() or filter_text.lower() in v.lower()
        ]

    for i, (key, label) in enumerate(filtered):
        if multi:
            checked = "◉" if (selected_items and key in selected_items) else "○"
        else:
            checked = "▸" if i == selected_index else " "
        style = f"bold {C_TEXT}" if i == selected_index else C_DIM
        table.add_row(Text(checked, style=style), Text(f"{label}", style=style))

    if filter_text:
        table.add_row(
            Text(""),
            Text(f"  filter: {filter_text}", style=f"italic {C_DIM}"),
        )

    return table


def _render_card(title: str, body: Any, accent: str = C_ACCENT) -> Panel:
    return make_card(
        title,
        body,
        accent=accent,
        icon_str=STEP_ICONS.get(title.lower(), "◇"),
    )


# =============================================================================
# SetupCheckpoint — persistent crash recovery
# =============================================================================

class SetupCheckpoint:
    """Persistent setup state for crash recovery and ``--resume``."""

    def __init__(self, state: dict | None = None):
        self.state = state or {
            "version": 3,
            "current_step": 0,
            "completed_steps": [],
            "skipped_steps": [],
            "step_data": {},
            "last_updated": None,
        }

    @classmethod
    def load(cls) -> Optional["SetupCheckpoint"]:
        path = get_aetheros_home() / _CHECKPOINT_FILE
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(data)
        except (json.JSONDecodeError, OSError):
            return None

    def save(
        self,
        current_step: int,
        completed: list[str],
        skipped: list[str] | None = None,
        step_data: dict | None = None,
    ) -> None:
        self.state["current_step"] = current_step
        self.state["completed_steps"] = completed
        if skipped is not None:
            self.state["skipped_steps"] = skipped
        if step_data:
            self.state["step_data"].update(step_data)
        self.state["last_updated"] = datetime.now().isoformat()
        path = get_aetheros_home() / _CHECKPOINT_FILE
        path.write_text(
            json.dumps(self.state, indent=2, default=str), encoding="utf-8"
        )

    def delete(self) -> None:
        path = get_aetheros_home() / _CHECKPOINT_FILE
        if path.exists():
            path.unlink()

    def is_completed(self, step_name: str) -> bool:
        return step_name in self.state.get("completed_steps", [])

    def is_skipped(self, step_name: str) -> bool:
        return step_name in self.state.get("skipped_steps", [])

    @property
    def current_step(self) -> int:
        return self.state.get("current_step", 0)

    def mark_editing(self, step_name: str) -> None:
        completed = self.state.get("completed_steps", [])
        if step_name in completed:
            completed.remove(step_name)
        self.state["completed_steps"] = completed

    def complete_step(self, step_name: str) -> None:
        completed = self.state.get("completed_steps", [])
        if step_name not in completed:
            completed.append(step_name)
        self.state["completed_steps"] = completed

    def skip_step(self, step_name: str) -> None:
        skipped = self.state.get("skipped_steps", [])
        if step_name not in skipped:
            skipped.append(step_name)
        self.state["skipped_steps"] = skipped


# =============================================================================
# Step Base
# =============================================================================

class SetupStep:
    name: str = ""
    title: str = ""
    subtitle: str = ""
    required: bool = False
    step_number: int = 0
    total_steps: int = 0
    wizard: "AdvancedSetupWizard" = None

    def __init__(self, wizard: "AdvancedSetupWizard"):
        self.wizard = wizard
        self._valid = False
        self._data: dict = {}
        self._field_index = 0
        self._field_count = 1
        self._done_message: str | None = None

    @property
    def config(self) -> dict:
        return self.wizard.config

    @property
    def step_icon(self) -> str:
        return icon(self.name)

    def render(self) -> Panel:
        raise NotImplementedError

    def handle_action(self, action: str) -> str | None:
        return None

    def validate(self) -> bool:
        return self._valid

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> dict | None:
        return None

    def save_to_config(self) -> None:
        pass

    def on_skip(self) -> dict | None:
        return None


# =============================================================================
# Step 1: Welcome
# =============================================================================

class WelcomeStep(SetupStep):
    name = "welcome"
    title = "Welcome"
    subtitle = "Begin your AetherOS journey"
    required = True

    def __init__(self, wizard):
        super().__init__(wizard)
        self._valid = True
        self.step_number = 1

    def render(self) -> Panel:
        welcome = Table.grid(padding=(0, 1))
        welcome.add_column(justify="center")
        welcome.add_row(Text(""))
        welcome.add_row(
            Text("◆  AetherOS  ◆", style=f"bold {C_PURPLE}")
        )
        welcome.add_row(
            Text("Autonomous AI Operating System", style=f"italic {C_DIM}")
        )
        welcome.add_row(Text(""))
        welcome.add_row(
            Text("Welcome to the next generation of AI-powered computing.", style=C_TEXT)
        )
        welcome.add_row(Text(""))
        welcome.add_row(
            Text("This quick setup will configure your:", style=C_DIM)
        )
        welcome.add_row(Text(""))
        features = [
            "  ✦  AI Providers & Models",
            "  ✦  Connected Services & Integrations",
            "  ✦  Workspace & Tools",
            "  ✦  Privacy & Security",
            "  ✦  Automation & Memory",
        ]
        for f in features:
            welcome.add_row(Text(f, style=C_DIM))
        welcome.add_row(Text(""))
        welcome.add_row(
            Text("Estimated time: 2 minutes", style=f"bold {C_CYAN}")
        )

        return _render_card("Welcome", welcome, C_PURPLE)


# =============================================================================
# Step 2: Profile
# =============================================================================

_PROFILE_LANGUAGES = [
    ("en", "English"), ("es", "Español"), ("fr", "Français"), ("de", "Deutsch"),
    ("it", "Italiano"), ("pt", "Português"), ("ru", "Русский"), ("ja", "日本語"),
    ("ko", "한국어"), ("zh", "中文"), ("ar", "العربية"), ("hi", "हिन्दी"),
    ("nl", "Nederlands"), ("pl", "Polski"), ("tr", "Türkçe"), ("vi", "Tiếng Việt"),
    ("th", "ไทย"), ("sv", "Svenska"), ("da", "Dansk"), ("fi", "Suomi"),
    ("no", "Norsk"), ("cs", "Čeština"), ("hu", "Magyar"), ("ro", "Română"),
    ("uk", "Українська"), ("el", "Ελληνικά"), ("he", "עברית"),
]

_PROFILE_TIMEZONES = []  # lazily loaded

_THEMES = [
    ("dark", "Dark — easy on the eyes"),
    ("light", "Light — bright and clean"),
    ("system", "System — follow your OS preference"),
]


class ProfileStep(SetupStep):
    name = "profile"
    title = "Profile"
    subtitle = "Tell us about yourself"
    required = True

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 2
        self._field_count = 5
        self._field_index = 0
        self._name = ""
        self._username = ""
        self._language = "en"
        self._timezone = "UTC"
        self._theme = "dark"
        self._filter_lang = ""
        self._filter_tz = ""
        self._lang_selected = 0
        self._tz_selected = 0
        self._tz_list = _PROFILE_TIMEZONES
        if not self._tz_list:
            try:
                import zoneinfo
                self._tz_list = [(z, z.replace("_", " ")) for z in sorted(zoneinfo.available_timezones())]
            except Exception:
                self._tz_list = [("UTC", "UTC"), ("US/Eastern", "US/Eastern"),
                                 ("US/Pacific", "US/Pacific"), ("Europe/London", "Europe/London"),
                                 ("Europe/Berlin", "Europe/Berlin"), ("Asia/Tokyo", "Asia/Tokyo")]

    def on_enter(self) -> None:
        if not self._name:
            self._field_index = 0
        self._valid = bool(self._name and self._username)

    def set_input(self, value: str) -> None:
        if self._field_index == 0:
            self._name = value
            self._field_index = 1
        elif self._field_index == 1:
            self._username = value
            self._field_index = 2
        self._valid = bool(self._name and self._username)

    def render(self) -> Panel:
        form = Table.grid(padding=(0, 2))
        form.add_column("Label", width=16)
        form.add_column("Value", width=50)

        fields = [
            ("Name", self._name or "(enter your name)", 0),
            ("Username", self._username or "(enter a username)", 1),
            ("Language", f"{self._language}", 2),
            ("Timezone", f"{self._timezone}", 3),
            ("Theme", f"{self._theme}", 4),
        ]

        for label, value, idx in fields:
            style = f"bold {C_ACCENT}" if idx == self._field_index else C_DIM
            val_style = f"bold {C_TEXT}" if idx == self._field_index else C_DIM
            cursor = " ▸" if idx == self._field_index else ""
            form.add_row(
                Text(f"  {label}{cursor}", style=style),
                Text(str(value), style=val_style),
            )

        if self._field_index == 2:
            items = [(k, v) for k, v in _PROFILE_LANGUAGES]
            filtered = items
            if self._filter_lang:
                filtered = [(k, v) for k, v in items
                           if self._filter_lang.lower() in k.lower() or self._filter_lang.lower() in v.lower()]
            pick_table = Table.grid(padding=(0, 2))
            pick_table.add_column("Sel", width=4)
            pick_table.add_column("Language", width=30)
            pick_table.add_column("Code", width=8)
            for i, (code, name) in enumerate(filtered):
                sel = "▸" if i == self._lang_selected and not self._filter_lang else ""
                pick_table.add_row(
                    Text(sel, style=C_ACCENT),
                    Text(name, style=C_TEXT if i == self._lang_selected else C_DIM),
                    Text(code, style=f"dim {C_DIM}"),
                )
            if self._filter_lang:
                pick_table.add_row(Text(""), Text(f"filter: {self._filter_lang}", style=f"italic {C_DIM}"))
            form.add_row(Text(""), pick_table)

        elif self._field_index == 3:
            items = self._tz_list
            filtered = items
            if self._filter_tz:
                filtered = [(k, v) for k, v in items
                           if self._filter_tz.lower() in k.lower() or self._filter_tz.lower() in v.lower()]
            pick_table = Table.grid(padding=(0, 2))
            pick_table.add_column("Sel", width=4)
            pick_table.add_column("Timezone", width=40)
            for i, (code, name) in enumerate(filtered[:20]):
                sel = "▸" if i == self._tz_selected else ""
                pick_table.add_row(
                    Text(sel, style=C_ACCENT),
                    Text(name, style=C_TEXT if i == self._tz_selected else C_DIM),
                )
            if len(filtered) > 20:
                pick_table.add_row(Text(""), Text(f"... and {len(filtered)-20} more", style=f"dim {C_DIM}"))
            if self._filter_tz:
                pick_table.add_row(Text(""), Text(f"filter: {self._filter_tz}", style=f"italic {C_DIM}"))
            form.add_row(Text(""), pick_table)

        elif self._field_index == 4:
            pick_table = Table.grid(padding=(0, 2))
            pick_table.add_column("Sel", width=4)
            pick_table.add_column("Theme", width=20)
            pick_table.add_column("Description", width=30)
            for i, (key, desc) in enumerate(_THEMES):
                sel = "▸" if key == self._theme else ""
                pick_table.add_row(
                    Text(sel, style=C_ACCENT),
                    Text(key, style=C_TEXT if key == self._theme else C_DIM),
                    Text(desc, style=C_DIM),
                )
            form.add_row(Text(""), pick_table)

        hint = "  ↑↓ navigate  ·  Tab/Shift+Tab switch field  ·  type to filter"

        return _render_card(
            "Profile",
            Group(form, Text(""), Text(hint, style=f"dim {C_DIM}")),
            C_CYAN,
        )

    def handle_action(self, action: str) -> str | None:
        if self._field_index == 0:
            return None
        elif self._field_index == 1:
            return None
        elif self._field_index == 2:
            items = [(k, v) for k, v in _PROFILE_LANGUAGES]
            filtered = items
            if self._filter_lang:
                filtered = [(k, v) for k, v in items
                           if self._filter_lang.lower() in k.lower() or self._filter_lang.lower() in v.lower()]
            if action == "up":
                self._lang_selected = max(0, self._lang_selected - 1)
            elif action == "down":
                self._lang_selected = min(len(filtered) - 1, self._lang_selected + 1)
            elif action == "confirm" and filtered:
                self._language = filtered[self._lang_selected][0]
            elif action and len(action) == 1 and action.isprintable():
                self._filter_lang += action
                self._lang_selected = 0
            elif action == "backspace":
                self._filter_lang = self._filter_lang[:-1]
                self._lang_selected = 0
        elif self._field_index == 3:
            filtered = self._tz_list
            if self._filter_tz:
                filtered = [(k, v) for k, v in self._tz_list
                           if self._filter_tz.lower() in k.lower() or self._filter_tz.lower() in v.lower()]
            if action == "up":
                self._tz_selected = max(0, self._tz_selected - 1)
            elif action == "down":
                self._tz_selected = min(len(filtered) - 1, self._tz_selected + 1)
            elif action == "confirm" and filtered:
                self._timezone = filtered[self._tz_selected][0]
            elif action and len(action) == 1 and action.isprintable():
                self._filter_tz += action
                self._tz_selected = 0
            elif action == "backspace":
                self._filter_tz = self._filter_tz[:-1]
                self._tz_selected = 0
        elif self._field_index == 4:
            idx = next((i for i, (k, _) in enumerate(_THEMES) if k == self._theme), 0)
            if action == "up":
                idx = max(0, idx - 1)
                self._theme = _THEMES[idx][0]
            elif action == "down":
                idx = min(len(_THEMES) - 1, idx + 1)
                self._theme = _THEMES[idx][0]
        return None

    def on_exit(self) -> dict:
        return {
            "name": self._name,
            "username": self._username,
            "language": self._language,
            "timezone": self._timezone,
            "theme": self._theme,
        }

    def save_to_config(self) -> None:
        self.config.setdefault("onboarding", {}).update({
            "profile_build": "completed",
        })
        self.config.setdefault("display", {})["skin"] = (
            "daylight" if self._theme == "light" else
            "warm-lightmode" if self._theme == "warm" else
            "default"
        )


# =============================================================================
# Step 3: Purpose
# =============================================================================

_PURPOSES = [
    ("programming", "Programming", "Write, debug, and review code"),
    ("research", "Research", "Analyze data and synthesize findings"),
    ("business", "Business", "Automate workflows and reporting"),
    ("student", "Student", "Learn and study with AI assistance"),
    ("devops", "DevOps", "Manage infrastructure and deployments"),
    ("cybersecurity", "Cybersecurity", "Security analysis and threat detection"),
    ("content_creation", "Content Creation", "Write, design, and produce media"),
    ("automation", "Automation", "Automate repetitive tasks and processes"),
    ("personal_assistant", "Personal Assistant", "Daily productivity and organization"),
    ("ai_development", "AI Agent Development", "Build and deploy AI agents"),
]


class PurposeStep(SetupStep):
    name = "purpose"
    title = "Purpose"
    subtitle = "What will you use AetherOS for?"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 3
        self._valid = True
        self._selected: set[str] = set()
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Purpose", width=24)
        table.add_column("Description", width=40)

        for i, (key, label, desc) in enumerate(_PURPOSES):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(label, style=style),
                Text(desc, style=f"italic {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("Purpose", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_ACCENT)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_PURPOSES) - 1, self._cursor + 1)
        elif action in ("confirm", "right"):
            return None
        elif action == " " or action == "toggle":
            key = _PURPOSES[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"purposes": list(self._selected)}

    def save_to_config(self) -> None:
        if self._selected:
            self.config.setdefault("onboarding", {})["purposes"] = list(self._selected)


# =============================================================================
# Step 4: Experience Level
# =============================================================================

_EXPERIENCE_LEVELS = [
    ("beginner", "Beginner", "New to AI and terminals"),
    ("intermediate", "Intermediate", "Comfortable with basic concepts"),
    ("advanced", "Advanced", "Experienced with AI tools and APIs"),
    ("expert", "Expert", "Professional AI/ML practitioner"),
]


class ExperienceStep(SetupStep):
    name = "experience"
    title = "Experience Level"
    subtitle = "How experienced are you with AI tools?"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 4
        self._valid = True
        self._selected = 1
        self._cursor = 1

    def render(self) -> Panel:
        cards = []
        for i, (key, label, desc) in enumerate(_EXPERIENCE_LEVELS):
            sel = key == self._selected
            border = C_ACCENT if sel else C_BORDER
            style = f"bold {C_TEXT}" if sel else C_DIM
            table = Table.grid(padding=(0, 1))
            indicator = "◉" if sel else "○"
            table.add_row(Text(f"  {indicator}  {label}", style=style))
            table.add_row(Text(f"       {desc}", style=f"dim {C_DIM}"))
            cards.append(Panel(table, border_style=border, padding=(0, 1), box=box.ROUNDED))

        hint = "  ↑↓ navigate  ·  Enter select"
        return _render_card(
            "Experience",
            Group(Columns(cards, equal=False, expand=False), Text(""), Text(hint, style=f"dim {C_DIM}")),
            C_ACCENT,
        )

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_EXPERIENCE_LEVELS) - 1, self._cursor + 1)
        elif action in ("confirm", "right"):
            self._selected = _EXPERIENCE_LEVELS[self._cursor][0]
            return None
        return None

    def on_exit(self) -> dict:
        return {"experience_level": self._selected}

    def save_to_config(self) -> None:
        if self._selected:
            self.config.setdefault("onboarding", {})["experience_level"] = self._selected


# =============================================================================
# Step 5: AI Providers
# =============================================================================

_AI_PROVIDERS = [
    ("openai", "OpenAI", "#00A67E"),
    ("anthropic", "Anthropic", "#D4A574"),
    ("gemini", "Gemini", "#4285F4"),
    ("openrouter", "OpenRouter", "#FF6B6B"),
    ("groq", "Groq", "#F55036"),
    ("together", "Together AI", "#FF6B4A"),
    ("deepseek", "DeepSeek", "#4F6BED"),
    ("mistral", "Mistral AI", "#FF6B00"),
    ("cohere", "Cohere", "#39594D"),
    ("perplexity", "Perplexity", "#1E1E2E"),
    ("xai", "xAI", "#1A1A2E"),
    ("azure", "Azure OpenAI", "#0078D4"),
    ("aws_bedrock", "AWS Bedrock", "#FF9900"),
    ("vertex_ai", "Vertex AI", "#34A853"),
    ("fireworks", "Fireworks AI", "#F5A623"),
    ("ollama", "Ollama", "#000000"),
    ("lm_studio", "LM Studio", "#4A90D9"),
    ("vllm", "vLLM", "#00C853"),
    ("open_webui", "Open WebUI", "#FF5722"),
    ("custom", "Custom OpenAI Compatible", "#8B949E"),
]


class AIProviderStep(SetupStep):
    name = "ai_providers"
    title = "AI Providers"
    subtitle = "Select your AI providers (you can add more later)"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 5
        self._valid = True
        self._selected: set[str] = set()
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Provider", width=24)
        table.add_column("Tag", width=14)

        for i, (key, name, tag) in enumerate(_AI_PROVIDERS):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(name, style=style),
                Text(f"[{tag}]", style=f"dim {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("AI Providers", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_ACCENT)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_AI_PROVIDERS) - 1, self._cursor + 1)
        elif action == " ":
            key = _AI_PROVIDERS[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"providers": list(self._selected)}

    def save_to_config(self) -> None:
        if self._selected:
            self.config.setdefault("onboarding", {})["selected_providers"] = list(self._selected)


# =============================================================================
# Step 6: Local Detection
# =============================================================================

_LOCAL_PROVIDERS = [
    ("ollama", "Ollama", "localhost:11434", "/api/tags"),
    ("lm_studio", "LM Studio", "localhost:1234", "/v1/models"),
    ("vllm", "vLLM", "localhost:8000", "/v1/models"),
    ("open_webui", "Open WebUI", "localhost:3000", "/api/models"),
]


class LocalDetectionStep(SetupStep):
    name = "local_detection"
    title = "Local Providers"
    subtitle = "Auto-detect local AI providers on your machine"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 6
        self._valid = True
        self._scan_results: dict[str, bool] = {}
        self._scanned = False
        self._scanning = False
        self._selected: set[str] = set()

    def on_enter(self) -> None:
        if not self._scanned and not self._scanning:
            self._scan()

    def _scan(self) -> None:
        self._scanning = True
        import urllib.request
        import urllib.error
        for key, name, host, path in _LOCAL_PROVIDERS:
            url = f"http://{host}{path}"
            try:
                req = urllib.request.Request(url, method="GET")
                req.timeout = 2
                with urllib.request.urlopen(req) as resp:
                    self._scan_results[key] = resp.status == 200
            except (urllib.error.URLError, OSError, ConnectionRefusedError, TimeoutError):
                self._scan_results[key] = False
        self._scanned = True
        self._scanning = False

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Status", width=10)
        table.add_column("Provider", width=16)
        table.add_column("Endpoint", width=22)
        table.add_column("Action", width=16)

        for key, name, host, _ in _LOCAL_PROVIDERS:
            if self._scanning:
                status = Text("⟳", style=C_ACCENT)
            elif self._scan_results.get(key):
                status = Text("✓ Detected", style=f"bold {C_SUCCESS}")
            else:
                status = Text("✗ Not Found", style=C_DIM)

            enabled = key in self._selected
            action = Text("✓ Enabled" if enabled else "○ Enable", style=C_TEXT if enabled else C_DIM)
            table.add_row(status, Text(name, style=C_TEXT), Text(host, style=f"dim {C_DIM}"), action)

        if self._scanning:
            table.add_row(Text(""), Text("Scanning...", style=f"italic {C_DIM}"), Text(""), Text(""))

        hint = "  ↑↓ navigate  ·  Space toggle enable  ·  R rescan"
        return _render_card("Local Providers", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_CYAN)

    def handle_action(self, action: str) -> str | None:
        if action == "r":
            self._scanned = False
            self._scan()
        elif action == " ":
            pass
        return None

    def on_exit(self) -> dict:
        return {"local_providers": {k: self._scan_results.get(k, False) for k, *_ in _LOCAL_PROVIDERS}}

    def save_to_config(self) -> None:
        for key, name, host, _ in _LOCAL_PROVIDERS:
            if self._scan_results.get(key):
                self.config.setdefault("providers", {})[key] = {"base_url": f"http://{host}", "api_key": "not-required"}


# =============================================================================
# Step 7: API Configuration
# =============================================================================

_API_CONFIG_PROVIDERS = [
    ("openai", "OpenAI", "OPENAI_API_KEY", "sk-..."),
    ("anthropic", "Anthropic", "ANTHROPIC_API_KEY", "sk-ant-..."),
    ("gemini", "Gemini", "GEMINI_API_KEY", "AIza..."),
    ("openrouter", "OpenRouter", "OPENROUTER_API_KEY", "sk-or-..."),
    ("groq", "Groq", "GROQ_API_KEY", "gsk_..."),
    ("deepseek", "DeepSeek", "DEEPSEEK_API_KEY", "sk-..."),
]


class APIConfigStep(SetupStep):
    name = "api_config"
    title = "API Configuration"
    subtitle = "Configure API keys for your selected cloud providers"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 7
        self._valid = True
        self._field_index = 0
        self._field_count = 1
        self._api_keys: dict[str, str] = {}
        self._active_provider = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Provider", width=16)
        table.add_column("API Key", width=40)

        for i, (key, name, env_var, _) in enumerate(_API_CONFIG_PROVIDERS):
            existing = get_env_value(env_var) or self._api_keys.get(key, "")
            masked = f"{'*' * 20}{existing[-4:]}" if len(existing) > 8 else "(not configured)"
            style = f"bold {C_TEXT}" if i == self._active_provider else C_DIM
            cursor = " ▸" if i == self._active_provider else ""
            table.add_row(
                Text(f"  {name}{cursor}", style=style),
                Text(masked, style=f"dim {C_DIM}" if not existing else C_CYAN),
            )

        hint = "  ↑↓ navigate  ·  Enter configure  ·  Leave blank to skip"
        return _render_card("API Configuration", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_WARN)

    def handle_action(self, action: str) -> str | None:
        if action in ("up",):
            self._active_provider = max(0, self._active_provider - 1)
        elif action in ("down",):
            self._active_provider = min(len(_API_CONFIG_PROVIDERS) - 1, self._active_provider + 1)
        elif action == "confirm":
            key, name, env_var, placeholder = _API_CONFIG_PROVIDERS[self._active_provider]
            existing = get_env_value(env_var) or self._api_keys.get(key, "")
            from prompt_toolkit import PromptSession
            from prompt_toolkit.styles import Style as PtStyle
            pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
            session = PromptSession(style=pt_style)
            try:
                value = session.prompt(
                    f"  {_accent('▸')}  {name} API Key ({placeholder}): ",
                    default=existing,
                    is_password=True,
                )
                if value:
                    self._api_keys[key] = value
                    save_env_value(env_var, value)
            except (EOFError, KeyboardInterrupt):
                pass
        return None

    def on_exit(self) -> dict:
        return {"api_keys": list(self._api_keys.keys())}

    def save_to_config(self) -> None:
        pass


# =============================================================================
# Step 8: Default Models
# =============================================================================

_MODEL_CATEGORIES = [
    ("coding", "Coding Model", "GPT-5, Claude Sonnet, Gemini Pro"),
    ("reasoning", "Reasoning Model", "Claude Opus, Gemini Ultra, o3"),
    ("vision", "Vision Model", "GPT-5 Vision, Claude 3.5 Sonnet Vision"),
    ("fast", "Fast Model", "GPT-5 Mini, Claude Haiku, Gemini Flash"),
    ("offline", "Offline Model", "Llama 3, Qwen, Mistral (local)"),
]


class DefaultModelsStep(SetupStep):
    name = "default_models"
    title = "Default Models"
    subtitle = "Choose your preferred models for each task"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 8
        self._valid = True

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Role", width=18)
        table.add_column("Suggested Models", width=50)

        for role, label, examples in _MODEL_CATEGORIES:
            table.add_row(
                Text(f"  {label}", style=f"bold {C_TEXT}"),
                Text(examples, style=C_DIM),
            )

        info = "  Models are detected from configured providers. Edit anytime in Settings."
        return _render_card("Default Models", Group(table, Text(""), Text(info, style=f"dim {C_DIM}")), C_PURPLE)

    def on_exit(self) -> dict:
        return {"model_categories": [c[0] for c in _MODEL_CATEGORIES]}

    def save_to_config(self) -> None:
        pass


# =============================================================================
# Step 9: Connect Services
# =============================================================================

_CONNECTABLE_SERVICES = [
    ("telegram", "Telegram Bot", "messaging", "🤖"),
    ("telegram_personal", "Telegram Personal", "messaging", "📱"),
    ("discord", "Discord", "messaging", "💬"),
    ("slack", "Slack", "messaging", "🔲"),
    ("teams", "Microsoft Teams", "messaging", "🪟"),
    ("whatsapp", "WhatsApp Business", "messaging", "📞"),
    ("gmail", "Gmail", "google", "📧"),
    ("calendar", "Google Calendar", "google", "📅"),
    ("drive", "Google Drive", "google", "📂"),
    ("docs", "Google Docs", "google", "📝"),
    ("sheets", "Google Sheets", "google", "📊"),
    ("github", "GitHub", "dev", "🐙"),
    ("gitlab", "GitLab", "dev", "🦊"),
    ("bitbucket", "Bitbucket", "dev", "🔵"),
    ("docker", "Docker", "dev", "🐳"),
    ("kubernetes", "Kubernetes", "dev", "☸"),
    ("notion", "Notion", "productivity", "📘"),
    ("jira", "Jira", "productivity", "🔶"),
    ("linear", "Linear", "productivity", "⬛"),
    ("clickup", "ClickUp", "productivity", "🟣"),
    ("trello", "Trello", "productivity", "🔷"),
    ("dropbox", "Dropbox", "cloud", "📦"),
    ("onedrive", "OneDrive", "cloud", "☁"),
    ("box", "Box", "cloud", "📦"),
]


class ConnectServicesStep(SetupStep):
    name = "connect_services"
    title = "Connect Services"
    subtitle = "Integrate your accounts and services"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 9
        self._valid = True
        self._connected: set[str] = set()
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Service", width=24)
        table.add_column("Category", width=14)
        table.add_column("Status", width=16)
        table.add_column("Auth", width=14)

        for i, (key, name, cat, serv_icon) in enumerate(_CONNECTABLE_SERVICES):
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            status = _green("✓ Connected") if key in self._connected else "○ Connect"
            auth = "OAuth" if cat in ("google", "dev", "productivity") else "Token"
            table.add_row(
                Text(f"{sel} {serv_icon}", style=style),
                Text(name, style=style),
                Text(cat, style=f"dim {C_DIM}"),
                Text(status, style=f"bold {C_SUCCESS}" if key in self._connected else C_DIM),
                Text(auth, style=f"dim {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Continue later: Enter"
        return _render_card("Connect Services", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_ACCENT)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_CONNECTABLE_SERVICES) - 1, self._cursor + 1)
        elif action == " ":
            key = _CONNECTABLE_SERVICES[self._cursor][0]
            if key in self._connected:
                self._connected.discard(key)
            else:
                self._connected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"connected_services": list(self._connected)}

    def save_to_config(self) -> None:
        if self._connected:
            self.config.setdefault("onboarding", {})["connected_services"] = list(self._connected)


# =============================================================================
# Step 10: Automation
# =============================================================================

_AUTOMATION_OPTIONS = [
    ("background_agents", "Background Agents", "Run autonomous agents in the background"),
    ("scheduled_tasks", "Scheduled Tasks", "Schedule recurring operations"),
    ("cron_jobs", "Cron Jobs", "Set up cron-based job scheduling"),
    ("notifications", "Notifications", "Receive status updates and alerts"),
    ("workflow_engine", "Workflow Engine", "Design and run multi-step workflows"),
]


class AutomationStep(SetupStep):
    name = "automation"
    title = "Automation"
    subtitle = "Configure automation capabilities"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 10
        self._valid = True
        self._selected: set[str] = {"background_agents", "notifications"}
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Feature", width=24)
        table.add_column("Description", width=40)

        for i, (key, name, desc) in enumerate(_AUTOMATION_OPTIONS):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(name, style=style),
                Text(desc, style=f"italic {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("Automation", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_CYAN)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_AUTOMATION_OPTIONS) - 1, self._cursor + 1)
        elif action == " ":
            key = _AUTOMATION_OPTIONS[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"automation": list(self._selected)}

    def save_to_config(self) -> None:
        self.config.setdefault("onboarding", {})["automation"] = list(self._selected)


# =============================================================================
# Step 11: Tools
# =============================================================================

_TOOLS = [
    ("filesystem", "Filesystem", "Read, write, search files"),
    ("browser", "Browser", "Web navigation and automation"),
    ("python", "Python", "Execute Python code"),
    ("docker", "Docker", "Container management"),
    ("git", "Git", "Version control operations"),
    ("terminal", "Terminal", "Shell command execution"),
    ("computer_use", "Computer Use", "Desktop automation"),
    ("mcp", "MCP", "Model Context Protocol servers"),
    ("web_search", "Web Search", "Internet search capabilities"),
    ("ocr", "OCR", "Image text extraction"),
    ("pdf", "PDF", "PDF reading and processing"),
    ("spreadsheet", "Spreadsheet", "CSV and Excel handling"),
    ("voice", "Voice", "Speech input and output"),
    ("vision", "Vision", "Image analysis and understanding"),
]


class ToolsStep(SetupStep):
    name = "tools"
    title = "Tools"
    subtitle = "Enable the tools you need"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 11
        self._valid = True
        self._selected: set[str] = {"filesystem", "terminal", "web_search", "browser"}
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Tool", width=18)
        table.add_column("Description", width=40)

        for i, (key, name, desc) in enumerate(_TOOLS):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(name, style=style),
                Text(desc, style=f"italic {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("Tools", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_ACCENT)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_TOOLS) - 1, self._cursor + 1)
        elif action == " ":
            key = _TOOLS[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"tools": list(self._selected)}

    def save_to_config(self) -> None:
        self.config.setdefault("onboarding", {})["tools"] = list(self._selected)


# =============================================================================
# Step 12: Memory
# =============================================================================

_MEMORY_OPTIONS = [
    ("personal_memory", "Personal Memory", "Remembers your preferences and habits"),
    ("workspace_memory", "Workspace Memory", "Remembers workspace context and state"),
    ("project_memory", "Project Memory", "Remembers per-project information"),
    ("conversation_memory", "Conversation Memory", "Remembers conversation history across sessions"),
]


class MemoryStep(SetupStep):
    name = "memory"
    title = "Memory"
    subtitle = "Configure how AetherOS remembers information"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 12
        self._valid = True
        self._selected: set[str] = {"personal_memory", "workspace_memory"}
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Memory Type", width=24)
        table.add_column("Description", width=40)

        for i, (key, name, desc) in enumerate(_MEMORY_OPTIONS):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(name, style=style),
                Text(desc, style=f"italic {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("Memory", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_PURPLE)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_MEMORY_OPTIONS) - 1, self._cursor + 1)
        elif action == " ":
            key = _MEMORY_OPTIONS[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"memory": list(self._selected)}

    def save_to_config(self) -> None:
        self.config.setdefault("onboarding", {})["memory"] = list(self._selected)


# =============================================================================
# Step 13: Privacy
# =============================================================================

_PRIVACY_OPTIONS = [
    ("cloud_sync", "Cloud Sync", "Sync configuration across devices"),
    ("local_only", "Local Only", "Keep everything on this machine"),
    ("encrypted_storage", "Encrypted Storage", "Encrypt sensitive data at rest"),
    ("crash_reports", "Crash Reports", "Send anonymous crash reports"),
    ("analytics", "Analytics", "Share anonymous usage data"),
    ("auto_updates", "Auto Updates", "Automatically install updates"),
]


class PrivacyStep(SetupStep):
    name = "privacy"
    title = "Privacy"
    subtitle = "Configure privacy and data preferences"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 13
        self._valid = True
        self._selected: set[str] = {"encrypted_storage", "auto_updates"}
        self._cursor = 0

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Option", width=24)
        table.add_column("Description", width=40)

        for i, (key, name, desc) in enumerate(_PRIVACY_OPTIONS):
            checked = "◉" if key in self._selected else "○"
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            table.add_row(
                Text(f"{sel} {checked}", style=style),
                Text(name, style=style),
                Text(desc, style=f"italic {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Space toggle  ·  Enter continue"
        return _render_card("Privacy", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_WARN)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(_PRIVACY_OPTIONS) - 1, self._cursor + 1)
        elif action == " ":
            key = _PRIVACY_OPTIONS[self._cursor][0]
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        return None

    def on_exit(self) -> dict:
        return {"privacy": list(self._selected)}

    def save_to_config(self) -> None:
        self.config.setdefault("onboarding", {})["privacy"] = list(self._selected)


# =============================================================================
# Step 14: Workspace
# =============================================================================

_WORKSPACE_PRESETS = [
    ("projects", "Projects Folder", "~/aetheros-projects"),
    ("downloads", "Downloads", "~/Downloads"),
    ("documents", "Documents", "~/Documents"),
    ("custom", "Custom Folder", "Choose your own path"),
]


class WorkspaceStep(SetupStep):
    name = "workspace"
    title = "Workspace"
    subtitle = "Choose your workspace directories"
    required = False

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 14
        self._valid = True
        self._selected = 0
        self._projects_path = str(Path.home() / "aetheros-projects")
        self._custom_path = str(Path.home() / "aetheros-workspace")

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Folder", width=20)
        table.add_column("Path", width=40)

        for i, (key, name, default_path) in enumerate(_WORKSPACE_PRESETS):
            sel = "◉" if i == self._selected else "○"
            path = self._projects_path if key == "projects" else (
                self._custom_path if key == "custom" else default_path
            )
            style = f"bold {C_TEXT}" if i == self._selected else C_DIM
            table.add_row(
                Text(f"  {sel}", style=style),
                Text(name, style=style),
                Text(path, style=f"dim {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  Enter confirm  ·  Edit paths later in Settings"
        return _render_card("Workspace", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_ACCENT)

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._selected = max(0, self._selected - 1)
        elif action == "down":
            self._selected = min(len(_WORKSPACE_PRESETS) - 1, self._selected + 1)
        return None

    def on_exit(self) -> dict:
        key, _, _ = _WORKSPACE_PRESETS[self._selected]
        path = self._projects_path if key == "projects" else (
            self._custom_path if key == "custom" else str(Path.home() / key.capitalize())
        )
        return {"workspace": key, "workspace_path": path}

    def save_to_config(self) -> None:
        key, _, _ = _WORKSPACE_PRESETS[self._selected]
        if key == "projects":
            self.config.setdefault("terminal", {})["cwd"] = self._projects_path


# =============================================================================
# Step 15: Review
# =============================================================================

class ReviewStep(SetupStep):
    name = "review"
    title = "Review"
    subtitle = "Review your configuration before finishing"
    required = True

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 15
        self._valid = True
        self._cursor = 0
        self._section_names = [
            "profile", "purpose", "experience", "ai_providers",
            "local_detection", "api_config", "default_models", "connect_services",
            "automation", "tools", "memory", "privacy", "workspace",
        ]

    def render(self) -> Panel:
        data = self.wizard.checkpoint.state.get("step_data", {})
        table = Table.grid(padding=(0, 2))
        table.add_column("Section", width=22)
        table.add_column("Status", width=14)
        table.add_column("Summary", width=50)

        for i, section in enumerate(self._section_names):
            step_data = data.get(section, {})
            completed = self.wizard.checkpoint.is_completed(section)
            skipped = self.wizard.checkpoint.is_skipped(section)
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM
            ico = icon(section)

            if completed or skipped:
                status = _green("✓ Done") if completed else _yellow("⏭ Skipped")
            else:
                status = _dim("— Not set")

            summary = ""
            if completed and step_data:
                summary = self._summarize(section, step_data)

            table.add_row(
                Text(f"{sel} {ico}  {section.replace('_', ' ').title()}", style=style),
                Text(status, style=style),
                Text(summary, style=f"dim {C_DIM}"),
            )

        hint = "  ↑↓ navigate  ·  E edit section  ·  Enter continue"
        return _render_card("Review", Group(table, Text(""), Text(hint, style=f"dim {C_DIM}")), C_SUCCESS)

    def _summarize(self, section: str, data: dict) -> str:
        if section == "profile":
            return f"{data.get('name', '?')} · {data.get('language', '?')} · {data.get('theme', '?')}"
        if section == "purpose":
            purposes = data.get("purposes", [])
            return ", ".join(p[:12] for p in purposes[:3]) + ("..." if len(purposes) > 3 else "")
        if section == "experience":
            return str(data.get("experience_level", "?"))
        if section == "ai_providers":
            providers = data.get("providers", [])
            return f"{len(providers)} selected" if providers else "None"
        if section == "connect_services":
            services = data.get("connected_services", [])
            return f"{len(services)} connected" if services else "None"
        if section == "automation":
            auto = data.get("automation", [])
            return ", ".join(a[:12] for a in auto[:2])
        if section == "tools":
            tools = data.get("tools", [])
            return f"{len(tools)} tools"
        if section == "memory":
            mem = data.get("memory", [])
            return ", ".join(m[:12] for m in mem[:2])
        if section == "privacy":
            priv = data.get("privacy", [])
            return ", ".join(p[:12] for p in priv[:2])
        if section == "workspace":
            return data.get("workspace_path", "?")
        return ""

    def handle_action(self, action: str) -> str | None:
        if action == "up":
            self._cursor = max(0, self._cursor - 1)
        elif action == "down":
            self._cursor = min(len(self._section_names) - 1, self._cursor + 1)
        elif action == "edit" or action == "e":
            if self._cursor < len(self._section_names):
                section = self._section_names[self._cursor]
                return f"edit:{section}"
        return None


# =============================================================================
# Step 16: Finish
# =============================================================================

class FinishStep(SetupStep):
    name = "finish"
    title = "Finish"
    subtitle = "Setup complete"
    required = True

    def __init__(self, wizard):
        super().__init__(wizard)
        self.step_number = 16
        self._valid = True
        self._launch_choice = "1"

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="center")

        table.add_row(Text(""))
        table.add_row(
            Text("◆  Configuration Saved  ◆", style=f"bold {C_SUCCESS}")
        )
        table.add_row(Text(""))
        table.add_row(
            Text("Your AetherOS system is ready.", style=C_TEXT)
        )
        table.add_row(Text(""))

        summary = self.wizard.checkpoint.state.get("completed_steps", [])
        table.add_row(
            Text(f"  {len(summary)} of {len(self.wizard.steps)} steps completed", style=C_CYAN)
        )
        table.add_row(Text(""))

        launch_table = Table.grid(padding=(0, 2))
        launch_table.add_column("Sel", width=4)
        launch_table.add_column("Option", width=24)
        launch_table.add_column("Description", width=40)

        options = [
            ("1", "Terminal", "Launch AetherOS in the terminal"),
            ("2", "Browser Dashboard", "Open the web dashboard"),
            ("3", "Both", "Terminal + Browser together"),
        ]
        for num, opt, desc in options:
            sel = "◉" if self._launch_choice == num else "○"
            style = f"bold {C_TEXT}" if self._launch_choice == num else C_DIM
            launch_table.add_row(
                Text(f"  {sel}", style=style),
                Text(opt, style=style),
                Text(desc, style=C_DIM),
            )

        table.add_row(launch_table)
        table.add_row(Text(""))
        table.add_row(
            Text("Press Enter to launch, Esc to exit", style=f"dim {C_DIM}")
        )

        return _render_card("Finish", table, C_SUCCESS)

    def handle_action(self, action: str) -> str | None:
        if action in ("1", "2", "3"):
            self._launch_choice = action
        elif action == "confirm":
            return "launch"
        return None

    def on_exit(self) -> dict:
        return {"launch_choice": self._launch_choice}


# =============================================================================
# Step Registry
# =============================================================================

_STEP_REGISTRY: list[tuple[str, type[SetupStep], bool]] = [
    ("welcome", WelcomeStep, True),
    ("profile", ProfileStep, True),
    ("purpose", PurposeStep, False),
    ("experience", ExperienceStep, False),
    ("ai_providers", AIProviderStep, False),
    ("local_detection", LocalDetectionStep, False),
    ("api_config", APIConfigStep, False),
    ("default_models", DefaultModelsStep, False),
    ("connect_services", ConnectServicesStep, False),
    ("automation", AutomationStep, False),
    ("tools", ToolsStep, False),
    ("memory", MemoryStep, False),
    ("privacy", PrivacyStep, False),
    ("workspace", WorkspaceStep, False),
    ("review", ReviewStep, True),
    ("finish", FinishStep, True),
]


# =============================================================================
# Keyboard Input (prompt_toolkit) — enhanced with Tab/Shift+Tab support
# =============================================================================

def _get_key() -> str:
    """Capture a single keypress using prompt_toolkit.

    Supports: Enter, Tab, Shift+Tab, Arrows, Esc, Ctrl+C, Ctrl+S,
    alphanumeric, Space, Backspace.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.input import create_input
    from prompt_toolkit.key_binding import KeyBindings

    kb = KeyBindings()
    result: list[str] = []

    @kb.add(Keys.ControlC)
    def _(event):
        event.app.exit(result="ctrl_c")

    @kb.add(Keys.ControlS)
    def _(event):
        event.app.exit(result="save")

    @kb.add(Keys.ControlD)
    def _(event):
        event.app.exit(result="ctrl_c")

    @kb.add(Keys.ControlM)
    def _(event):
        event.app.exit(result="confirm")

    @kb.add(Keys.Enter)
    def _(event):
        if event.key_sequence and event.key_sequence[0].key == Keys.ControlM:
            event.app.exit(result="confirm")

    @kb.add(Keys.Escape)
    def _(event):
        event.app.exit(result="cancel")

    @kb.add(Keys.Tab)
    def _(event):
        event.app.exit(result="tab")

    @kb.add(Keys.BackTab)
    def _(event):
        event.app.exit(result="back_tab")

    @kb.add(Keys.Up)
    def _(event):
        event.app.exit(result="up")

    @kb.add(Keys.Down)
    def _(event):
        event.app.exit(result="down")

    @kb.add(Keys.Left)
    def _(event):
        event.app.exit(result="left")

    @kb.add(Keys.Right)
    def _(event):
        event.app.exit(result="right")

    @kb.add(Keys.Backspace)
    def _(event):
        event.app.exit(result="backspace")

    @kb.add(Keys.Home)
    def _(event):
        event.app.exit(result="home")

    @kb.add(Keys.End)
    def _(event):
        event.app.exit(result="end")

    @kb.add(Keys.Delete)
    def _(event):
        event.app.exit(result="delete")

    @kb.add(Keys.Space)
    def _(event):
        event.app.exit(result=" ")

    @kb.add("<any>")
    def _(event):
        key = event.key_sequence[0].key
        if hasattr(key, "value") and len(key.value) == 1 and key.value.isprintable():
            event.app.exit(result=key.value)
        elif isinstance(key, str) and len(key) == 1:
            event.app.exit(result=key)

    session = PromptSession(key_bindings=kb, erase_when_done=True)
    try:
        return session.prompt("")
    except (EOFError, KeyboardInterrupt):
        return "ctrl_c"


# =============================================================================
# AdvancedSetupWizard
# =============================================================================

class AdvancedSetupWizard:
    """Premium AetherOS setup wizard with step navigation and resume."""

    def __init__(self, args=None):
        self.args = args
        self.config: dict = {}
        self.checkpoint: SetupCheckpoint | None = None
        self.steps: list[SetupStep] = []
        self._current_index: int = 0
        self._running: bool = True
        self._field_index: int = 0
        self._field_count: int = 1
        self._edit_return: bool = False

    def run(self) -> None:
        """Run the setup wizard."""
        ensure_aetheros_home()

        # Handle --reset
        if self.args and getattr(self.args, "reset", False):
            save_config(copy.deepcopy(DEFAULT_CONFIG))
            get_console().print(
                Panel(
                    Align.center(Text("[bold #3fb950]✓ Configuration reset to defaults[/]")),
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            cp = SetupCheckpoint.load()
            if cp:
                cp.delete()

        # Load config
        self.config = load_config()

        # Load or create checkpoint
        resume_requested = self.args and getattr(self.args, "resume", False)
        if resume_requested:
            self.checkpoint = SetupCheckpoint.load()
            if self.checkpoint:
                get_console().print(
                    Panel(
                        Align.center(
                            Text(f"[bold #58a6ff]↻ Resuming from step {self.checkpoint.current_step + 1}[/]")
                        ),
                        border_style=C_BORDER,
                        padding=(1, 2),
                        box=box.ROUNDED,
                    )
                )
                time.sleep(1)
            else:
                get_console().print(
                    Panel(
                        Align.center(
                            Text("[#d29922]⚠ No saved setup state found — starting from beginning[/]")
                        ),
                        border_style=C_BORDER,
                        padding=(1, 2),
                        box=box.ROUNDED,
                    )
                )
                time.sleep(1)

        if not self.checkpoint:
            self.checkpoint = SetupCheckpoint()

        # Build steps
        self._build_steps()

        # Determine starting index
        if self.checkpoint and resume_requested:
            self._current_index = self.checkpoint.current_step
            while (
                self._current_index < len(self.steps)
                and self.checkpoint.is_completed(
                    self.steps[self._current_index].name
                )
            ):
                self._current_index += 1
        else:
            self._current_index = 0

        # Run the wizard loop
        try:
            self._wizard_loop()
        except KeyboardInterrupt:
            self._handle_ctrl_c_dialog()

    def _build_steps(self) -> None:
        """Build step instances from the registry."""
        total = len(_STEP_REGISTRY)
        for i, (name, step_cls, required) in enumerate(_STEP_REGISTRY):
            step = step_cls(self)
            step.name = name
            step.required = required
            step.step_number = i + 1
            step.total_steps = total
            self.steps.append(step)

    def _wizard_loop(self) -> None:
        """Main wizard loop."""
        while self._running and self._current_index < len(self.steps):
            step = self.steps[self._current_index]

            # Handle edit return from review
            if self._edit_return:
                self._edit_return = False
                target = getattr(self, "_edit_target", None)
                if target:
                    idx = next((i for i, s in enumerate(self.steps) if s.name == target), -1)
                    if idx >= 0:
                        self._current_index = idx
                        self.checkpoint.mark_editing(target)
                        continue

            # Check if we're resuming and this step is already done
            if self.checkpoint.is_completed(step.name) or self.checkpoint.is_skipped(step.name):
                if step.name in ("welcome",):
                    pass
                elif self._current_index + 1 < len(self.steps):
                    self._current_index += 1
                    continue

            step.on_enter()
            clear()
            self._render_step(step)
            action = self._wait_for_action(step)
            result = self._process_action(step, action)

            if result == "next":
                self._handle_next(step)
            elif result == "back":
                self._handle_back()
            elif result == "skip":
                self._handle_skip(step)
            elif result == "save":
                self._handle_save()
            elif result == "save_exit":
                self._handle_save_exit()
            elif result == "cancel":
                if self._handle_cancel_dialog():
                    return
            elif result and result.startswith("edit:"):
                self._edit_target = result.split(":", 1)[1]
                self._edit_return = True
            elif result == "launch":
                self._on_complete()
                return

        self._on_complete()

    def _handle_next(self, step: SetupStep) -> None:
        data = step.on_exit()
        if data:
            self.checkpoint.save(
                current_step=self._current_index,
                completed=self.checkpoint.state.get("completed_steps", []),
                step_data={step.name: data},
            )
        step.save_to_config()
        save_config(self.config)
        self.checkpoint.complete_step(step.name)
        self.checkpoint.save(
            current_step=self._current_index,
            completed=self.checkpoint.state.get("completed_steps", []),
        )
        if self._current_index + 1 < len(self.steps):
            self._current_index += 1

    def _handle_back(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1

    def _handle_skip(self, step: SetupStep) -> None:
        data = step.on_skip()
        if data:
            self.checkpoint.save(
                current_step=self._current_index,
                completed=self.checkpoint.state.get("completed_steps", []),
                step_data={step.name: data},
            )
        self.checkpoint.skip_step(step.name)
        self.checkpoint.save(
            current_step=self._current_index,
            completed=self.checkpoint.state.get("completed_steps", []),
        )
        if self._current_index + 1 < len(self.steps):
            self._current_index += 1

    def _handle_save(self) -> None:
        save_config(self.config)
        get_console().print(
            Panel(
                Align.center(Text(f"[dim]Progress saved. Use [bold]--resume[/] to continue.[/dim]")),
                border_style=C_BORDER,
                padding=(0, 2),
                box=box.ROUNDED,
            )
        )

    def _handle_save_exit(self) -> None:
        save_config(self.config)
        get_console().print(
            Panel(
                Align.center(Text("[dim]Setup saved. Run [bold]aetheros setup --resume[/] to continue.[/dim]")),
                border_style=C_BORDER,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        self._running = False

    def _handle_cancel_dialog(self) -> bool:
        get_console().print(
            Panel(
                Align.center(
                    Text("Cancel setup? All progress will be lost.", style=C_WARN)
                ),
                border_style=C_WARN,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        get_console().print(_dim("  Press Y to confirm, any other key to continue"))
        key = _get_key()
        if key in ("y", "Y"):
            cp = SetupCheckpoint.load()
            if cp:
                cp.delete()
            get_console().print(
                Panel(
                    Align.center(Text("Setup cancelled.", style=C_DIM)),
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            self._running = False
            return True
        clear()
        self._render_step(self.steps[self._current_index])
        return False

    def _render_step(self, step: SetupStep) -> None:
        """Render a single step with premium OS-installer layout."""
        progress = make_step_progress(step.step_number, step.total_steps, step.title)
        content = step.render()
        can_back = self._current_index > 0
        can_next = step.validate()
        can_skip = not step.required

        # Check if we need text input mode
        is_text_input = isinstance(step, ProfileStep) and step._field_index < 2

        # Build nav with field count info for Tab/Shift+Tab
        nav = make_nav_bar(
            can_back=can_back,
            can_next=can_next,
            can_skip=can_skip,
            step_name=step.name,
        )

        # Keyboard hints bar
        hints = []
        if is_text_input:
            hints = [
                ("Enter", "Confirm"),
                ("Tab", "Next field"),
                ("Esc", "Cancel"),
            ]
        else:
            hints = [
                ("↑↓", "Navigate"),
                ("Enter", "Next"),
                ("Esc", "Cancel"),
            ]
            if can_skip:
                hints.append(("S", "Skip"))
            hints.extend([
                ("Ctrl+S", "Save"),
                ("Tab", "Next field"),
                ("Shift+Tab", "Prev field"),
            ])

        hint_bar = make_keyboard_hints(hints)

        get_console().print(progress)
        get_console().print()
        get_console().print(content)
        get_console().print()
        get_console().print(nav)
        get_console().print(hint_bar)
        get_console().print()

    def _wait_for_action(self, step: SetupStep) -> str:
        """Wait for a keypress and dispatch to the step handler.

        Supports Tab/Shift+Tab navigation between fields, Ctrl+S save,
        arrow navigation, and all standard actions.
        """
        if isinstance(step, (ProfileStep,)):
            if step._field_index < 2:
                return self._wait_for_text_input(step)

        while True:
            key = _get_key()
            if key == "ctrl_c":
                return self._handle_ctrl_c_dialog()
            elif key == "cancel":
                return self._handle_cancel_dialog() if not self._handle_cancel_dialog() else "cancel"
            elif key == "save":
                return "save"
            elif key == "tab":
                # Tab: advance to next field if multi-field step
                if hasattr(step, "_field_count") and step._field_count > 1:
                    step._field_index = (step._field_index + 1) % max(step._field_count, 1)
                    clear()
                    self._render_step(step)
                continue
            elif key == "back_tab":
                # Shift+Tab: go to previous field
                if hasattr(step, "_field_count") and step._field_count > 1:
                    step._field_index = (step._field_index - 1) % max(step._field_count, 1)
                    clear()
                    self._render_step(step)
                continue
            elif key in ("confirm", "right"):
                if step.validate() or not step.required:
                    return "confirm"
            elif key == "left" and self._current_index > 0:
                return "back"
            elif key in ("up", "down"):
                step.handle_action(key)
                clear()
                self._render_step(step)
                continue
            elif key == "backspace" and hasattr(step, "_filter"):
                step._filter = step._filter[:-1]
                step._selected = 0
                clear()
                self._render_step(step)
                continue
            elif key == "s":
                return "skip"
            elif key and len(key) == 1 and key.isprintable():
                if hasattr(step, "_filter"):
                    step._filter += key
                    step._selected = 0
                    clear()
                    self._render_step(step)
                    continue
                elif isinstance(step, FinishStep):
                    result = step.handle_action(key)
                    if result is not None:
                        return result
                elif isinstance(step, ReviewStep) and key == "e":
                    result = step.handle_action("edit")
                    if result and result.startswith("edit:"):
                        return result
                continue
            step_result = step.handle_action(key)
            if step_result and step_result.startswith("edit:"):
                return step_result
            clear()
            self._render_step(step)

    def _wait_for_text_input(self, step: SetupStep) -> str:
        """Prompt for text input using prompt_toolkit."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle

        if isinstance(step, ProfileStep):
            if step._field_index == 0:
                placeholder = "Enter your name"
                default = step._name
            else:
                placeholder = "Enter a username"
                default = step._username
        else:
            placeholder = "Enter value"
            default = ""

        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})

        get_console().print(
            Panel(
                Align.center(_dim("Press Esc to cancel, Tab to skip to nav")),
                border_style=C_NAV_BG,
                padding=(0, 1),
                box=box.SIMPLE,
                style="dim",
            )
        )

        session = PromptSession(style=pt_style)
        try:
            value = session.prompt(f" {_accent('▸')}  {placeholder}: ", default=default)
        except (EOFError, KeyboardInterrupt):
            return self._handle_ctrl_c_dialog()

        if not value:
            key = _get_key()
            if key == "ctrl_c":
                return self._handle_ctrl_c_dialog()
            elif key == "cancel":
                return self._handle_cancel_dialog() if not self._handle_cancel_dialog() else "cancel"
            elif key == "save":
                return "save"
            elif key == "left" and self._current_index > 0:
                return "back"
            return "confirm" if step.validate() else ""

        step.set_input(value)
        clear()
        self._render_step(step)
        return "confirm" if step.validate() else ""

    def _handle_ctrl_c_dialog(self) -> str:
        """Ctrl+C confirmation dialog — saves progress and exits."""
        get_console().print(
            Panel(
                Align.center(Text("Exit setup?", style=C_WARN)),
                border_style=C_WARN,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        get_console().print(_dim("  Press Y to exit (progress saved), N to continue"))
        key = _get_key()
        if key in ("y", "Y"):
            self.checkpoint.save(
                current_step=self._current_index,
                completed=self.checkpoint.state.get("completed_steps", []),
            )
            save_config(self.config)
            get_console().print(
                Panel(
                    Align.center(Text("[dim]Progress saved. Use [bold]--resume[/] to continue.[/dim]")),
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            self._running = False
            return "save_exit"
        clear()
        self._render_step(self.steps[self._current_index])
        return ""

    def _process_action(self, step: SetupStep, action: str) -> str | None:
        if action == "confirm":
            return "next"
        elif action == "back":
            return "back"
        elif action == "skip":
            return "skip"
        elif action == "save":
            return "save"
        elif action == "save_exit":
            return "save_exit"
        elif action == "cancel":
            return "cancel"
        elif action == "launch":
            return "launch"
        return None

    def _on_complete(self) -> None:
        """Setup complete — run initialization, then launch the selected mode."""
        self.checkpoint.delete()
        data = self.checkpoint.state.get("step_data", {}).get("finish", {})
        launch_choice = data.get("launch_choice", "1")

        # ── Phase 1: Initialize workspace + system ─────────────────
        get_console().print()
        get_console().print(
            Panel(
                Align.center(
                    Text("◆  Initializing Your AI Operating System  ◆", style=f"bold {C_PURPLE}"),
                    vertical="middle",
                ),
                border_style=C_PURPLE,
                padding=(1, 4),
                box=box.ROUNDED,
            )
        )
        from aetheros_cli.initialization_flow import run_full_initialization
        init_results = run_full_initialization(self.config)

        # ── Phase 2: Create agent identity ──────────────────────────
        from aetheros_cli.agent_creator import run_agent_creator
        identity = run_agent_creator(self.config)

        # ── Phase 3: Mark onboarding complete ───────────────────────
        self.config.setdefault("onboarding", {}).update({
            "setup_completed": True,
            "initialization_completed": True,
            "agent_created": True,
        })
        from aetheros_cli.config import save_config
        save_config(self.config)

        # ── Phase 4: Welcome dashboard (first launch) ───────────────
        from aetheros_cli.first_launch import show_welcome_dashboard, mark_dashboard_shown
        show_welcome_dashboard(self.config)
        mark_dashboard_shown(self.config)

        # ── Launch ──────────────────────────────────────────────────
        get_console().print()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text("◆  Setup Complete  ◆", style=f"bold {C_SUCCESS}"),
                        Text(""),
                        Text("Your AetherOS system is ready.", style=C_TEXT),
                    ),
                    vertical="middle",
                ),
                border_style=C_SUCCESS,
                padding=(2, 4),
                box=box.ROUNDED,
            )
        )

        if launch_choice == "1":
            get_console().print(_dim("  Launching terminal..."))
        elif launch_choice == "2":
            get_console().print(_dim("  Opening browser dashboard..."))
            try:
                import webbrowser
                webbrowser.open("http://localhost:8080")
            except Exception:
                pass
        elif launch_choice == "3":
            get_console().print(_dim("  Launching terminal + browser..."))
            try:
                import webbrowser
                webbrowser.open("http://localhost:8080")
            except Exception:
                pass


# =============================================================================
# Entry Point
# =============================================================================

def run_advanced_setup_wizard(args=None) -> None:
    """Entry point called from the CLI subcommand."""
    ensure_aetheros_home()
    backup_config()
    wizard = AdvancedSetupWizard(args)
    wizard.run()


def backup_config() -> None:
    """Back up config before modifying."""
    config_path = get_config_path()
    if config_path.exists():
        backup_path = config_path.with_suffix(
            f".yaml.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        try:
            shutil.copy2(config_path, backup_path)
        except Exception:
            pass
