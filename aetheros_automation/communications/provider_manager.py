from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    EXPIRED = "expired"


class ProviderType(Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    GMAIL = "gmail"
    DISCORD = "discord"
    SLACK = "slack"
    SMS = "sms"
    OUTLOOK = "outlook"
    TEAMS = "teams"
    SIGNAL = "signal"
    WEBHOOK = "webhook"
    CUSTOM_REST = "custom-rest"


class AuthMethod(Enum):
    OAUTH = "oauth"
    BOT_TOKEN = "bot_token"
    API_KEY = "api_key"
    DEVICE_CODE = "device_code"
    SIGN_IN = "sign_in"
    ACCOUNT_LINKING = "account_linking"
    PASSPORT = "passport"


@dataclass
class ProviderCapabilities:
    send_messages: bool = True
    receive_messages: bool = True
    send_files: bool = False
    send_images: bool = False
    send_voice: bool = False
    receive_media: bool = True
    search: bool = True
    threads: bool = False
    channels: bool = False
    reactions: bool = False
    read_receipts: bool = False
    typing_indicator: bool = False
    webhook_support: bool = False
    voice_calls: bool = False
    video_calls: bool = False


@dataclass
class ProviderConnection:
    id: str
    provider: ProviderType
    label: str
    auth_method: AuthMethod
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    credentials_id: str = ""
    account_name: str = ""
    account_avatar: str = ""
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    last_sync: Optional[datetime] = None
    error_message: str = ""
    rate_limit_remaining: int = 100
    rate_limit_reset: float = 0.0
    connected_at: Optional[datetime] = None
    config: dict[str, Any] = field(default_factory=dict)


class ProviderManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._connections: dict[str, ProviderConnection] = {}
        self._load()

    def _load(self):
        path = self._storage_path / "connections.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for item in data:
                    conn = self._deserialize_connection(item)
                    self._connections[conn.id] = conn
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = [self._serialize_connection(c) for c in self._connections.values()]
        path = self._storage_path / "connections.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def _serialize_connection(self, conn: ProviderConnection) -> dict:
        return {
            "id": conn.id,
            "provider": conn.provider.value,
            "label": conn.label,
            "auth_method": conn.auth_method.value,
            "status": conn.status.value,
            "credentials_id": conn.credentials_id,
            "account_name": conn.account_name,
            "account_avatar": conn.account_avatar,
            "capabilities": {k: v for k, v in conn.capabilities.__dict__.items()},
            "last_sync": conn.last_sync.isoformat() if conn.last_sync else None,
            "error_message": conn.error_message,
            "rate_limit_remaining": conn.rate_limit_remaining,
            "rate_limit_reset": conn.rate_limit_reset,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
            "config": conn.config,
        }

    def _deserialize_connection(self, data: dict) -> ProviderConnection:
        caps_data = data.get("capabilities", {})
        caps = ProviderCapabilities(**{k: v for k, v in caps_data.items() if hasattr(ProviderCapabilities, k)})
        last_sync = None
        if data.get("last_sync"):
            try:
                last_sync = datetime.fromisoformat(data["last_sync"])
            except (ValueError, TypeError):
                pass
        connected_at = None
        if data.get("connected_at"):
            try:
                connected_at = datetime.fromisoformat(data["connected_at"])
            except (ValueError, TypeError):
                pass
        return ProviderConnection(
            id=data["id"],
            provider=ProviderType(data["provider"]),
            label=data.get("label", ""),
            auth_method=AuthMethod(data.get("auth_method", "oauth")),
            status=ConnectionStatus(data.get("status", "disconnected")),
            credentials_id=data.get("credentials_id", ""),
            account_name=data.get("account_name", ""),
            account_avatar=data.get("account_avatar", ""),
            capabilities=caps,
            last_sync=last_sync,
            error_message=data.get("error_message", ""),
            rate_limit_remaining=data.get("rate_limit_remaining", 100),
            rate_limit_reset=data.get("rate_limit_reset", 0.0),
            connected_at=connected_at,
            config=data.get("config", {}),
        )

    def register_connection(self, conn: ProviderConnection):
        self._connections[conn.id] = conn
        self._save()

    def get_connection(self, conn_id: str) -> Optional[ProviderConnection]:
        return self._connections.get(conn_id)

    def get_connections_by_provider(self, provider: ProviderType) -> list[ProviderConnection]:
        return [c for c in self._connections.values() if c.provider == provider]

    def get_active_connections(self) -> list[ProviderConnection]:
        return [c for c in self._connections.values() if c.status == ConnectionStatus.CONNECTED]

    def list_connections(self) -> list[ProviderConnection]:
        return list(self._connections.values())

    def update_connection(self, conn_id: str, **kwargs) -> bool:
        conn = self._connections.get(conn_id)
        if not conn:
            return False
        for key, value in kwargs.items():
            if hasattr(conn, key):
                setattr(conn, key, value)
        self._save()
        return True

    def remove_connection(self, conn_id: str) -> bool:
        if conn_id in self._connections:
            del self._connections[conn_id]
            self._save()
            return True
        return False

    def set_connection_status(self, conn_id: str, status: ConnectionStatus, error: str = ""):
        conn = self._connections.get(conn_id)
        if conn:
            conn.status = status
            conn.error_message = error
            if status == ConnectionStatus.CONNECTED:
                conn.connected_at = datetime.now()
            self._save()

    def check_rate_limit(self, conn_id: str) -> bool:
        conn = self._connections.get(conn_id)
        if not conn:
            return False
        now = time.time()
        if conn.rate_limit_reset > now:
            return conn.rate_limit_remaining > 0
        conn.rate_limit_remaining = 100
        conn.rate_limit_reset = now + 60
        self._save()
        return True

    def consume_rate_limit(self, conn_id: str):
        conn = self._connections.get(conn_id)
        if conn and conn.rate_limit_remaining > 0:
            conn.rate_limit_remaining -= 1
            self._save()

    def get_provider_capabilities(self, provider: ProviderType) -> ProviderCapabilities:
        defaults = {
            ProviderType.TELEGRAM: ProviderCapabilities(send_files=True, send_images=True, send_voice=True, threads=True, channels=True, reactions=True),
            ProviderType.WHATSAPP: ProviderCapabilities(send_files=True, send_images=True, send_voice=True, read_receipts=True),
            ProviderType.GMAIL: ProviderCapabilities(search=True),
            ProviderType.DISCORD: ProviderCapabilities(send_files=True, send_images=True, threads=True, channels=True, reactions=True, typing_indicator=True),
            ProviderType.SLACK: ProviderCapabilities(send_files=True, send_images=True, threads=True, channels=True, reactions=True),
            ProviderType.SMS: ProviderCapabilities(send_files=False, send_images=False, send_voice=False),
            ProviderType.OUTLOOK: ProviderCapabilities(search=True),
            ProviderType.TEAMS: ProviderCapabilities(send_files=True, send_images=True, threads=True, channels=True, voice_calls=True, video_calls=True),
            ProviderType.SIGNAL: ProviderCapabilities(send_files=True, send_images=True),
            ProviderType.WEBHOOK: ProviderCapabilities(send_messages=True, receive_messages=False, search=False),
            ProviderType.CUSTOM_REST: ProviderCapabilities(receive_messages=False, search=False),
        }
        return defaults.get(provider, ProviderCapabilities())
