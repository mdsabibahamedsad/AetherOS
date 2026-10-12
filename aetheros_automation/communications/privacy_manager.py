from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ProcessingScope(Enum):
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    HYBRID = "hybrid"


class DataRetentionPolicy(Enum):
    KEEP_ALL = "keep_all"
    KEEP_30_DAYS = "keep_30_days"
    KEEP_90_DAYS = "keep_90_days"
    KEEP_1_YEAR = "keep_1_year"
    DELETE_AFTER_READ = "delete_after_read"
    CUSTOM = "custom"


@dataclass
class PrivacySettings:
    ai_processing_enabled: bool = True
    ai_processing_provider: ProcessingScope = ProcessingScope.LOCAL_ONLY
    memory_enabled: bool = True
    cloud_sync_enabled: bool = False
    data_retention: DataRetentionPolicy = DataRetentionPolicy.KEEP_90_DAYS
    share_usage_stats: bool = False
    allow_caching: bool = True
    allow_search_indexing: bool = True
    anonymize_data: bool = True
    delete_on_disconnect: bool = False
    custom_retention_days: int = 0


@dataclass
class ConnectedAccount:
    provider: str
    label: str
    connected_at: datetime
    permissions: list[str] = field(default_factory=list)
    data_accessed: list[str] = field(default_factory=list)
    last_access: Optional[datetime] = None


class PrivacyManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._settings: PrivacySettings = PrivacySettings()
        self._accounts: dict[str, ConnectedAccount] = {}
        self._audit_log: list[dict] = []
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "privacy.json"

    def _load(self):
        if self._path().exists():
            try:
                data = json.loads(self._path().read_text())
                settings_data = data.get("settings", {})
                self._settings = PrivacySettings(
                    ai_processing_enabled=settings_data.get("ai_processing_enabled", True),
                    ai_processing_provider=ProcessingScope(settings_data.get("ai_processing_provider", "local_only")),
                    memory_enabled=settings_data.get("memory_enabled", True),
                    cloud_sync_enabled=settings_data.get("cloud_sync_enabled", False),
                    data_retention=DataRetentionPolicy(settings_data.get("data_retention", "keep_90_days")),
                    share_usage_stats=settings_data.get("share_usage_stats", False),
                    allow_caching=settings_data.get("allow_caching", True),
                    allow_search_indexing=settings_data.get("allow_search_indexing", True),
                    anonymize_data=settings_data.get("anonymize_data", True),
                    delete_on_disconnect=settings_data.get("delete_on_disconnect", False),
                    custom_retention_days=settings_data.get("custom_retention_days", 0),
                )
                for acc_data in data.get("accounts", []):
                    acc = ConnectedAccount(
                        provider=acc_data["provider"],
                        label=acc_data.get("label", ""),
                        connected_at=datetime.fromisoformat(acc_data["connected_at"]),
                        permissions=acc_data.get("permissions", []),
                        data_accessed=acc_data.get("data_accessed", []),
                        last_access=datetime.fromisoformat(acc_data["last_access"]) if acc_data.get("last_access") else None,
                    )
                    self._accounts[acc.provider] = acc
                self._audit_log = data.get("audit_log", [])
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

    def _save(self):
        data = {
            "settings": {
                "ai_processing_enabled": self._settings.ai_processing_enabled,
                "ai_processing_provider": self._settings.ai_processing_provider.value,
                "memory_enabled": self._settings.memory_enabled,
                "cloud_sync_enabled": self._settings.cloud_sync_enabled,
                "data_retention": self._settings.data_retention.value,
                "share_usage_stats": self._settings.share_usage_stats,
                "allow_caching": self._settings.allow_caching,
                "allow_search_indexing": self._settings.allow_search_indexing,
                "anonymize_data": self._settings.anonymize_data,
                "delete_on_disconnect": self._settings.delete_on_disconnect,
                "custom_retention_days": self._settings.custom_retention_days,
            },
            "accounts": [
                {
                    "provider": a.provider,
                    "label": a.label,
                    "connected_at": a.connected_at.isoformat(),
                    "permissions": a.permissions,
                    "data_accessed": a.data_accessed,
                    "last_access": a.last_access.isoformat() if a.last_access else None,
                }
                for a in self._accounts.values()
            ],
            "audit_log": self._audit_log[-1000:],
        }
        self._path().write_text(json.dumps(data, indent=2, default=str))

    def get_settings(self) -> PrivacySettings:
        return self._settings

    def update_settings(self, **kwargs) -> PrivacySettings:
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self._save()
        return self._settings

    def get_connected_accounts(self) -> list[ConnectedAccount]:
        return list(self._accounts.values())

    def register_account_access(self, provider: str, label: str, permissions: list[str]):
        if provider not in self._accounts:
            self._accounts[provider] = ConnectedAccount(
                provider=provider,
                label=label,
                connected_at=datetime.now(),
                permissions=permissions,
            )
        else:
            self._accounts[provider].last_access = datetime.now()
            self._accounts[provider].data_accessed.extend(permissions)
            self._accounts[provider].data_accessed = list(set(self._accounts[provider].data_accessed))
        self._save()

    def remove_account(self, provider: str) -> bool:
        if provider in self._accounts:
            if self._settings.delete_on_disconnect:
                self._audit_log = [e for e in self._audit_log if e.get("provider") != provider]
            del self._accounts[provider]
            self._save()
            return True
        return False

    def log_access(self, action: str, provider: str, details: str = ""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "provider": provider,
            "details": details,
        }
        self._audit_log.append(entry)
        self._save()

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        return self._audit_log[-limit:]

    def clear_audit_log(self):
        self._audit_log.clear()
        self._save()

    def clear_all_data(self):
        self._accounts.clear()
        self._audit_log.clear()
        self._save()

    def can_process_with_ai(self, content_type: str = "") -> bool:
        return self._settings.ai_processing_enabled

    def is_memory_enabled(self) -> bool:
        return self._settings.memory_enabled

    def get_data_retention_days(self) -> int:
        mapping = {
            DataRetentionPolicy.KEEP_ALL: 0,
            DataRetentionPolicy.KEEP_30_DAYS: 30,
            DataRetentionPolicy.KEEP_90_DAYS: 90,
            DataRetentionPolicy.KEEP_1_YEAR: 365,
            DataRetentionPolicy.DELETE_AFTER_READ: 0,
            DataRetentionPolicy.CUSTOM: self._settings.custom_retention_days,
        }
        return mapping.get(self._settings.data_retention, 90)

    def should_purge(self, item_date: datetime) -> bool:
        days = self.get_data_retention_days()
        if days <= 0:
            return False
        age = (datetime.now() - item_date).days
        return age > days

    def get_ai_processing_summary(self) -> dict:
        return {
            "enabled": self._settings.ai_processing_enabled,
            "scope": self._settings.ai_processing_provider.value,
            "memory_enabled": self._settings.memory_enabled,
            "cloud_sync": self._settings.cloud_sync_enabled,
        }
