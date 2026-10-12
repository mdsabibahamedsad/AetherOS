"""Health monitor — check API availability, auth validity, rate limits, latency, errors."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from connect.store import ConnectStore
from connect.models import (ConnectionStatus, HealthCheckResult, ActivityEntry)

logger = logging.getLogger(__name__)


class HealthMonitor:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()

    async def check_connection(self, connection: dict,
                                connector=None) -> HealthCheckResult:
        start = time.time()
        try:
            if connector and hasattr(connector, 'health'):
                result = await connector.health(
                    self._dict_to_connection(connection))
                result.latency_ms = (time.time() - start) * 1000
                self.store.save_health_check(result)
                self.store.set_status(connection["id"],
                                       result.status.value)
                return result
        except Exception as e:
            logger.error("Health check failed for %s: %s",
                          connection.get("id"), e)

        result = HealthCheckResult(
            service_id=connection.get("service_id", ""),
            connection_id=connection["id"],
            status=ConnectionStatus.ERROR,
            api_available=False,
            auth_valid=False,
            latency_ms=(time.time() - start) * 1000,
            last_error=str(e) if 'e' in dir() else "Unknown",
            checked_at=datetime.utcnow().isoformat() + "Z",
        )
        self.store.save_health_check(result)
        return result

    async def check_all(self, get_connector_fn=None) -> list[HealthCheckResult]:
        connections = self.store.list_connections()
        results = []
        for conn in connections:
            connector = None
            if get_connector_fn:
                connector = get_connector_fn(conn.get("service_id", ""))
            result = await self.check_connection(conn, connector)
            results.append(result)
        return results

    def get_latest(self, connection_id: str) -> Optional[dict]:
        return self.store.get_latest_health(connection_id)

    def get_history(self, connection_id: str, limit: int = 50) -> list[dict]:
        return self.store.get_health_history(connection_id, limit)

    def get_summary(self) -> list[dict]:
        connections = self.store.list_connections()
        summary = []
        for conn in connections:
            health = self.store.get_latest_health(conn["id"])
            summary.append({
                "connection_id": conn["id"],
                "service_name": conn.get("service_name", ""),
                "status": conn.get("status", "disconnected"),
                "api_available": health.get("api_available", False) if health else False,
                "auth_valid": health.get("auth_valid", False) if health else False,
                "latency_ms": health.get("latency_ms", 0) if health else 0,
                "last_error": health.get("last_error", "") if health else "",
            })
        return summary

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
            permissions_granted=d.get("permissions_granted", []),
            permissions_missing=d.get("permissions_missing", []),
            connected_at=d.get("connected_at"),
            last_health_check=d.get("last_health_check"),
            last_sync=d.get("last_sync"),
            sync_mode=SyncMode(d.get("sync_mode", "manual")),
            error_message=d.get("error_message", ""),
            version=d.get("version", "1.0.0"),
            metadata=d.get("metadata", {}),
        )
