"""Sync engine — background synchronization for services that support it."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from connect.store import ConnectStore
from connect.models import (ConnectionStatus, SyncMode, ActivityEntry)

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._get_connector_fn: Optional[Callable] = None

    def set_connector_fn(self, fn: Callable) -> None:
        self._get_connector_fn = fn

    async def sync_connection(self, connection: dict) -> dict:
        from uuid import uuid4
        conn_id = connection["id"]
        service_id = connection.get("service_id", "")
        service_name = connection.get("service_name", "")

        if self._get_connector_fn:
            connector_cls = self._get_connector_fn(service_id)
            if connector_cls:
                try:
                    connector = connector_cls(self.store)
                    if hasattr(connector, 'sync'):
                        result = await connector.sync(
                            self._dict_to_connection(connection))
                        self.store.set_status(conn_id, "syncing")
                        entry = ActivityEntry(
                            id=str(uuid4())[:12],
                            connection_id=conn_id,
                            service_id=service_id,
                            service_name=service_name,
                            action="sync_completed",
                            status="success" if result.success else "error",
                            message=result.message,
                            timestamp=datetime.utcnow().isoformat() + "Z",
                            details={"result": result.message},
                        )
                        self.store.log_activity(entry)
                        self.store.set_status(conn_id, "connected")
                        return {"success": result.success, "message": result.message}
                except Exception as e:
                    logger.error("Sync failed for %s: %s", conn_id, e)
                    return {"success": False, "error": str(e)}
        return {"success": False, "error": "No connector available"}

    async def sync_all(self) -> list[dict]:
        connections = self.store.list_connections()
        results = []
        for conn in connections:
            if conn.get("status") == "connected":
                result = await self.sync_connection(conn)
                results.append(result)
        return results

    async def sync_category(self, category: str) -> list[dict]:
        connections = self.store.list_connections(category=category)
        results = []
        for conn in connections:
            if conn.get("status") == "connected":
                result = await self.sync_connection(conn)
                results.append(result)
        return results

    def start_auto_sync(self, interval_seconds: int = 3600) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop, args=(interval_seconds,), daemon=True)
        self._thread.start()
        logger.info("Auto-sync started (interval: %ds)", interval_seconds)

    def stop_auto_sync(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _sync_loop(self, interval: int) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self._running:
            try:
                connections = self.store.list_connections(status="connected")
                for conn in connections:
                    if conn.get("sync_mode") in ("auto", "scheduled"):
                        loop.run_until_complete(self.sync_connection(conn))
            except Exception as e:
                logger.error("Auto-sync loop error: %s", e)
            time.sleep(interval)

    def _dict_to_connection(self, d: dict) -> 'ServiceConnection':
        from connect.models import ServiceConnection, ConnectionStatus, SyncMode, ServiceCategory
        try:
            cat = ServiceCategory(d.get("category", "local"))
        except ValueError:
            cat = ServiceCategory.LOCAL
        try:
            status = ConnectionStatus(d.get("status", "disconnected"))
        except ValueError:
            status = ConnectionStatus.DISCONNECTED
        return ServiceConnection(
            id=d["id"], service_id=d.get("service_id", ""),
            service_name=d.get("service_name", ""),
            category=cat, status=status,
            label=d.get("label", ""),
            config=d.get("config", {}),
            sync_mode=SyncMode(d.get("sync_mode", "manual")),
            error_message=d.get("error_message", ""),
        )
