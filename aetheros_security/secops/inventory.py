"""
Component inventory + integrity monitoring + config drift.

The SecOps layer keeps an inventory of the components it protects (backend,
gateway, agents, tools, MCP, plugins, skills, config, model providers) so it
can detect:

    - integrity drift (a security-relevant file's hash changed),
    - config drift (a tracked config value differs from the expected value),
    - newly discovered components (supply-chain surface).

Integrity checks are deterministic (sha256 over file content).  The
inventory is the source of truth the forensics module uses when correlating
"what changed right before this incident".
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComponentRecord:
    """A tracked component."""

    component_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    kind: str = ""                 # backend | gateway | agent | tool | mcp | plugin | skill | config | provider
    version: str = ""
    discovered_at: float = field(default_factory=time.time)
    integrity_hashes: Dict[str, str] = field(default_factory=dict)   # path -> sha256
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "kind": self.kind,
            "version": self.version,
            "discovered_at": self.discovered_at,
            "integrity_files": len(self.integrity_hashes),
            "metadata": dict(self.metadata),
        }


@dataclass
class IntegrityResult:
    component_id: str
    name: str
    ok: bool
    changes: List[Dict[str, Any]] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "ok": self.ok,
            "changes": list(self.changes),
            "checked_at": self.checked_at,
        }


def sha256_file(path: str) -> str:
    """Deterministic sha256 of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class ComponentInventory:
    """Tracks components, their integrity hashes and expected config values.

    Usage::

        inv = ComponentInventory()
        inv.register("agent-core", kind="agent", version="1.0",
                     integrity_files=["path/to/file.py"])
        result = inv.check_integrity("agent-core")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._components: Dict[str, ComponentRecord] = {}
        self._expected_config: Dict[str, Dict[str, Any]] = {}   # name -> expected values
        self._results: List[IntegrityResult] = []
        self._max_results = 200

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, *, kind: str = "",
                 version: str = "",
                 integrity_files: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> ComponentRecord:
        record = ComponentRecord(name=name, kind=kind, version=version,
                                 metadata=metadata or {})
        for path in integrity_files or []:
            try:
                record.integrity_hashes[path] = sha256_file(path)
            except Exception as exc:
                logger.debug("Could not hash %s: %s", path, exc)
        with self._lock:
            self._components[record.component_id] = record
        return record

    def register_config_expected(self, name: str, values: Dict[str, Any]) -> None:
        with self._lock:
            self._expected_config[name] = dict(values)

    def get(self, component_id: str) -> Optional[ComponentRecord]:
        with self._lock:
            return self._components.get(component_id)

    def list(self, kind: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._components.values())
        return [r.to_dict() for r in records
                if not kind or r.kind == kind]

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def check_integrity(self, component_id: str) -> Optional[IntegrityResult]:
        """Re-hash a component's tracked files; report any change."""
        with self._lock:
            record = self._components.get(component_id)
        if record is None:
            return None
        changes = []
        for path, expected in record.integrity_hashes.items():
            try:
                current = sha256_file(path)
            except Exception as exc:
                current = f"unreadable:{exc}"
            if current != expected:
                changes.append({"path": path, "expected": expected,
                                "current": current})
        result = IntegrityResult(component_id=record.component_id,
                                 name=record.name, ok=not changes,
                                 changes=changes)
        with self._lock:
            self._results.append(result)
            if len(self._results) > self._max_results:
                self._results = self._results[-self._max_results:]
        return result

    def check_all(self) -> List[IntegrityResult]:
        with self._lock:
            ids = list(self._components.keys())
        return [r for r in (self.check_integrity(i) for i in ids) if r is not None]

    def integrity_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._results[-limit:]]

    # ------------------------------------------------------------------
    # Config drift
    # ------------------------------------------------------------------

    def check_config_drift(self, name: str,
                           current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare a current config snapshot against the expected values."""
        with self._lock:
            expected = self._expected_config.get(name, {})
        changes = []
        for key, want in expected.items():
            got = current.get(key, "<missing>")
            if got != want:
                changes.append({"key": key, "expected": want, "current": got})
        return {
            "name": name,
            "drift": bool(changes),
            "changes": changes,
            "checked_at": time.time(),
        }

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "components": len(self._components),
                "kinds": sorted({r.kind for r in self._components.values()}),
                "expected_configs": len(self._expected_config),
                "integrity_checks": len(self._results),
            }


# Global component inventory
_component_inventory: Optional[ComponentInventory] = None


def get_component_inventory() -> ComponentInventory:
    """Return the process-wide ComponentInventory singleton."""
    global _component_inventory
    if _component_inventory is None:
        _component_inventory = ComponentInventory()
    return _component_inventory