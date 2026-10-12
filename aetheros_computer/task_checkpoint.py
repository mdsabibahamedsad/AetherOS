"""
Computer-task checkpoints, resume and budgets (Master 15 Phases 50-51, 82).

One JSON record per task under ``<AETHEROS_HOME>/computer_actions/tasks/``::

    {task_id, goal, completed: [action_id...], action_count,
     budget: {max_actions}, created_at, updated_at}

Contract:
- ``record_completion`` after each successful (idempotent-safe) action.
- ``resume_filter`` drops already-completed action ids so a restarted task
  never repeats irreversible work (Phase 51).
- ``check_budget`` refuses new actions once ``max_actions`` is exhausted
  (Phase 82 default budget; overridable per task).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_ACTIONS = 200


def _tasks_dir():
    from aetheros_constants import get_aetheros_home

    d = get_aetheros_home() / "computer_actions" / "tasks"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def _safe_task_id(task_id: str) -> str:
    text = "".join(c for c in str(task_id or "task") if c.isalnum() or c in "-_")
    return (text or "task")[:80]


def _path(task_id: str) -> Path:
    return _tasks_dir() / f"{_safe_task_id(task_id)}.json"


_lock = threading.Lock()


def _load(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(_path(task_id).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _save(record: Dict[str, Any]) -> None:
    path = _path(record.get("task_id", "task"))
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f)
        os.replace(tmp, path)
    except OSError:
        logger.debug("Task checkpoint save failed", exc_info=True)


def start_task(task_id: str, goal: str = "", max_actions: int = DEFAULT_MAX_ACTIONS) -> Dict[str, Any]:
    """Create-or-return checkpoint record for a task (never resets existing)."""
    with _lock:
        existing = _load(task_id)
        if existing is not None:
            return existing
        record = {
            "task_id": task_id,
            "goal": str(goal or "")[:300],
            "completed": [],
            "action_count": 0,
            "budget": {"max_actions": max(1, int(max_actions))},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        _save(record)
        return record


def record_completion(task_id: str, action_id: str) -> Dict[str, Any]:
    """Checkpoint one finished action (dedup by action_id)."""
    with _lock:
        rec = _load(task_id) or {
            "task_id": task_id, "goal": "", "completed": [], "action_count": 0,
            "budget": {"max_actions": DEFAULT_MAX_ACTIONS},
            "created_at": time.time(),
        }
        if action_id and action_id not in rec["completed"]:
            rec["completed"].append(action_id)
        rec["action_count"] = int(rec.get("action_count", 0)) + 1
        rec["updated_at"] = time.time()
        _save(rec)
        return rec


def completed_ids(task_id: str) -> List[str]:
    rec = _load(task_id)
    return list(rec.get("completed", [])) if rec else []


def resume_filter(task_id: str, pending_action_ids: List[str]) -> List[str]:
    """Phase 51: drop actions already completed for this task."""
    done = set(completed_ids(task_id))
    return [a for a in pending_action_ids if a not in done]


def check_budget(task_id: str) -> Dict[str, Any]:
    """Return {'allowed': bool, 'used': int, 'max': int}."""
    rec = _load(task_id)
    if rec is None:
        return {"allowed": True, "used": 0, "max": DEFAULT_MAX_ACTIONS}
    used = int(rec.get("action_count", 0))
    mx = int((rec.get("budget") or {}).get("max_actions", DEFAULT_MAX_ACTIONS))
    return {"allowed": used < mx, "used": used, "max": mx}


def finish_task(task_id: str) -> bool:
    """Remove the checkpoint file on successful completion."""
    with _lock:
        try:
            _path(task_id).unlink(missing_ok=True)
            return True
        except OSError:
            return False


def reset_all() -> None:
    """Test helper."""
    with _lock:
        d = _tasks_dir()
        try:
            for p in d.glob("*.json"):
                p.unlink()
        except OSError:
            pass


__all__ = [
    "start_task",
    "record_completion",
    "completed_ids",
    "resume_filter",
    "check_budget",
    "finish_task",
    "reset_all",
    "DEFAULT_MAX_ACTIONS",
]
