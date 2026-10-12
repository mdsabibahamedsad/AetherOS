"""
MASTER 13 automation entrypoint for computer workflows (Phase 90).

Cron jobs created through the existing ``cronjob`` tool can invoke
:func:`run_workflow_scheduled` from a job script/prompt-driven flow. The
workflow executes through the standard Dispatcher pipeline, so EVERY global
control stays active for scheduled runs: emergency stop, safe mode, task
budgets, approvals, verification, checkpoints/resume.

This is a thin adapter — no scheduler changes, no new queue.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List


def run_workflow_scheduled(
    dispatcher: Any,
    task_id: str,
    goal: str,
    steps: List[Dict[str, Any]],
    session_key: str = "",
) -> Dict[str, Any]:
    """Sync bridge so cron's script runner can drive a Master-15 workflow."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(
                asyncio.run,
                _run(dispatcher, task_id, goal, steps, session_key),
            )
            return fut.result()
    return asyncio.run(_run(dispatcher, task_id, goal, steps, session_key))


async def _run(dispatcher, task_id, goal, steps, session_key):
    from aetheros_computer.workflow import WorkflowResult, run_workflow

    res: WorkflowResult = await run_workflow(dispatcher, task_id, goal, steps,
                                             session_key=session_key)
    return {
        "task_id": res.task_id, "status": res.status,
        "completed": res.completed, "skipped": res.skipped,
        "failed_step": res.failed_step, "error": res.error,
        "duration_seconds": res.duration_seconds,
    }


__all__ = ["run_workflow_scheduled"]
