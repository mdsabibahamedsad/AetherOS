"""Resolve AETHEROS_HOME for standalone skill scripts.

Skill scripts may run outside the Aetheros process (e.g. system Python,
nix env, CI) where ``aetheros_constants`` is not importable.  This module
provides the same ``get_aetheros_home()`` and ``display_aetheros_home()``
contracts as ``aetheros_constants`` without requiring it on ``sys.path``.

When ``aetheros_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``aetheros_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``AETHEROS_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from aetheros_constants import display_aetheros_home as display_aetheros_home
    from aetheros_constants import get_aetheros_home as get_aetheros_home
except (ModuleNotFoundError, ImportError):

    def get_aetheros_home() -> Path:
        """Return the Aetheros home directory (default: ~/.aetheros).

        Mirrors ``aetheros_constants.get_aetheros_home()``."""
        val = os.environ.get("AETHEROS_HOME", "").strip()
        return Path(val) if val else Path.home() / ".aetheros"

    def display_aetheros_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``aetheros_constants.display_aetheros_home()``."""
        home = get_aetheros_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
