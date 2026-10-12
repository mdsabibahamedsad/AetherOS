"""Shared persistence + home helpers for the agent marketplace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    from pathlib import Path as _P

    def get_aetheros_home():  # type: ignore[misc]
        from os import environ
        return _P(environ.get("AETHEROS_HOME", str(_P.home() / ".aetheros")))


def market_home() -> Path:
    home = Path(get_aetheros_home()) / "agent_market"
    home.mkdir(parents=True, exist_ok=True)
    return home


class JsonStore:
    """Atomic JSON dict store: {key: record}. Migrations must be explicit."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._data = raw.get("records", {}) if isinstance(raw, dict) else {}
            except (ValueError, OSError):
                self._data = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"records": self._data}, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self.save()
            return True
        return False

    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    def values(self) -> List[Any]:
        return list(self._data.values())
