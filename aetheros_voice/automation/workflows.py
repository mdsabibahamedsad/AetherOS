from __future__ import annotations

import json, os, time, uuid
from pathlib import Path
from typing import Any


class VoiceWorkflows:
    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(str(Path.home() / ".aetheros" / "voice"), "workflows.json")
        self._path = Path(storage_path)
        self._workflows: dict[str, dict] = {}
        self._load()

    def create(self, name: str, trigger: str, actions: list[dict]) -> dict:
        wf = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "trigger": trigger,
            "actions": actions,
            "enabled": True,
            "created_at": time.time(),
        }
        self._workflows[name.lower()] = wf
        self._save()
        return wf

    def get(self, name: str) -> dict | None:
        return self._workflows.get(name.lower())

    def match_trigger(self, text: str) -> list[dict]:
        lower = text.lower().strip()
        results = []
        for name, wf in self._workflows.items():
            if wf["enabled"] and (wf["trigger"].lower() in lower or lower == wf["trigger"].lower()):
                results.append(wf)
        return results

    def list_all(self) -> list[dict]:
        return list(self._workflows.values())

    def delete(self, name: str):
        self._workflows.pop(name.lower(), None)
        self._save()

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                for item in raw:
                    self._workflows[item["name"].lower()] = item
            except Exception:
                pass

    def _save(self):
        raw = list(self._workflows.values())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(raw, indent=2))
