"""
Workflow execution engine (Master 13 Phases 18-26, 38-42, 47).

Executes an automation's DAG through the SAME machinery as ordinary cron
runs: every step is executed by ``cron.scheduler.run_job`` on a synthetic
single-prompt job, so prompt-injection scanning, toolset denylists,
resource limits and provider fallback all apply per step. No second worker
infrastructure exists.

Contract for ``run_workflow(job)`` mirrors ``run_job``:
    (success, output_doc, final_response, error)

Versioning (Phase 19): the normalized spec is snapshotted into the run
record at start; a running execution always finishes on the spec version it
started with. New dispatches pick up edited definitions automatically.
"""

from __future__ import annotations

import inspect
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 120


def _call_notify(notify_fn, message: str, event_type: str) -> None:
    """Invoke a notification callback honoring both calling conventions.

    New-style callbacks accept ``(message, event_type)`` so delivery can gate
    on notification preferences (Phases 59-61); legacy single-argument
    callbacks keep working unchanged.
    """
    try:
        accepts_event = len(inspect.signature(notify_fn).parameters) >= 2
    except (TypeError, ValueError):
        accepts_event = False
    if accepts_event:
        notify_fn(message, event_type)
    else:
        notify_fn(message)


def _notify_bus(event_type: str, payload: Dict[str, Any]) -> None:
    try:
        from automation.events import publish_internal

        publish_internal(event_type, payload, source="workflow")
    except Exception:
        logger.debug("Workflow event emission failed", exc_info=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _backoff_seconds(attempt: int) -> float:
    base = min(DEFAULT_BACKOFF_SECONDS * attempt, MAX_BACKOFF_SECONDS)
    return base + random.uniform(0, 1.0)


def run_workflow(
    job: dict,
    notify_fn=None,
) -> Tuple[bool, str, str, Optional[str]]:
    """Execute (or resume) one automation's workflow. See module docstring."""
    from automation import approvals, runs as run_store, workflow as wf

    job_id = job.get("id") or "unknown"
    name = str(job.get("name") or job_id)

    try:
        spec = wf.normalize_workflow(job.get("workflow"))
    except ValueError as exc:
        return False, f"# Workflow '{name}' INVALID\n\n{exc}", "", str(exc)
    if not spec:
        return False, "", "", "workflow missing"

    active = run_store.active_run_for(str(job_id))
    if active is not None:
        # Phase 19: resume on the snapshotted spec, not the current one.
        run = active
        spec = run.get("spec") or spec
    else:
        run = run_store.new_run(
            str(job_id), name, job.get("definition_version", 1), spec
        )
        run["spec"] = spec
        run_store.save_run(run)
        _notify_bus("automation.progress", {
            "automation_id": job_id, "run_id": run["run_id"],
            "state": "started",
        })

    if run_store.cancel_requested(run):
        run_store.finish_run(run, "cancelled")
        _notify_bus("automation.cancelled", {"automation_id": job_id, "run_id": run["run_id"]})
        return False, _doc(name, run, "cancelled"), "", "workflow cancelled"

    serial_only = bool((job.get("workdir") or "").strip())
    concurrency = 1 if serial_only else int(spec.get("concurrency") or 1)

    while True:
        # Cancellation may come from another process (CLI); re-read the
        # durable flag at every step boundary (Phase 47).
        fresh = run_store.load_run(run["run_id"])
        if fresh and fresh.get("cancel_requested"):
            run["cancel_requested"] = True
        if run_store.cancel_requested(run):
            run_store.finish_run(run, "cancelled")
            _notify_bus("automation.cancelled", {"automation_id": job_id, "run_id": run["run_id"]})
            return False, _doc(name, run, "cancelled"), "", "workflow cancelled"

        blocked_by_approval, waiting_step = _approval_gate(
            job, run, spec, notify_fn
        )
        if blocked_by_approval:
            return waiting_step

        from automation.errors import is_retryable  # noqa: F401 (used below)

        ready = wf.ready_steps(run["steps"], spec)
        # ready_steps may mark condition-false branches skipped — checkpoint
        # that transition so a crash cannot resurrect a skipped branch.
        run_store.save_run(run)
        if not ready:
            break

        batch = ready[: max(1, concurrency)]
        if len(batch) == 1:
            outcomes = [_execute_step(job, run, spec, next(s for s in spec["steps"] if s["id"] == batch[0]), notify_fn)]
        else:
            with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix="wf-step") as pool:
                outcomes = list(pool.map(
                    lambda sid: _execute_step(
                        job, run, spec,
                        next(s for s in spec["steps"] if s["id"] == sid), notify_fn,
                    ),
                    batch,
                ))
        stop_now = False
        for step_id, status, error in outcomes:
            step_spec = next(s for s in spec["steps"] if s["id"] == step_id)
            policy = step_spec.get("on_failure") or "stop"
            if status == "done":
                continue
            if status == "skipped":
                continue
            # failed
            global_policy = spec.get("on_failure") or "stop"
            effective = policy if policy != "stop" else global_policy
            if effective == "pause":
                run["status"] = "paused"
                run_store.save_run(run)
                _notify_bus("automation.progress", {
                    "automation_id": job_id, "run_id": run["run_id"],
                    "state": "paused", "step": step_id, "error": error,
                })
                return False, _doc(name, run, "paused"), "", f"paused at step '{step_id}': {error}"
            if effective == "stop":
                stop_now = True
        if stop_now:
            run_store.finish_run(run, "failed")
            _notify_bus("automation.failed", {
                "automation_id": job_id, "run_id": run["run_id"],
            })
            return False, _doc(name, run, "failed"), "", _first_error(run)
        # skip / continue policies: loop continues; dependent steps of a
        # skipped step stay blocked (safe semantics, documented).

        if any(
            state.get("status") == "running"
            for state in run["steps"].values()
        ):
            # A parallel batch member crashed hard mid-mark; avoid spin.
            break

    statuses = [s.get("status") for s in run["steps"].values()]
    if all(s in ("done", "skipped") for s in statuses):
        run_store.finish_run(run, "completed")
        final = _last_output(run)
        _notify_bus("automation.progress", {
            "automation_id": job_id, "run_id": run["run_id"], "state": "completed",
        })
        return True, _doc(name, run, "completed"), final, None

    run_store.finish_run(run, "failed")
    return False, _doc(name, run, "failed"), "", _first_error(run) or "no runnable steps"


