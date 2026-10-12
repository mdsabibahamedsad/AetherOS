from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.modes.base import BaseExecutionMode
from aetheros_automation.models.models import Task, TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class ManualMode(BaseExecutionMode):
    async def execute(self, task: Task, context: dict[str, Any]) -> str:
        logger.info("ManualMode: executing task %s (%s)", task.id, task.name)
        results: list[str] = []

        for step in task.steps:
            approved = await self.approve_step(step, context)
            if not approved:
                logger.info("ManualMode: step %s blocked – waiting for user", step.id)
                step.status = TaskStatus.BLOCKED
                raise _ApprovalPendingError(
                    f"Step {step.id} ('{step.name}') requires manual approval"
                )

            step.status = TaskStatus.RUNNING
            result = await self._run_step(step, context)
            step.status = TaskStatus.COMPLETED
            step.result = result
            results.append(result)

        return "\n".join(results)

    async def approve_step(self, step: Any, context: dict[str, Any]) -> bool:
        return False

    async def _run_step(self, step: TaskStep, context: dict[str, Any]) -> str:
        if self.engine:
            result = await self.engine._dispatch_step(step, context)
            return str(result.get("data", result.get("result", str(result))))
        logger.info("ManualMode: running step %s (%s)", step.id, step.name)
        return f"[manual] step {step.id} executed"


class _ApprovalPendingError(Exception):
    """Raised when a step needs external approval in manual or assisted mode."""
