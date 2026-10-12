"""macOS filesystem paths (Master 65).

Canonical AetherOS home is UNCHANGED (`~/.aetheros` on macOS — moving
existing users to ~/Library would be a breaking migration). This module
maps satellite state to macOS conventions for NEW state only:

  CONFIG    ~/Library/Application Support/AetherOS
  DATA      ~/Library/Application Support/AetherOS/Data
  CACHE     ~/Library/Caches/AetherOS
  LOGS      ~/Library/Logs/AetherOS
  RUNTIME   ~/Library/Application Support/AetherOS/Runtime
  ARTIFACTS ~/Library/Application Support/AetherOS/Artifacts
  BACKUPS   ~/Library/Application Support/AetherOS/Backups

Never mix secrets into cache/logs. Pure path logic; `home` injectable
so tests run on any platform.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MacOSPaths:
    home: Path
    config: Path
    data: Path
    cache: Path
    logs: Path
    runtime: Path
    artifacts: Path
    backups: Path


def macos_paths(home: Path | None = None) -> MacOSPaths:
    """Resolve satellite paths. `home` override is for tests/tools only."""
    user_home = Path(home).expanduser() if home is not None else Path.home()
    library = user_home / "Library"
    support = library / "Application Support" / "AetherOS"
    return MacOSPaths(
        home=user_home,
        config=support,
        data=support / "Data",
        cache=library / "Caches" / "AetherOS",
        logs=library / "Logs" / "AetherOS",
        runtime=support / "Runtime",
        artifacts=support / "Artifacts",
        backups=support / "Backups",
    )


def secrets_may_live_here(kind: str) -> bool:
    """Secrets belong in Keychain or encrypted vault — never cache/logs."""
    return kind in ("config", "data", "runtime")