def _execute_step(
    parent_job: dict,
    run: dict,
    spec: dict,
    step: dict,
    notify_fn=None,
) -> Tuple[str, str, Optional[str]]:
    """Run one step with retries; checkpoints each milestone. Returns
    (step_id, final_status, error)."""
    from automation import runs as run_store
    from automation.errors import classify, is_retryable

    step_id = step["id"]
    attempts_allowed = int(step.get("attempts") or 1)
    last_error: Optional[str] = None

    while True:
        state = run["steps"][step_id]
        attempt_index = int(state.get("attempts") or 0)
        # Checkpoint every attempt so a crash mid-step cannot loop retries.
        state["attempts"] = attempt_index + 1
        state["status"] = "running"
        run_store.save_run(run)

        success, output, _final_response, error = _invoke(
            parent_job, step, run["steps"]
        )
        if success:
            run_store.mark_step(run, step_id, "done", output=output)
            state = run["steps"][step_id]
            state["final_response"] = str(_final_response or "")[:20000]
            run_store.save_run(run)
            _notify_bus("automation.progress", {
                "automation_id": run["automation_id"], "run_id": run["run_id"],
                "step": step_id, "state": "done",
            })
            return step_id, "done", None

        last_error = error
        category = classify(last_error or "")
        can_retry = (
            attempt_index + 1 < attempts_allowed
            and is_retryable(last_error or "")
        )
        logger.warning(
            "Step '%s' attempt %d/%d failed (%s): %s",
            step_id, attempt_index + 1, attempts_allowed, category,
            str(last_error)[:200],
        )
        if can_retry:
            time.sleep(_backoff_seconds(attempt_index + 1))
            continue

        policy = step.get("on_failure") or "stop"
        if policy in ("skip", "continue"):
            run_store.mark_step(
                run, step_id, "skipped", output="", error=last_error or ""
            )
            _notify_bus("automation.progress", {
                "automation_id": run["automation_id"], "run_id": run["run_id"],
                "step": step_id, "state": "skipped", "error": last_error,
            })
            return step_id, "skipped", last_error
        run_store.mark_step(run, step_id, "failed", output="", error=last_error or "")
        _notify_bus("automation.progress", {
            "automation_id": run["automation_id"], "run_id": run["run_id"],
            "step": step_id, "state": "failed", "error": last_error,
        })
        return step_id, "failed", last_error


def _invoke(parent_job: dict, step: dict, run_steps: Dict[str, Any]) -> Tuple[bool, str, str, Optional[str]]:
    """Execute one step through the standard run_job path, with upstream
    outputs injected as context (Phase 20 data flow)."""
    from automation.workflow import build_step_prompt
    from cron.scheduler import run_job

    synthetic = {k: v for k, v in parent_job.items()
                 if k not in {"workflow", "trigger", "next_run_at"}}
    script_only = bool(step.get("script")) and not str(step.get("prompt") or "").strip()
    if script_only:
        synthetic["prompt"] = ""
    else:
        synthetic["prompt"] = build_step_prompt(step, run_steps)
    synthetic["script"] = step.get("script")
    synthetic["no_agent"] = bool(script_only)
    limits = dict(parent_job.get("resource_limits") or {})
    if step.get("max_turns"):
        limits["max_turns"] = step["max_turns"]
    synthetic["resource_limits"] = limits or None
    return run_job(synthetic)


