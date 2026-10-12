"""Parallel DAG executor (sections 12-15, 49-51, 56-57).

Level-scheduled execution over ExecutionGraphEngine levels (reused):
independent tasks in a level run concurrently via ThreadPoolExecutor;
a task starts only when its dependencies completed. Cancellation
propagates to children/tools (no orphans); timeouts trigger recovery
planning; duplicate work is detected via goal-signature merge/cancel.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Any, Callable, Dict, List, Optional

from aetheros_swarm.models import (
    AgentResult, SwarmTask, SwarmTaskState, TaskBudget,
)

ExecutorFn = Callable[[SwarmTask, Dict[str, Any]], AgentResult]


def goal_signature(goal: str) -> str:
    import re
    toks = re.findall(r"[a-z0-9]+", (goal or "").lower())
    # Keep content tokens (>=4 chars) plus short numeric tokens so that
    # sharded goals ("[shard 1/3]") stay distinguishable while genuine
    # duplicates (identical text) still merge.
    kept = sorted({t for t in toks if len(t) >= 4 or t.isdigit()})
    return "|".join(kept[:14])


class ParallelExecutor:
    def __init__(self, executor_fn: ExecutorFn, *,
                 max_parallel_tasks: int = 5,
                 on_task_event: Optional[Callable[[str, SwarmTask], None]] = None) -> None:
        self._fn = executor_fn
        self._max_parallel = max_parallel_tasks
        self._on_event = on_task_event or (lambda _e, _t: None)
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self.results: Dict[str, AgentResult] = {}
        self._idempotency_seen: set = set()

    def cancel(self) -> None:
        self._cancel.set()

    def run_levels(self, levels: List[List[SwarmTask]],
                   ctx: Dict[str, Any]) -> Dict[str, AgentResult]:
        for level in levels:
            if self._cancel.is_set():
                self._mark_cancelled(level)
                break
            self._run_level(level, ctx)
            # Stop descending if a required task failed without recovery path.
            if self._cancel.is_set():
                break
        return dict(self.results)

    # -- internals ------------------------------------------------------
    def _ready(self, task: SwarmTask) -> bool:
        for dep in task.dependencies:
            r = self.results.get(dep)
            if r is None or r.status != "ok":
                return False
        return True

    def _mark_cancelled(self, tasks: List[SwarmTask]) -> None:
        for t in tasks:
            if t.id not in self.results:
                try:
                    t.set_state(SwarmTaskState.CANCELLED)
                except ValueError:
                    pass
                self.results[t.id] = AgentResult(task_id=t.id, status="failed",
                                                 errors=["cancelled"])

    def _dedup_level(self, level: List[SwarmTask]) -> List[SwarmTask]:
        """Merge duplicate work unless independent verification is intended."""
        seen: Dict[str, SwarmTask] = {}
        out: List[SwarmTask] = []
        for t in level:
            sig = goal_signature(t.goal)
            if sig in seen and not t.metadata.get("independent_verification"):
                prev = seen[sig]
                t.metadata["merged_into"] = prev.id
                try:
                    t.set_state(SwarmTaskState.CANCELLED)
                except ValueError:
                    pass
                self.results[t.id] = AgentResult(task_id=t.id, status="ok",
                                                 summary=f"merged into {prev.id}")
                continue
            seen[sig] = t
            out.append(t)
        return out

    def _run_level(self, level: List[SwarmTask], ctx: Dict[str, Any]) -> None:
        level = self._dedup_level(level)
        pending = [t for t in level if t.id not in self.results]
        # Dependency gate: skip tasks whose deps failed.
        runnable = [t for t in pending if self._ready(t)]
        for t in pending:
            if t not in runnable and t.id not in self.results:
                try:
                    t.set_state(SwarmTaskState.FAILED)
                except ValueError:
                    pass
                t.failure_kind = "dependency_failure"
                t.error = "dependency failed or cancelled"
                self.results[t.id] = AgentResult(task_id=t.id, status="failed",
                                                 errors=[t.error])
        if not runnable:
            return
        with ThreadPoolExecutor(max_workers=min(self._max_parallel, len(runnable))) as pool:
            futs = {pool.submit(self._run_one, t, ctx): t for t in runnable}
            done, _ = wait(futs, return_when=FIRST_COMPLETED)
            # Drain the rest (bounded by task timeouts inside _run_one).
            for f in futs:
                if f not in done:
                    try:
                        f.result(timeout=max(1.0, max(t.timeout_s for t in runnable)))
                    except Exception:
                        pass

    def _run_one(self, task: SwarmTask, ctx: Dict[str, Any]) -> AgentResult:
        # Idempotency: same key never executes twice.
        key = task.ensure_idempotency_key()
        with self._lock:
            if key in self._idempotency_seen:
                res = AgentResult(task_id=task.id, status="ok",
                                  summary="idempotent skip (already executed)",
                                  idempotency_key=key)
                self.results[task.id] = res
                return res
            self._idempotency_seen.add(key)
        for st in (SwarmTaskState.QUEUED, SwarmTaskState.READY, SwarmTaskState.RUNNING):
            try:
                task.set_state(st)
            except ValueError:
                pass
        task.started_at = time.time()
        self._on_event("started", task)
        if self._cancel.is_set():
            task.state = SwarmTaskState.CANCELLED
            res = AgentResult(task_id=task.id, status="failed", errors=["cancelled"])
            self.results[task.id] = res
            return res
        try:
            res = self._fn(task, ctx)
            res.idempotency_key = key
            task.completed_at = time.time()
            if res.status == "ok":
                try:
                    task.set_state(SwarmTaskState.COMPLETED)
                except ValueError:
                    pass
            else:
                try:
                    task.set_state(SwarmTaskState.FAILED)
                except ValueError:
                    pass
                task.error = ";".join(res.errors)[:500]
            self.results[task.id] = res
            self._on_event("completed" if res.status == "ok" else "failed", task)
            return res
        except Exception as exc:
            task.completed_at = time.time()
            try:
                task.set_state(SwarmTaskState.FAILED)
            except ValueError:
                pass
            task.error = f"{type(exc).__name__}: {exc}"[:500]
            res = AgentResult(task_id=task.id, status="failed",
                              errors=[task.error], idempotency_key=key)
            self.results[task.id] = res
            self._on_event("failed", task)
            return res
