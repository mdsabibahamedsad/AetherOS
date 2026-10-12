"""AetherOS Design System — skin/theme engine.

A data-driven skin system. Premium, minimal, dark-first.
Skins are defined as YAML files in ~/.aetheros/skins/ or as built-in presets.

SKIN YAML SCHEMA
================

All fields are optional. Missing values inherit from the ``default`` skin.

.. code-block:: yaml

    name: mytheme
    description: Short description

    colors:
      banner_title: "#e6edf3"
      banner_accent: "#58a6ff"
      banner_dim: "#8b949e"
      banner_text: "#e6edf3"
      ui_accent: "#58a6ff"
      ui_label: "#8b949e"
      ui_ok: "#57d2a0"
      ui_error: "#ff6b6b"
      ui_warn: "#ffc164"
      prompt: "#e6edf3"
      input_rule: "#30363d"
      response_border: "#58a6ff"
      status_bar_bg: "#0d1117"
      status_bar_text: "#8b949e"
      status_bar_strong: "#e6edf3"
      status_bar_dim: "#646a73"
      status_bar_good: "#57d2a0"
      status_bar_warn: "#ffc164"
      status_bar_bad: "#ff6b6b"
      status_bar_critical: "#ff6b6b"
      session_label: "#58a6ff"
      session_border: "#646a73"

    spinner:
      waiting_frames: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
      thinking_frames: ["◌", "◯", "◌"]
      thinking_verbs: ["thinking", "reasoning", "planning", "analyzing"]

    branding:
      agent_name: "AetherOS"
      welcome: "Ready."
      goodbye: "Goodbye."
      response_label: " AetherOS "
      prompt_symbol: ">"
      help_header: "Commands"

    tool_prefix: " "

    tool_emojis:
      terminal: "$"
      web_search: "?"
      read_file: "."
      write_file: "+"
      patch: "~"

USAGE
=====

.. code-block:: python

    from aetheros_cli.skin_engine import get_active_skin, list_skins, set_active_skin

    skin = get_active_skin()
    print(skin.colors.get("banner_title", "#e6edf3"))
    print(skin.get_branding("agent_name", "AetherOS"))

    set_active_skin("mono")
    set_active_skin("mytheme")

BUILT-IN SKINS
==============

- ``default`` — AetherOS classic dark (white, gray, blue, cyan, purple)
- ``mono``    — Clean grayscale monochrome
- ``slate``   — Cool blue developer-focused theme
- ``daylight`` — Light background theme
- ``warm-lightmode`` — Warm light theme

USER SKINS
==========

Drop a YAML file in ``~/.aetheros/skins/<name>.yaml`` following the schema above.
Activate with ``/skin <name>`` in the CLI or ``display.skin: <name>`` in config.yaml.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


# =============================================================================
# Skin data structure
# =============================================================================

@dataclass
class SkinConfig:
    """Complete skin configuration."""
    name: str
    description: str = ""
    colors: Dict[str, str] = field(default_factory=dict)
    spinner: Dict[str, Any] = field(default_factory=dict)
    branding: Dict[str, str] = field(default_factory=dict)
    tool_prefix: str = " "
    tool_emojis: Dict[str, str] = field(default_factory=dict)  # per-tool emoji overrides

    def get_color(self, key: str, fallback: str = "") -> str:
        """Get a color value with fallback."""
        return self.colors.get(key, fallback)

    def get_spinner_wings(self) -> List[Tuple[str, str]]:
        """Get spinner wing pairs, or empty list if none."""
        raw = self.spinner.get("wings", [])
        result = []
        for pair in raw:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                result.append((str(pair[0]), str(pair[1])))
        return result

    def get_branding(self, key: str, fallback: str = "") -> str:
        """Get a branding value with fallback."""
        return self.branding.get(key, fallback)


# =============================================================================
# Built-in skin definitions
# =============================================================================

_BUILTIN_SKINS: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "default",
        "description": "AetherOS classic — dark, minimal, premium",
        "colors": {
            "banner_title": "#e6edf3",
            "banner_accent": "#58a6ff",
            "banner_dim": "#8b949e",
            "banner_text": "#e6edf3",
            "ui_accent": "#58a6ff",
            "ui_label": "#8b949e",
            "ui_ok": "#57d2a0",
            "ui_error": "#ff6b6b",
            "ui_warn": "#ffc164",
            "prompt": "#e6edf3",
            "input_rule": "#30363d",
            "response_border": "#58a6ff",
            "status_bar_bg": "#0d1117",
            "status_bar_text": "#8b949e",
            "status_bar_strong": "#e6edf3",
            "status_bar_dim": "#646a73",
            "status_bar_good": "#57d2a0",
            "status_bar_warn": "#ffc164",
            "status_bar_bad": "#ff6b6b",
            "status_bar_critical": "#ff6b6b",
            "status_bar_active": "#39d2c0",
            "session_label": "#58a6ff",
            "session_border": "#646a73",
            "voice_status_bg": "#0d1117",
            "selection_bg": "#1e2430",
            "completion_menu_bg": "#0d1117",
            "completion_menu_current_bg": "#1e2430",
            "completion_menu_meta_bg": "#0d1117",
            "completion_menu_meta_current_bg": "#1e2430",
        },
        "spinner": {},
        "branding": {
            "agent_name": "AetherOS",
            "welcome": "Ready.",
            "goodbye": "Goodbye.",
            "response_label": " AetherOS ",
            "prompt_symbol": ">",
            "help_header": "Commands",
        },
        "tool_prefix": " ",
    },
    "mono": {
        "name": "mono",
        "description": "Monochrome — clean grayscale",
        "colors": {
            "banner_title": "#e6edf3",
            "banner_accent": "#cccccc",
            "banner_dim": "#777777",
            "banner_text": "#c9d1d9",
            "ui_accent": "#aaaaaa",
            "ui_label": "#888888",
            "ui_ok": "#aaaaaa",
            "ui_error": "#cccccc",
            "ui_warn": "#999999",
            "prompt": "#c9d1d9",
            "input_rule": "#444444",
            "response_border": "#aaaaaa",
            "status_bar_bg": "#111111",
            "status_bar_text": "#999999",
            "status_bar_strong": "#e6edf3",
            "status_bar_dim": "#555555",
            "status_bar_good": "#bbbbbb",
            "status_bar_warn": "#aaaaaa",
            "status_bar_bad": "#cccccc",
            "status_bar_critical": "#e6edf3",
            "status_bar_active": "#bbbbbb",
            "session_label": "#888888",
            "session_border": "#555555",
            "voice_status_bg": "#111111",
            "selection_bg": "#222222",
            "completion_menu_bg": "#111111",
            "completion_menu_current_bg": "#222222",
            "completion_menu_meta_bg": "#111111",
            "completion_menu_meta_current_bg": "#222222",
        },
        "spinner": {},
        "branding": {
            "agent_name": "AetherOS",
            "welcome": "Ready.",
            "goodbye": "Goodbye.",
            "response_label": " AetherOS ",
            "prompt_symbol": ">",
            "help_header": "Commands",
        },
        "tool_prefix": " ",
    },
    "slate": {
        "name": "slate",
        "description": "Cool blue — developer-focused",
        "colors": {
            "banner_title": "#e6edf3",
            "banner_accent": "#7eb8f6",
            "banner_dim": "#4b5563",
            "banner_text": "#c9d1d9",
            "ui_accent": "#7eb8f6",
            "ui_label": "#8EA8FF",
            "ui_ok": "#63D0A6",
            "ui_error": "#F7A072",
            "ui_warn": "#e6a855",
            "prompt": "#c9d1d9",
            "input_rule": "#4169e1",
            "response_border": "#7eb8f6",
            "status_bar_bg": "#151C2F",
            "status_bar_text": "#C9D1D9",
            "status_bar_strong": "#7EB8F6",
            "status_bar_dim": "#4B5563",
            "status_bar_good": "#63D0A6",
            "status_bar_warn": "#E6A855",
            "status_bar_bad": "#F7A072",
            "status_bar_critical": "#FF7A7A",
            "status_bar_active": "#63D0A6",
            "session_label": "#7eb8f6",
            "session_border": "#4b5563",
            "voice_status_bg": "#151C2F",
            "selection_bg": "#1E2A4A",
            "completion_menu_bg": "#151C2F",
            "completion_menu_current_bg": "#1E2A4A",
            "completion_menu_meta_bg": "#151C2F",
            "completion_menu_meta_current_bg": "#1E2A4A",
        },
        "spinner": {},
        "branding": {
            "agent_name": "AetherOS",
            "welcome": "Ready.",
            "goodbye": "Goodbye.",
            "response_label": " AetherOS ",
            "prompt_symbol": ">",
            "help_header": "Commands",
        },
        "tool_prefix": " ",
    },
    "daylight": {
        "name": "daylight",
        "description": "Light theme for bright terminals",
        "colors": {
            "banner_title": "#0F172A",
            "banner_accent": "#2563EB",
            "banner_dim": "#475569",
            "banner_text": "#111827",
            "ui_accent": "#2563EB",
            "ui_label": "#0F766E",
            "ui_ok": "#15803D",
            "ui_error": "#B91C1C",
            "ui_warn": "#B45309",
            "prompt": "#111827",
            "input_rule": "#93C5FD",
            "response_border": "#2563EB",
            "session_label": "#1D4ED8",
            "session_border": "#64748B",
            "status_bar_bg": "#E5EDF8",
            "status_bar_active": "#0F766E",
            "voice_status_bg": "#E5EDF8",
            "completion_menu_bg": "#F8FAFC",
            "completion_menu_current_bg": "#DBEAFE",
            "completion_menu_meta_bg": "#EEF2FF",
            "completion_menu_meta_current_bg": "#BFDBFE",
        },
        "spinner": {},
        "branding": {
            "agent_name": "AetherOS",
            "welcome": "Ready.",
            "goodbye": "Goodbye.",
            "response_label": " AetherOS ",
            "prompt_symbol": ">",
            "help_header": "Commands",
        },
        "tool_prefix": " ",
    },
    "warm-lightmode": {
        "name": "warm-lightmode",
        "description": "Warm light mode",
        "colors": {
            "banner_title": "#5C3D11",
            "banner_accent": "#8B4513",
            "banner_dim": "#8B7355",
            "banner_text": "#2C1810",
            "ui_accent": "#8B4513",
            "ui_label": "#5C3D11",
            "ui_ok": "#2E7D32",
            "ui_error": "#C62828",
            "ui_warn": "#E65100",
            "prompt": "#2C1810",
            "input_rule": "#8B6914",
            "response_border": "#8B6914",
            "session_label": "#5C3D11",
            "session_border": "#A0845C",
            "status_bar_bg": "#F5F0E8",
            "status_bar_active": "#2E7D32",
            "voice_status_bg": "#F5F0E8",
            "completion_menu_bg": "#F5EFE0",
            "completion_menu_current_bg": "#E8DCC8",
            "completion_menu_meta_bg": "#F0E8D8",
            "completion_menu_meta_current_bg": "#DFCFB0",
        },
        "spinner": {},
        "branding": {
            "agent_name": "AetherOS",
            "welcome": "Ready.",
            "goodbye": "Goodbye.",
            "response_label": " AetherOS ",
            "prompt_symbol": ">",
            "help_header": "Commands",
        },
        "tool_prefix": " ",
    },
}


# =============================================================================
# Skin loading and management
# =============================================================================

_active_skin: Optional[SkinConfig] = None
_active_skin_name: str = "default"


def _skins_dir() -> Path:
    """User skins directory."""
    return get_aetheros_home() / "skins"


def _load_skin_from_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Load a skin definition from a YAML file."""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "name" in data:
            return data
    except Exception as e:
        logger.debug("Failed to load skin from %s: %s", path, e)
    return None


