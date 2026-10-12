"""AetherOS Hub — unified marketplace and extension system for plugins, MCP, skills, themes, and more."""

from __future__ import annotations

import logging
from typing import Optional

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
from hub.models import (HubCategory, HubItem, HubAuthor, Permission,
                         InstallStatus, SandboxRuntime,
                         PublisherVerification)

logger = logging.getLogger(__name__)


_store_instance: Optional[HubStore] = None


def get_store() -> HubStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = HubStore()
    return _store_instance


def init_hub_system() -> None:
    """Initialize the hub system — DB, catalog, background updater."""
    logger.info("Initializing AetherOS Hub system...")
    store = get_store()
    logger.info("Hub database: %s", store.db_path)
    try:
        updater = AutoUpdater(store)
        updater.start_background_checker(interval_hours=24)
        logger.info("Background update checker started")
    except Exception as e:
        logger.warning("Background updater init failed: %s", e)
    store.set_setting("hub_initialized",
                       __import__('datetime').datetime.utcnow().isoformat() + "Z")
    logger.info("AetherOS Hub initialized")


__all__ = [
    "HubStore", "HubMarketplace",
    "PluginManager", "MCPMarketplace",
    "ThemeManager", "LanguagePackManager", "IconPackManager",
    "ExtensionSDK", "BackupManager", "AutoUpdater",
    "PermissionManager", "DependencyResolver", "SecurityManager",
    "HubCategory", "HubItem", "HubAuthor", "Permission",
    "InstallStatus", "SandboxRuntime", "PublisherVerification",
    "get_store", "init_hub_system",
]
