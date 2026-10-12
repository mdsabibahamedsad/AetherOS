"""
Idempotency store for computer actions (Master 15 Phase 52).

Prevents duplicate side effects caused by retries/restarts: callers derive a
stable key for an irreversible action (submit, download, send), then call
:func:`check_and_record` before executing. First call records and returns
False (proceed); repeats within the TTL return True (duplicate — skip).

Storage: one JSON file under ``<AETHEROS_HOME>/computer_actions/`` — atomic
replace on write, bounded entry count. Keys are caller-supplied opaque hashes;
no payloads or secrets are persisted, only the digest and timestamp.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600
MAX_ENTRIES = 4096


def _store_path():
    from aetheros_constants import get_aetheros_home

    d = get_aetheros_home() / "computer_actions"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d / "idempotency.json"


_lock = threading.Lock()


def _load() -> Dict[str, Any]:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: Dict[str, Any]) -> None:
    path = _store_path()
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        logger.debug("Idempotency save failed", exc_info=True)


def make_key(*parts: str) -> str:
    """Stable digest from arbitrary parts (never store the parts themselves)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


def check_and_record(key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    """Return True when ``key`` was already recorded within TTL (duplicate).

    Records the key otherwise. Expired entries are pruned opportunistically.
    """
    if not key:
        return False
    now = time.time()
    with _lock:
        data = _load()
        entries = data.get("entries", {}) if isinstance(data.get("entries"), dict) else {}
        # prune expired
        entries = {k: v for k, v in entries.items()
                   if isinstance(v, (int, float)) and (now - v) < max(1, ttl_seconds)}
        if key in entries:
            return True
        entries[key] = now
        while len(entries) > MAX_ENTRIES:
            oldest = min(entries, key=lambda k: entries[k])
            del entries[oldest]
        _save({"entries": entries})
        return False


def reset_key(key: str) -> bool:
    """Forget one key so a failed action may be retried later."""
    if not key:
        return False
    with _lock:
        data = _load()
        entries = data.get("entries", {}) if isinstance(data.get("entries"), dict) else {}
        if key in entries:
            del entries[key]
            _save({"entries": entries})
            return True
    return False


def reset() -> None:
    """Test helper: drop all recorded keys."""
    with _lock:
        _save({"entries": {}})
