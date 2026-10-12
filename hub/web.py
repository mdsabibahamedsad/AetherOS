"""Web API — JSON endpoints for the AetherOS Hub store frontend."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from hub.store import HubStore
from hub.marketplace import HubMarketplace
from hub.plugins import PluginManager
from hub.mcp_marketplace import MCPMarketplace
from hub.themes import ThemeManager
from hub.languages import LanguagePackManager
from hub.icons import IconPackManager
from hub.sdk import ExtensionSDK
from hub.backup import BackupManager
from hub.updater import AutoUpdater
from hub.permissions import PermissionManager
from hub.dependencies import DependencyResolver
from hub.security import SecurityManager

logger = logging.getLogger(__name__)


class HubAPI:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self.marketplace = HubMarketplace(self.store)
        self.plugins = PluginManager(self.store)
        self.mcp = MCPMarketplace(self.store)
        self.themes = ThemeManager(self.store)
        self.languages = LanguagePackManager(self.store)
        self.icons = IconPackManager(self.store)
        self.sdk = ExtensionSDK()
        self.backup = BackupManager(self.store)
        self.updater = AutoUpdater(self.store)
        self.permissions = PermissionManager(self.store)
        self.dependencies = DependencyResolver(self.store)
        self.security = SecurityManager()

    # ── Catalog ──
    def get_catalog(self, category: str = None) -> list[dict]:
        return self.marketplace.get_catalog(category)

    def search(self, query: str = "", category: str = None,
               tags: list[str] = None, sort_by: str = "",
               page: int = 1, limit: int = 20) -> dict:
        results = self.marketplace.search(query, category, tags, sort_by)
        total = len(results)
        start = (page - 1) * limit
        return {"results": results[start:start + limit], "total": total,
                "page": page, "limit": limit, "pages": (total + limit - 1) // limit}

    def get_item(self, item_id: str) -> Optional[dict]:
        item = self.marketplace.get_item(item_id)
        if item:
            d = item.to_dict()
            d["reviews"] = [r.__dict__ for r in item.reviews]
            d["changelog"] = [{"version": v.version, "changelog": v.changelog,
                                "released_at": v.released_at} for v in item.changelog]
            return d
        return None

    def get_categories(self) -> list[dict]:
        return self.marketplace.get_categories()

    def get_featured(self) -> list[dict]:
        return self.marketplace.get_featured()

    def get_trending(self) -> list[dict]:
        return self.marketplace.get_trending()

    def get_editors_choice(self) -> list[dict]:
        return self.marketplace.get_editors_choice()

    def get_stats(self) -> dict:
        return self.marketplace.get_stats()

    # ── Installation ──
    def install(self, item_id: str, auto_approve: bool = False) -> dict:
        return self.marketplace.install(item_id, auto_approve)

    def remove(self, item_id: str) -> dict:
        item = self.store.get_installed_item(item_id)
        if not item:
            return {"success": False, "error": "Not installed"}
        cat = item.get("category", "")
        if cat == "plugins":
            return self.plugins.remove(item_id)
        if cat == "mcp_servers":
            return self.mcp.uninstall(item_id)
        if cat == "themes":
            return self.themes.remove(item_id)
        self.store.remove_item(item_id)
        return {"success": True}

    def get_installed(self, category: str = None) -> list[dict]:
        return self.store.get_installed(category)

    def get_installed_item(self, item_id: str) -> Optional[dict]:
        return self.store.get_installed_item(item_id)

    def set_enabled(self, item_id: str, enabled: bool) -> dict:
        self.store.set_enabled(item_id, enabled)
        return {"success": True}

    # ── Updates ──
    def check_updates(self) -> list[dict]:
        return self.updater.check_all()

    def apply_update(self, item_id: str) -> dict:
        return self.updater.apply_update(item_id)

    def apply_all_updates(self) -> list[dict]:
        return self.updater.apply_all_pending()

    # ── Permissions ──
    def get_permissions(self, item_id: str = None) -> dict:
        if item_id:
            return {"grants": [{"permission": g.permission.value,
                                "level": g.level.value,
                                "reason": g.reason}
                               for g in self.permissions.get_grants(item_id)]}
        return {"grants": {k: [{"permission": g.permission.value,
                                "level": g.level.value,
                                "reason": g.reason}
                               for g in v]
                           for k, v in self.permissions.get_all_grants().items()}}

    def revoke_permissions(self, item_id: str, permission: str = None) -> dict:
        from hub.models import Permission
        perm = Permission(permission) if permission else None
        self.permissions.revoke(item_id, perm)
        return {"success": True}

    # ── Dependencies ──
    def check_dependencies(self, item_id: str) -> dict:
        item = self.store.get_installed_item(item_id)
        if not item:
            return {"satisfied": False, "error": "Not installed"}
        deps = item.get("dependencies", [])
        if isinstance(deps, str):
            deps = json.loads(deps)
        return self.dependencies.check_dependencies(item_id, deps)

    def get_dependency_tree(self, item_id: str) -> dict:
        return self.dependencies.get_dependency_tree(item_id)

    # ── MCP ──
    def list_mcp_servers(self) -> list[dict]:
        return self.mcp.get_catalog()

    def install_mcp(self, server_id: str, config: dict = None) -> dict:
        return self.mcp.install(server_id, config)

    def test_mcp(self, server_id: str) -> dict:
        return self.mcp.test_connection(server_id)

    # ── Themes ──
    def list_themes(self) -> list[dict]:
        return self.themes.list_installed()

    def activate_theme(self, theme_id: str) -> dict:
        return self.themes.activate(theme_id)

    def get_active_theme(self) -> str:
        return self.themes.get_active()

    # ── SDK ──
    def list_sdk_templates(self) -> list[dict]:
        return self.sdk.list_templates()

    def init_sdk_project(self, project_type: str, name: str,
                          author: str = "", description: str = "",
                          path: str = "") -> dict:
        return self.sdk.init_project(project_type, name, author, description, path)

    def build_sdk_project(self, project_path: str, output_path: str = "") -> dict:
        return self.sdk.build(project_path, output_path)

    # ── Backups ──
    def list_backups(self) -> list[dict]:
        return self.backup.list_backups()

    def create_backup(self, name: str = "") -> dict:
        return self.backup.create_backup(name=name)

    def restore_backup(self, backup_id: str) -> dict:
        return self.backup.restore(backup_id)

    # ── Integity ──
    def verify_integrity(self, item_id: str) -> dict:
        item = self.store.get_installed_item(item_id)
        if not item or not item.get("install_path"):
            return {"valid": False, "error": "Not installed"}
        return self.security.get_integrity_report(item_id, item["install_path"])
