from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.modes.base import BaseExecutionMode
from aetheros_automation.models.models import Task, TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class SemiAutonomousMode(BaseExecutionMode):
    _RISKY_ACTIONS: set[str] = {
        "delete_file",
        "format_disk",
        "send_email",
        "payment",
        "publish_code",
        "deploy",
        "shutdown",
        "install_software",
        "run_privileged",
        "modify_system_config",
        "execute_shell",
        "modify_registry",
        "install_driver",
        "modify_boot_config",
        "network_proxy",
        "firewall_change",
        "user_management",
        "permission_change",
        "file.delete",
        "file.encrypt",
        "docker.down",
        "terraform.destroy",
    }

    async def execute(self, task: Task, context: dict[str, Any]) -> str:
        logger.info("SemiAutonomousMode: executing task %s (%s)", task.id, task.name)
        results: list[str] = []
        notify = context.get("notify")

        for step in task.steps:
            is_risky = self._is_risky(step, context)
            if is_risky:
                logger.info("SemiAutonomousMode: step %s requires approval", step.id)
                if notify:
                    await notify("approval_required", self._format_risk(step))

            approved = await self.approve_step(step, context)
            if not approved:
                if is_risky:
                    step.status = TaskStatus.BLOCKED
                    logger.info("SemiAutonomousMode: risky step %s denied – pausing task", step.id)
                    return (
                        f"Task {task.id} paused at risky step "
                        f"{step.id} ('{step.name}') – awaiting user decision"
                    )
                logger.info("SemiAutonomousMode: safe step %s skipped", step.id)
                continue

            step.status = TaskStatus.RUNNING
            result = await self._run_step(step, context)
            step.status = TaskStatus.COMPLETED
            step.result = result
            results.append(result)

        return "\n".join(results)

    async def approve_step(self, step: Any, context: dict[str, Any]) -> bool:
        if not self._is_risky(step, context):
            return True
        step_id = step.id if hasattr(step, "id") else str(id(step))
        approvals = context.setdefault("_semi_approvals", {})
        return approvals.get(step_id, False)

    def _is_risky(self, step: Any, context: dict[str, Any]) -> bool:
        action = getattr(step, "action", "")
        if action in self._RISKY_ACTIONS:
            return True
        forced = context.get("_risky_override", {})
        if forced:
            step_id = getattr(step, "id", str(id(step)))
            return forced.get(step_id, False)
        return False

    @staticmethod
    def _format_risk(step: TaskStep) -> str:
        return (
            f"[approval required] step '{step.name}'\n"
            f"  action: {step.action}\n"
            f"  reason: classified as risky"
        )

    async def _run_step(self, step: TaskStep, context: dict[str, Any]) -> str:
        if self.engine:
            result = await self.engine._dispatch_step(step, context)
            return str(result.get("data", result.get("result", str(result))))
        logger.info("SemiAutonomousMode: running step %s (%s)", step.id, step.name)
        return f"[semi] step {step.id} executed"