def _mapping_or_empty(value: Any, *, section: str, skin_name: str) -> Dict[str, Any]:
    """Return a mapping value or an empty dict when the section type is invalid."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    logger.warning(
        "Skin '%s' has invalid '%s' section type (%s); ignoring section",
        skin_name,
        section,
        type(value).__name__,
    )
    return {}


def _build_skin_config(data: Dict[str, Any]) -> SkinConfig:
    """Build a SkinConfig from a raw dict (built-in or loaded from YAML)."""
    # Start with default values as base for missing keys
    default = _BUILTIN_SKINS["default"]
    skin_name = str(data.get("name", "unknown"))
    color_overrides = _mapping_or_empty(data.get("colors"), section="colors", skin_name=skin_name)
    spinner_overrides = _mapping_or_empty(data.get("spinner"), section="spinner", skin_name=skin_name)
    branding_overrides = _mapping_or_empty(data.get("branding"), section="branding", skin_name=skin_name)
    emoji_overrides = _mapping_or_empty(data.get("tool_emojis"), section="tool_emojis", skin_name=skin_name)

    colors = dict(default.get("colors", {}))
    colors.update(color_overrides)
    spinner = dict(default.get("spinner", {}))
    spinner.update(spinner_overrides)
    branding = dict(default.get("branding", {}))
    branding.update(branding_overrides)

    return SkinConfig(
        name=skin_name,
        description=data.get("description", ""),
        colors=colors,
        spinner=spinner,
        branding=branding,
        tool_prefix=data.get("tool_prefix", default.get("tool_prefix", " ")),
        tool_emojis=emoji_overrides,
    )


def list_skins() -> List[Dict[str, str]]:
    """List all available skins (built-in + user-installed).

    Returns list of {"name": ..., "description": ..., "source": "builtin"|"user"}.
    """
    result = []
    for name, data in _BUILTIN_SKINS.items():
        result.append({
            "name": name,
            "description": data.get("description", ""),
            "source": "builtin",
        })

    skins_path = _skins_dir()
    if skins_path.is_dir():
        for f in sorted(skins_path.glob("*.yaml")):
            data = _load_skin_from_yaml(f)
            if data:
                skin_name = data.get("name", f.stem)
                # Skip if it shadows a built-in
                if any(s["name"] == skin_name for s in result):
                    continue
                result.append({
                    "name": skin_name,
                    "description": data.get("description", ""),
                    "source": "user",
                })

    return result


def load_skin(name: str) -> SkinConfig:
    """Load a skin by name. Checks user skins first, then built-in."""
    # Check user skins directory
    skins_path = _skins_dir()
    user_file = skins_path / f"{name}.yaml"
    if user_file.is_file():
        data = _load_skin_from_yaml(user_file)
        if data:
            return _build_skin_config(data)

    # Check built-in skins
    if name in _BUILTIN_SKINS:
        return _build_skin_config(_BUILTIN_SKINS[name])

    # Fallback to default
    logger.warning("Skin '%s' not found, using default", name)
    return _build_skin_config(_BUILTIN_SKINS["default"])


def get_active_skin() -> SkinConfig:
    """Get the currently active skin config (cached)."""
    global _active_skin
    if _active_skin is None:
        _active_skin = load_skin(_active_skin_name)
    return _active_skin


def set_active_skin(name: str) -> SkinConfig:
    """Switch the active skin. Returns the new SkinConfig."""
    global _active_skin, _active_skin_name
    _active_skin_name = name
    _active_skin = load_skin(name)
    return _active_skin


def get_active_skin_name() -> str:
    """Get the name of the currently active skin."""
    return _active_skin_name


def init_skin_from_config(config: dict) -> None:
    """Initialize the active skin from CLI config at startup.

    Call this once during CLI init with the loaded config dict.
    """
    display = config.get("display") or {}
    if not isinstance(display, dict):
        display = {}
    skin_name = display.get("skin", "default")
    if isinstance(skin_name, str) and skin_name.strip():
        set_active_skin(skin_name.strip())
    else:
        set_active_skin("default")


# =============================================================================
# Convenience helpers for CLI modules
# =============================================================================


def get_active_prompt_symbol(fallback: str = ">") -> str:
    """Return the interactive prompt symbol with a single trailing space.

    Skins store ``prompt_symbol`` as a bare token (no spaces). The trailing
    space is appended here so callers can drop it straight into a rendered
    prompt without hand-rolling whitespace.
    """
    try:
        raw = get_active_skin().get_branding("prompt_symbol", fallback)
    except Exception:
        raw = fallback

    cleaned = (raw or fallback).strip()

    return f"{cleaned or fallback.strip()} "



def get_active_help_header(fallback: str = "Commands") -> str:
    """Get the /help header from the active skin."""
    try:
        return get_active_skin().get_branding("help_header", fallback)
    except Exception:
        return fallback



def get_active_goodbye(fallback: str = "Goodbye.") -> str:
    """Get the goodbye line from the active skin."""
    try:
        return get_active_skin().get_branding("goodbye", fallback)
    except Exception:
        return fallback



def get_prompt_toolkit_style_overrides() -> Dict[str, str]:
    """Return prompt_toolkit style overrides derived from the active skin.

    These are layered on top of the CLI's base TUI style so /skin can refresh
    the live prompt_toolkit UI immediately without rebuilding the app.
    """
    try:
        skin = get_active_skin()
    except Exception:
        return {}

    # Input/prompt: leave unset by default so the typed text inherits
    # the terminal's foreground color (readable in both light and dark
    # color schemes).  Skins can opt into a colored prompt by setting
    # `prompt` explicitly in their YAML.
    prompt = skin.get_color("prompt", "")
    input_rule = skin.get_color("input_rule", "#30363d")
    title = skin.get_color("banner_title", "#e6edf3")
    text = skin.get_color("banner_text", "#e6edf3")
    dim = skin.get_color("banner_dim", "#646a73")
    label = skin.get_color("ui_label", "#8b949e")
    warn = skin.get_color("ui_warn", "#ffc164")
    error = skin.get_color("ui_error", "#ff6b6b")
    status_bg = skin.get_color("status_bar_bg", "#0d1117")
    status_text = skin.get_color("status_bar_text", "#8b949e")
    status_strong = skin.get_color("status_bar_strong", "#e6edf3")
    status_dim = skin.get_color("status_bar_dim", "#646a73")
    status_good = skin.get_color("status_bar_good", skin.get_color("ui_ok", "#57d2a0"))
    status_warn = skin.get_color("status_bar_warn", warn)
    status_bad = skin.get_color("status_bar_bad", skin.get_color("banner_accent", "#ff6b6b"))
    status_critical = skin.get_color("status_bar_critical", error)
    status_active = skin.get_color("status_bar_active", "#39d2c0")
    voice_bg = skin.get_color("voice_status_bg", status_bg)
    menu_bg = skin.get_color("completion_menu_bg", "#0d1117")
    menu_current_bg = skin.get_color("completion_menu_current_bg", "#1e2430")
    menu_meta_bg = skin.get_color("completion_menu_meta_bg", menu_bg)
    menu_meta_current_bg = skin.get_color("completion_menu_meta_current_bg", menu_current_bg)

    return {
        # Typed input always uses terminal default fg/bg so it's
        # readable in both light and dark Terminal.app modes.  The
        # skin's `prompt` color (if any) only styles the prompt symbol,
        # NOT the user's typed text.
        "input-area": "",
        "placeholder": f"{dim} italic",
        "prompt": prompt,
        "prompt-working": f"{dim} italic",
        "hint": f"{dim} italic",
        "status-bar": f"bg:{status_bg} {status_text}",
        "status-bar-strong": f"bg:{status_bg} {status_strong} bold",
        "status-bar-dim": f"bg:{status_bg} {status_dim}",
        "status-bar-good": f"bg:{status_bg} {status_good} bold",
        "status-bar-warn": f"bg:{status_bg} {status_warn} bold",
        "status-bar-bad": f"bg:{status_bg} {status_bad} bold",
        "status-bar-critical": f"bg:{status_bg} {status_critical} bold",
        "status-bar-active": f"bg:{status_bg} {status_active} bold",
        "input-rule": input_rule,
        "image-badge": f"{label} bold",
        "completion-menu": f"bg:{menu_bg} {text}",
        "completion-menu.completion": f"bg:{menu_bg} {text}",
        "completion-menu.completion.current": f"bg:{menu_current_bg} {title}",
        "completion-menu.meta.completion": f"bg:{menu_meta_bg} {dim}",
        "completion-menu.meta.completion.current": f"bg:{menu_meta_current_bg} {label}",
        "clarify-border": input_rule,
        "clarify-title": f"{title} bold",
        "clarify-question": f"{text} bold",
        "clarify-choice": dim,
        "clarify-selected": f"{title} bold",
        "clarify-active-other": f"{title} italic",
        "clarify-countdown": input_rule,
        "sudo-prompt": f"{error} bold",
        "sudo-border": input_rule,
        "sudo-title": f"{error} bold",
        "sudo-text": text,
        "approval-border": input_rule,
        "approval-title": f"{warn} bold",
        "approval-desc": f"{text} bold",
        "approval-cmd": f"{dim} italic",
        "approval-choice": dim,
        "approval-selected": f"{title} bold",
        "voice-status": f"bg:{voice_bg} {label}",
        "voice-status-recording": f"bg:{voice_bg} {error} bold",
    }
