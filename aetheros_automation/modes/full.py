from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.modes.base import BaseExecutionMode
from aetheros_automation.models.models import Task, TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class FullyAutonomousMode(BaseExecutionMode):
    _DESTRUCTIVE_ACTIONS: set[str] = {
        "delete_file",
        "file.delete",
        "format_disk",
        "shutdown",
        "deploy",
        "payment",
        "terraform.destroy",
    }

    async def execute(self, task: Task, context: dict[str, Any]) -> str:
        logger.info("FullyAutonomousMode: executing task %s (%s)", task.id, task.name)
        results: list[str] = []

        for step in task.steps:
            if step.action in self._DESTRUCTIVE_ACTIONS:
                logger.warning(
                    "FullyAutonomousMode: destructive action '%s' in step %s – proceeding",
                    step.action, step.id,
                )

            if not await self.approve_step(step, context):
                step.status = TaskStatus.BLOCKED
                logger.info("FullyAutonomousMode: step %s blocked", step.id)
                continue

            step.status = TaskStatus.RUNNING
            result = await self._run_step(step, context)
            step.status = TaskStatus.COMPLETED
            step.result = result
            results.append(result)

        return "\n".join(results)

    async def approve_step(self, step: Any, context: dict[str, Any]) -> bool:
        return True

    async def _run_step(self, step: TaskStep, context: dict[str, Any]) -> str:
        if self.engine:
            result = await self.engine._dispatch_step(step, context)
            return str(result.get("data", result.get("result", str(result))))
        logger.info("FullyAutonomousMode: running step %s (%s)", step.id, step.name)
        return f"[full] step {step.id} executed"
