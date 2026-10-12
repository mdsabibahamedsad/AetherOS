"""
Human approval gates for automations (Master 13 Phases 22-23).

One pending approval per automation, stored at
``~/.aetheros/automation/approvals/<automation_id>.json``::

    {automation_id, name, reason, run_id, step_id, created_at,
     expires_at, status: pending|approved|denied|expired}

Rules:
- dispatch never auto-executes while a gate is pending;
- expired gates resolve to DENIED — execution after expiry is impossible
  by construction (Phase 23);
- resolving is an explicit user action (CLI ``aetheros automation
  approve|deny``).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 3600


def _dir() -> Path:
    from aetheros_constants import get_aetheros_home

    path = get_aetheros_home() / "automation" / "approvals"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def _path(automation_id: str) -> Path:
    return _dir() / f"{automation_id}.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_request(
    automation_id: str,
    name: str,
    reason: str,
    *,
    run_id: str = "",
    step_id: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    timeout_seconds = max(30, int(timeout_seconds))
    request = {
        "automation_id": str(automation_id),
        "name": name,
        "reason": str(reason or "").strip()[:500],
        "run_id": run_id,
        "step_id": step_id,
        "created_at": _now().isoformat(),
        "expires_at": (_now() + timedelta(seconds=timeout_seconds)).isoformat(),
        "status": "pending",
    }
    _write(request)
    return request


def _write(request: Dict[str, Any]) -> None:
    path = _path(request["automation_id"])
    try:
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(request, handle)
        os.replace(tmp_name, path)
    except OSError:
        logger.exception("Failed to persist approval for %s", request.get("automation_id"))


def load(automation_id: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(_path(str(automation_id)).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def pending_request(automation_id: str) -> Optional[Dict[str, Any]]:
    request = load(automation_id)
    if request and request.get("status") == "pending":
        return request
    return None


def is_expired(request: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    if request.get("status") != "pending":
        return False
    try:
        expires = datetime.fromisoformat(str(request.get("expires_at")))
    except (TypeError, ValueError):
        return True
    now = now or _now()
    return expires <= now


def resolve(automation_id: str, approve: bool) -> Optional[Dict[str, Any]]:
    """Approve or deny the pending request. Returns the resolved request."""
    request = load(str(automation_id))
    if not request or request.get("status") != "pending":
        return None
    request["status"] = "approved" if approve else "denied"
    request["resolved_at"] = _now().isoformat()
    _write(request)
    return request


def sweep_expired() -> List[Dict[str, Any]]:
    """Expire any pending-but-stale requests. Returns newly expired ones."""
    expired: List[Dict[str, Any]] = []
    directory = _dir()
    try:
        files = list(directory.glob("*.json"))
    except OSError:
        return []
    for path in files:
        try:
            request = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(request, dict) and is_expired(request):
            request["status"] = "expired"
            request["resolved_at"] = _now().isoformat()
            _write(request)
            expired.append(request)
    return expired
