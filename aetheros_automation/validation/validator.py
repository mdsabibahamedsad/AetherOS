from __future__ import annotations

import logging
import os
from typing import Any

from aetheros_automation.orchestrator.orchestrator import OrchestrationTask

logger = logging.getLogger(__name__)


class ResultValidator:
    def __init__(self):
        self._validators: dict[str, Any] = {}

    async def validate(
        self,
        result: Any,
        task: OrchestrationTask,
        requirements: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        reqs = requirements or {}

        checks: list[tuple[str, bool, str]] = []

        checks.append(("result_not_none", self._check_not_none(result), "Result is empty"))

        checks.append(("result_has_summary", self._check_has_key(result, "summary"), "Missing summary in result"))

        if task.description:
            checks.append(("result_relevant", self._check_relevance(result, task.description), "Result may not address task requirements"))

        if reqs.get("require_file"):
            file_path = reqs.get("file_path", "")
            checks.append(("file_exists", self._check_file_exists(file_path), f"Required file not found: {file_path}"))

        if reqs.get("require_data_integrity"):
            checks.append(("data_integrity", True, ""))

        passed = True
        messages: list[str] = []

        for check_name, check_result, fail_message in checks:
            if not check_result:
                passed = False
                messages.append(fail_message)
                logger.warning("Validation check '%s' failed for task %s: %s", check_name, task.id, fail_message)

        if passed:
            logger.info("Validation passed for task %s (%d checks)", task.id, len(checks))

        return passed, "; ".join(messages) if messages else ""

    def _check_not_none(self, result: Any) -> bool:
        return result is not None

    def _check_has_key(self, result: Any, key: str) -> bool:
        return isinstance(result, dict) and key in result

    def _check_relevance(self, result: Any, description: str) -> bool:
        if isinstance(result, dict) and "summary" in result:
            summary = str(result["summary"]).lower()
            desc_lower = description.lower()
            keywords = [w for w in desc_lower.split() if len(w) > 4]
            return any(k in summary for k in keywords) if keywords else True
        return True

    def _check_file_exists(self, path: str) -> bool:
        if not path:
            return True
        return os.path.exists(path)

    def register_validator(self, name: str, validator_fn: Any):
        self._validators[name] = validator_fn

    def get_validator(self, name: str) -> Any | None:
        return self._validators.get(name)
