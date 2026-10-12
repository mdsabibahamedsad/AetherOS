"""Connect Hub — universal account and service connection center for AetherOS."""

from __future__ import annotations

import logging
from typing import Optional

from connect.store import ConnectStore
from connect.registry import (SERVICE_REGISTRY, get_service, get_all_services,
                               get_services_by_category, search_services,
                               get_categories, ServiceCategory)
from connect.auth import CredentialManager
from connect.health import HealthMonitor
from connect.sync import SyncEngine
from connect.discovery import DiscoveryService
from connect.activity import ActivityLog
from connect.notifications import ConnectNotifier
from connect.dashboard import ConnectDashboard
from connect.cli import build_connect_parser, handle_connect_command
from connect.web import ConnectAPI

logger = logging.getLogger(__name__)

_store_instance: Optional[ConnectStore] = None
_connect_initialized = False


def get_store() -> ConnectStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = ConnectStore()
    return _store_instance


def _ensure_initialized() -> None:
    """Lazily initialize the Connect Hub on first use."""
    global _connect_initialized
    if _connect_initialized:
        return
    logger.info("Initializing Connect Hub...")
    store = get_store()
    logger.info("Connect database: %s", store.db_path)

    # Run auto-discovery for local services
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        discovery = DiscoveryService(get_store())
        results = loop.run_until_complete(discovery.discover_and_connect())
        if results:
            logger.info("Auto-discovered %d local services", len(results))
        loop.close()
    except Exception as e:
        logger.debug("Auto-discovery skipped: %s", e)

    store.set_setting("connect_initialized",
                       __import__('datetime').datetime.utcnow().isoformat() + "Z")
    logger.info("Connect Hub initialized")
    _connect_initialized = True


def get_store_ensure_init() -> ConnectStore:
    """Get the store, ensuring initialization happens on first use."""
    _ensure_initialized()
    return get_store()


def init_connect_system() -> None:
    """Initialize the Connect Hub — DB, auto-discovery, background health checks.
    
    This is now a no-op; initialization happens lazily on first use via
    get_store_ensure_init(). Kept for backward compatibility.
    """
    pass


__all__ = [
    "ConnectStore", "CredentialManager", "HealthMonitor", "SyncEngine",
    "DiscoveryService", "ActivityLog", "ConnectNotifier", "ConnectDashboard",
    "ConnectAPI",
    "get_service", "get_all_services", "get_services_by_category",
    "search_services", "get_categories", "ServiceCategory",
    "SERVICE_REGISTRY",
    "build_connect_parser", "handle_connect_command",
    "get_store", "get_store_ensure_init", "init_connect_system",
]
