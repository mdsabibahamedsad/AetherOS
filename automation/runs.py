"""
Durable workflow run state (Master 13 Phases 38-42).

One JSON file per run under ``~/.aetheros/automation/runs/``::

    {run_id, automation_id, name, definition_version, status,
     steps: {id: {status, output, error, attempts}},
     created_at, updated_at}

Checkpoint discipline (Phase 39): the file is rewritten only on step
milestones — never per tool call. Resume (Phase 40): a run found in
running/paused/waiting_approval after restart continues from its completed
steps; steps already marked ``done`` are never re-executed (Phase 42
idempotency at step granularity). Cancellation (Phase 47) is checked between
steps; an in-flight step finishes naturally and is honored.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("running", "paused", "waiting_approval")
TERMINAL_STATUSES = ("completed", "failed", "cancelled", "expired")


def runs_dir() -> Path:
    from aetheros_constants import get_aetheros_home

    path = get_aetheros_home() / "automation" / "runs"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run(automation_id: str, name: str, definition_version: Any, workflow: Dict[str, Any]) -> Dict[str, Any]:
    run = {
        "run_id": uuid.uuid4().hex[:16],
        "automation_id": automation_id,
        "name": name,
        # Phase 19: executions pin the version they started with.
        "definition_version": int(definition_version or 1),
        "status": "running",
        "steps": {
            step["id"]: {"status": "pending", "output": "", "error": "", "attempts": 0}
            for step in workflow["steps"]
        },
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    save_run(run)
    return run


def load_run(run_id: str) -> Optional[Dict[str, Any]]:
    path = runs_dir() / f"{run_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_run(run: Dict[str, Any]) -> None:
    # The cancel flag is monotonic across processes: a CLI cancellation must
    # never be overwritten by an engine save that started before it landed.
    try:
        path_probe = runs_dir() / f"{run['run_id']}.json"
        existing = json.loads(path_probe.read_text(encoding="utf-8"))
        if isinstance(existing, dict) and existing.get("cancel_requested"):
            run["cancel_requested"] = True
    except (OSError, ValueError):
        pass
    run["updated_at"] = _now_iso()
    path = runs_dir() / f"{run['run_id']}.json"
    try:
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(run, handle)
        os.replace(tmp_name, path)
    except OSError:
        logger.exception("Failed to persist workflow run %s", run.get("run_id"))


def active_run_for(automation_id: str) -> Optional[Dict[str, Any]]:
    """Most recent non-terminal run for one automation, if any."""
    best: Optional[Dict[str, Any]] = None
    best_key = ""
    for run in list_runs(automation_id=automation_id, limit=200):
        if run.get("status") in ACTIVE_STATUSES:
            key = str(run.get("created_at") or "")
            if key >= best_key:
                best, best_key = run, key
    return best


def list_runs(
    automation_id: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    directory = runs_dir()
    try:
        files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    for path in files[: max(limit * 3, limit)]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if automation_id and data.get("automation_id") != automation_id:
            continue
        entries.append(data)
        if len(entries) >= limit:
            break
    return entries


def prune_runs(retention_days: int) -> int:
    """Delete terminal run records older than retention. Returns count."""
    cutoff = time.time() - max(1, retention_days) * 86400
    removed = 0
    directory = runs_dir()
    try:
        files = list(directory.glob("*.json"))
    except OSError:
        return 0
    for path in files:
        try:
            if path.stat().st_mtime < cutoff:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("status") in TERMINAL_STATUSES:
                    path.unlink(missing_ok=True)
                    removed += 1
        except (OSError, ValueError):
            continue
    return removed


def mark_step(run: Dict[str, Any], step_id: str, status: str,
              output: str = "", error: str = "") -> None:
    """Checkpoint a milestone: step transitions always hit disk (Phase 39)."""
    state = run["steps"].setdefault(
        step_id, {"status": status, "output": "", "error": "", "attempts": 0}
    )
    state["status"] = status
    state["output"] = str(output or "")
    state["error"] = str(error or "")
    save_run(run)


def request_cancel(run: Dict[str, Any]) -> bool:
    """Phase 47: cooperative cancellation between steps."""
    if run.get("status") in TERMINAL_STATUSES:
        return False
    run["cancel_requested"] = True
    save_run(run)
    return True


def cancel_requested(run: Dict[str, Any]) -> bool:
    return bool(run.get("cancel_requested"))


def finish_run(run: Dict[str, Any], status: str) -> None:
    run["status"] = status
    save_run(run)
