"""Workflow engine (sections 31, 36-38, 61-63): bounded loops, waits,
branches, dry-run + simulation, step debugger.

Steps are dicts: {action, ...}. Supported actions: agent, tool, notify,
memory_write, artifact, wait_time, wait_event, branch, loop, approval,
verify. Dry-run returns would-do lists without side effects.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import RunRecord
from aetheros_autonomy.triggers import eval_condition

StepFn = Callable[[Dict[str, Any], RunRecord, bool], Dict[str, Any]]


class WorkflowEngine:
    def __init__(self, step_fn: Optional[StepFn] = None) -> None:
        self._step_fn = step_fn or (lambda step, run, dry: {
            "action": step.get("action"), "dry": dry, "ok": True})
        self._breakpoints: set = set()

    def describe_plan(self, workflow: List[Dict[str, Any]]) -> List[str]:
        """Simulation: expected path without executing side effects."""
        return [f"{i + 1}. {s.get('action', '?')}: {s.get('goal', s.get('tool', s.get('text', '')))}"[:160]
                for i, s in enumerate(workflow)]

    def run(self, workflow: List[Dict[str, Any]], run: RunRecord, *,
            dry_run: bool = False, debugger: Optional[Dict[str, Any]] = None) -> RunRecord:
        i = 0
        while i < len(workflow):
            step = workflow[i]
            action = str(step.get("action", ""))
            if debugger is not None and (i in self._breakpoints or debugger.get("pause_each")):
                debugger["paused_at"] = i
                debugger["run_id"] = run.run_id
                return run  # paused for inspection; resume() continues
            if action == "branch":
                branch = "then" if eval_condition(step.get("cond", {"op": "true"}),
                                                  {"run": run.to_dict()}) else "else"
                for sub in step.get(branch, []):
                    self.run([sub], run, dry_run=dry_run)
            elif action == "loop":
                self._run_loop(step, run, dry_run=dry_run)
            elif action in ("wait_time", "wait_event", "wait_approval"):
                run.steps.append({"action": action, "waiting": True,
                                  "spec": {k: v for k, v in step.items() if k != "action"}})
                if not dry_run:
                    run.steps[-1]["note"] = "wait registered; run resumes on signal"
            else:
                result = self._step_fn(step, run, dry_run)
                run.steps.append({"action": action, **result})
                if not result.get("ok", True) and not dry_run:
                    run.error = str(result.get("error", f"step failed: {action}"))[:400]
                    break
            i += 1
        return run

    def _run_loop(self, step: Dict[str, Any], run: RunRecord, *, dry_run: bool) -> None:
        items = step.get("for_each", [])
        max_iter = int(step.get("max_iterations", len(items) or 1))
        budget_s = float(step.get("timeout_s", 600.0))
        if max_iter <= 0 or max_iter > 1000:
            run.steps.append({"action": "loop", "ok": False,
                              "error": "loop requires 1..1000 max_iterations"})
            run.error = "invalid loop bounds"
            return
        deadline = time.time() + budget_s
        body = step.get("do", [])
        for n, item in enumerate(items[:max_iter]):
            if time.time() > deadline:
                run.steps.append({"action": "loop", "ok": False,
                                  "error": f"loop timeout after {n} iterations"})
                break
            for sub in body:
                merged = dict(sub)
                merged["item"] = item
                self.run([merged], run, dry_run=dry_run)
            if run.error:
                break

    # -- debugger ----------------------------------------------------------
    def add_breakpoint(self, index: int) -> None:
        self._breakpoints.add(index)

    def clear_breakpoints(self) -> None:
        self._breakpoints.clear()

    def resume(self, workflow: List[Dict[str, Any]], run: RunRecord,
               debugger: Dict[str, Any], *, dry_run: bool = False) -> RunRecord:
        start = int(debugger.pop("paused_at", 0))
        return self.run(workflow[start:], run, dry_run=dry_run, debugger=None)
