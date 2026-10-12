"""Plugin manager — install, update, remove, enable, disable, repair plugins."""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore
from hub.models import (HubCategory, InstallStatus, Permission, SandboxRuntime,
                         PluginManifest, HubItem, HubAuthor)
from hub.permissions import PermissionManager
from hub.security import SecurityManager

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self.permissions = PermissionManager(self.store)
        self.security = SecurityManager()
        self.plugins_dir = get_aetheros_home() / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def list_installed(self, status: str = None) -> list[dict]:
        items = self.store.get_installed("plugins")
        if status == "disabled":
            return [i for i in items if not i["enabled"]]
        if status == "broken":
            return [i for i in items if not i["compatible"]]
        return items

    def get_plugin(self, plugin_id: str) -> Optional[dict]:
        return self.store.get_installed_item(plugin_id)

    def install(self, plugin_id: str, source: str = None,
                manifest: dict = None, file_path: str = None,
                auto_approve: bool = False) -> dict:
        """Install a plugin from a file, URL, or manifest dict."""
        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            return {"success": False, "error": f"Plugin {plugin_id} already installed"}

        if file_path:
            return self._install_from_file(plugin_id, file_path)
        if manifest:
            return self._install_from_manifest(plugin_id, manifest, auto_approve)
        from hub.marketplace import HubMarketplace
        mp = HubMarketplace()
        item = mp.get_item(plugin_id)
        if item:
            manifest_dict = {"name": item.name, "version": item.version,
                             "description": item.description, "author": item.author.name,
                             "permissions": [p.value for p in item.permissions],
                             "dependencies": [{"package_id": d.package_id,
                                               "version": d.version,
                                               "optional": d.optional}
                                             for d in item.dependencies]}
            return self._install_from_manifest(plugin_id, manifest_dict, auto_approve)
        return {"success": False, "error": f"Plugin {plugin_id} not found"}

    def _install_from_file(self, plugin_id: str, file_path: str) -> dict:
        plugin_dir = self.plugins_dir / plugin_id
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(str(plugin_dir))
            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                shutil.rmtree(plugin_dir, ignore_errors=True)
                return {"success": False, "error": "manifest.json not found in package"}
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            integrity = self.security.verify_package_integrity(str(plugin_dir))
            if not integrity.get("valid"):
                logger.warning("Integrity check failed: %s", integrity.get("error"))
            entrypoint = manifest.get("entrypoint", "plugin.py")
            entry_path = plugin_dir / entrypoint
            if not entry_path.exists():
                return {"success": False, "error": f"Entrypoint {entrypoint} not found"}
            self._register_install(plugin_id, manifest, str(plugin_dir))
            return {"success": True, "plugin_id": plugin_id, "path": str(plugin_dir)}
        except zipfile.BadZipFile:
            shutil.rmtree(plugin_dir, ignore_errors=True)
            return {"success": False, "error": "Invalid zip file"}

    def _install_from_manifest(self, plugin_id: str, manifest: dict,
                                auto_approve: bool = False) -> dict:
        plugin_dir = self.plugins_dir / plugin_id
        os.makedirs(str(plugin_dir), exist_ok=True)
        manifest_path = plugin_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        permissions = [Permission(p) for p in manifest.get("permissions", [])
                       if p in Permission.__members__.values()]
        if not auto_approve:
            results = self.permissions.request_many(
                plugin_id, permissions, ["Required for operation"] * len(permissions))
            denied = [k for k, v in results.items() if not v]
            if denied:
                logger.warning("Permissions denied for %s: %s", plugin_id, denied)
        self._register_install(plugin_id, manifest, str(plugin_dir))
        return {"success": True, "plugin_id": plugin_id, "path": str(plugin_dir)}

    def _register_install(self, plugin_id: str, manifest: dict,
                           install_path: str) -> None:
        deps = manifest.get("dependencies", [])
        if isinstance(deps, list):
            deps = [{"package_id": d.get("package_id", d) if isinstance(d, dict) else d,
                      "version": d.get("version", "*") if isinstance(d, dict) else "*"}
                    for d in deps]
        self.store.install_item(
            plugin_id,
            manifest.get("name", plugin_id),
            "plugins",
            manifest.get("version", "1.0.0"),
            description=manifest.get("description", ""),
            author=manifest.get("author", "Unknown"),
            license=manifest.get("license", "MIT"),
            tags=manifest.get("tags", []),
            permissions=manifest.get("permissions", []),
            dependencies=deps,
            manifest=manifest,
            checksum="",
            install_path=install_path,
            size_bytes=0,
        )
        logger.info("Installed plugin: %s v%s", plugin_id, manifest.get("version", "1.0.0"))

    def update(self, plugin_id: str, new_manifest: dict = None,
               file_path: str = None) -> dict:
        existing = self.store.get_installed_item(plugin_id)
        if not existing:
            return {"success": False, "error": f"Plugin {plugin_id} not installed"}
        if file_path:
            backup_path = str(self.plugins_dir / f"{plugin_id}.bak")
            self.security.safe_uninstall(str(self.plugins_dir / plugin_id), backup_path)
            result = self._install_from_file(plugin_id, file_path)
            if not result["success"]:
                if os.path.exists(backup_path):
                    shutil.copytree(backup_path, str(self.plugins_dir / plugin_id),
                                    dirs_exist_ok=True)
                return result
            shutil.rmtree(backup_path, ignore_errors=True)
            return result
        if new_manifest:
            return self._install_from_manifest(plugin_id, new_manifest)
        return {"success": False, "error": "No update source provided"}

    def remove(self, plugin_id: str, safe: bool = True) -> dict:
        plugin_dir = self.plugins_dir / plugin_id
        if safe:
            backup_dir = get_aetheros_home() / "hub" / "trash" / plugin_id
            self.security.safe_uninstall(str(plugin_dir), str(backup_dir))
        elif plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)
        self.store.remove_item(plugin_id)
        self.permissions.revoke(plugin_id)
        logger.info("Removed plugin: %s", plugin_id)
        return {"success": True, "plugin_id": plugin_id}

    def enable(self, plugin_id: str) -> bool:
        plugin_dir = self.plugins_dir / plugin_id
        if not plugin_dir.exists():
            logger.warning("Plugin directory not found: %s", plugin_id)
            return False
        self.store.set_enabled(plugin_id, True)
        logger.info("Enabled plugin: %s", plugin_id)
        return True

    def disable(self, plugin_id: str) -> bool:
        self.store.set_enabled(plugin_id, False)
        logger.info("Disabled plugin: %s", plugin_id)
        return True

    def repair(self, plugin_id: str) -> dict:
        """Verify and repair a plugin installation."""
        plugin_dir = self.plugins_dir / plugin_id
        if not plugin_dir.exists():
            return {"success": False, "error": "Plugin not found"}
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            return {"success": False, "error": "manifest.json missing"}
        integrity = self.security.verify_package_integrity(str(plugin_dir))
        missing = []
        if not integrity.get("valid"):
            for file_name in integrity.get("checksums", {}):
                if not (plugin_dir / file_name).exists():
                    missing.append(file_name)
        self.store.install_item(
            plugin_id,
            plugin_id, "plugins", "1.0.0",
            compatible=not bool(missing),
        )
        return {"success": True, "repaired": not bool(missing),
                "missing_files": missing}

    def load_plugin(self, plugin_id: str) -> Optional[Any]:
        """Load and return a plugin module."""
        item = self.store.get_installed_item(plugin_id)
        if not item or not item["enabled"]:
            return None
        plugin_dir = self.plugins_dir / plugin_id
        entrypoint = item.get("manifest", {}).get("entrypoint", "plugin.py")
        entry_path = plugin_dir / entrypoint
        if not entry_path.exists():
            logger.error("Plugin entrypoint not found: %s", entry_path)
            return None
        import importlib.util
        spec = importlib.util.spec_from_file_location(plugin_id, str(entry_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return None

    def get_updates(self) -> list[dict]:
        from hub.marketplace import HubMarketplace
        mp = HubMarketplace()
        installed = self.list_installed()
        updates = []
        for item in installed:
            mp_item = mp.get_item(item["id"])
            if mp_item and mp_item.version > item.get("version", "0.0.0"):
                updates.append({"plugin_id": item["id"], "current": item.get("version"),
                                "available": mp_item.version})
        return updates

    def rollback(self, plugin_id: str, version: str = None) -> dict:
        from hub.backup import BackupManager
        bm = BackupManager()
        return bm.restore_plugin(plugin_id, version)
