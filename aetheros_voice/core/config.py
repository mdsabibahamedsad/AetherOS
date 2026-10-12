from __future__ import annotations

import json, os, time, copy
from pathlib import Path
from typing import Any

from aetheros_voice.models.models import VoiceConfig, VoiceProfile


class VoiceConfigManager:
    def __init__(self, config_dir: str | Path | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".aetheros" / "voice"
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._config_dir / "config.json"
        self._profiles_path = self._config_dir / "profiles.json"
        self._config: VoiceConfig = VoiceConfig.defaults()
        self._profiles: dict[str, VoiceProfile] = {}
        self._active_profile: str = "Default"
        self._load()

    @property
    def config(self) -> VoiceConfig:
        return self._config

    @config.setter
    def config(self, value: VoiceConfig):
        self._config = value
        self._save()

    def update(self, **kwargs):
        for key, val in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, val)
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any):
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self._save()

    def reset(self):
        self._config = VoiceConfig.defaults()
        self._save()

    def save_profile(self, profile: VoiceProfile):
        self._profiles[profile.name] = profile
        if self._active_profile == profile.name:
            self._config = profile.config
        self._save_profiles()

    def get_profile(self, name: str) -> VoiceProfile | None:
        return self._profiles.get(name)

    def list_profiles(self) -> list[VoiceProfile]:
        return list(self._profiles.values())

    def delete_profile(self, name: str):
        self._profiles.pop(name, None)
        self._save_profiles()

    def activate_profile(self, name: str) -> bool:
        profile = self._profiles.get(name)
        if profile:
            self._active_profile = name
            self._config = profile.config
            self._save()
            return True
        return False

    def export_config(self) -> dict:
        return {
            "active_profile": self._active_profile,
            "config": {k: v.value if hasattr(v, "value") else v for k, v in self._config.__dict__.items()},
        }

    def import_config(self, data: dict):
        if "config" in data:
            for key, val in data["config"].items():
                if hasattr(self._config, key):
                    setattr(self._config, key, val)
        self._save()

    def _load(self):
        if self._config_path.exists():
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    raw = json.loads(f.read())
                for key, val in raw.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, val)
            except Exception:
                pass
        self._load_profiles()
        if self._active_profile in self._profiles:
            self._config = self._profiles[self._active_profile].config

    def _save(self):
        raw = {}
        for key in VoiceConfig.__dataclass_fields__:
            val = getattr(self._config, key)
            if hasattr(val, "value"):
                raw[key] = val.value
            else:
                raw[key] = val
        self._config_path.write_text(json.dumps(raw, indent=2, default=str))

    def _load_profiles(self):
        if self._profiles_path.exists():
            try:
                raw = json.loads(self._profiles_path.read_text())
                for name, data in raw.items():
                    cfg = VoiceConfig.defaults()
                    if "config" in data:
                        for k, v in data["config"].items():
                            if hasattr(cfg, k):
                                setattr(cfg, k, v)
                    self._profiles[name] = VoiceProfile(
                        id=data.get("id", name), name=name, config=cfg,
                        created_at=data.get("created_at", 0),
                        updated_at=data.get("updated_at", 0),
                    )
                self._active_profile = raw.get("active_profile", "Default")
            except Exception:
                pass
        if not self._profiles:
            self._profiles["Default"] = VoiceProfile(name="Default", config=self._config)

    def _save_profiles(self):
        raw: dict = {}
        for name, profile in self._profiles.items():
            cfg = {}
            for k in VoiceConfig.__dataclass_fields__:
                val = getattr(profile.config, k)
                cfg[k] = val.value if hasattr(val, "value") else val
            raw[name] = {
                "id": profile.id, "config": cfg,
                "created_at": profile.created_at, "updated_at": profile.updated_at,
            }
        raw["active_profile"] = self._active_profile
        self._profiles_path.write_text(json.dumps(raw, indent=2, default=str))
