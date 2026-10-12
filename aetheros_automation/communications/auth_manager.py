from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class OAuthFlow(Enum):
    AUTHORIZATION_CODE = "authorization_code"
    DEVICE_CODE = "device_code"
    CLIENT_CREDENTIALS = "client_credentials"
    PKCE = "pkce"
    IMPLICIT = "implicit"


class TokenStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REFRESHING = "refreshing"


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    scope: list[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    status: TokenStatus = TokenStatus.ACTIVE
    provider: str = ""
    account_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    @property
    def expires_soon(self, margin: int = 300) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at - timedelta(seconds=margin)


@dataclass
class AuthConfig:
    provider: str
    auth_flow: OAuthFlow
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    scopes: list[str] = field(default_factory=list)
    auth_endpoint: str = ""
    token_endpoint: str = ""
    device_code_endpoint: str = ""
    bot_token: str = ""
    api_key: str = ""
    additional_params: dict[str, Any] = field(default_factory=dict)
    credentials_id: str = ""


class AuthManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._tokens: dict[str, OAuthToken] = {}
        self._configs: dict[str, AuthConfig] = {}
        self._load()

    def _token_path(self) -> Path:
        return self._storage_path / "tokens.json"

    def _config_path(self) -> Path:
        return self._storage_path / "auth_configs.json"

    def _load(self):
        for path, target in [(self._token_path(), self._tokens), (self._config_path(), self._configs)]:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    for k, v in data.items():
                        if "expires_at" in v and v["expires_at"]:
                            v["expires_at"] = datetime.fromisoformat(v["expires_at"])
                        if "created_at" in v and v["created_at"]:
                            v["created_at"] = datetime.fromisoformat(v["created_at"])
                        if "status" in v:
                            v["status"] = TokenStatus(v["status"])
                        if target is self._tokens:
                            target[k] = OAuthToken(**v)
                        else:
                            if "auth_flow" in v:
                                v["auth_flow"] = OAuthFlow(v["auth_flow"])
                            target[k] = AuthConfig(**v)
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

    def _save_tokens(self):
        data = {}
        for k, t in self._tokens.items():
            d = {k: v for k, v in t.__dict__.items()}
            d["status"] = t.status.value
            d["expires_at"] = t.expires_at.isoformat() if t.expires_at else None
            d["created_at"] = t.created_at.isoformat()
            data[k] = d
        self._token_path().write_text(json.dumps(data, indent=2))

    def _save_configs(self):
        data = {}
        for k, c in self._configs.items():
            d = {k: v for k, v in c.__dict__.items()}
            d["auth_flow"] = c.auth_flow.value
            data[k] = d
        self._config_path().write_text(json.dumps(data, indent=2))

    def register_auth_config(self, config: AuthConfig) -> str:
        config_id = f"auth_{secrets.token_hex(8)}"
        config.credentials_id = config_id
        self._configs[config_id] = config
        self._save_configs()
        return config_id

    def get_auth_config(self, config_id: str) -> Optional[AuthConfig]:
        return self._configs.get(config_id)

    def get_auth_configs_for_provider(self, provider: str) -> list[AuthConfig]:
        return [c for c in self._configs.values() if c.provider == provider]

    def remove_auth_config(self, config_id: str) -> bool:
        if config_id in self._configs:
            del self._configs[config_id]
            self._save_configs()
            return True
        return False

    def store_token(self, token: OAuthToken) -> str:
        token_id = f"tok_{secrets.token_hex(8)}"
        self._tokens[token_id] = token
        self._save_tokens()
        return token_id

    def get_token(self, token_id: str) -> Optional[OAuthToken]:
        token = self._tokens.get(token_id)
        if token and token.is_expired and token.status == TokenStatus.ACTIVE:
            token.status = TokenStatus.EXPIRED
            self._save_tokens()
        return token

    def get_tokens_for_account(self, account_id: str) -> list[OAuthToken]:
        return [t for t in self._tokens.values() if t.account_id == account_id]

    def refresh_token(self, token_id: str) -> Optional[OAuthToken]:
        token = self._tokens.get(token_id)
        if not token or not token.refresh_token:
            return None
        token.status = TokenStatus.REFRESHING
        self._save_tokens()
        return token

    def revoke_token(self, token_id: str) -> bool:
        token = self._tokens.get(token_id)
        if token:
            token.status = TokenStatus.REVOKED
            self._save_tokens()
            return True
        return False

    def remove_token(self, token_id: str) -> bool:
        if token_id in self._tokens:
            del self._tokens[token_id]
            self._save_tokens()
            return True
        return False

    def clear_account_tokens(self, account_id: str) -> int:
        count = 0
        for tid in list(self._tokens.keys()):
            if self._tokens[tid].account_id == account_id:
                del self._tokens[tid]
                count += 1
        if count:
            self._save_tokens()
        return count

    def get_provider_auth_config(self, provider: str) -> AuthConfig:
        defaults = {
            "telegram": AuthConfig(provider="telegram", auth_flow=OAuthFlow.AUTHORIZATION_CODE, scopes=["read", "send", "files"]),
            "whatsapp": AuthConfig(provider="whatsapp", auth_flow=OAuthFlow.AUTHORIZATION_CODE, scopes=["messages", "media", "templates"]),
            "gmail": AuthConfig(provider="gmail", auth_flow=OAuthFlow.AUTHORIZATION_CODE, scopes=["https://www.googleapis.com/auth/gmail.modify"]),
            "discord": AuthConfig(provider="discord", auth_flow=OAuthFlow.AUTHORIZATION_CODE, scopes=["identify", "email", "guilds", "messages.read"]),
            "slack": AuthConfig(provider="slack", auth_flow=OAuthFlow.AUTHORIZATION_CODE, scopes=["channels:history", "channels:read", "chat:write", "users:read"]),
            "sms": AuthConfig(provider="sms", auth_flow=OAuthFlow.CLIENT_CREDENTIALS),
        }
        return defaults.get(provider, AuthConfig(provider=provider, auth_flow=OAuthFlow.AUTHORIZATION_CODE))
