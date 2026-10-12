"""Jarvis Mode — configuration management.

Persists :class:`JarvisConfig` to the profile-aware AetherOS home directory
as JSON. Never hardcodes ``~/.aetheros`` — always resolves through
``get_aetheros_home()`` so profiles are respected.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_jarvis.models import JarvisConfig, JarvisMode

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover - fallback when not in the full distribution
    def get_aetheros_home() -> Path:  # type: ignore[misc]
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class JarvisConfigManager:
    """Loads and saves Jarvis configuration from the AetherOS home."""

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._lock = threading.RLock()
        self._config_path = self._home / "jarvis" / "config.json"
        self._config: Optional[JarvisConfig] = None
        self._load()

    @property
    def config(self) -> JarvisConfig:
        if self._config is None:
            self._config = JarvisConfig()
        return self._config

    def reload(self) -> None:
        with self._lock:
            self._load()

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            self._save()

    def set_mode(self, mode: JarvisMode) -> None:
        with self._lock:
            self.config.mode = mode
            self._save()

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.config, key, default)

    def export(self) -> Dict[str, Any]:
        with self._lock:
            return self.config.to_dict()

    def _load(self) -> None:
        try:
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = JarvisConfig.from_dict(data)
            else:
                self._config = JarvisConfig()
        except Exception as exc:
            logger.warning("Could not load Jarvis config (%s); using defaults: %s", self._config_path, exc)
            self._config = JarvisConfig()

    def _save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Could not save Jarvis config: %s", exc)
