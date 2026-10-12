"""Provider Settings Manager — per-provider configuration.

Manages per-provider settings:
temperature, top_p, frequency_penalty, presence_penalty,
reasoning_effort, thinking_mode, streaming, json_mode,
system_prompt, safety, retries, timeout.
"""

from __future__ import annotations

import copy
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_providers.settings")


@dataclass
class ProviderSettings:
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    reasoning_effort: str = "medium"
    thinking_mode: bool = False
    streaming: bool = True
    json_mode: bool = False
    system_prompt: str = ""
    max_retries: int = 3
    timeout_seconds: int = 120
    max_tokens: int = 4096
    safe_mode: bool = False
    custom_headers: Dict[str, str] = field(default_factory=dict)
    extra_body: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "reasoning_effort": self.reasoning_effort,
            "thinking_mode": self.thinking_mode,
            "streaming": self.streaming,
            "json_mode": self.json_mode,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "safe_mode": self.safe_mode,
        }


DEFAULT_PROVIDER_SETTINGS: Dict[str, ProviderSettings] = {
    "openai": ProviderSettings(temperature=0.7, max_tokens=8192),
    "anthropic": ProviderSettings(temperature=0.7, max_tokens=8192, thinking_mode=True),
    "google": ProviderSettings(temperature=0.7, max_tokens=8192),
    "openrouter": ProviderSettings(temperature=0.7, max_tokens=8192),
    "deepseek": ProviderSettings(temperature=0.7, max_tokens=8192),
    "mistral": ProviderSettings(temperature=0.7, max_tokens=8192),
    "cohere": ProviderSettings(temperature=0.3, max_tokens=4096),
    "together": ProviderSettings(temperature=0.7, max_tokens=4096),
    "groq": ProviderSettings(temperature=0.7, max_tokens=8192),
    "xai": ProviderSettings(temperature=0.7, max_tokens=8192),
    "ollama": ProviderSettings(temperature=0.7, max_tokens=4096),
    "lm_studio": ProviderSettings(temperature=0.7, max_tokens=4096),
}


class ProviderSettingsManager:
    """Per-provider settings management.

    Stores provider-specific parameters with defaults.
    Supports JSON persistence.
    """

    def __init__(self, settings_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._settings: Dict[str, ProviderSettings] = {}
        self._settings_dir = settings_dir

        self._load_defaults()

        if settings_dir:
            self._settings_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # Settings access
    # ------------------------------------------------------------------

    def get_settings(self, provider: str) -> ProviderSettings:
        with self._lock:
            if provider in self._settings:
                return self._settings[provider]
            return ProviderSettings()

    def set_settings(self, provider: str, settings: ProviderSettings) -> None:
        with self._lock:
            self._settings[provider] = settings
            self._save()
            logger.info("Settings updated for %s", provider)

    def update_setting(self, provider: str, key: str, value: Any) -> bool:
        with self._lock:
            if provider not in self._settings:
                self._settings[provider] = ProviderSettings()
            settings = self._settings[provider]
            if hasattr(settings, key):
                setattr(settings, key, value)
                self._save()
                logger.info("Setting %s.%s = %s", provider, key, value)
                return True
            return False

    def get_setting(self, provider: str, key: str, default: Any = None) -> Any:
        settings = self.get_settings(provider)
        return getattr(settings, key, default)

    def reset_to_default(self, provider: Optional[str] = None) -> None:
        with self._lock:
            if provider:
                self._settings.pop(provider, None)
            else:
                self._settings.clear()
            self._load_defaults()
            self._save()

    def list_configured_providers(self) -> List[str]:
        with self._lock:
            return list(self._settings.keys())

    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                provider: settings.to_dict()
                for provider, settings in self._settings.items()
            }

    def _load_defaults(self) -> None:
        for provider, settings in DEFAULT_PROVIDER_SETTINGS.items():
            if provider not in self._settings:
                self._settings[provider] = copy.deepcopy(settings)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._settings_dir:
            return
        try:
            data = {}
            for provider, settings in self._settings.items():
                data[provider] = settings.to_dict()
            config_file = self._settings_dir / "provider_settings.json"
            tmp = config_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(config_file)
        except Exception as exc:
            logger.warning("Failed to save provider settings: %s", exc)

    def _load(self) -> None:
        if not self._settings_dir:
            return
        config_file = self._settings_dir / "provider_settings.json"
        if not config_file.exists():
            return
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            for provider, raw in data.items():
                settings = ProviderSettings(
                    temperature=raw.get("temperature", 0.7),
                    top_p=raw.get("top_p", 1.0),
                    frequency_penalty=raw.get("frequency_penalty", 0.0),
                    presence_penalty=raw.get("presence_penalty", 0.0),
                    reasoning_effort=raw.get("reasoning_effort", "medium"),
                    thinking_mode=raw.get("thinking_mode", False),
                    streaming=raw.get("streaming", True),
                    json_mode=raw.get("json_mode", False),
                    max_retries=raw.get("max_retries", 3),
                    timeout_seconds=raw.get("timeout_seconds", 120),
                    max_tokens=raw.get("max_tokens", 4096),
                    safe_mode=raw.get("safe_mode", False),
                )
                self._settings[provider] = settings
        except Exception as exc:
            logger.warning("Failed to load provider settings: %s", exc)

    # ------------------------------------------------------------------
    # API kwargs builder
    # ------------------------------------------------------------------

    def build_api_kwargs(self, provider: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build API kwargs dict from settings with optional overrides."""
        settings = self.get_settings(provider)
        kwargs = {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "frequency_penalty": settings.frequency_penalty,
            "presence_penalty": settings.presence_penalty,
            "stream": settings.streaming,
            "max_tokens": settings.max_tokens,
        }
        if overrides:
            kwargs.update(overrides)
        return kwargs

    def summary(self) -> str:
        lines = ["Provider Settings:"]
        with self._lock:
            for provider, settings in sorted(self._settings.items()):
                lines.append(
                    f"  {provider:20s} temp={settings.temperature:.1f} "
                    f"top_p={settings.top_p:.1f} "
                    f"stream={settings.streaming} "
                    f"retries={settings.max_retries} "
                    f"timeout={settings.timeout_seconds}s"
                )
        return "\n".join(lines)