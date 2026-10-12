"""Jarvis Mode — voice personalization.

Manages named voice profiles (multiple voices, speaking speed, pitch,
language, emotion). Profiles persist to the Jarvis config directory and can
be switched at runtime.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_jarvis.models import VoiceProfileData

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    import os

    def get_aetheros_home() -> Path:
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class VoicePersonalization:
    """Profile-based voice customization.

    Profiles are persisted to ``<home>/jarvis/voice_profiles.json``.
    ``active`` names the current profile; ``apply_to`` pushes the profile's
    settings into a target object (e.g. the voice config) when it exposes the
    matching attributes.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._path = self._home / "jarvis" / "voice_profiles.json"
        self._lock = threading.RLock()
        self._profiles: Dict[str, VoiceProfileData] = {}
        self._active: str = "default"
        self._load()

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    def create(self, name: str, **overrides: Any) -> VoiceProfileData:
        profile = VoiceProfileData(name=name)
        for key, value in overrides.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        with self._lock:
            self._profiles[name] = profile
            self._save()
        return profile

    def get(self, name: Optional[str] = None) -> Optional[VoiceProfileData]:
        name = name or self._active
        with self._lock:
            return self._profiles.get(name)

    def update(self, name: str, **overrides: Any) -> Optional[VoiceProfileData]:
        with self._lock:
            profile = self._profiles.get(name)
            if profile is None:
                return None
            for key, value in overrides.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            self._save()
            return profile

    def delete(self, name: str) -> bool:
        with self._lock:
            if name not in self._profiles or name == "default":
                return False
            del self._profiles[name]
            if self._active == name:
                self._active = "default"
            self._save()
            return True

    def list_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {**profile.to_dict(), "active": name == self._active}
                for name, profile in self._profiles.items()
            ]

    def set_active(self, name: str) -> bool:
        with self._lock:
            if name not in self._profiles:
                return False
            self._active = name
            self._save()
            return True

    @property
    def active(self) -> VoiceProfileData:
        with self._lock:
            return self._profiles.get(self._active, VoiceProfileData(name="default"))

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def apply_to(self, target: Any) -> Dict[str, Any]:
        """Copy the active profile's settings onto a compatible target."""
        profile = self.active
        applied = {}
        for attr in ("voice", "speed", "pitch", "language", "emotion"):
            value = getattr(profile, attr)
            if value and hasattr(target, attr):
                try:
                    setattr(target, attr, value)
                    applied[attr] = value
                except Exception:
                    pass
        return applied

    def snapshot(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "profiles": [p.name for p in self._profiles.values()],
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._profiles = {name: VoiceProfileData.from_dict(p) for name, p in data.get("profiles", {}).items()}
                self._active = data.get("active", "default")
            if "default" not in self._profiles:
                self._profiles["default"] = VoiceProfileData(name="default")
                self._save()
        except Exception as exc:
            logger.warning("Could not load voice profiles: %s", exc)
            self._profiles = {"default": VoiceProfileData(name="default")}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active": self._active,
                "profiles": {name: p.to_dict() for name, p in self._profiles.items()},
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Could not save voice profiles: %s", exc)
