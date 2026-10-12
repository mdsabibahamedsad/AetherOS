from __future__ import annotations

import json, os, time, uuid
from pathlib import Path
from typing import Any, Callable

from aetheros_voice.models.models import VoiceCommand, VoiceShortcut


class VoiceShortcuts:
    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(str(Path.home() / ".aetheros" / "voice"), "shortcuts.json")
        self._path = Path(storage_path)
        self._shortcuts: dict[str, VoiceShortcut] = {}
        self._load()

    def create(self, name: str, phrase: str, commands: list[VoiceCommand]) -> VoiceShortcut:
        shortcut = VoiceShortcut(
            id=str(uuid.uuid4())[:8], name=name, phrase=phrase, commands=commands,
        )
        self._shortcuts[phrase.lower()] = shortcut
        self._save()
        return shortcut

    def match(self, text: str) -> VoiceShortcut | None:
        lower = text.lower().strip()
        for phrase, sc in self._shortcuts.items():
            if phrase in lower or lower == phrase:
                return sc
        return None

    def list_all(self) -> list[VoiceShortcut]:
        return list(self._shortcuts.values())

    def delete(self, name: str):
        to_del = [k for k, v in self._shortcuts.items() if v.name == name]
        for k in to_del:
            self._shortcuts.pop(k, None)
        self._save()

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                for item in raw:
                    cmds = [VoiceCommand(**c) for c in item.get("commands", [])]
                    sc = VoiceShortcut(id=item["id"], name=item["name"], phrase=item["phrase"], commands=cmds)
                    self._shortcuts[item["phrase"].lower()] = sc
            except Exception:
                pass

    def _save(self):
        raw = [{"id": s.id, "name": s.name, "phrase": s.phrase, "commands": [c.__dict__ for c in s.commands]}
               for s in self._shortcuts.values()]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(raw, indent=2))
