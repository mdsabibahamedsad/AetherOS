"""Web API — JSON endpoints for the Connect Hub frontend."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from connect.store import ConnectStore
from connect.registry import (get_service, get_all_services,
                               get_services_by_category, search_services,
                               get_categories, ServiceCategory)
from connect.models import (ServiceConnection, ConnectionStatus, SyncMode)
from connect.dashboard import ConnectDashboard
from connect.health import HealthMonitor
from connect.sync import SyncEngine
from connect.activity import ActivityLog
from connect.auth import CredentialManager
from connect.discovery import DiscoveryService
from connect.notifications import ConnectNotifier

logger = logging.getLogger(__name__)


class ConnectAPI:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()
        self.dashboard = ConnectDashboard(self.store)
        self.health = HealthMonitor(self.store)
        self.sync = SyncEngine(self.store)
        self.activity = ActivityLog(self.store)
        self.auth = CredentialManager(self.store)
        self.discovery = DiscoveryService(self.store)
        self.notifier = ConnectNotifier(self.store)

    def get_overview(self) -> dict:
        return self.dashboard.get_overview()

    def get_category(self, category: str) -> dict:
        try:
            cat = ServiceCategory(category)
        except ValueError:
            return {"error": f"Invalid category: {category}"}
        return self.dashboard.get_category_status(cat)

    def get_services(self, category: str = None) -> list[dict]:
        if category:
            try:
                cat = ServiceCategory(category)
                services = get_services_by_category(cat)
            except ValueError:
                return []
        else:
            services = get_all_services()
        connections = self.store.list_connections()
        connected_ids = {c["service_id"]: c for c in connections}
        results = []
        for s in services:
            conn = connected_ids.get(s.id)
            results.append({
                "id": s.id, "name": s.name, "description": s.description,
                "category": s.category.value, "icon": s.icon,
                "official": s.official, "auth_type": s.auth_type,
                "supports_sync": s.supports_sync,
                "auto_discoverable": s.auto_discoverable,
                "connected": conn is not None,
                "connection_id": conn["id"] if conn else None,
                "status": conn.get("status") if conn else "disconnected",
                "config_schema": s.config_schema,
            })
        return results

    def get_categories(self) -> list[dict]:
        return get_categories()

    def search(self, query: str, category: str = None) -> list[dict]:
        return self.dashboard.search_services(query, category)

    def get_recommendations(self) -> list[dict]:
        return self.dashboard.get_recommendations()

    def get_connections(self, category: str = None,
                         status: str = None) -> list[dict]:
        return self.store.list_connections(category, status)

    def get_connection(self, connection_id: str) -> Optional[dict]:
        return self.store.get_connection(connection_id)

    async def connect_service(self, service_id: str, label: str = "",
                               config: dict = None,
                               credentials: dict = None) -> dict:
        from uuid import uuid4
        service = get_service(service_id)
        if not service:
            return {"success": False, "error": f"Service not found: {service_id}"}
        from connect.connectors.communication import CONNECTOR_MAP as cm
        from connect.connectors.email import CONNECTOR_MAP as em
        from connect.connectors.development import CONNECTOR_MAP as dm
        from connect.connectors.productivity import CONNECTOR_MAP as pm
        from connect.connectors.ai_providers import CONNECTOR_MAP as am
        all_maps = {**cm, **em, **dm, **pm, **am}
        conn_id = str(uuid4())[:12]
        conn = ServiceConnection(
            id=conn_id, service_id=service_id,
            service_name=service.name, category=service.category,
            status=ConnectionStatus.CONNECTING,
            label=label or service.name,
            config=config or {}, sync_mode=SyncMode.MANUAL,
        )
        self.store.save_connection(conn)
        connector_cls = all_maps.get(service_id)
        if connector_cls:
            connector = connector_cls(self.store)
            result = await connector.connect(conn, credentials)
            if result.success:
                conn.status = ConnectionStatus.CONNECTED
                conn.connected_at = __import__('datetime').datetime.utcnow().isoformat() + "Z"
                self.store.save_connection(conn)
                if credentials:
                    self.auth.save_credentials(conn_id, service_id, credentials)
                self.notifier.notify_connected(conn_id, service_id, service.name,
                                                result.message)
                return {"success": True, "connection_id": conn_id,
                        "message": result.message, "data": result.data}
            else:
                conn.status = result.status
                conn.error_message = result.error
                self.store.save_connection(conn)
                return {"success": False, "connection_id": conn_id,
                        "error": result.error}
        conn.status = ConnectionStatus.CONNECTED
        self.store.save_connection(conn)
        return {"success": True, "connection_id": conn_id}

    async def disconnect_service(self, connection_id: str) -> dict:
        conn = self.store.get_connection(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        self.store.set_status(connection_id, "disconnected")
        self.notifier.notify_disconnected(
            connection_id, conn.get("service_id", ""),
            conn.get("service_name", ""))
        return {"success": True}

    def remove_connection(self, connection_id: str) -> dict:
        conn = self.store.get_connection(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        self.auth.delete_credentials(connection_id)
        self.store.delete_connection(connection_id)
        return {"success": True}

    async def check_health(self, connection_id: str = None) -> Any:
        if connection_id:
            conn = self.store.get_connection(connection_id)
            if not conn:
                return {"error": "Connection not found"}
            result = await self.health.check_connection(conn)
            return {"connection_id": connection_id, "status": result.status.value,
                    "api_available": result.api_available,
                    "auth_valid": result.auth_valid,
                    "latency_ms": result.latency_ms,
                    "error": result.last_error}
        summary = self.health.get_summary()
        return {"connections": summary}

    async def check_all_health(self) -> list[dict]:
        results = await self.health.check_all()
        return [{"service_id": r.service_id, "status": r.status.value,
                  "api_available": r.api_available, "latency_ms": r.latency_ms}
                for r in results]

    async def sync_connection(self, connection_id: str) -> dict:
        conn = self.store.get_connection(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        result = await self.sync.sync_connection(conn)
        return result

    async def sync_all(self) -> list[dict]:
        return await self.sync.sync_all()

    def get_activity(self, connection_id: str = None, limit: int = 100) -> list[dict]:
        return self.activity.get_for_connection(connection_id, limit) if connection_id \
            else self.activity.get_all(limit)

    def get_credentials_status(self, connection_id: str) -> dict:
        return {
            "has_credentials": self.auth.has_credentials(connection_id),
            "key_hint": self.auth.get_key_hint(connection_id),
        }

    def update_credentials(self, connection_id: str,
                            credentials: dict) -> dict:
        conn = self.store.get_connection(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        self.auth.save_credentials(connection_id, conn.get("service_id", ""),
                                    credentials)
        self.notifier.notify_credential_updated(
            connection_id, conn.get("service_id", ""),
            conn.get("service_name", ""))
        return {"success": True}

    def get_stats(self) -> dict:
        return self.store.get_stats()

    async def discover_local(self) -> list[dict]:
        results = await self.discovery.discover_all()
        return [{"service_id": r.service_id, "service_name": r.service_name,
                 "detected": r.detected, "version": r.version,
                 "path": r.path, "status": r.status}
                for r in results]

    async def discover_and_connect(self) -> list[dict]:
        connections = await self.discovery.discover_and_connect()
        return [{"service_id": c.service_id, "service_name": c.service_name,
                 "connection_id": c.id} for c in connections]
