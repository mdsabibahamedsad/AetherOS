from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any, Callable

from aetheros_automation.models.models import FailureType

logger = logging.getLogger(__name__)


class RetryHandler:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self._retry_counts: dict[str, int] = {}

    async def execute_with_retry(
        self,
        task_id: str,
        operation: Callable,
        failure_type: FailureType = FailureType.UNKNOWN,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        last_error: Exception | None = None
        attempt = 0

        while attempt <= self.max_retries:
            if attempt > 0:
                delay = self.get_backoff(attempt, failure_type)
                logger.info(
                    "Retry %d/%d for task %s, waiting %.2fs",
                    attempt, self.max_retries, task_id, delay,
                )
                await asyncio.sleep(delay)

            try:
                result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
                self._retry_counts[task_id] = attempt
                return True, result
            except Exception as e:
                last_error = e
                attempt += 1
                logger.warning(
                    "Attempt %d/%d failed for task %s: %s",
                    attempt, self.max_retries, task_id, e,
                )

                if not self._is_retryable(e):
                    break

        self._retry_counts[task_id] = attempt - 1
        return False, last_error

    def get_backoff(self, attempt: int, failure_type: FailureType = FailureType.UNKNOWN) -> float:
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if failure_type == FailureType.RATE_LIMIT:
            delay = max(delay, 5.0)
        elif failure_type == FailureType.TIMEOUT:
            delay = min(delay, self.max_delay / 2)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def _is_retryable(self, error: Exception) -> bool:
        error_str = str(error).lower()
        non_retryable = [
            "invalid_api_key", "authentication_error",
            "invalid_request_error", "permission_error",
            "not_found", "does not exist",
        ]
        return not any(n in error_str for n in non_retryable)

    def classify_failure(self, error: Exception) -> FailureType:
        error_str = str(error).lower()
        if any(k in error_str for k in ["timeout", "timed out", "deadline"]):
            return FailureType.TIMEOUT
        if any(k in error_str for k in ["rate", "limit", "too many"]):
            return FailureType.RATE_LIMIT
        if any(k in error_str for k in ["auth", "api_key", "unauthorized", "forbidden"]):
            return FailureType.AUTH_ERROR
        if any(k in error_str for k in ["permission", "denied"]):
            return FailureType.PERMISSION_DENIED
        if any(k in error_str for k in ["provider", "server error", "service"]):
            return FailureType.PROVIDER_ERROR
        if any(k in error_str for k in ["tool", "function"]):
            return FailureType.TOOL_ERROR
        if any(k in error_str for k in ["validation", "invalid"]):
            return FailureType.VALIDATION_ERROR
        if any(k in error_str for k in ["model"]):
            return FailureType.MODEL_ERROR
        return FailureType.UNKNOWN

    def get_retry_count(self, task_id: str) -> int:
        return self._retry_counts.get(task_id, 0)

    def reset_retry_count(self, task_id: str):
        self._retry_counts.pop(task_id, None)

    def clear(self):
        self._retry_counts.clear()
