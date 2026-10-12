from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, OrchestrationResult, TaskStatus, TaskType,
    FailurePolicy, ValidationResult, Checkpoint,
)

logger = logging.getLogger(__name__)

FAILURE_CATEGORIES = {
    "timeout": {"retryable": True, "backoff": True},
    "rate_limit": {"retryable": True, "backoff": True, "delay": 5.0},
    "auth_error": {"retryable": False, "backoff": False},
    "invalid_input": {"retryable": False, "backoff": False},
    "provider_error": {"retryable": True, "backoff": True},
    "model_error": {"retryable": True, "backoff": True, "fallback_model": True},
    "tool_error": {"retryable": True, "backoff": False, "fallback_tool": True},
    "agent_error": {"retryable": True, "backoff": False, "fallback_agent": True},
    "permission_denied": {"retryable": False, "backoff": False},
    "resource_exhausted": {"retryable": True, "backoff": True, "delay": 10.0},
    "unknown": {"retryable": True, "backoff": True},
}


class FailureRecovery:
    def __init__(self):
        self._policy: FailurePolicy = FailurePolicy()

    def set_policy(self, policy: FailurePolicy):
        self._policy = policy

    def classify_failure(self, error: str) -> str:
        error_lower = error.lower()
        for keyword, category in [
            ("timeout", "timeout"),
            ("rate limit", "rate_limit"),
            ("too many requests", "rate_limit"),
            ("auth", "auth_error"),
            ("unauthorized", "auth_error"),
            ("invalid", "invalid_input"),
            ("provider", "provider_error"),
            ("model", "model_error"),
            ("tool", "tool_error"),
            ("agent", "agent_error"),
            ("permission", "permission_denied"),
            ("denied", "permission_denied"),
            ("resource", "resource_exhausted"),
            ("quota", "resource_exhausted"),
        ]:
            if keyword in error_lower:
                return category
        return "unknown"

    async def handle_task_failure(
        self,
        task,
        error: str,
        plan: Plan,
        orchestrator: Any,
    ) -> bool:
        category = self.classify_failure(error)
        config = FAILURE_CATEGORIES.get(category, FAILURE_CATEGORIES["unknown"])
        if not config["retryable"]:
            logger.warning("Non-retryable failure %s: %s", category, error)
            return False
        if task.retry_count >= task.max_retries:
            logger.warning("Task %s exceeded max retries (%d)", task.id, task.max_retries)
            if config.get("fallback_model") and task.model:
                fallback_route = None
                if orchestrator and hasattr(orchestrator, 'model_router'):
                    fallback_route = orchestrator.model_router.route_for_role(task.agent_role)
                if fallback_route and fallback_route.fallback_model:
                    task.model = fallback_route.fallback_model
                    task.provider = fallback_route.fallback_provider
                    task.retry_count = 0
                    logger.info("Fallback to model %s for task %s", task.model, task.id)
                    return True
            if config.get("fallback_agent") and task.fallback_task_id:
                return await self._execute_fallback_task(task, plan, orchestrator)
            return False
        delay = config.get("delay", self._policy.retry_delay)
        if config["backoff"] and self._policy.exponential_backoff:
            delay *= self._policy.backoff_factor ** task.retry_count
        task.status = TaskStatus.RETRYING
        task.retry_count += 1
        logger.info("Retrying task %s (attempt %d/%d) after %.1fs delay",
                     task.id, task.retry_count, task.max_retries, delay)
        await asyncio.sleep(delay)
        return True

    async def handle_validation_failure(
        self,
        plan: Plan,
        result: OrchestrationResult,
        validation: ValidationResult,
        orchestrator: Any,
    ) -> OrchestrationResult:
        logger.warning("Validation failed for plan %s: %s", plan.id, validation.errors)
        for error in validation.errors:
            for task in plan.tasks:
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    continue
                if error in task.error:
                    recovered = await self.handle_task_failure(task, error, plan, orchestrator)
                    if recovered:
                        result.status = "running"
                        result.errors = []
                        return result
        result.status = "failed"
        result.error = "Validation failed: " + "; ".join(validation.errors)
        result.errors.extend(validation.errors)
        return result

    async def _execute_fallback_task(
        self, task, plan, orchestrator
    ) -> bool:
        if not task.fallback_task_id:
            return False
        fallback_task = None
        for t in plan.tasks:
            if t.id == task.fallback_task_id:
                fallback_task = t
                break
        if not fallback_task:
            return False
        fallback_task.status = TaskStatus.RUNNING
        if orchestrator and hasattr(orchestrator, 'engine'):
            result = await orchestrator.engine._execute_task(
                fallback_task, plan, orchestrator, {}
            )
            return result is not None and isinstance(result, dict) and not result.get("error")
        return False

    def record_failure(self, task_id: str, error: str, category: str):
        logger.info("Recorded failure for task %s: [%s] %s", task_id, category, error)

    def get_stats(self) -> dict:
        return {
            "policy": {
                "max_retries": self._policy.max_retries,
                "exponential_backoff": self._policy.exponential_backoff,
                "use_fallback_model": self._policy.use_fallback_model,
                "use_fallback_agent": self._policy.use_fallback_agent,
            },
            "categories": list(FAILURE_CATEGORIES.keys()),
        }
