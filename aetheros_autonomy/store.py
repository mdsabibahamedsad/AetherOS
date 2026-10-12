"""Durable store: automations + runs + checkpoints (atomic JSON).

Versioned definitions (snapshot on update, rollback), validated
import/export (secrets refused, dangerous actions flagged, UNTRUSTED on
import), retention/deletion support.
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

from aetheros_autonomy.models import AutomationDefinition, RunRecord

_SECRET_RE = re.compile(
    r"(api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|bearer\s+\S+|"
    r"sk-(live|test)-[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]+|"
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)", re.I)

_DANGEROUS = ("delete", "drop", "shutdown", "rm -rf", "format", "publish",
              "deploy", "purchase", "send_email", "upload")


def find_secrets(text: str) -> bool:
    return bool(_SECRET_RE.search(text or ""))


def scan_definition(d: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an automation dict: secrets refused, risks flagged."""
    blob = json.dumps(d, ensure_ascii=False)
    if find_secrets(blob):
        return {"ok": False, "reason": "secret-shaped content in definition"}
    flags = [w for w in _DANGEROUS if w in blob.lower()]
    unknown_tools = [t for t in d.get("tool_policy", {}).get("tools", [])
                     if not isinstance(t, str) or not t]
    if unknown_tools:
        return {"ok": False, "reason": "invalid tool entries"}
    return {"ok": True, "risk_flags": flags}


class AutonomyStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._autos: Dict[str, AutomationDefinition] = {}
        self._runs: Dict[str, RunRecord] = {}
        self._idem: Dict[str, str] = {}  # idempotency_key -> run_id
        self._batch_depth = 0
        self._dirty = False

    def batched(self):
        """Coalesce persistence across a burst of mutations (one write)."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            with self._lock:
                self._batch_depth += 1
            try:
                yield self
            finally:
                with self._lock:
                    self._batch_depth -= 1
                    if self._batch_depth <= 0 and self._dirty:
                        self._dirty = False
                        self._persist()
        return _ctx()

    def _touch(self) -> None:
        if self._batch_depth > 0:
            self._dirty = True
        else:
            self._persist()

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./autonomy_store")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    # -- automations ---------------------------------------------------
    def save_auto(self, a: AutomationDefinition) -> AutomationDefinition:
        with self._lock:
            a.updated_at = time.time()
            self._autos[a.id] = a
            self._touch()
            return a

    def get_auto(self, aid: str) -> Optional[AutomationDefinition]:
        with self._lock:
            return self._autos.get(aid)

    def list_autos(self) -> List[AutomationDefinition]:
        with self._lock:
            return list(self._autos.values())

    def delete_auto(self, aid: str) -> bool:
        with self._lock:
            if aid in self._autos:
                self._autos.pop(aid)
                self._touch()
                return True
            return False

    def update_auto(self, aid: str, patch: Dict[str, Any]) -> Optional[AutomationDefinition]:
        """Versioned update: snapshot current, apply patch, bump version."""
        with self._lock:
            a = self._autos.get(aid)
            if a is None:
                return None
            a.snapshot_version()
            for k, v in patch.items():
                if k in ("id", "history"):
                    continue
                if hasattr(a, k):
                    setattr(a, k, v)
            a.version += 1
            a.updated_at = time.time()
            # Snapshot the new state too so every version is diffable/rollback-able.
            a.history.append({"version": a.version, "at": time.time(),
                              "trigger": dict(a.trigger),
                              "workflow": [dict(s) for s in a.workflow],
                              "tools": list(a.tool_policy.get("tools", []))})
            self._touch()
            return a

    def rollback_auto(self, aid: str, version: int) -> Optional[AutomationDefinition]:
        with self._lock:
            a = self._autos.get(aid)
            if a is None:
                return None
            for snap in reversed(a.history):
                if snap.get("version") == version:
                    a.trigger = dict(snap.get("trigger", {}))
                    a.workflow = list(snap.get("workflow", []))
                    if "tools" in snap:
                        a.tool_policy["tools"] = list(snap["tools"])
                    a.snapshot_version()
                    a.version += 1
                    a.updated_at = time.time()
                    self._touch()
                    return a
            return None

    # -- runs ------------------------------------------------------------
    def save_run(self, r: RunRecord) -> RunRecord:
        with self._lock:
            self._runs[r.run_id] = r
            if r.idempotency_key:
                self._idem[r.idempotency_key] = r.run_id
            self._touch()
            return r

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            return self._runs.get(run_id)

    def find_by_idempotency(self, key: str) -> Optional[RunRecord]:
        with self._lock:
            rid = self._idem.get(key)
            return self._runs.get(rid) if rid else None

    def list_runs(self, *, automation_id: str = "", limit: int = 200) -> List[RunRecord]:
        with self._lock:
            out = [r for r in self._runs.values()
                   if not automation_id or r.automation_id == automation_id]
            out.sort(key=lambda r: r.created_at, reverse=True)
            return out[:limit]

    def prune_runs(self, keep_s: float, *, now: Optional[float] = None) -> int:
        """Retention: drop completed runs older than keep_s."""
        now = now if now is not None else time.time()
        with self._lock:
            drop = [rid for rid, r in self._runs.items()
                    if r.state.value in ("completed", "failed", "cancelled")
                    and (now - r.created_at) > keep_s]
            for rid in drop:
                r = self._runs.pop(rid)
                if r.idempotency_key in self._idem:
                    self._idem.pop(r.idempotency_key)
            if drop:
                self._touch()
            return len(drop)

    # -- export/import -----------------------------------------------------
    def export_auto(self, aid: str) -> Optional[Dict[str, Any]]:
        a = self.get_auto(aid)
        if a is None:
            return None
        d = a.to_dict()
        d.pop("metadata", None)
        return {"format": "aetheros-automation/1", "definition": d}

    def import_auto(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        d = (bundle.get("definition") or {})
        scan = scan_definition(d)
        if not scan["ok"]:
            return {"ok": False, "reason": scan["reason"]}
        a = AutomationDefinition.from_dict(d)
        a.enabled = False  # UNTRUSTED until reviewed
        a.trusted = False
        with self._lock:
            self._autos[a.id] = a
            self._touch()
        return {"ok": True, "id": a.id, "risk_flags": scan.get("risk_flags", [])}

    # -- persistence ---------------------------------------------------------
    def _path(self) -> Path:
        assert self._root is not None
        return self._root / "autonomy.json"

    def _persist(self) -> None:
        if self._root is None:
            return
        data = {"autos": {i: a.to_dict() for i, a in self._autos.items()},
                "runs": {i: r.to_dict() for i, r in self._runs.items()},
                "idem": dict(self._idem)}
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
        for raw in (data.get("autos") or {}).values():
            try:
                a = AutomationDefinition.from_dict(raw)
                self._autos[a.id] = a
            except (ValueError, KeyError):
                continue
        for raw in (data.get("runs") or {}).values():
            try:
                r = RunRecord.from_dict(raw)
                self._runs[r.run_id] = r
                if r.idempotency_key:
                    self._idem[r.idempotency_key] = r.run_id
            except (ValueError, KeyError):
                continue
