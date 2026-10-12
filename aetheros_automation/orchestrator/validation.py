from __future__ import annotations

import logging
import os
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, OrchestrationResult, ValidationRule, ValidationResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class ValidationManager:
    def __init__(self):
        self._rules: dict[str, list[ValidationRule]] = {}

    def register_rules(self, task_type: str, rules: list[ValidationRule]):
        self._rules[task_type] = rules

    async def validate_completion(
        self, plan: Plan, result: OrchestrationResult
    ) -> ValidationResult:
        validation = ValidationResult()
        if plan.tasks:
            completed = [t for t in plan.tasks if t.status == TaskStatus.COMPLETED]
            failed = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
            if failed:
                validation.valid = False
                validation.errors.append(
                    f"{len(failed)} task(s) failed: {', '.join(t.name for t in failed)}"
                )
            for task in plan.tasks:
                if task.status == TaskStatus.COMPLETED:
                    if task.validation_rules:
                        task_validation = self._validate_task(task)
                        if not task_validation.valid:
                            validation.valid = False
                            validation.errors.extend(task_validation.errors)
                            validation.warnings.extend(task_validation.warnings)
                if task.error:
                    validation.warnings.append(f"Task '{task.name}' had errors: {task.error}")
        if result.error:
            validation.valid = False
            validation.errors.append(result.error)
        if result.errors:
            validation.valid = False
            validation.errors.extend(result.errors)
        return validation

    async def validate_task_output(
        self, task, output: dict
    ) -> ValidationResult:
        validation = ValidationResult()
        rules = task.validation_rules or []
        for rule in rules:
            if rule.field:
                value = output.get(rule.field)
                if rule.operator == "exists" and value is None:
                    validation.valid = False
                    validation.errors.append(
                        rule.error_message or f"Field '{rule.field}' is missing"
                    )
                elif rule.operator == "equals" and value != rule.expected_value:
                    validation.valid = False
                    validation.errors.append(
                        rule.error_message or f"Field '{rule.field}' expected {rule.expected_value}, got {value}"
                    )
                elif rule.operator == "contains" and rule.expected_value and value and rule.expected_value not in str(value):
                    validation.valid = False
                    validation.errors.append(
                        rule.error_message or f"Field '{rule.field}' does not contain '{rule.expected_value}'"
                    )
        return validation

    def _validate_task(self, task) -> ValidationResult:
        validation = ValidationResult()
        if not task.output:
            validation.warnings.append(f"Task '{task.name}' has no output data")
        return validation

    def get_stats(self) -> dict:
        return {
            "registered_rule_sets": len(self._rules),
            "total_rules": sum(len(v) for v in self._rules.values()),
        }
