"""Theme manager — install, preview, activate, and manage themes from the hub."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore
from hub.models import HubCategory

logger = logging.getLogger(__name__)


BUILTIN_THEMES: list[dict] = [
    {"id": "theme_dark", "name": "Dark", "description": "Classic dark theme — easy on the eyes",
     "type": "dark", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_light", "name": "Light", "description": "Clean light theme for bright environments",
     "type": "light", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_glass", "name": "Glass", "description": "Frosted glass effect with blur and transparency",
     "type": "glass", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_minimal", "name": "Minimal", "description": "Bare essentials — maximum focus, minimum chrome",
     "type": "minimal", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_cyberpunk", "name": "Cyberpunk", "description": "Neon-soaked cyberpunk aesthetic with vibrant glow",
     "type": "cyberpunk", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_nord", "name": "Nord", "description": "Arctic, bluish arctic theme — calm and readable",
     "type": "nord", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_dracula", "name": "Dracula", "description": "Dark vampire-themed syntax highlighting",
     "type": "dracula", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_catppuccin", "name": "Catppuccin", "description": "Soothing pastel theme with warm tones",
     "type": "catppuccin", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_solarized", "name": "Solarized", "description": "Precision color palette for day/night work",
     "type": "solarized", "author": "Aetheros", "version": "1.0.0", "official": True},
    {"id": "theme_mono", "name": "Monochrome", "description": "Clean grayscale monochrome theme",
     "type": "mono", "author": "Aetheros", "version": "1.0.0", "official": True, "builtin": True},
    {"id": "theme_slate", "name": "Slate", "description": "Cool blue developer-focused theme",
     "type": "slate", "author": "Aetheros", "version": "1.0.0", "official": True, "builtin": True},
    {"id": "theme_ares", "name": "Ares", "description": "Crimson/bronze war-god theme",
     "type": "ares", "author": "Aetheros", "version": "1.0.0", "official": True, "builtin": True},
]


class ThemeManager:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self.themes_dir = get_aetheros_home() / "themes"
        self.skins_dir = get_aetheros_home() / "skins"
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        self.skins_dir.mkdir(parents=True, exist_ok=True)

    def get_catalog(self) -> list[dict]:
        return list(BUILTIN_THEMES)

    def get_theme(self, theme_id: str) -> Optional[dict]:
        for t in BUILTIN_THEMES:
            if t["id"] == theme_id:
                return dict(t)
        from aetheros_cli.skin_engine import load_skin
        try:
            skin = load_skin(theme_id.replace("theme_", ""))
            if skin:
                return {"id": theme_id, "name": skin.name, "description": "Custom skin",
                        "type": "custom", "author": "User", "version": "1.0.0", "loaded": True}
        except Exception:
            pass
        return None

    def install(self, theme_id: str) -> dict:
        info = self.get_theme(theme_id)
        if not info:
            return {"success": False, "error": f"Theme {theme_id} not found"}
        if info.get("builtin"):
            self.store.install_item(theme_id, info["name"], "themes",
                                    info.get("version", "1.0.0"),
                                    description=info.get("description", ""),
                                    author=info.get("author", "Aetheros"),
                                    tags=[info.get("type", "")])
            return {"success": True, "theme_id": theme_id, "builtin": True}
        theme_dir = self.themes_dir / theme_id
        theme_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"name": info["name"], "type": info.get("type", "custom"),
                     "version": info.get("version", "1.0.0"),
                     "description": info.get("description", ""),
                     "author": info.get("author", "Aetheros")}
        with open(theme_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        self.store.install_item(theme_id, info["name"], "themes",
                                info.get("version", "1.0.0"),
                                description=info.get("description", ""),
                                author=info.get("author", "Aetheros"),
                                tags=[info.get("type", "")],
                                manifest=manifest,
                                install_path=str(theme_dir))
        return {"success": True, "theme_id": theme_id, "path": str(theme_dir)}

    def activate(self, theme_id: str) -> dict:
        info = self.get_theme(theme_id)
        if not info:
            return {"success": False, "error": f"Theme {theme_id} not found"}
        try:
            from aetheros_cli.skin_engine import set_active_skin
            skin_name = theme_id.replace("theme_", "")
            set_active_skin(skin_name)
            self.store.set_setting("active_theme", theme_id)
            logger.info("Activated theme: %s", theme_id)
            return {"success": True, "theme_id": theme_id, "skin": skin_name}
        except Exception as e:
            from cli import _cprint
            _cprint(f"  To activate, use: /skin {theme_id.replace('theme_', '')}")
            return {"success": True, "theme_id": theme_id, "note": "Use /skin command"}

    def list_installed(self) -> list[dict]:
        items = self.store.get_installed("themes")
        for t in BUILTIN_THEMES:
            if not any(i["id"] == t["id"] for i in items):
                items.append({
                    "id": t["id"], "name": t["name"],
                    "description": t.get("description", ""),
                    "version": t.get("version", "1.0.0"),
                    "author": t.get("author", ""),
                    "category": "themes",
                    "enabled": 1, "compatible": 1,
                })
        return items

    def remove(self, theme_id: str) -> dict:
        theme_dir = self.themes_dir / theme_id
        if theme_dir.exists():
            shutil.rmtree(theme_dir, ignore_errors=True)
        self.store.remove_item(theme_id)
        return {"success": True}

    def get_active(self) -> Optional[str]:
        return self.store.get_setting("active_theme", "theme_dark")
