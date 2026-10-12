"""Scheduler integration — bridges workflow triggers to the AetherOS cron scheduler."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from workflows.store import WorkflowStore
from workflows.models import WorkflowConfig, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """Manages scheduled workflow execution through AetherOS cron jobs."""

    def __init__(self, store: Optional[WorkflowStore] = None):
        self.store = store or WorkflowStore()

    def register_scheduled_workflows(self) -> int:
        """Register all active scheduled workflows as cron jobs."""
        from cron.jobs import cron_job_store
        count = 0
        for wf in self.store.list_workflows(status=WorkflowStatus.ACTIVE):
            if not wf.schedule:
                continue
            job_id = f"workflow_{wf.id}"
            cron_job_store.set_job(job_id, {
                "schedule": wf.schedule,
                "command": f"aetheros workflow run {wf.id}",
                "type": "workflow",
                "workflow_id": wf.id,
                "enabled": True,
            })
            count += 1
        return count

    def unregister_workflow_job(self, workflow_id: str) -> bool:
        from cron.jobs import cron_job_store
        return cron_job_store.remove_job(f"workflow_{workflow_id}")

    def sync_schedules(self) -> tuple[int, int]:
        """Sync all workflow schedules with cron: returns (added, removed)."""
        from cron.jobs import cron_job_store
        cron_jobs = {k: v for k, v in cron_job_store.get_all_jobs().items()
                     if v.get("type") == "workflow"}
        active_workflows = [
            wf for wf in self.store.list_workflows(status=WorkflowStatus.ACTIVE)
            if wf.schedule
        ]
        active_ids = {wf.id for wf in active_workflows}
        cron_ids = {k.replace("workflow_", "") for k in cron_jobs}
        to_add = active_ids - cron_ids
        to_remove = cron_ids - active_ids
        for wf_id in to_add:
            wf = self.store.get_workflow(wf_id)
            if wf and wf.schedule:
                cron_job_store.set_job(f"workflow_{wf.id}", {
                    "schedule": wf.schedule,
                    "command": f"aetheros workflow run {wf.id}",
                    "type": "workflow",
                    "workflow_id": wf.id,
                    "enabled": True,
                })
        for wf_id in to_remove:
            cron_job_store.remove_job(f"workflow_{wf_id}")
        return len(to_add), len(to_remove)

    def get_schedule_status(self) -> list[dict]:
        """Return all workflow cron jobs with their status."""
        from cron.jobs import cron_job_store
        jobs = []
        for job_id, job in cron_job_store.get_all_jobs().items():
            if job.get("type") == "workflow":
                jobs.append({
                    "job_id": job_id,
                    "workflow_id": job.get("workflow_id"),
                    "schedule": job.get("schedule"),
                    "enabled": job.get("enabled", True),
                })
        return jobs
