"""Base connector ABC — every service integration implements this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ActivityEntry, SyncMode, ServiceCategory)


@dataclass
class ConnectorResult:
    success: bool = True
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    message: str = ""
    data: Any = None
    error: str = ""


class BaseConnector(ABC):
    """All service connectors must implement these methods."""

    service_id: str = ""
    service_name: str = ""
    category: ServiceCategory = ServiceCategory.LOCAL

    def __init__(self, store=None):
        from connect.store import ConnectStore
        self.store = store or ConnectStore()

    @abstractmethod
    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        ...

    @abstractmethod
    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        ...

    @abstractmethod
    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        ...

    @abstractmethod
    async def permissions(self, connection: ServiceConnection) -> dict:
        ...

    @abstractmethod
    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        """Optional sync — raise NotImplementedError if unsupported."""
        raise NotImplementedError

    @abstractmethod
    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        ...

    def get_config_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    def get_display_fields(self) -> list[str]:
        return []

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        return errors
