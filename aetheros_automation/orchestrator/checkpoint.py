from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.orchestrator.types import ExecutionState

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover - fallback for standalone use
    from pathlib import Path

    def get_aetheros_home():
        return Path.home() / ".aetheros"

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, base_dir: str | None = None):
        self._base_dir = base_dir or str(
            get_aetheros_home() / "automation" / "checkpoints"
        )
        os.makedirs(self._base_dir, exist_ok=True)
        self._checkpoints: dict[str, dict[str, Any]] = {}

    async def save_checkpoint(
        self,
        plan_id: str,
        task_id: str,
        result: Any,
        state: ExecutionState | None = None,
    ) -> str | None:
        checkpoint_id = uuid.uuid4().hex[:12]
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "plan_id": plan_id,
            "task_id": task_id,
            "result": result,
            "timestamp": time.time(),
            "state": {
                "completed_tasks": list(state.completed_tasks) if state else [],
                "failed_tasks": list(state.failed_tasks) if state else [],
                "pending_tasks": list(state.pending_tasks) if state else [],
                "paused": state.paused if state else False,
                "cancelled": state.cancelled if state else False,
            } if state else {},
        }

        self._checkpoints[checkpoint_id] = checkpoint

        path = os.path.join(self._base_dir, f"{plan_id}", f"{checkpoint_id}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_checkpoint, path, checkpoint
        )

        logger.info(
            "Checkpoint %s saved for plan %s, task %s",
            checkpoint_id, plan_id, task_id,
        )
        return checkpoint_id

    def _write_checkpoint(self, path: str, data: dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    async def load_checkpoint(
        self, plan_id: str, checkpoint_id: str
    ) -> dict[str, Any] | None:
        path = os.path.join(self._base_dir, plan_id, f"{checkpoint_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self._checkpoints[checkpoint_id] = data
            return data
        except Exception as e:
            logger.exception("Failed to load checkpoint %s: %s", checkpoint_id, e)
            return None

    async def restore_state(
        self, plan_id: str, checkpoint_id: str
    ) -> dict[str, Any] | None:
        checkpoint = await self.load_checkpoint(plan_id, checkpoint_id)
        if not checkpoint:
            return None
        return checkpoint.get("state")

    async def list_checkpoints(self, plan_id: str) -> list[dict[str, Any]]:
        plan_dir = os.path.join(self._base_dir, plan_id)
        if not os.path.isdir(plan_dir):
            return []
        checkpoints: list[dict[str, Any]] = []
        for name in sorted(os.listdir(plan_dir), reverse=True):
            if name.endswith(".json"):
                path = os.path.join(plan_dir, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    checkpoints.append({
                        "id": data.get("checkpoint_id"),
                        "plan_id": data.get("plan_id"),
                        "task_id": data.get("task_id"),
                        "timestamp": data.get("timestamp", 0),
                        "state": data.get("state", {}),
                    })
                except Exception:
                    logger.warning("Failed to read checkpoint %s", path)
        return checkpoints

    async def delete_checkpoint(self, plan_id: str, checkpoint_id: str) -> bool:
        path = os.path.join(self._base_dir, plan_id, f"{checkpoint_id}.json")
        if os.path.isfile(path):
            os.remove(path)
            self._checkpoints.pop(checkpoint_id, None)
            logger.info("Checkpoint %s deleted", checkpoint_id)
            return True
        return False

    async def get_latest_checkpoint(self, plan_id: str) -> dict[str, Any] | None:
        checkpoints = await self.list_checkpoints(plan_id)
        if checkpoints:
            return checkpoints[0]
        return None

    async def cleanup_old_checkpoints(self, plan_id: str, keep_last: int = 10):
        checkpoints = await self.list_checkpoints(plan_id)
        if len(checkpoints) > keep_last:
            for cp in checkpoints[keep_last:]:
                await self.delete_checkpoint(plan_id, cp["id"])
