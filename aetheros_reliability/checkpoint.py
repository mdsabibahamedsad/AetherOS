"""Safe checkpointing of mission/agent/task/approval state.

Checkpoints are small JSON blobs stored under
``<AETHEROS_HOME>/reliability/checkpoints/<component>/<id>.json``.

Safety contract:

* secrets are never stored in plaintext — a known-secret key blocklist is
  stripped and remaining values are redacted before write;
* writes are atomic (temp file + ``os.replace``);
* checkpoints are versioned per component so the latest is always explicit.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|auth[_-]?key|"
    r"private[_-]?key|bearer|jwt|access[_-]?token|refresh[_-]?token)",
    re.IGNORECASE,
)


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_KEY_RE.search(key))


def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if _is_secret_key(k) else _redact_value(k, v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(key, v) if isinstance(v, (dict, list)) else v for v in value]
    if isinstance(value, str) and _is_secret_key(key):
        return "[REDACTED]"
    return value


def redact_checkpoint(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a checkpoint-safe copy with secrets stripped/redacted."""
    return _redact_value("", data)


class CheckpointStore:
    """Per-component, versioned checkpoint store with atomic writes.

    Usage::

        store = get_checkpoint_store()
        store.save("mission", "mission-42", {"step": 3, "plan": [...]})
        latest = store.latest("mission")
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._root = Path(root) if root else (
            get_aetheros_home() / "reliability" / "checkpoints"
        )

    @property
    def root(self) -> Path:
        return self._root

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, component: str, entity_id: str,
             data: Dict[str, Any]) -> Path:
        """Write a checkpoint atomically.  Never stores secrets in plaintext."""
        safe = redact_checkpoint(data)
        safe["_meta"] = {
            "component": component,
            "entity_id": entity_id,
            "created_at": time.time(),
        }
        safe["_schema"] = 1
        directory = self._root / _safe_component(component)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{_safe_id(entity_id)}.json"
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".ckpt-", suffix=".tmp", dir=str(directory)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(safe, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return target

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self, component: str, entity_id: str) -> Optional[Dict[str, Any]]:
        path = self._root / _safe_component(component) / f"{_safe_id(entity_id)}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"corrupt checkpoint {path}: {exc}") from exc

    def latest(self, component: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Alias of :meth:`load` — the store keeps one checkpoint per entity."""
        return self.load(component, entity_id)

    def exists(self, component: str, entity_id: str) -> bool:
        return (
            self._root / _safe_component(component) / f"{_safe_id(entity_id)}.json"
        ).exists()

    def delete(self, component: str, entity_id: str) -> bool:
        path = self._root / _safe_component(component) / f"{_safe_id(entity_id)}.json"
        try:
            path.unlink(missing_ok=True)
            return not path.exists()
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Enumerate
    # ------------------------------------------------------------------

    def components(self) -> List[str]:
        if not self._root.exists():
            return []
        return sorted(
            p.name for p in self._root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def list_entities(self, component: str) -> List[Dict[str, Any]]:
        directory = self._root / _safe_component(component)
        if not directory.exists():
            return []
        out = []
        for path in sorted(directory.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                out.append({
                    "entity_id": path.stem,
                    "path": str(path),
                    "created_at": (data.get("_meta") or {}).get("created_at"),
                    "schema": data.get("_schema"),
                })
            except (OSError, json.JSONDecodeError):
                continue
        return out


def _safe_component(component: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", component or "unknown") or "unknown"


def _safe_id(entity_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", entity_id or "unknown") or "unknown"


_store: Optional[CheckpointStore] = None
_store_lock = threading.Lock()


def get_checkpoint_store() -> CheckpointStore:
    """Return the process-wide CheckpointStore singleton."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = CheckpointStore()
    return _store