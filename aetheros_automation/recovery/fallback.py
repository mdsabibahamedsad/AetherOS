from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from aetheros_automation.models.models import FailureType

logger = logging.getLogger(__name__)


class FallbackHandler:
    def __init__(self):
        self._fallback_registry: dict[str, list[dict[str, Any]]] = {}

    def register_fallback(self, task_type: str, fallbacks: list[dict[str, Any]]):
        self._fallback_registry[task_type] = fallbacks
        logger.info(
            "Registered %d fallbacks for task type '%s'",
            len(fallbacks), task_type,
        )

    async def execute_with_fallback(
        self,
        task_type: str,
        primary_operation: Callable,
        fallback_operations: list[Callable] | None = None,
        failure_type: FailureType = FailureType.UNKNOWN,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any, str | None]:
        try:
            result = await primary_operation() if asyncio.iscoroutinefunction(primary_operation) else primary_operation()
            return True, result, None
        except Exception as e:
            logger.warning("Primary operation failed: %s", e)

            ops = fallback_operations or []
            registered = self._fallback_registry.get(task_type, [])
            for fb in registered:
                fb_op = fb.get("operation")
                if fb_op:
                    ops.append(fb_op)

            for i, fb_op in enumerate(ops):
                try:
                    result = await fb_op() if asyncio.iscoroutinefunction(fb_op) else fb_op()
                    fb_name = getattr(fb_op, "__name__", f"fallback_{i}")
                    logger.info("Fallback '%s' succeeded", fb_name)
                    return True, result, fb_name
                except Exception as fb_e:
                    logger.warning("Fallback %d failed: %s", i, fb_e)

            return False, e, None

    async def execute_fallback_chain(
        self,
        operations: list[Callable],
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any, int]:
        for i, op in enumerate(operations):
            try:
                result = await op() if asyncio.iscoroutinefunction(op) else op()
                return True, result, i
            except Exception as e:
                logger.warning("Chain operation %d failed: %s", i, e)

        return False, Exception("All fallback operations failed"), -1

    def get_fallbacks(self, task_type: str) -> list[dict[str, Any]]:
        return list(self._fallback_registry.get(task_type, []))
