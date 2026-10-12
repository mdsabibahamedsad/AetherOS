"""Icon pack manager — install and switch icon packs for the UI."""

from __future__ import annotations

import json
import logging
import shutil
from typing import Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore

logger = logging.getLogger(__name__)


ICON_PACKS: list[dict] = [
    {"id": "icons_material", "name": "Material Icons", "description": "Google Material Design icons",
     "author": "Google", "version": "1.0.0", "official": True, "count": 2500},
    {"id": "icons_lucide", "name": "Lucide", "description": "Simple, clean SVG icon library",
     "author": "Lucide", "version": "1.0.0", "official": True, "count": 1200},
    {"id": "icons_heroicons", "name": "Heroicons", "description": "Beautiful hand-crafted SVG icons by Tailwind",
     "author": "Tailwind Labs", "version": "1.0.0", "official": True, "count": 800},
    {"id": "icons_tabler", "name": "Tabler Icons", "description": "Over 4900 customizable SVG icons",
     "author": "Tabler", "version": "1.0.0", "official": True, "count": 4900},
    {"id": "icons_phosphor", "name": "Phosphor", "description": "Flexible icon family with 6 styles",
     "author": "Phosphor", "version": "1.0.0", "official": True, "count": 1800},
]


class IconPackManager:
    def __init__(self, store=None):
        self.store = store or HubStore()
        self.icons_dir = get_aetheros_home() / "icons"
        self.icons_dir.mkdir(parents=True, exist_ok=True)

    def get_catalog(self) -> list[dict]:
        return list(ICON_PACKS)

    def get_pack(self, pack_id: str) -> Optional[dict]:
        for p in ICON_PACKS:
            if p["id"] == pack_id:
                return dict(p)
        return None

    def install(self, pack_id: str) -> dict:
        info = self.get_pack(pack_id)
        if not info:
            return {"success": False, "error": f"Icon pack {pack_id} not found"}
        self.store.install_item(pack_id, info["name"], "icon_packs",
                                info.get("version", "1.0.0"),
                                description=info.get("description", ""),
                                author=info.get("author", ""),
                                tags=[])
        return {"success": True, "pack_id": pack_id}

    def activate(self, pack_id: str) -> dict:
        self.store.set_setting("active_icon_pack", pack_id)
        return {"success": True, "pack_id": pack_id}

    def get_active(self) -> str:
        return self.store.get_setting("active_icon_pack", "icons_lucide")

    def list_installed(self) -> list[dict]:
        return self.store.get_installed("icon_packs")
