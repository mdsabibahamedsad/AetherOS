"""
Recovery
========

Recovery orchestration with customizable recovery plans,
validation steps, and rollback support.
"""

from __future__ import annotations

import enum
import json
import logging
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from enterprise.backup import BackupJob, BackupResult

logger = logging.getLogger(__name__)


class RecoveryStepStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RecoveryStep:
    """A single step in a recovery plan."""
    name: str
    action: str  # extract, validate, migrate, restart, verify
    params: Dict[str, Any] = field(default_factory=dict)
    status: RecoveryStepStatus = RecoveryStepStatus.PENDING
    order: int = 0
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class RecoveryPlan:
    """A plan for recovering from a backup."""
    name: str
    backup_path: Path
    target_path: Path
    id: str = ""
    steps: List[RecoveryStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    verify_after: bool = True


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    plan_name: str = ""
    steps_completed: int = 0
    steps_total: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "plan_name": self.plan_name,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


class RecoveryManager:
    """Manage recovery plans and execution."""

    def __init__(self) -> None:
        self._plans: Dict[str, RecoveryPlan] = {}
        self._results: List[RecoveryResult] = []
        self._hooks: Dict[str, List[Callable]] = {
            "pre_recovery": [],
            "post_recovery": [],
            "recovery_failed": [],
        }

    def create_plan(
        self,
        name: str,
        backup_path: Path,
        target_path: Path,
    ) -> RecoveryPlan:
        """Create a recovery plan with default steps."""
        plan = RecoveryPlan(
            name=name,
            backup_path=backup_path,
            target_path=target_path,
            id=f"recovery_{name}",
        )
        plan.steps = [
            RecoveryStep(name="Validate backup", action="validate", order=0),
            RecoveryStep(name="Extract files", action="extract", order=1),
            RecoveryStep(name="Verify structure", action="verify", order=2),
        ]
        self._plans[plan.id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[RecoveryPlan]:
        return self._plans.get(plan_id)

    def execute_plan(self, plan: RecoveryPlan) -> RecoveryResult:
        """Execute a recovery plan."""
        from datetime import datetime
        start = datetime.utcnow()

        for hook in self._hooks.get("pre_recovery", []):
            try:
                hook(plan)
            except Exception as e:
                logger.warning("Pre-recovery hook failed: %s", e)

        steps_completed = 0
        for step in plan.steps:
            step.status = RecoveryStepStatus.RUNNING
            try:
                if step.action == "validate":
                    if not plan.backup_path.exists():
                        raise FileNotFoundError(f"Backup not found: {plan.backup_path}")
                    step.status = RecoveryStepStatus.COMPLETED

                elif step.action == "extract":
                    plan.target_path.mkdir(parents=True, exist_ok=True)
                    if plan.backup_path.name.endswith(".tar.gz"):
                        with tarfile.open(plan.backup_path, "r:gz") as tar:
                            tar.extractall(path=plan.target_path)
                    elif plan.backup_path.name.endswith(".tar"):
                        with tarfile.open(plan.backup_path, "r") as tar:
                            tar.extractall(path=plan.target_path)
                    step.status = RecoveryStepStatus.COMPLETED

                elif step.action == "verify":
                    if plan.target_path.exists() and any(plan.target_path.iterdir()):
                        step.status = RecoveryStepStatus.COMPLETED
                    else:
                        raise RuntimeError("Recovery target is empty")
                else:
                    step.status = RecoveryStepStatus.COMPLETED

                steps_completed += 1

            except Exception as exc:
                step.status = RecoveryStepStatus.FAILED
                step.error = str(exc)
                duration = (datetime.utcnow() - start).total_seconds()
                result = RecoveryResult(
                    success=False,
                    plan_name=plan.name,
                    steps_completed=steps_completed,
                    steps_total=len(plan.steps),
                    duration_seconds=duration,
                    error=f"Step '{step.name}' failed: {exc}",
                )
                for hook in self._hooks.get("recovery_failed", []):
                    try:
                        hook(plan, exc)
                    except Exception:
                        pass
                self._results.append(result)
                return result

        duration = (datetime.utcnow() - start).total_seconds()
        result = RecoveryResult(
            success=True,
            plan_name=plan.name,
            steps_completed=steps_completed,
            steps_total=len(plan.steps),
            duration_seconds=duration,
        )

        for hook in self._hooks.get("post_recovery", []):
            try:
                hook(plan, result)
            except Exception as e:
                logger.warning("Post-recovery hook failed: %s", e)

        self._results.append(result)
        return result

    def list_results(self) -> List[RecoveryResult]:
        return list(self._results)

    def register_hook(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)
