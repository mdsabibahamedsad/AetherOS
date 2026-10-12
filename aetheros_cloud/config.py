"""Cloud configuration manager — loads config from existing Hermes config.yaml."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_cloud.models import CloudConfig, CloudMode, CloudProvider

logger = logging.getLogger(__name__)


class CloudConfigManager:
    """Manages cloud configuration from config.yaml or environment."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path
        self._config = CloudConfig()
        self._load()

    def _load(self):
        """Load cloud config from Hermes config.yaml if it exists."""
        try:
            from aetheros_cli.config import load_config
            cfg = load_config()
            cloud = cfg.get("cloud", {})
            if cloud:
                self._config.mode = CloudMode(cloud.get("mode", "local"))
                self._config.provider = CloudProvider(cloud.get("provider", "custom"))
                self._config.endpoint = cloud.get("endpoint", "")
                self._config.api_key = cloud.get("api_key", os.getenv("AETHER_CLOUD_KEY", ""))
                self._config.workspace_id = cloud.get("workspace_id", "")
                self._config.user_id = cloud.get("user_id", "")
                self._config.sync_interval = cloud.get("sync_interval", 30)
                self._config.offline_mode = cloud.get("offline_mode", True)
                self._config.auto_sync = cloud.get("auto_sync", True)
                self._config.conflict_strategy = cloud.get("conflict_strategy", "last_write_wins")
                self._config.encryption_enabled = cloud.get("encryption_enabled", True)
        except ImportError:
            logger.debug("Hermes config not available; using default cloud config")
        except Exception as e:
            logger.debug("Error loading cloud config: %s", e)

    @property
    def config(self) -> CloudConfig:
        return self._config

    @property
    def is_cloud_enabled(self) -> bool:
        return self._config.mode != CloudMode.LOCAL

    @property
    def is_offline(self) -> bool:
        return self._config.offline_mode

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        self._save()

    def _save(self):
        try:
            from aetheros_cli.config import save_config_value
            save_config_value("cloud.mode", self._config.mode.value)
            save_config_value("cloud.provider", self._config.provider.value)
            save_config_value("cloud.endpoint", self._config.endpoint)
            save_config_value("cloud.sync_interval", self._config.sync_interval)
            save_config_value("cloud.offline_mode", self._config.offline_mode)
            save_config_value("cloud.auto_sync", self._config.auto_sync)
        except Exception as e:
            logger.debug("Could not save cloud config: %s", e)
