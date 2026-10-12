"""Extension registry: discovery, state, deps, health, compat, updates.

Single canonical registry for all 14 types and all sources
(local/bundled/remote/private/org/offline). Persists ExtensionRecord +
InstallationRecord + health + update/rollback pointers as atomic JSON
(profile-aware root, same pattern as sibling stores).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aetheros_extensions.manifest import (
    ExtensionManifest, ExtensionType, LifecycleState, can_transition,
)


@dataclass
class ExtensionRecord:
    id: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)
    source: str = "local"  # local|bundled|remote|git|private|org|builtin
    source_ref: str = ""
    state: str = LifecycleState.DISCOVERED.value
    installed_version: str = ""
    available_version: str = ""
    previous_version: str = ""
    install_path: str = ""
    trust_level: str = "unsigned"
    publisher_trust: str = "unknown"
    grants: List[Dict[str, Any]] = field(default_factory=list)
    health: Dict[str, Any] = field(default_factory=dict)
    quarantine: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    installed_at: float = 0.0

    def set_state(self, nxt: str) -> None:
        frm = LifecycleState(self.state)
        to = LifecycleState(nxt)
        if not can_transition(frm, to):
            raise ValueError(f"illegal transition {frm.value} -> {to.value}")
        self.state = to.value
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in (
            "id", "manifest", "source", "source_ref", "state",
            "installed_version", "available_version", "previous_version",
            "install_path", "trust_level", "publisher_trust", "grants",
            "health", "quarantine", "created_at", "updated_at",
            "installed_at")}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExtensionRecord":
        r = cls()
        for k in ("id", "source", "source_ref", "state",
                  "installed_version", "available_version",
                  "previous_version", "install_path", "trust_level",
                  "publisher_trust", "created_at", "updated_at",
                  "installed_at"):
            if k in d:
                setattr(r, k, d[k])
        r.manifest = dict(d.get("manifest", {}))
        r.grants = list(d.get("grants", []))
        r.health = dict(d.get("health", {}))
        r.quarantine = dict(d.get("quarantine", {}))
        return r


def _parse_version(v: str) -> Tuple[int, ...]:
    core = str(v).split("-")[0].split("+")[0]
    parts = []
    for seg in core.split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            parts.append(0)
    return tuple(parts + [0] * (3 - len(parts)))


def satisfies(spec: str, version: str) -> bool:
    """Minimal range check: exact, >=, ^, ~. Unknown specs fail closed."""
    spec = (spec or "").strip()
    if not spec or spec == "*":
        return False
    try:
        if spec.startswith(">="):
            return _parse_version(version) >= _parse_version(spec[2:])
        if spec.startswith("^"):
            base = _parse_version(spec[1:])
            return base <= _parse_version(version) < (base[0] + 1, 0, 0)
        if spec.startswith("~"):
            base = _parse_version(spec[1:])
            return base <= _parse_version(version) < (base[0], base[1] + 1, 0)
        return _parse_version(version) == _parse_version(spec)
    except (ValueError, IndexError):
        return False


def check_compat(manifest: Dict[str, Any], *, engine: str = "44",
                 platform: str = "windows", arch: str = "x64",
                 api: str = "1") -> Dict[str, Any]:
    warnings: List[str] = []
    eng = str(manifest.get("engineVersion", "") or engine)
    try:
        ok_engine = int(eng) <= int(engine)
    except ValueError:
        return {"verdict": "INCOMPATIBLE", "reason": "bad engineVersion", "warnings": []}
    if not ok_engine:
        return {"verdict": "INCOMPATIBLE",
                "reason": f"requires engine {eng}, have {engine}", "warnings": []}
    if str(manifest.get("apiVersion", "1")) != api:
        return {"verdict": "INCOMPATIBLE",
                "reason": f"requires api {manifest.get('apiVersion')}", "warnings": []}
    plats = manifest.get("platformSupport") or manifest.get("platforms") or []
    if plats and platform not in [str(p).lower() for p in plats]:
        return {"verdict": "INCOMPATIBLE",
                "reason": f"platform {platform} unsupported", "warnings": []}
    archs = manifest.get("architectureSupport") or manifest.get("architectures") or []
    if archs and arch not in [str(a).lower() for a in archs]:
        warnings.append(f"arch {arch} not listed")
        return {"verdict": "COMPATIBLE_WITH_WARNINGS", "reason": "", "warnings": warnings}
    return {"verdict": "COMPATIBLE", "reason": "", "warnings": warnings}


class ExtensionRegistry:
    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._records: Dict[str, ExtensionRecord] = {}

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./extensions_registry")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    # -- CRUD ----------------------------------------------------------
    def upsert(self, rec: ExtensionRecord) -> ExtensionRecord:
        with self._lock:
            self._records[rec.id] = rec
            self._persist()
            return rec

    def get(self, eid: str) -> Optional[ExtensionRecord]:
        with self._lock:
            return self._records.get(eid)

    def list(self, *, ext_type: str = "", state: str = "",
             query: str = "") -> List[ExtensionRecord]:
        with self._lock:
            out = list(self._records.values())
        if ext_type:
            out = [r for r in out
                   if str(r.manifest.get("extension_type", "")) == ext_type]
        if state:
            out = [r for r in out if r.state == state]
        if query:
            q = query.lower()
            out = [r for r in out if q in (
                str(r.manifest.get("name", "")) + " " +
                str(r.manifest.get("description", "")) + " " + r.id).lower()]
        return sorted(out, key=lambda r: r.id)

    def remove(self, eid: str) -> bool:
        with self._lock:
            if eid in self._records:
                self._records.pop(eid)
                self._persist()
                return True
            return False

    # -- dependencies ----------------------------------------------------
    def resolve(self, manifest: ExtensionManifest) -> Dict[str, Any]:
        """Resolve + lock deps against installed records. Fail closed."""
        locked: Dict[str, str] = {}
        problems: List[str] = []
        with self._lock:
            for dep, spec in manifest.dependencies.items():
                rec = self._records.get(dep)
                if rec is None or not rec.installed_version:
                    problems.append(f"missing dependency: {dep} {spec}")
                    continue
                if not satisfies(spec, rec.installed_version):
                    problems.append(
                        f"dependency mismatch: {dep} needs {spec}, have {rec.installed_version}")
                    continue
                locked[dep] = rec.installed_version
            # Cycle check over install graph + candidate.
            graph = {rid: [d for d in (r.manifest.get("dependencies") or {})]
                     for rid, r in self._records.items()}
            graph[manifest.id] = list(manifest.dependencies)
            if _has_cycle(graph):
                problems.append("dependency cycle detected")
        return {"ok": not problems, "problems": problems, "locked": locked}

    # -- health ------------------------------------------------------------
    def record_health(self, eid: str, health: Dict[str, Any]) -> None:
        with self._lock:
            rec = self._records.get(eid)
            if rec is None:
                return
            rec.health = health
            self._persist()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_state: Dict[str, int] = {}
            by_type: Dict[str, int] = {}
            for r in self._records.values():
                by_state[r.state] = by_state.get(r.state, 0) + 1
                t = str(r.manifest.get("extension_type", "unknown"))
                by_type[t] = by_type.get(t, 0) + 1
            return {"total": len(self._records), "by_state": by_state,
                    "by_type": by_type}

    # -- persistence -------------------------------------------------------
    def _path(self) -> Path:
        assert self._root is not None
        return self._root / "registry.json"

    def _persist(self) -> None:
        if self._root is None:
            return
        data = {rid: r.to_dict() for rid, r in self._records.items()}
        fd, tmp = tempfile.mkstemp(dir=str(self._root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, str(self._path()))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _load(self) -> None:
        path = self._path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for rid, raw in (data or {}).items():
            try:
                self._records[rid] = ExtensionRecord.from_dict(raw)
            except (ValueError, KeyError):
                continue


def _has_cycle(graph: Dict[str, List[str]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def dfs(n: str) -> bool:
        color[n] = GRAY
        for m in graph.get(n, []):
            if m not in color:
                continue
            if color[m] == GRAY:
                return True
            if color[m] == WHITE and dfs(m):
                return True
        color[n] = BLACK
        return False

    return any(dfs(n) for n in graph if color[n] == WHITE)
