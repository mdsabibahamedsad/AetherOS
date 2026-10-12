"""Data models for the Connect Hub — services, connections, credentials, activity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ServiceCategory(str, Enum):
    COMMUNICATION = "communication"
    EMAIL = "email"
    DEVELOPMENT = "development"
    CLOUD_STORAGE = "cloud_storage"
    PRODUCTIVITY = "productivity"
    SOCIAL = "social"
    DATABASES = "databases"
    CLOUD_PROVIDERS = "cloud_providers"
    AI_PROVIDERS = "ai_providers"
    MEDIA = "media"
    AUTOMATION = "automation"
    LOCAL = "local"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    AUTH_REQUIRED = "auth_required"
    EXPIRED = "expired"
    SYNCING = "syncing"
    ERROR = "error"


class SyncMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    SCHEDULED = "scheduled"


@dataclass
class ServiceInfo:
    id: str
    name: str
    description: str
    category: ServiceCategory
    icon: str = ""
    official: bool = False
    community: bool = False
    website: str = ""
    docs_url: str = ""
    version: str = "1.0.0"
    supports_sync: bool = False
    supports_webhook: bool = False
    auth_type: str = "oauth"  # oauth, api_key, basic, token, none
    config_schema: dict = field(default_factory=dict)
    permissions_available: list[str] = field(default_factory=list)
    default_scopes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    auto_discoverable: bool = False


@dataclass
class ServiceConnection:
    id: str
    service_id: str
    service_name: str
    category: ServiceCategory
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    label: str = ""
    config: dict = field(default_factory=dict)
    permissions_granted: list[str] = field(default_factory=list)
    permissions_missing: list[str] = field(default_factory=list)
    connected_at: Optional[str] = None
    last_health_check: Optional[str] = None
    last_sync: Optional[str] = None
    sync_mode: SyncMode = SyncMode.MANUAL
    sync_interval: int = 3600
    error_message: str = ""
    version: str = "1.0.0"
    metadata: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.label or self.service_name


@dataclass
class HealthCheckResult:
    service_id: str
    connection_id: str
    status: ConnectionStatus
    api_available: bool = False
    auth_valid: bool = False
    rate_limited: bool = False
    latency_ms: float = 0.0
    error_count: int = 0
    last_error: str = ""
    checked_at: str = ""


@dataclass
class ActivityEntry:
    id: str
    connection_id: str
    service_id: str
    service_name: str
    action: str  # connected, disconnected, sync_completed, error, permission_changed, credential_updated
    status: str = "success"
    message: str = ""
    timestamp: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class CredentialEntry:
    service_id: str
    connection_id: str
    encrypted_data: str = ""
    key_hint: str = ""
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""


@dataclass
class DiscoveryResult:
    service_id: str
    service_name: str
    detected: bool = False
    version: str = ""
    path: str = ""
    config: dict = field(default_factory=dict)
    status: str = ""
