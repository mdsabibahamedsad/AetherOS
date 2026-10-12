from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.modes.base import BaseExecutionMode
from aetheros_automation.models.models import Task, TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class AssistedMode(BaseExecutionMode):
    async def execute(self, task: Task, context: dict[str, Any]) -> str:
        logger.info("AssistedMode: executing task %s (%s)", task.id, task.name)
        results: list[str] = []
        notify = context.get("notify")
        pending_store = context.get("pending_store")

        for step in task.steps:
            suggestion = self._format_suggestion(task, step)
            if notify:
                await notify("suggestion", suggestion)
            if pending_store is not None:
                pending_store[step.id] = suggestion

            approved = await self.approve_step(step, context)
            if not approved:
                step.status = TaskStatus.BLOCKED
                logger.info("AssistedMode: step %s denied by user", step.id)
                return f"Task {task.id} cancelled at step {step.id} ('{step.name}')"

            step.status = TaskStatus.RUNNING
            if pending_store is not None:
                pending_store.pop(step.id, None)

            result = await self._run_step(step, context)
            step.status = TaskStatus.COMPLETED
            step.result = result
            results.append(result)

        return "\n".join(results)

    async def approve_step(self, step: Any, context: dict[str, Any]) -> bool:
        step_id = step.id if hasattr(step, "id") else str(id(step))
        approvals = context.setdefault("_assisted_approvals", {})
        if approvals.get(step_id, False):
            return True
        return False

    @staticmethod
    def _format_suggestion(task: Task, step: TaskStep) -> str:
        return (
            f"[suggest] task '{task.name}' step '{step.name}'\n"
            f"  action: {step.action}\n"
            f"  params: {step.params}"
        )

    async def _run_step(self, step: TaskStep, context: dict[str, Any]) -> str:
        if self.engine:
            result = await self.engine._dispatch_step(step, context)
            return str(result.get("data", result.get("result", str(result))))
        logger.info("AssistedMode: running step %s (%s)", step.id, step.name)
        return f"[assisted] step {step.id} executed"
