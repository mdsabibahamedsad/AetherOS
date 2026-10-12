"""Backup manager — backup and restore plugins, extensions, themes, and settings."""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from aetheros_constants import get_aetheros_home
from hub.store import HubStore
from hub.models import BackupManifest

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self.backup_dir = get_aetheros_home() / "hub" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, name: str = "",
                       include_plugins: bool = True,
                       include_themes: bool = True,
                       include_settings: bool = True) -> dict:
        backup_id = str(uuid4())[:8]
        name = name or f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_id}.zip"
        items = []
        manifest = BackupManifest(
            created_at=datetime.utcnow().isoformat() + "Z",
            items=items,
            plugins=[],
            themes=[],
            settings={} if include_settings else {},
        )

        with zipfile.ZipFile(str(backup_path), "w", zipfile.ZIP_DEFLATED) as zf:
            if include_plugins:
                plugins_dir = get_aetheros_home() / "plugins"
                if plugins_dir.exists():
                    for plugin_dir in plugins_dir.iterdir():
                        if plugin_dir.is_dir():
                            for root, dirs, files in os.walk(str(plugin_dir)):
                                for fn in files:
                                    fp = Path(root) / fn
                                    arc = f"plugins/{plugin_dir.name}/{fp.relative_to(plugin_dir)}"
                                    zf.write(str(fp), arc)
                            items.append({"type": "plugin", "name": plugin_dir.name})
                            manifest.plugins.append(plugin_dir.name)

            if include_themes:
                themes_dir = get_aetheros_home() / "themes"
                if themes_dir.exists():
                    for theme_dir in themes_dir.iterdir():
                        if theme_dir.is_dir():
                            for root, dirs, files in os.walk(str(theme_dir)):
                                for fn in files:
                                    fp = Path(root) / fn
                                    arc = f"themes/{theme_dir.name}/{fp.relative_to(theme_dir)}"
                                    zf.write(str(fp), arc)
                            items.append({"type": "theme", "name": theme_dir.name})
                            manifest.themes.append(theme_dir.name)

            if include_settings:
                settings = {}
                for key in ["active_theme", "active_language", "active_icon_pack",
                            "permission_grants", "hub_settings"]:
                    val = self.store.get_setting(key)
                    if val:
                        settings[key] = val
                manifest.settings = settings
                zf.writestr("settings.json", json.dumps(settings, indent=2))

            zf.writestr("manifest.json", json.dumps(manifest.__dict__, indent=2))

        size = backup_path.stat().st_size
        self.store.save_backup(backup_id, name, str(backup_path), size,
                               len(items), manifest.__dict__)
        logger.info("Backup created: %s (%d items, %d bytes)", name, len(items), size)
        return {"success": True, "backup_id": backup_id, "name": name,
                "path": str(backup_path), "items": len(items), "size": size}

    def list_backups(self) -> list[dict]:
        return self.store.list_backups()

    def restore(self, backup_id: str, restore_plugins: bool = True,
                restore_themes: bool = True,
                restore_settings: bool = True) -> dict:
        records = self.store.list_backups()
        record = next((r for r in records if r["id"] == backup_id), None)
        if not record:
            return {"success": False, "error": f"Backup {backup_id} not found"}
        backup_path = Path(record["path"])
        if not backup_path.exists():
            return {"success": False, "error": "Backup file not found"}

        restored = {"plugins": [], "themes": [], "settings": False}
        with zipfile.ZipFile(str(backup_path), "r") as zf:
            for entry in zf.namelist():
                if entry.startswith("plugins/") and restore_plugins:
                    parts = entry.split("/")
                    if len(parts) >= 2:
                        plugin_name = parts[1]
                        target = get_aetheros_home() / "plugins" / plugin_name
                        target_dir = entry.replace(f"plugins/{plugin_name}/", "")
                        if target_dir:
                            (target / target_dir).parent.mkdir(parents=True, exist_ok=True)
                            zf.extract(entry, str(target.parent))
                            restored["plugins"].append(plugin_name)

                elif entry.startswith("themes/") and restore_themes:
                    parts = entry.split("/")
                    if len(parts) >= 2:
                        theme_name = parts[1]
                        target = get_aetheros_home() / "themes" / theme_name
                        target_dir = entry.replace(f"themes/{theme_name}/", "")
                        if target_dir:
                            (target / target_dir).parent.mkdir(parents=True, exist_ok=True)
                            zf.extract(entry, str(target.parent))
                            restored["themes"].append(theme_name)

                elif entry == "settings.json" and restore_settings:
                    settings = json.loads(zf.read(entry))
                    for key, value in settings.items():
                        self.store.set_setting(key, str(value))
                    restored["settings"] = True

        plugins_count = len(set(restored["plugins"]))
        themes_count = len(set(restored["themes"]))
        logger.info("Restored backup %s: %d plugins, %d themes, settings=%s",
                     backup_id, plugins_count, themes_count, restored["settings"])
        return {"success": True, "backup_id": backup_id,
                "plugins_restored": plugins_count,
                "themes_restored": themes_count,
                "settings_restored": restored["settings"]}

    def delete_backup(self, backup_id: str) -> dict:
        records = self.store.list_backups()
        record = next((r for r in records if r["id"] == backup_id), None)
        if record:
            path = Path(record["path"])
            if path.exists():
                path.unlink()
        self.store.delete_backup(backup_id)
        return {"success": True}

    def restore_plugin(self, plugin_id: str, version: str = None) -> dict:
        backups = self.store.list_backups()
        for record in backups:
            backup_path = Path(record["path"])
            if not backup_path.exists():
                continue
            with zipfile.ZipFile(str(backup_path), "r") as zf:
                plugin_files = [n for n in zf.namelist()
                                if n.startswith(f"plugins/{plugin_id}/")]
                if plugin_files:
                    target_base = get_aetheros_home() / "plugins"
                    for entry in plugin_files:
                        target_dir = entry.replace(f"plugins/{plugin_id}/", "")
                        if target_dir:
                            (target_base / plugin_id / target_dir).parent.mkdir(
                                parents=True, exist_ok=True)
                            zf.extract(entry, str(target_base))
                    logger.info("Restored plugin %s from backup %s",
                                plugin_id, record["id"])
                    return {"success": True, "plugin_id": plugin_id,
                            "backup_id": record["id"]}
        return {"success": False, "error": f"No backup found for {plugin_id}"}
