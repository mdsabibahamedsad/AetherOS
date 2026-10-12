from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, Checkpoint, TaskTemplate, OrchestrationResult, ExecutionStats,
    TaskStatus,
)

logger = logging.getLogger(__name__)


def _default_storage_dir() -> str:
    try:
        from aetheros_constants import get_aetheros_home
        return str(get_aetheros_home() / "automation" / "orchestrator")
    except Exception:  # pragma: no cover - fallback for standalone use
        return os.path.join(
            os.path.expanduser("~/.aetheros"), "automation", "orchestrator"
        )


_STORAGE_DIR = _default_storage_dir()


class OrchestratorStore:
    def __init__(self, storage_dir: str = ""):
        self._storage_dir = storage_dir or _STORAGE_DIR
        self._plans: dict[str, Plan] = {}
        self._checkpoints: dict[str, Checkpoint] = {}
        self._templates: dict[str, TaskTemplate] = {}
        self._results: dict[str, OrchestrationResult] = {}
        os.makedirs(self._storage_dir, exist_ok=True)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ("plans", "checkpoints", "templates", "results"):
            os.makedirs(os.path.join(self._storage_dir, sub), exist_ok=True)

    def save_plan(self, plan: Plan):
        self._plans[plan.id] = plan
        self._persist_plan(plan)

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        if plan_id in self._plans:
            return self._plans[plan_id]
        return self._load_plan(plan_id)

    def list_plans(
        self, status: Optional[str] = None, limit: int = 50
    ) -> list[Plan]:
        plans = list(self._plans.values())
        if not plans:
            plans = self._load_all_plans()
        if status:
            plans = [p for p in plans if p.status == status]
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans[:limit]

    def delete_plan(self, plan_id: str) -> bool:
        if plan_id in self._plans:
            del self._plans[plan_id]
        path = os.path.join(self._storage_dir, "plans", f"{plan_id}.json")
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False

    def save_checkpoint(self, checkpoint: Checkpoint):
        self._checkpoints[checkpoint.id] = checkpoint
        self._persist_checkpoint(checkpoint)

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]
        path = os.path.join(self._storage_dir, "checkpoints", f"{checkpoint_id}.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                ckpt = Checkpoint(**data)
                self._checkpoints[ckpt.id] = ckpt
                return ckpt
            except Exception as e:
                logger.warning("Failed to load checkpoint %s: %s", checkpoint_id, e)
        return None

    def save_template(self, template: TaskTemplate):
        self._templates[template.id] = template
        self._persist_template(template)

    def load_template(self, template_id: str) -> Optional[TaskTemplate]:
        if template_id in self._templates:
            return self._templates[template_id]
        path = os.path.join(self._storage_dir, "templates", f"{template_id}.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                template = TaskTemplate(**data)
                self._templates[template.id] = template
                return template
            except Exception:
                pass
        return None

    def save_result(self, result: OrchestrationResult):
        self._results[result.plan_id] = result
        path = os.path.join(self._storage_dir, "results", f"{result.plan_id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "plan_id": result.plan_id,
                    "success": result.success,
                    "status": result.status,
                    "tasks_completed": result.tasks_completed,
                    "tasks_failed": result.tasks_failed,
                    "total_duration": result.total_duration,
                    "total_cost": result.total_cost,
                    "error": result.error,
                }, f, indent=2)
        except Exception as e:
            logger.warning("Failed to persist result: %s", e)

    def get_stats(self) -> ExecutionStats:
        plans = list(self._plans.values())
        if not plans:
            plans = self._load_all_plans()
        completed = [p for p in plans if p.status == "completed"]
        failed = [p for p in plans if p.status == "failed"]
        running = [p for p in plans if p.status == "running"]
        pending = [p for p in plans if p.status == "pending"]
        durations = []
        for p in completed:
            if p.completed_at and p.started_at:
                durations.append(p.completed_at - p.started_at)
        avg_dur = sum(durations) / len(durations) if durations else 0.0
        return ExecutionStats(
            total_plans=len(plans),
            completed_plans=len(completed),
            failed_plans=len(failed),
            running_plans=len(running),
            pending_plans=len(pending),
            total_tasks=sum(len(p.tasks) for p in plans),
            completed_tasks=sum(
                len([t for t in p.tasks if t.status == TaskStatus.COMPLETED])
                for p in plans
            ),
            failed_tasks=sum(
                len([t for t in p.tasks if t.status == TaskStatus.FAILED])
                for p in plans
            ),
            avg_duration=avg_dur,
        )

    def _persist_plan(self, plan: Plan):
        path = os.path.join(self._storage_dir, "plans", f"{plan.id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._plan_to_dict(plan), f, indent=2, default=str)
        except Exception as e:
            logger.warning("Failed to persist plan: %s", e)

    def _load_plan(self, plan_id: str) -> Optional[Plan]:
        path = os.path.join(self._storage_dir, "plans", f"{plan_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            plan = Plan(
                id=data.get("id", plan_id),
                goal=data.get("goal", ""),
                status=data.get("status", "pending"),
                created_at=data.get("created_at", 0),
                started_at=data.get("started_at", 0),
                completed_at=data.get("completed_at", 0),
                estimated_time=data.get("estimated_time", 0),
                estimated_cost=data.get("estimated_cost", 0),
                error=data.get("error", ""),
                metadata=data.get("metadata", {}),
            )
            self._plans[plan.id] = plan
            return plan
        except Exception as e:
            logger.warning("Failed to load plan %s: %s", plan_id, e)
            return None

    def _load_all_plans(self) -> list[Plan]:
        plans_dir = os.path.join(self._storage_dir, "plans")
        if not os.path.isdir(plans_dir):
            return []
        plans = []
        for name in os.listdir(plans_dir):
            if name.endswith(".json"):
                plan_id = name[:-5]
                plan = self._load_plan(plan_id)
                if plan:
                    plans.append(plan)
        return plans

    def _plan_to_dict(self, plan: Plan) -> dict:
        return {
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status,
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "estimated_time": plan.estimated_time,
            "estimated_cost": plan.estimated_cost,
            "risk_level": plan.risk_level.value if hasattr(plan.risk_level, 'value') else str(plan.risk_level),
            "error": plan.error,
            "metadata": plan.metadata,
        }

    def _persist_checkpoint(self, checkpoint: Checkpoint):
        path = os.path.join(self._storage_dir, "checkpoints", f"{checkpoint.id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": checkpoint.id,
                    "plan_id": checkpoint.plan_id,
                    "completed_task_ids": checkpoint.completed_task_ids,
                    "pending_task_ids": checkpoint.pending_task_ids,
                    "errors": checkpoint.errors,
                    "created_at": checkpoint.created_at,
                }, f, indent=2)
        except Exception as e:
            logger.warning("Failed to persist checkpoint: %s", e)

    def _persist_template(self, template: TaskTemplate):
        path = os.path.join(self._storage_dir, "templates", f"{template.id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category.value if hasattr(template.category, 'value') else str(template.category),
                    "estimated_duration": template.estimated_duration,
                    "estimated_cost": template.estimated_cost,
                    "tags": template.tags,
                    "is_builtin": template.is_builtin,
                }, f, indent=2)
        except Exception as e:
            logger.warning("Failed to persist template: %s", e)
