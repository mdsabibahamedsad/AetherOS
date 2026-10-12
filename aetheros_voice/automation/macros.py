from __future__ import annotations

import json, os, time, uuid
from pathlib import Path
from typing import Any

from aetheros_voice.models.models import VoiceMacro


class VoiceMacros:
    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(str(Path.home() / ".aetheros" / "voice"), "macros.json")
        self._path = Path(storage_path)
        self._macros: dict[str, VoiceMacro] = {}
        self._load()

    def create(self, name: str, steps: list[str]) -> VoiceMacro:
        macro = VoiceMacro(id=str(uuid.uuid4())[:8], name=name, steps=steps)
        self._macros[name.lower()] = macro
        self._save()
        return macro

    def execute(self, name: str) -> list[str]:
        macro = self._macros.get(name.lower())
        if macro is None:
            return [f"Macro not found: {name}"]
        return macro.steps

    def match(self, text: str) -> VoiceMacro | None:
        lower = text.lower().strip()
        for name, macro in self._macros.items():
            if name in lower or lower == name:
                return macro
        return None

    def list_all(self) -> list[VoiceMacro]:
        return list(self._macros.values())

    def delete(self, name: str):
        self._macros.pop(name.lower(), None)
        self._save()

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                for item in raw:
                    m = VoiceMacro(id=item["id"], name=item["name"], steps=item["steps"])
                    self._macros[item["name"].lower()] = m
            except Exception:
                pass

    def _save(self):
        raw = [{"id": m.id, "name": m.name, "steps": m.steps} for m in self._macros.values()]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(raw, indent=2))
