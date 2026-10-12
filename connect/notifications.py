"""Notifications — alert users about connection events."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from connect.store import ConnectStore
from connect.models import ActivityEntry

logger = logging.getLogger(__name__)


class ConnectNotifier:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()

    def notify_connected(self, connection_id: str, service_id: str,
                          service_name: str, message: str = "") -> None:
        self._log(connection_id, service_id, service_name,
                  "connected", "success", message or f"Connected to {service_name}")

    def notify_disconnected(self, connection_id: str, service_id: str,
                             service_name: str, message: str = "") -> None:
        self._log(connection_id, service_id, service_name,
                  "disconnected", "info", message or f"Disconnected from {service_name}")

    def notify_error(self, connection_id: str, service_id: str,
                      service_name: str, error: str) -> None:
        self._log(connection_id, service_id, service_name,
                  "error", "error", error)

    def notify_auth_expired(self, connection_id: str, service_id: str,
                             service_name: str) -> None:
        self._log(connection_id, service_id, service_name,
                  "auth_expired", "warning", f"Authentication expired for {service_name}")

    def notify_sync_completed(self, connection_id: str, service_id: str,
                               service_name: str, details: str = "") -> None:
        self._log(connection_id, service_id, service_name,
                  "sync_completed", "success",
                  f"Sync completed for {service_name}", details={"info": details})

    def notify_permission_changed(self, connection_id: str, service_id: str,
                                   service_name: str, changes: str) -> None:
        self._log(connection_id, service_id, service_name,
                  "permission_changed", "info",
                  f"Permissions changed for {service_name}: {changes}")

    def notify_credential_updated(self, connection_id: str, service_id: str,
                                   service_name: str) -> None:
        self._log(connection_id, service_id, service_name,
                  "credential_updated", "info",
                  f"Credentials updated for {service_name}")

    def _log(self, connection_id: str, service_id: str, service_name: str,
              action: str, status: str, message: str,
              details: dict = None) -> None:
        entry = ActivityEntry(
            id=str(uuid4())[:12],
            connection_id=connection_id,
            service_id=service_id,
            service_name=service_name,
            action=action,
            status=status,
            message=message,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details=details or {},
        )
        self.store.log_activity(entry)
        logger.info("[%s] %s: %s", action, service_name, message)

    def get_recent(self, limit: int = 20) -> list[dict]:
        return self.store.get_activity(limit=limit)
