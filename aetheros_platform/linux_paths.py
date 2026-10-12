"""Linux XDG paths + Hermes migration detection (Master 66).

Canonical layout (new state; existing ~/.aetheros home untouched):

  CONFIG ~/.config/aetheros
  DATA   ~/.local/share/aetheros
  STATE  ~/.local/state/aetheros
  CACHE  ~/.cache/aetheros
  RUNTIME $XDG_RUNTIME_DIR/aetheros (fallback: /tmp/aetheros-$UID)

Secrets NEVER live in cache/logs/runtime. Migration is detect → plan →
copy → verify; never delete legacy; idempotent.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LinuxPaths:
    home: Path
    config: Path
    data: Path
    state: Path
    cache: Path
    logs: Path
    runtime: Path
    artifacts: Path
    backups: Path


def _env(name: str, default: Path) -> Path:
    val = os.environ.get(name, "").strip()
    return Path(val) if val else default


def linux_paths(home: Path | None = None,
                env: dict | None = None) -> LinuxPaths:
    """Pure path resolution; `env` injectable for tests."""
    h = Path(home).expanduser() if home is not None else Path.home()
    e = env if env is not None else os.environ
    get = lambda k, d: Path(e[k]) if str(e.get(k, "")).strip() else d
    config = get("XDG_CONFIG_HOME", h / ".config") / "aetheros"
    data = get("XDG_DATA_HOME", h / ".local" / "share") / "aetheros"
    state = get("XDG_STATE_HOME", h / ".local" / "state") / "aetheros"
    cache = get("XDG_CACHE_HOME", h / ".cache") / "aetheros"
    rt_base = e.get("XDG_RUNTIME_DIR", "").strip()
    runtime = (Path(rt_base) / "aetheros" if rt_base
               else Path(f"/tmp/aetheros-{os.getuid()}") if hasattr(os, "getuid")
               else cache / "runtime")
    return LinuxPaths(home=h, config=config, data=data, state=state,
                      cache=cache, logs=state / "logs", runtime=runtime,
                      artifacts=data / "artifacts", backups=data / "backups")


LEGACY_CANDIDATES = (".hermes", ".config/hermes", ".local/share/hermes",
                     ".cache/hermes", ".local/state/hermes")


def detect_legacy(home: Path | None = None) -> list[dict]:
    """Report legacy Hermes state. Read-only; never migrates or deletes."""
    h = Path(home).expanduser() if home is not None else Path.home()
    found = []
    for rel in LEGACY_CANDIDATES:
        p = h / rel
        if p.exists():
            try:
                files = sum(1 for _ in p.rglob("*") if _.is_file())
            except OSError:
                files = -1
            found.append({"path": str(p), "files": files})
    if os.environ.get("HERMES_HOME", "").strip():
        found.append({"path": os.environ["HERMES_HOME"].strip(),
                      "files": -1, "source": "HERMES_HOME"})
    return found


def plan_migration(sources: list[dict], dest: Path) -> dict:
    """Build a copy-plan (no I/O). Caller executes with backup+verify."""
    return {"sources": [s["path"] for s in sources],
            "destination": str(dest),
            "mode": "copy (never move, never delete source)",
            "idempotent": True}


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
