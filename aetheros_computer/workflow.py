"""
Application workflows over the unified dispatcher (Master 15 Phase 47).

A workflow is a declarative step list executed through ``Dispatcher.execute``
so EVERY step inherits: estop/safe-mode/budget gates, approval, verification,
checkpointing, audit, and stream events. Steps carry optional ``depends_on``
for linear/DAG ordering; failure stops unless the step declares
``on_failure: continue``.

MASTER 11/13 connection: an orchestrator or cron job can drive
:func:`run_workflow` (pure async entry), and every run is checkpointed by
task_id so cron-triggered reruns RESUME instead of repeating irreversible
work (delegates to task_checkpoint.resume_filter + record_completion).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_STEPS = 64


@dataclass
class WorkflowStep:
    step_id: str
    action: str
    intent: str = ""
    target: str = ""
    depends_on: List[str] = field(default_factory=list)
    on_failure: str = "stop"          # stop | continue | skip
    max_retries: int = 0


@dataclass
class WorkflowResult:
    task_id: str
    status: str                        # completed | failed | stopped_budget | blocked
    completed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


def normalize_workflow_steps(steps: List[Dict[str, Any]]) -> List[WorkflowStep]:
    if not isinstance(steps, list) or not steps:
        raise ValueError("workflow steps must be a non-empty list")
    if len(steps) > MAX_STEPS:
        raise ValueError(f"workflow supports at most {MAX_STEPS} steps")
    out: List[WorkflowStep] = []
    seen = set()
    for raw in steps:
        sid = str(raw.get("step_id") or raw.get("id") or "").strip()
        action = str(raw.get("action") or "").strip()
        if not sid or any(ch.isspace() for ch in sid):
            raise ValueError(f"invalid step id {raw.get('id')!r}")
        if sid in seen:
            raise ValueError(f"duplicate step id {sid!r}")
        if not action:
            raise ValueError(f"step {sid!r} missing action")
        deps = [str(d).strip() for d in (raw.get("depends_on") or []) if str(d).strip()]
        out.append(WorkflowStep(
            step_id=sid,
            action=action,
            intent=str(raw.get("intent", "")),
            target=str(raw.get("target", "")),
            depends_on=deps,
            on_failure=str(raw.get("on_failure", "stop")).lower(),
            max_retries=int(raw.get("max_retries", 0) or 0),
        ))
        seen.add(sid)
    unknown = {d for s in out for d in s.depends_on} - seen
    if unknown:
        raise ValueError(f"unknown depends_on entries: {sorted(unknown)}")
    return out


async def run_workflow(
    dispatcher: Any,
    task_id: str,
    goal: str,
    steps: List[Dict[str, Any]],
    session_key: str = "",
) -> WorkflowResult:
    """Execute a workflow through the dispatcher with checkpoint/resume."""
    started = time.time()
    norm = normalize_workflow_steps(steps)

    from aetheros_computer import task_checkpoint as tcp

    tcp.start_task(task_id, goal=goal)
    done_before = set(tcp.completed_ids(task_id))
    budget = tcp.check_budget(task_id)

    result = WorkflowResult(task_id=task_id, status="completed")
    done: set = set(done_before)
    pending_ids = [s.step_id for s in norm]
    remaining = tcp.resume_filter(task_id, pending_ids)

    # Topological-ish pass: iterate until no progress (simple DAG loop guard).
    progress = True
    while remaining and progress:
        progress = False
        for step in list(norm):
            if step.step_id not in remaining:
                continue
            if any(d not in done for d in step.depends_on):
                continue
            remaining.remove(step.step_id)
            progress = True

            budget = tcp.check_budget(task_id)
            if not budget["allowed"]:
                result.status = "stopped_budget"
                result.error = f"budget exhausted at step '{step.step_id}'"
                return _finish(result, started)

            from aetheros_computer.action import ActionMetadata, ActionDomain, RiskTier, get_action_risk
            md = ActionMetadata(
                action_type=step.action,
                target=step.target,
                intent=step.intent or f"workflow:{goal}:{step.step_id}",
                task_id=task_id,
                domain=ActionDomain.SYSTEM,
                risk_level=get_action_risk(step.action),
                max_retries=step.max_retries,
            )
            outcome = await dispatcher.execute(md, {"session_key": session_key})
            success = bool(outcome.get("success"))
            if success:
                done.add(step.step_id)
                result.completed.append(step.step_id)
            else:
                if step.on_failure == "continue":
                    result.skipped.append(step.step_id)
                    continue
                if step.on_failure == "skip":
                    result.skipped.append(step.step_id)
                    done.add(step.step_id)   # unblock dependents? NO — keep blocked:
                    done.discard(step.step_id)
                    continue
                result.status = "failed"
                result.failed_step = step.step_id
                result.error = str(outcome.get("error", "step failed"))
                return _finish(result, started)

    if result.status == "completed" and remaining:
        result.status = "blocked"
        result.error = f"circular or unsatisfiable dependencies: {sorted(remaining)}"
    return _finish(result, started)


def _finish(result: WorkflowResult, started: float) -> WorkflowResult:
    result.duration_seconds = round(time.time() - started, 4)
    try:
        from aetheros_computer.events_stream import get_stream

        get_stream().emit(
            "COMPLETE" if result.status == "completed" else "FAILED",
            task_id=result.task_id, action="workflow",
            detail=f"{result.status} completed={len(result.completed)} "
                   f"skipped={len(result.skipped)}",
        )
    except Exception:
        pass
    return result


__all__ = [
    "WorkflowStep",
    "WorkflowResult",
    "normalize_workflow_steps",
    "run_workflow",
]
