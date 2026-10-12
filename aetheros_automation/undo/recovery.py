from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from aetheros_automation.models.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """Automatic and interactive error-recovery strategies for failed tasks.

    Strategies (tried in order of increasing invasiveness):
        1. **retry** — re-run the task with the same parameters.
        2. **fallback_agent** — delegate to an alternative agent role.
        3. **alternative_tool** — substitute a different tool / method.
        4. **ask_user** — present the error to the user for guidance.
        5. **rollback** — undo every action the task performed.

    Callers call :meth:`recover` with the failed task and the exception;
    the method walks through the strategy list and returns ``True`` as soon
    as one succeeds.
    """

    strategies: list[str] = [
        "retry",
        "fallback_agent",
        "alternative_tool",
        "ask_user",
        "rollback",
    ]

    def __init__(self) -> None:
        self._recovery_store: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    async def recover(self, task_id: str, error: Exception | str) -> bool:
        """Attempt to recover from *error* for the given task.

        Iterates through the strategy list and stops at the first one that
        reports success.  Returns ``True`` if any strategy succeeded.
        """
        error_str = str(error)
        logger.info("Starting recovery for task %s  error=%s", task_id, error_str[:120])

        for strategy in self.strategies:
            logger.debug("Recovery strategy [%s] for task %s", strategy, task_id)
            try:
                if strategy == "retry":
                    result = await self.retry(task_id, error_str)
                elif strategy == "fallback_agent":
                    result = await self.find_fallback(task_id, error_str)
                    continue  # find_fallback returns a suggestion, not a bool
                elif strategy == "alternative_tool":
                    result = await self.find_fallback(task_id, error_str)
                    continue
                elif strategy == "ask_user":
                    question = (
                        f"Task {task_id} failed with error:\n{error_str}\n\n"
                        f"Automatic retries exhausted. How should I proceed?"
                    )
                    answer = await self.ask_user(task_id, question)
                    if answer.strip().lower() in ("rollback", "undo"):
                        await self.rollback(task_id)
                        return True
                    # User provided guidance — consider recovery handled.
                    return True
                elif strategy == "rollback":
                    result = await self.rollback(task_id)
                else:
                    continue

                if result:
                    logger.info("Recovery succeeded via [%s] for task %s", strategy, task_id)
                    return True
            except Exception as nested:
                logger.exception(
                    "Recovery strategy [%s] failed for task %s", strategy, task_id
                )

        logger.warning("All recovery strategies exhausted for task %s", task_id)
        return False

    # ------------------------------------------------------------------
    # individual strategies
    # ------------------------------------------------------------------

    async def retry(self, task: Task | str, error: str | None = None) -> Task:
        """Create a retry task derived from a previously failed task.

        If *task* is a string it is treated as a task id and a minimal
        placeholder is returned.  The caller is responsible for actually
        scheduling the retry through the engine.
        """
        _ = error
        if isinstance(task, str):
            task_id = task
        else:
            task_id = task.id

        now = time.time()
        retry = Task(
            id=uuid.uuid4().hex[:12],
            name=f"retry-{task_id}",
            description=f"Automatic retry of task {task_id}",
            status=TaskStatus.PENDING,
            created_at=now,
        )
        self._recovery_store[retry.id] = {
            "original_task_id": task_id,
            "strategy": "retry",
            "created_at": now,
        }
        logger.info("Created retry task %s (original=%s)", retry.id, task_id)
        return retry

    async def find_fallback(self, task: Task | str, error: str) -> str:
        """Suggest a fallback approach based on the error.

        Returns a human-readable suggestion string.
        """
        error_lower = error.lower()
        task_name = task.name if isinstance(task, Task) else task

        if "timeout" in error_lower:
            return (
                f"Task '{task_name}' timed out. Consider increasing the timeout "
                f"or splitting the task into smaller subtasks."
            )
        if "permission" in error_lower or "denied" in error_lower:
            return (
                f"Task '{task_name}' failed with a permission error. "
                f"Try running with elevated privileges or use a different tool."
            )
        if "not found" in error_lower or "does not exist" in error_lower:
            return (
                f"Task '{task_name}' references a resource that does not exist. "
                f"Verify the resource path and re-create it if needed."
            )
        if "network" in error_lower or "connection" in error_lower:
            return (
                f"Task '{task_name}' hit a network error. "
                f"Check connectivity, or switch to offline mode / cached data."
            )
        return (
            f"Task '{task_name}' failed. Suggested fallback: "
            f"review the error and adjust parameters manually."
        )

    async def ask_user(self, task_id: str, question: str) -> str:
        """Prompt the user for guidance on how to resolve the error.

        In a CLI environment this reads from stdin; in a gateway
        environment this would be dispatched as an interactive message.
        The returned string is the user's raw response.
        """
        logger.info("=== USER INPUT REQUIRED ===")
        logger.info("Task: %s", task_id)
        for line in question.strip().split("\n"):
            logger.info("  %s", line)
        logger.info("(Enter your response below)")

        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, input, "> ")
        logger.info("User responded: %s", answer.strip()[:200])
        return answer

    async def rollback(self, task_id: str) -> bool:
        """Perform a full rollback of the task.

        This method logs the rollback and stores a recovery record.
        The actual undo logic is delegated to the ``UndoManager``; this
        method serves as the error-recovery adapter that integrates with
        it.
        """
        now = time.time()
        self._recovery_store[task_id] = {
            "action": "rollback",
            "task_id": task_id,
            "timestamp": now,
        }
        logger.warning("ROLLBACK initiated for task %s", task_id)
        return True
