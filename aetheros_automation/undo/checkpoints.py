from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import Task, TaskStatus, Workflow

logger = logging.getLogger(__name__)

_CHECKPOINTS_DIR = os.path.expanduser("~/.aetheros/automation/checkpoints")


class CheckpointManager:
    """Save and restore snapshots of workflow / task state.

    Checkpoints are stored as JSON files under
    ``~/.aetheros/automation/checkpoints/`` and can be used to
    resume interrupted workflows or roll back to a known-good state.
    """

    def __init__(self) -> None:
        os.makedirs(_CHECKPOINTS_DIR, exist_ok=True)
        self._loaded = False
        self._index: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # save / restore
    # ------------------------------------------------------------------

    async def save(self, task_id: str, data: dict[str, Any]) -> str:
        """Create a checkpoint for *task_id* and return its checkpoint id.

        *data* should be a serialisable dict that captures the full state
        to be restored later (task steps, variables, file paths, etc.).
        """
        ck_id = uuid.uuid4().hex[:12]
        now = time.time()
        entry = {
            "id": ck_id,
            "task_id": task_id,
            "created_at": now,
            "data": data,
        }
        self._index[ck_id] = entry
        await self._persist(entry)
        logger.info("Checkpoint saved  id=%s  task=%s", ck_id, task_id)
        return ck_id

    async def restore(self, checkpoint_id: str) -> dict[str, Any]:
        """Return the data payload of a previously saved checkpoint.

        Raises ``FileNotFoundError`` when the checkpoint does not exist.
        """
        await self._ensure_loaded()
        entry = self._index.get(checkpoint_id)
        if entry is None:
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")
        return dict(entry["data"])

    async def list_checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        """Return all checkpoints for *task_id*, newest first."""
        await self._ensure_loaded()
        matches = [
            e for e in self._index.values() if e["task_id"] == task_id
        ]
        return sorted(matches, key=lambda e: e["created_at"], reverse=True)

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint.  Returns ``True`` if it existed."""
        entry = self._index.pop(checkpoint_id, None)
        if entry is None:
            return False
        path = os.path.join(_CHECKPOINTS_DIR, f"{checkpoint_id}.json")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _remove_file, path)
        logger.info("Checkpoint deleted  id=%s", checkpoint_id)
        return True

    async def resume_workflow(self, workflow_id: str) -> Workflow:
        """Reconstruct a ``Workflow`` from its latest checkpoint.

        The checkpoint must have been created with a ``"workflow"`` key
        in its data dict that contains the serialised ``Workflow`` fields.

        Raises ``FileNotFoundError`` if no checkpoint is found for the
        workflow.
        """
        checkpoints = [
            e
            for e in self._index.values()
            if e["data"].get("workflow", {}).get("id") == workflow_id
        ]
        if not checkpoints:
            # Try loading from disk fresh.
            await self._ensure_loaded()
            checkpoints = [
                e
                for e in self._index.values()
                if e["data"].get("workflow", {}).get("id") == workflow_id
            ]
        if not checkpoints:
            raise FileNotFoundError(f"No checkpoint found for workflow {workflow_id}")

        latest = max(checkpoints, key=lambda e: e["created_at"])
        wf_data = latest["data"]["workflow"]

        tasks = [
            Task(
                id=t.get("id", ""),
                name=t.get("name", ""),
                description=t.get("description", ""),
                status=TaskStatus(t["status"]) if "status" in t else TaskStatus.PENDING,
                created_at=t.get("created_at", 0.0),
                started_at=t.get("started_at", 0.0),
                completed_at=t.get("completed_at", 0.0),
                result=t.get("result", ""),
                error=t.get("error", ""),
                retry_count=t.get("retry_count", 0),
                max_retries=t.get("max_retries", 3),
                progress=t.get("progress", 0.0),
            )
            for t in wf_data.get("tasks", [])
        ]

        workflow = Workflow(
            id=wf_data.get("id", workflow_id),
            name=wf_data.get("name", ""),
            description=wf_data.get("description", ""),
            tasks=tasks,
            status=TaskStatus(wf_data["status"]) if "status" in wf_data else TaskStatus.PAUSED,
            created_at=wf_data.get("created_at", 0.0),
            started_at=wf_data.get("started_at", 0.0),
            completed_at=wf_data.get("completed_at", 0.0),
            checkpoint_path=latest["id"],
            graph=wf_data.get("graph", {}),
        )
        logger.info("Resumed workflow %s from checkpoint %s", workflow_id, latest["id"])
        return workflow

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
        if not os.path.isdir(_CHECKPOINTS_DIR):
            return
        for name in os.listdir(_CHECKPOINTS_DIR):
            if not name.endswith(".json"):
                continue
            path = os.path.join(_CHECKPOINTS_DIR, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    entry = json.load(fh)
                self._index[entry["id"]] = entry
            except Exception:
                logger.exception("Failed to load checkpoint %s", path)

    async def _persist(self, entry: dict[str, Any]) -> None:
        path = os.path.join(_CHECKPOINTS_DIR, f"{entry['id']}.json")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, entry)


def _write_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
