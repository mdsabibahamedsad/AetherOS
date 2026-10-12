"""
Theme Engine for AetherOS
=========================

Theme system supporting dark, light, and custom themes with CSS variables,
animations, fonts, icons, layouts, and window effects.

Usage::

    from aetheros_developer_platform.theme_engine import ThemeManager

    manager = ThemeManager()
    manager.set_theme("dark")
    css_vars = manager.get_css_variables()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """Theme modes."""
    DARK = "dark"
    LIGHT = "light"
    CUSTOM = "custom"
    SYSTEM = "system"


@dataclass
class ThemeColors:
    """Theme color definitions."""
    primary: str = "#007ACC"
    secondary: str = "#1E1E1E"
    background: str = "#FFFFFF"
    surface: str = "#F5F5F5"
    text: str = "#000000"
    text_secondary: str = "#666666"
    border: str = "#E0E0E0"
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#F44336"
    info: str = "#2196F3"
    muted: str = "#9E9E9E"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "background": self.background,
            "surface": self.surface,
            "text": self.text,
            "text-secondary": self.text_secondary,
            "border": self.border,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "info": self.info,
            "muted": self.muted,
        }


@dataclass
class ThemeFonts:
    """Theme font definitions."""
    primary: str = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    mono: str = "JetBrains Mono, Fira Code, monospace"
    size_xs: str = "0.75rem"
    size_sm: str = "0.875rem"
    size_base: str = "1rem"
    size_lg: str = "1.125rem"
    size_xl: str = "1.25rem"
    size_2xl: str = "1.5rem"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "primary": self.primary,
            "mono": self.mono,
            "size-xs": self.size_xs,
            "size-sm": self.size_sm,
            "size-base": self.size_base,
            "size-lg": self.size_lg,
            "size-xl": self.size_xl,
            "size-2xl": self.size_2xl,
        }


@dataclass
class ThemeSpacing:
    """Theme spacing definitions."""
    unit: int = 4
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"
    radius: int = 8
    radius_sm: str = "4px"
    radius_md: str = "8px"
    radius_lg: str = "12px"
    radius_full: str = "9999px"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "unit": self.unit,
            "xs": self.xs,
            "sm": self.sm,
            "md": self.md,
            "lg": self.lg,
            "xl": self.xl,
            "radius": self.radius,
            "radius-sm": self.radius_sm,
            "radius-md": self.radius_md,
            "radius-lg": self.radius_lg,
            "radius-full": self.radius_full,
        }


@dataclass
class ThemeAnimations:
    """Theme animation definitions."""
    duration_fast: str = "0.1s"
    duration_normal: str = "0.2s"
    duration_slow: str = "0.3s"
    easing: str = "ease-in-out"
    easing_in: str = "ease-in"
    easing_out: str = "ease-out"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "duration-fast": self.duration_fast,
            "duration-normal": self.duration_normal,
            "duration-slow": self.duration_slow,
            "easing": self.easing,
            "easing-in": self.easing_in,
            "easing-out": self.easing_out,
        }


@dataclass
class ThemeConfig:
    """Complete theme configuration."""
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    mode: ThemeMode = ThemeMode.LIGHT
    colors: ThemeColors = field(default_factory=ThemeColors)
    fonts: ThemeFonts = field(default_factory=ThemeFonts)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    animations: ThemeAnimations = field(default_factory=ThemeAnimations)
    css_variables: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "mode": self.mode.value,
            "colors": self.colors.to_dict(),
            "fonts": self.fonts.to_dict(),
            "spacing": self.spacing.to_dict(),
            "animations": self.animations.to_dict(),
            "css_variables": self.css_variables,
            "metadata": self.metadata,
        }

    def to_css_variables(self) -> str:
        """Generate CSS variables string."""
        lines = [":root {"]

        # Colors
        for key, value in self.colors.to_dict().items():
            lines.append(f"  --color-{key}: {value};")

        # Fonts
        for key, value in self.fonts.to_dict().items():
            lines.append(f"  --font-{key}: {value};")

        # Spacing
        for key, value in self.spacing.to_dict().items():
            if isinstance(value, int):
                lines.append(f"  --spacing-{key}: {value}px;")
            else:
                lines.append(f"  --spacing-{key}: {value};")

        # Animations
        for key, value in self.animations.to_dict().items():
            lines.append(f"  --animation-{key}: {value};")

        # Custom CSS variables
        for key, value in self.css_variables.items():
            lines.append(f"  --{key}: {value};")

        lines.append("}")
        return "\n".join(lines)


# Built-in themes
DARK_THEME = ThemeConfig(
    name="dark",
    description="Dark theme for AetherOS",
    author="AetherOS",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        primary="#007ACC",
        secondary="#2D2D2D",
        background="#1E1E1E",
        surface="#252526",
        text="#FFFFFF",
        text_secondary="#CCCCCC",
        border="#3C3C3C",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        info="#2196F3",
        muted="#666666",
    ),
)

LIGHT_THEME = ThemeConfig(
    name="light",
    description="Light theme for AetherOS",
    author="AetherOS",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(
        primary="#007ACC",
        secondary="#F5F5F5",
        background="#FFFFFF",
        surface="#F5F5F5",
        text="#000000",
        text_secondary="#666666",
        border="#E0E0E0",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        info="#2196F3",
        muted="#9E9E9E",
    ),
)

MONO_THEME = ThemeConfig(
    name="mono",
    description="Monochrome theme for AetherOS",
    author="AetherOS",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(
        primary="#000000",
        secondary="#333333",
        background="#FFFFFF",
        surface="#F5F5F5",
        text="#000000",
        text_secondary="#666666",
        border="#CCCCCC",
        success="#000000",
        warning="#666666",
        error="#000000",
        info="#333333",
        muted="#999999",
    ),
)

CYBERPUNK_THEME = ThemeConfig(
    name="cyberpunk",
    description="Cyberpunk neon theme",
    author="AetherOS",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        primary="#FF00FF",
        secondary="#00FFFF",
        background="#0A0A0A",
        surface="#1A1A2E",
        text="#00FFFF",
        text_secondary="#FF00FF",
        border="#FF00FF",
        success="#00FF00",
        warning="#FFFF00",
        error="#FF0000",
        info="#00FFFF",
        muted="#666666",
    ),
    css_variables={
        "glow-primary": "0 0 10px #FF00FF",
        "glow-secondary": "0 0 10px #00FFFF",
    },
)


class ThemeManager:
    """Manages themes for AetherOS.

    Usage::

        manager = ThemeManager()
        manager.set_theme("dark")
        css_vars = manager.get_css_variables()
        manager.register_theme(custom_theme)
    """

    def __init__(self) -> None:
        self._themes: Dict[str, ThemeConfig] = {}
        self._current_theme: Optional[ThemeConfig] = None
        self._listeners: List[Callable[[ThemeConfig], None]] = []

        # Register built-in themes
        self.register_theme(DARK_THEME)
        self.register_theme(LIGHT_THEME)
        self.register_theme(MONO_THEME)
        self.register_theme(CYBERPUNK_THEME)

        # Set default theme
        self._current_theme = LIGHT_THEME

    @property
    def current_theme(self) -> ThemeConfig:
        """Return the current theme."""
        return self._current_theme or LIGHT_THEME

    def register_theme(self, theme: ThemeConfig) -> None:
        """Register a theme."""
        self._themes[theme.name] = theme
        logger.info("Registered theme: %s", theme.name)

    def unregister_theme(self, name: str) -> bool:
        """Unregister a theme."""
        if name in self._themes:
            del self._themes[name]
            return True
        return False

    def set_theme(self, name: str) -> bool:
        """Set the current theme by name."""
        theme = self._themes.get(name)
        if theme:
            self._current_theme = theme
            self._notify_listeners(theme)
            return True
        return False

    def get_theme(self, name: str) -> Optional[ThemeConfig]:
        """Get a theme by name."""
        return self._themes.get(name)

    def list_themes(self) -> List[ThemeConfig]:
        """List all registered themes."""
        return list(self._themes.values())

    def get_css_variables(self) -> str:
        """Get CSS variables for the current theme."""
        return self._current_theme.to_css_variables() if self._current_theme else ""

    def get_css_variables_dict(self) -> Dict[str, str]:
        """Get CSS variables as a dictionary."""
        if not self._current_theme:
            return {}

        vars_dict = {}
        vars_dict.update(self._current_theme.colors.to_dict())
        vars_dict.update(self._current_theme.fonts.to_dict())
        vars_dict.update({
            k: str(v) for k, v in self._current_theme.spacing.to_dict().items()
        })
        vars_dict.update(self._current_theme.animations.to_dict())
        vars_dict.update(self._current_theme.css_variables)
        return vars_dict

    def on_theme_change(self, callback: Callable[[ThemeConfig], None]) -> None:
        """Register a theme change listener."""
        self._listeners.append(callback)

    def _notify_listeners(self, theme: ThemeConfig) -> None:
        """Notify all listeners of a theme change."""
        for listener in self._listeners:
            try:
                listener(theme)
            except Exception as exc:
                logger.warning("Theme listener error: %s", exc)

    def export_theme(self, name: str, path: Path) -> bool:
        """Export a theme to a JSON file."""
        theme = self._themes.get(name)
        if not theme:
            return False

        try:
            path.write_text(json.dumps(theme.to_dict(), indent=2), encoding="utf-8")
            return True
        except Exception as exc:
            logger.error("Failed to export theme: %s", exc)
            return False

    def import_theme(self, path: Path) -> Optional[ThemeConfig]:
        """Import a theme from a JSON file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            colors = ThemeColors(**data.get("colors", {}))
            fonts = ThemeFonts(**data.get("fonts", {}))
            spacing = ThemeSpacing(**data.get("spacing", {}))
            animations = ThemeAnimations(**data.get("animations", {}))

            theme = ThemeConfig(
                name=data["name"],
                description=data.get("description", ""),
                author=data.get("author", ""),
                version=data.get("version", "1.0.0"),
                mode=ThemeMode(data.get("mode", "light")),
                colors=colors,
                fonts=fonts,
                spacing=spacing,
                animations=animations,
                css_variables=data.get("css_variables", {}),
            )

            self.register_theme(theme)
            return theme
        except Exception as exc:
            logger.error("Failed to import theme: %s", exc)
            return None


# Global theme manager
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Return the global ThemeManager singleton."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
