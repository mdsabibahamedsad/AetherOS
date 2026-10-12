from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aetheros_automation.models.models import AutomationConfig, ExecutionMode, AgentRole, Permission


_ENUM_FIELDS = {
    "execution_mode": ExecutionMode,
    "default_agent": AgentRole,
}


class AutomationConfigManager:
    """Manages loading, saving, and mutating the automation configuration."""

    def __init__(self, initial: AutomationConfig | None = None) -> None:
        self._config: AutomationConfig = initial or AutomationConfig()
        self._path: Path = self._resolve_path()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> None:
        if hasattr(self._config, key):
            value = self._convert_enum(key, value)
            setattr(self._config, key, value)
            self._save()
        else:
            msg = f"AutomationConfig has no attribute '{key}'"
            raise AttributeError(msg)

    def update(self, overrides: dict[str, Any]) -> None:
        for key, value in overrides.items():
            if hasattr(self._config, key):
                value = self._convert_enum(key, value)
                setattr(self._config, key, value)
        self._save()

    def reset(self) -> None:
        self._config = AutomationConfig()
        self._save()

    def load(self) -> AutomationConfig:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._config = self._merge(raw)
            except (json.JSONDecodeError, OSError):
                pass
        return self._config

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _convert_enum(self, key: str, value: Any) -> Any:
        enum_cls = _ENUM_FIELDS.get(key)
        if enum_cls is not None and not isinstance(value, enum_cls):
            try:
                return enum_cls(value)
            except (ValueError, TypeError):
                return next(iter(enum_cls))
        return value

    @staticmethod
    def _resolve_path() -> Path:
        home = Path.home() / ".aetheros" / "automation"
        home.mkdir(parents=True, exist_ok=True)
        return home / "config.json"

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(asdict(self._config), indent=2, default=str),
            encoding="utf-8",
        )

    def _merge(self, raw: dict[str, Any]) -> AutomationConfig:
        current = asdict(self._config)
        current.update(raw)
        for key, val in current.items():
            enum_cls = _ENUM_FIELDS.get(key)
            if enum_cls is not None and not isinstance(val, enum_cls):
                try:
                    current[key] = enum_cls(val)
                except (ValueError, TypeError):
                    current[key] = next(iter(enum_cls))
        return AutomationConfig(**current)
