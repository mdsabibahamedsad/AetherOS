from __future__ import annotations

from typing import Any

from aetheros_voice.core.engine import VoiceEngine
from aetheros_voice.models.models import VoiceConfig, VoiceProfile, Personality, VoiceMode


class VoiceWebAPI:
    def __init__(self, engine: VoiceEngine):
        self._engine = engine

    def get_status(self) -> dict:
        return {
            "state": self._engine.state.summary(),
            "config": self._engine.config_mgr.export_config(),
            "listening": self._engine.state.is_listening,
            "speaking": self._engine.state.is_speaking,
            "mode": self._engine.state.mode.value,
        }

    def get_config(self) -> dict:
        return self._engine.config_mgr.export_config()

    def update_config(self, updates: dict) -> dict:
        self._engine.config_mgr.update(**updates)
        return {"status": "ok", "config": self._engine.config_mgr.export_config()}

    def get_profiles(self) -> list[dict]:
        return [{"name": p.name, "config": p.config.__dict__} for p in self._engine.config_mgr.list_profiles()]

    def save_profile(self, name: str) -> dict:
        profile = VoiceProfile(name=name, config=self._engine.config_mgr.config)
        self._engine.config_mgr.save_profile(profile)
        return {"status": "ok", "profile": name}

    def activate_profile(self, name: str) -> dict:
        ok = self._engine.config_mgr.activate_profile(name)
        return {"status": "ok" if ok else "not_found"}

    def get_history(self, limit: int = 50) -> list[dict]:
        return [{"id": e.id, "text": e.text, "response": e.response, "mode": e.mode, "timestamp": e.timestamp}
                for e in self._engine.history.list(limit=limit)]

    def delete_history(self, entry_id: str | None = None) -> dict:
        if entry_id:
            self._engine.history.delete(entry_id)
        else:
            self._engine.history.clear_all()
        return {"status": "ok"}

    def get_shortcuts(self) -> list[dict]:
        return [{"name": s.name, "phrase": s.phrase} for s in self._engine.commands.list_commands()]

    def test_microphone(self) -> dict:
        devices = self._engine.capture.list_devices()
        return {"status": "ok", "devices": devices, "selected": self._engine.config_mgr.get("mic_device")}

    def get_languages(self) -> dict:
        from aetheros_voice.detector.lang import SUPPORTED_LANGUAGES
        return {"languages": SUPPORTED_LANGUAGES, "current": self._engine.config_mgr.get("language")}

    def get_personalities(self) -> list[dict]:
        return [{"name": p.name, "profile": p.__dict__} for p in self._engine.personality.list_personalities()]