def _approval_gate(job, run, spec, notify_fn) -> Tuple[bool, Optional[Tuple[bool, str, str, Optional[str]]]]:
    """Phase 22-23: pause on approval-required steps before they execute."""
    import automation.runs as run_store
    import automation.workflow as wf

    from automation import approvals

    job_id = str(job.get("id"))
    name = str(job.get("name") or job_id)

    request = approvals.load(job_id)
    if request is not None and request.get("status") != "pending":
        if request.get("status") == "approved":
            step_id = str(request.get("step_id") or "")
            if step_id in run.get("steps"):
                run["steps"][step_id]["approved"] = True
                run_store.save_run(run)
            try:
                os_remove_approval(job_id)
            except Exception:
                pass
        else:
            # denied or expired — never executes silently (Phase 23)
            reason = f"approval {request.get('status')} for step '{request.get('step_id')}'"
            target = str(request.get("step_id") or "")
            if target in run.get("steps", {}):
                run_store.mark_step(run, target, "failed", error=reason)
            run_store.finish_run(run, "failed")
            _notify_bus("automation.failed", {
                "automation_id": job_id, "run_id": run["run_id"], "error": reason,
            })
            return True, (False, _doc(name, run, "failed"), "", reason)

    for step in spec["steps"]:
        if not step.get("approval_required"):
            continue
        state = run["steps"].get(step["id"]) or {}
        if state.get("status") != "pending" or state.get("approved"):
            continue
        deps_done = all(
            run["steps"].get(d, {}).get("status") == "done"
            for d in step["depends_on"]
        )
        if not deps_done:
            continue

        existing = approvals.pending_request(job_id)
        if existing is None:
            cfg_timeout = _approval_timeout()
            request = approvals.create_request(
                job_id, name,
                f"Step '{step['id']}' requires approval before running",
                run_id=run["run_id"], step_id=step["id"],
                timeout_seconds=cfg_timeout,
            )
            run["status"] = "waiting_approval"
            run_store.save_run(run)
            message = (
                f"⏸ Automation '{name}' is WAITING APPROVAL\n"
                f"Step: {step['id']}\n"
                f"Approve:  aetheros automation approve {job_id}\n"
                f"Deny:     aetheros automation deny {job_id}\n"
                f"Expires:  {request.get('expires_at')}"
            )
            if notify_fn:
                try:
                    _call_notify(notify_fn, message, "automation.waiting_approval")
                except Exception:
                    logger.exception("Approval notification delivery failed")
            _notify_bus("automation.waiting_approval", {
                "automation_id": job_id, "run_id": run["run_id"],
                "step": step["id"],
            })
        return True, (True, _doc(name, run, "waiting_approval"), "[SILENT]", None)

    return False, None


def _approval_timeout() -> int:
    try:
        from aetheros_cli.config import load_config

        cfg = load_config() or {}
        section = cfg.get("automation", {}) or {}
        wf_cfg = section.get("workflow", {}) or {}
        return int(wf_cfg.get("approval_timeout_seconds", 3600))
    except Exception:
        return 3600


def os_remove_approval(automation_id: str) -> None:
    from automation.approvals import _path

    try:
        _path(automation_id).unlink(missing_ok=True)
    except OSError:
        pass


def expire_pending_run(request: dict) -> None:
    """Called by the dispatcher when an approval expires (never executes)."""
    import automation.runs as run_store

    run = run_store.load_run(str(request.get("run_id") or ""))
    if run is None or run.get("status") in run_store.TERMINAL_STATUSES:
        return
    reason = f"approval expired for step '{request.get('step_id')}'"
    target = str(request.get("step_id") or "")
    if target in run.get("steps", {}):
        run_store.mark_step(run, target, "failed", error=reason)
    run_store.finish_run(run, "expired")
    _notify_bus("automation.failed", {
        "automation_id": request.get("automation_id"),
        "run_id": run["run_id"], "error": reason,
    })


def _last_output(run: dict) -> str:
    """Final response of the last completed step (falls back to raw output)."""
    for sid in reversed(list(run["steps"].keys())):
        state = run["steps"][sid]
        if state.get("status") != "done":
            continue
        final = str(state.get("final_response") or "").strip()
        if final:
            return final
        raw = str(state.get("output") or "").strip()
        if raw:
            return raw
    return ""


def _first_error(run: dict) -> str:
    for sid, state in run["steps"].items():
        if state.get("status") == "failed" and state.get("error"):
            return f"step '{sid}': {state['error']}"
    return ""


def _doc(name: str, run: dict, status: str) -> str:
    lines = [
        f"# Workflow: {name}",
        "",
        f"**Status:** {status}",
        f"**Version:** {run.get('definition_version', 1)}",
        f"**Run ID:** {run.get('run_id')}",
        "",
        "| Step | Status | Note |",
        "|------|--------|------|",
    ]
    for sid, state in run["steps"].items():
        note = str(state.get("error") or state.get("skip_reason") or "")[:120]
        lines.append(f"| {sid} | {state.get('status')} | {note} |")
    return "\n".join(lines) + "\n"
