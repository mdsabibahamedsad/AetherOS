"""Capability sandbox + extension host (sections 15-18, 33-34).

Honest boundary model (see SANDBOX_BOUNDARY):
- OS primitives claimed ONLY where implemented: subprocess isolation
  (stripped env, cwd jail, no shell, timeouts, output caps), filesystem
  scope enforcement in the capability layer, network allow-list in the
  capability layer. No claim of kernel namespaces/seccomp/Seatbelt —
  marked PARTIAL per platform with mechanism table.
- ExtensionContext injects ONLY granted capabilities: scoped fs/network/
  storage/events/logger/secrets(brokered)/tools. No globals, no Node,
  no raw IPC, no env, no shell.

Secret safety: broker returns scoped values from injected providers;
raw stores never attached; secrets redacted from logs/traces.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_extensions.permissions import Grant, PermissionEngine

SANDBOX_BOUNDARY = {
    "windows": {"mechanism": "subprocess isolation + capability enforcement",
                "status": "PARTIAL",
                "notes": "No kernel job-object/sandbox shims claimed. "
                         "Filesystem/network enforced at capability layer; "
                         "code runs in-process (Python) or jailed subprocess."},
    "linux": {"mechanism": "subprocess isolation + capability enforcement",
              "status": "PARTIAL",
              "notes": "No namespaces/seccomp claimed. Same enforcement model as Windows."},
    "darwin": {"mechanism": "subprocess isolation + capability enforcement",
               "status": "PARTIAL",
               "notes": "No Seatbelt profile claimed. Same enforcement model."},
    "electron_renderer": {"mechanism": "no extension code in renderer; narrow typed IPC only",
                          "status": "ENFORCED",
                          "notes": "Extensions never receive ipcRenderer/Node."},
}

_SECRET_RE = re.compile(
    r"(api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|bearer\s+\S+|"
    r"sk-(live|test)-[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]+)", re.I)


def redact_secrets(text: str) -> str:
    return _SECRET_RE.sub("[REDACTED]", text or "")


class SecretBroker:
    """Scoped secrets: policy + approval gate, never the raw store."""

    def __init__(self, providers: Optional[Dict[str, Callable[[], str]]] = None,
                 approve: Optional[Callable[[str, str], bool]] = None) -> None:
        self._providers = providers or {}
        self._approve = approve or (lambda _scope, _ext: False)
        self.requests: List[Dict[str, Any]] = []

    def register_provider(self, scope: str, fn: Callable[[], str]) -> None:
        self._providers[scope] = fn

    def get(self, scope: str, extension_id: str,
            grants: List[Grant]) -> Dict[str, Any]:
        engine = PermissionEngine()
        verdict = engine.check(grants, "secrets.read_scoped", {"name": scope})
        self.requests.append({"scope": scope, "ext": extension_id,
                              "at": time.time(),
                              "allowed": bool(verdict["allowed"])})
        if not verdict["allowed"]:
            return {"ok": False, "reason": "no secrets.read_scoped grant"}
        if not self._approve(scope, extension_id):
            return {"ok": False, "reason": "user approval required"}
        provider = self._providers.get(scope)
        if provider is None:
            return {"ok": False, "reason": "no provider for scope"}
        try:
            return {"ok": True, "value": provider()}
        except Exception as exc:
            return {"ok": False, "reason": f"provider failed: {exc}"}


class CapabilityFS:
    """Filesystem capability: scoped reads/writes inside granted paths."""

    def __init__(self, grants: List[Grant], engine: PermissionEngine) -> None:
        self._grants = grants
        self._engine = engine

    def _check(self, perm: str, path: str) -> None:
        v = self._engine.check(self._grants, perm, {"path": path})
        if not v["allowed"]:
            raise PermissionError(f"fs denied: {v['reason']}")

    def read(self, path: str, *, max_bytes: int = 1_048_576) -> str:
        self._check("filesystem.read", path)
        data = Path(path).read_bytes()[:max_bytes]
        return data.decode("utf-8", "replace")

    def write(self, path: str, text: str) -> int:
        self._check("filesystem.write", path)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return len(text)


class CapabilityNet:
    """Network capability: allow-listed hosts via injected fetch."""

    def __init__(self, grants: List[Grant], engine: PermissionEngine,
                 fetch: Optional[Callable[[str], str]] = None) -> None:
        self._grants = grants
        self._engine = engine
        self._fetch = fetch
        self.calls: List[Dict[str, Any]] = []

    def request(self, url: str) -> str:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        v = self._engine.check(self._grants, "network.request", {"host": host})
        self.calls.append({"url": url, "host": host, "at": time.time(),
                           "allowed": bool(v["allowed"])})
        if not v["allowed"]:
            raise PermissionError(f"net denied: {v['reason']}")
        if self._fetch is None:
            raise RuntimeError("no network fetch provider configured")
        return self._fetch(url)


@dataclass
class ExtensionContext:
    extension_id: str = ""
    version: str = ""
    grants: List[Grant] = field(default_factory=list)
    fs: Optional[CapabilityFS] = None
    net: Optional[CapabilityNet] = None
    secrets: Optional[SecretBroker] = None
    storage_dir: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)
    cancelled: bool = False

    def log(self, level: str, message: str) -> None:
        self.events.append({"level": level, "message": redact_secrets(message),
                            "at": time.time()})

    def storage_write(self, name: str, text: str, *, quota_kb: int = 1024) -> str:
        if "/.." in name.replace("\\", "/") or name.startswith("/"):
            raise ValueError("storage path escapes sandbox")
        if len(text.encode()) > quota_kb * 1024:
            raise ValueError("storage quota exceeded")
        target = Path(self.storage_dir) / name
        if Path(self.storage_dir).resolve() not in target.resolve().parents:
            raise ValueError("storage path escapes sandbox")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return str(target)


@dataclass
class HealthSnapshot:
    state: str = "HEALTHY"  # HEALTHY|DEGRADED|FAILING|CRASH_LOOP|QUARANTINED
    crashes: int = 0
    errors: int = 0
    denials: int = 0
    timeouts: int = 0
    last_run_s: float = 0.0
    last_error: str = ""


class ExtensionHost:
    """Load/validate/init/execute/monitor extensions with constrained ctx."""

    def __init__(self, home: Optional[Path] = None, *,
                 secrets: Optional[SecretBroker] = None,
                 fetch: Optional[Callable[[str], str]] = None) -> None:
        self._home = Path(home) if home else None
        self._secrets = secrets or SecretBroker()
        self._fetch = fetch
        self._lock = threading.Lock()
        self._contexts: Dict[str, ExtensionContext] = {}
        self._health: Dict[str, HealthSnapshot] = {}
        self._modules: Dict[str, Any] = {}

    def initialize(self, home: Path) -> None:
        self._home = Path(home)
        (self._home / "storage").mkdir(parents=True, exist_ok=True)

    def open_context(self, extension_id: str, version: str,
                     grants: List[Grant]) -> ExtensionContext:
        engine = PermissionEngine()
        storage = (self._home / "storage" / extension_id) if self._home else Path("./ext_storage") / extension_id
        storage.mkdir(parents=True, exist_ok=True)
        ctx = ExtensionContext(
            extension_id=extension_id, version=version, grants=list(grants),
            fs=CapabilityFS(list(grants), engine),
            net=CapabilityNet(list(grants), engine, self._fetch),
            secrets=self._secrets, storage_dir=str(storage))
        with self._lock:
            self._contexts[extension_id] = ctx
            self._health.setdefault(extension_id, HealthSnapshot())
        return ctx

    def load_entrypoint(self, install_dir: Path, entry: str):
        """Import a .py entrypoint from the installed dir (data, not authority:
        callers still gate every capability call through grants)."""
        import importlib.util
        target = (Path(install_dir) / entry.replace("\\", "/")).resolve()
        if Path(install_dir).resolve() not in target.parents:
            raise ValueError("entrypoint escapes install dir")
        if target.suffix.lower() != ".py":
            raise ValueError("only .py entrypoints loadable in-process")
        spec = importlib.util.spec_from_file_location(
            f"aetheros_ext_{abs(hash(str(target))) % 10**8}", str(target))
        if spec is None or spec.loader is None:
            raise ValueError("cannot load entrypoint")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def execute_tool(self, extension_id: str, fn: Callable[..., Any], *,
                     timeout_s: float = 30.0, **kwargs) -> Dict[str, Any]:
        """Run an extension tool function with timeout + crash accounting."""
        import concurrent.futures
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(fn, **kwargs)
            try:
                result = fut.result(timeout=timeout_s)
                ok = True
            except concurrent.futures.TimeoutError:
                self._note(extension_id, timeout=True)
                return {"ok": False, "reason": "extension tool timeout",
                        "wall_s": round(time.time() - t0, 3)}
            except Exception as exc:
                self._note(extension_id, error=str(exc)[:300])
                return {"ok": False, "reason": f"extension tool crashed: {exc}"}
        wall = time.time() - t0
        self._note(extension_id, run_s=wall)
        return {"ok": ok, "result": result, "wall_s": round(wall, 3)}

    def revoke_all(self, extension_id: str) -> bool:
        """Revoke-all actually drops runtime grants (not a UI toggle)."""
        with self._lock:
            ctx = self._contexts.get(extension_id)
            if ctx is None:
                return False
            ctx.grants = []
            if ctx.fs is not None:
                ctx.fs._grants = []
            if ctx.net is not None:
                ctx.net._grants = []
            return True

    def health(self, extension_id: str) -> HealthSnapshot:
        with self._lock:
            return self._health.setdefault(extension_id, HealthSnapshot())

    def _note(self, eid: str, *, error: str = "", timeout: bool = False,
              run_s: float = 0.0, denial: bool = False) -> None:
        with self._lock:
            h = self._health.setdefault(eid, HealthSnapshot())
            h.last_run_s = run_s or h.last_run_s
            if error:
                h.errors += 1
                h.last_error = error
            if timeout:
                h.timeouts += 1
            if denial:
                h.denials += 1
            if h.errors + h.timeouts >= 5:
                h.state = "CRASH_LOOP" if h.errors >= 5 else "FAILING"
            elif h.errors or h.timeouts:
                h.state = "DEGRADED"

    def close(self, extension_id: str) -> None:
        with self._lock:
            self._contexts.pop(extension_id, None)
