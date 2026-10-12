"""Centralized Configuration Manager for AetherOS.

Provides a unified interface for loading, validating, and accessing
configuration from multiple sources:
- config.json (core settings)
- settings.json (user preferences)
- providers.json (provider configurations)
- gateway.json (messaging gateway)
- runtime.json (runtime parameters)
- memory.json (memory system)
- security.json (security settings)

Supports multiple modes: development, production, portable, local, cloud.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigMode(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    PORTABLE = "portable"
    LOCAL = "local"
    CLOUD = "cloud"


class ConfigScope(Enum):
    CORE = "config"
    SETTINGS = "settings"
    PROVIDERS = "providers"
    GATEWAY = "gateway"
    RUNTIME = "runtime"
    MEMORY = "memory"
    SECURITY = "security"


@dataclass
class ConfigFile:
    scope: ConfigScope
    filename: str
    data: Dict[str, Any] = field(default_factory=dict)
    loaded: bool = False
    validated: bool = False


_CONFIG_LOCK = threading.RLock()


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""


class ConfigManager:
    """Centralized configuration manager.

    Usage::

        cm = ConfigManager(aetheros_home=Path("~/.aetheros"))
        cm.load_all()
        value = cm.get("agent.max_iterations", default=90)
        cm.set("display.skin", "mono")
        cm.save()
    """

    def __init__(
        self,
        aetheros_home: Optional[Path] = None,
        mode: ConfigMode = ConfigMode.DEVELOPMENT,
        auto_load: bool = True,
    ) -> None:
        if aetheros_home is None:
            from aetheros_constants import get_aetheros_home
            aetheros_home = get_aetheros_home()
        self._home = aetheros_home
        self._mode = mode
        self._config_dir = aetheros_home / "config"
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._files: Dict[ConfigScope, ConfigFile] = {
            ConfigScope.CORE: ConfigFile(ConfigScope.CORE, "config.json"),
            ConfigScope.SETTINGS: ConfigFile(ConfigScope.SETTINGS, "settings.json"),
            ConfigScope.PROVIDERS: ConfigFile(ConfigScope.PROVIDERS, "providers.json"),
            ConfigScope.GATEWAY: ConfigFile(ConfigScope.GATEWAY, "gateway.json"),
            ConfigScope.RUNTIME: ConfigFile(ConfigScope.RUNTIME, "runtime.json"),
            ConfigScope.MEMORY: ConfigFile(ConfigScope.MEMORY, "memory.json"),
            ConfigScope.SECURITY: ConfigFile(ConfigScope.SECURITY, "security.json"),
        }

        self._merged: Dict[str, Any] = {}
        self._listeners: List[callable] = []

        if auto_load:
            self.load_all()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Load all configuration files from disk."""
        with _CONFIG_LOCK:
            for scope, cf in self._files.items():
                self._load_single(scope)
            self._rebuild_merged()

    def load(self, scope: ConfigScope) -> None:
        """Load a single configuration scope."""
        with _CONFIG_LOCK:
            self._load_single(scope)
            self._rebuild_merged()

    def _load_single(self, scope: ConfigScope) -> None:
        cf = self._files[scope]
        path = self._config_dir / cf.filename
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                cf.data = json.loads(raw) if raw.strip() else {}
                cf.loaded = True
            except (json.JSONDecodeError, OSError) as exc:
                from aetheros_logging import setup_logging
                import logging
                logger = logging.getLogger("aetheros_arch.config")
                logger.warning("Failed to load %s: %s", path, exc)
                cf.data = {}
                cf.loaded = False
        else:
            cf.data = {}
            cf.loaded = False

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-separated key.

        Searches all loaded scopes in priority order (core first).
        """
        parts = key.split(".")
        for scope in ConfigScope:
            cf = self._files[scope]
            if not cf.loaded:
                continue
            val = self._dict_get(cf.data, parts)
            if val is not None:
                return val
        return default

    def get_scope(self, scope: ConfigScope, key: str, default: Any = None) -> Any:
        """Get a value from a specific scope only."""
        cf = self._files[scope]
        if not cf.loaded:
            return default
        return self._dict_get(cf.data, key.split(".")) or default

    def set(self, key: str, value: Any, scope: Optional[ConfigScope] = None) -> None:
        """Set a config value.

        If *scope* is provided, sets it in that scope's data.
        Otherwise, sets it in the core scope.
        """
        with _CONFIG_LOCK:
            target_scope = scope or ConfigScope.CORE
            cf = self._files[target_scope]
            parts = key.split(".")
            self._dict_set(cf.data, parts, value)
            cf.loaded = True
            self._rebuild_merged()

    def has(self, key: str) -> bool:
        """Check if a config key exists in any loaded scope."""
        return self.get(key, _MISSING) is not _MISSING

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, scope: Optional[ConfigScope] = None) -> None:
        """Save configuration to disk."""
        with _CONFIG_LOCK:
            scopes = [scope] if scope else list(ConfigScope)
            for s in scopes:
                cf = self._files[s]
                if not cf.loaded:
                    continue
                path = self._config_dir / cf.filename
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                try:
                    tmp.write_text(
                        json.dumps(cf.data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    tmp.replace(path)
                except OSError as exc:
                    import logging
                    logger = logging.getLogger("aetheros_arch.config")
                    logger.error("Failed to save %s: %s", path, exc)

    def save_all(self) -> None:
        """Save all loaded configuration scopes."""
        for scope in ConfigScope:
            self.save(scope)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, scope: Optional[ConfigScope] = None) -> List[str]:
        """Validate configuration against known schemas.

        Returns a list of validation error messages (empty = valid).
        """
        errors: List[str] = []
        scopes = [scope] if scope else list(ConfigScope)
        for s in scopes:
            cf = self._files[s]
            schema = _SCHEMAS.get(s, {})
            scope_errors = self._validate_dict(cf.data, schema, prefix=s.value)
            errors.extend(scope_errors)
            cf.validated = len(scope_errors) == 0
        return errors

    def validate_all(self) -> List[str]:
        """Validate all loaded scopes."""
        return self.validate()

    # ------------------------------------------------------------------
    # Mode handling
    # ------------------------------------------------------------------

    @property
    def mode(self) -> ConfigMode:
        return self._mode

    @mode.setter
    def mode(self, new_mode: ConfigMode) -> None:
        self._mode = new_mode

    def is_production(self) -> bool:
        return self._mode == ConfigMode.PRODUCTION

    def is_development(self) -> bool:
        return self._mode == ConfigMode.DEVELOPMENT

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_change(self, callback: callable) -> None:
        """Register a callback for config changes.

        The callback receives ``(key, old_value, new_value)``.
        """
        self._listeners.append(callback)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_merged(self) -> None:
        merged: Dict[str, Any] = {}
        for scope in ConfigScope:
            cf = self._files[scope]
            if cf.loaded and cf.data:
                self._deep_merge(merged, cf.data)
        self._merged = merged

    @staticmethod
    def _dict_get(d: Dict[str, Any], parts: List[str]) -> Any:
        current: Any = d
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    @staticmethod
    def _dict_set(d: Dict[str, Any], parts: List[str], value: Any) -> None:
        for part in parts[:-1]:
            if part not in d or not isinstance(d[part], dict):
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _validate_dict(
        data: Dict[str, Any],
        schema: Dict[str, Any],
        prefix: str = "",
    ) -> List[str]:
        errors: List[str] = []
        for key, expected_type in schema.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in data:
                errors.append(f"Missing required key: {full_key}")
                continue
            if expected_type is not None and not isinstance(data[key], expected_type):
                errors.append(
                    f"Type mismatch for {full_key}: "
                    f"expected {expected_type.__name__}, got {type(data[key]).__name__}"
                )
            if isinstance(expected_type, dict):
                nested = data.get(key, {})
                if isinstance(nested, dict):
                    errors.extend(
                        ConfigManager._validate_dict(nested, expected_type, full_key)
                    )
        return errors


_MISSING = object()


_SCHEMAS: Dict[ConfigScope, Dict[str, Any]] = {
    ConfigScope.CORE: {
        "version": str,
        "mode": str,
        "debug": bool,
    },
    ConfigScope.SETTINGS: {
        "theme": str,
        "language": str,
        "notifications": dict,
    },
    ConfigScope.PROVIDERS: {
        "default_provider": str,
        "default_model": str,
    },
    ConfigScope.GATEWAY: {
        "enabled": bool,
        "port": int,
    },
    ConfigScope.RUNTIME: {
        "max_iterations": int,
        "timeout_seconds": int,
    },
    ConfigScope.MEMORY: {
        "enabled": bool,
        "provider": str,
    },
    ConfigScope.SECURITY: {
        "encryption_enabled": bool,
        "sandbox_enabled": bool,
    },
}