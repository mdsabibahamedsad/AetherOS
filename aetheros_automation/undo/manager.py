from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import UndoAction

logger = logging.getLogger(__name__)

_UNDO_DIR = os.path.expanduser("~/.aetheros/automation/undo")


class UndoManager:
    """Record and replay reversal of task actions.

    Each action is persisted as a separate JSON file under
    ``~/.aetheros/automation/undo/<task_id>/<undo_id>.json`` so it
    survives restarts and can be inspected independently.
    """

    def __init__(self) -> None:
        os.makedirs(_UNDO_DIR, exist_ok=True)
        self._store: dict[str, dict[str, UndoAction]] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------

    async def record_action(
        self,
        task_id: str,
        action_type: str,
        description: str,
        data: dict[str, Any],
    ) -> UndoAction:
        """Persist an action that can later be undone."""
        now = time.time()
        action = UndoAction(
            id=uuid.uuid4().hex[:12],
            action_type=action_type,
            description=description,
            data=data,
            timestamp=now,
            restored=False,
        )
        if task_id not in self._store:
            self._store[task_id] = {}
        self._store[task_id][action.id] = action
        await self._persist(task_id, action)
        logger.debug("Recorded undo action %s for task %s (%s)", action.id, task_id, action_type)
        return action

    # ------------------------------------------------------------------
    # undo
    # ------------------------------------------------------------------

    async def undo(self, undo_id: str) -> bool:
        """Reverse a single recorded action.

        The *data* dict should contain a ``"reverse"`` key whose value is a
        dict with keys such as ``"action"``, ``"path"``, ``"content"`` etc.
        that the caller uses to perform the reversal.

        This method marks the action as restored and persists the change.
        Actual reversal (file I/O, API call, etc.) is left to the caller so
        that every subsystem can supply its own domain-specific logic.
        """
        for task_actions in self._store.values():
            action = task_actions.get(undo_id)
            if action is not None:
                action.restored = True
                await self._persist_for_action(action)
                logger.info("Undid action %s (%s)", undo_id, action.action_type)
                return True
        logger.warning("undo: action %s not found", undo_id)
        return False

    async def undo_task(self, task_id: str) -> bool:
        """Undo every recorded action for *task_id* in reverse chronological order.

        Returns ``True`` if at least one action was restored.
        """
        await self._ensure_loaded()
        actions = self._store.get(task_id)
        if not actions:
            logger.warning("undo_task: no actions for task %s", task_id)
            return False

        sorted_actions = sorted(actions.values(), key=lambda a: a.timestamp, reverse=True)
        restored_any = False
        for action in sorted_actions:
            if not action.restored:
                action.restored = True
                await self._persist_for_action(action)
                restored_any = True
                logger.info("Undid action %s (%s) for task %s", action.id, action.action_type, task_id)

        return restored_any

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    async def list_actions(self, task_id: str) -> list[UndoAction]:
        """Return all recorded actions for a task, newest first."""
        await self._ensure_loaded()
        actions = list(self._store.get(task_id, {}).values())
        return sorted(actions, key=lambda a: a.timestamp, reverse=True)

    async def clear_task(self, task_id: str) -> None:
        """Remove all recorded undo data for *task_id*."""
        actions = self._store.pop(task_id, None)
        if actions is None:
            return
        task_dir = os.path.join(_UNDO_DIR, task_id)
        if os.path.isdir(task_dir):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _rmtree, task_dir)
        logger.info("Cleared undo data for task %s (%d actions)", task_id, len(actions))

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_all)

    def _load_all(self) -> None:
        if not os.path.isdir(_UNDO_DIR):
            return
        for task_id in os.listdir(_UNDO_DIR):
            task_dir = os.path.join(_UNDO_DIR, task_id)
            if not os.path.isdir(task_dir):
                continue
            for name in os.listdir(task_dir):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(task_dir, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    action = UndoAction(
                        id=data["id"],
                        action_type=data.get("action_type", ""),
                        description=data.get("description", ""),
                        data=data.get("data", {}),
                        timestamp=data.get("timestamp", 0.0),
                        restored=data.get("restored", False),
                    )
                    self._store.setdefault(task_id, {})[action.id] = action
                except Exception:
                    logger.exception("Failed to load undo action %s", path)

    async def _persist(self, task_id: str, action: UndoAction) -> None:
        task_dir = os.path.join(_UNDO_DIR, task_id)
        path = os.path.join(task_dir, f"{action.id}.json")
        data = self._action_to_dict(action)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, data)

    async def _persist_for_action(self, action: UndoAction) -> None:
        # Re-discover the task_id for this action by scanning our store.
        for task_id, actions in self._store.items():
            if action.id in actions:
                await self._persist(task_id, action)
                return

    @staticmethod
    def _action_to_dict(action: UndoAction) -> dict[str, Any]:
        return {
            "id": action.id,
            "action_type": action.action_type,
            "description": action.description,
            "data": action.data,
            "timestamp": action.timestamp,
            "restored": action.restored,
        }


def _write_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


def _rmtree(path: str) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)
