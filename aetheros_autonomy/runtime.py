"""Background agent runtime (sections 15, 20-22, 39, 64-68).

Thread-pool workers (never main/renderer): launch/supervise/pause/resume/
terminate/checkpoint/recover with per-run budgets. Offline classification:
LOCAL_EXECUTABLE vs NETWORK_REQUIRED (-> WAITING_NETWORK). ProactiveAgent
checks (blocked tasks, stale projects, pending approvals) emit suggestions
only — PROACTIVE never UNAUTHORIZED.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import RunRecord, RunState

WorkFn = Callable[[RunRecord], RunRecord]


class BackgroundAgentRuntime:
    def __init__(self, work_fn: Optional[WorkFn] = None, *,
                 max_workers: int = 4, online_fn: Optional[Callable[[], bool]] = None,
                 checkpoint_fn: Optional[Callable[[RunRecord], None]] = None) -> None:
        self._work = work_fn or (lambda r: r)
        self._pool = ThreadPoolExecutor(max_workers=max_workers,
                                        thread_name_prefix="auto-bg")
        self._online = online_fn or (lambda: True)
        self._checkpoint = checkpoint_fn or (lambda r: None)
        self._lock = threading.Lock()
        self._futures: Dict[str, Any] = {}
        self._paused: set = set()
        self.metrics = {"launched": 0, "completed": 0, "failed": 0,
                        "waiting_network": 0, "terminated": 0}

    def classify(self, run: RunRecord, needs_network: bool) -> str:
        if needs_network and not self._online():
            return "NETWORK_REQUIRED"
        return "LOCAL_EXECUTABLE"

    def launch(self, run: RunRecord, *, needs_network: bool = False) -> RunRecord:
        if self.classify(run, needs_network) == "NETWORK_REQUIRED":
            run.state = RunState.WAITING_NETWORK
            with self._lock:
                self.metrics["waiting_network"] += 1
            return run
        run.state = RunState.STARTING
        run.started_at = time.time()
        fut = self._pool.submit(self._guarded, run)
        with self._lock:
            self._futures[run.run_id] = fut
            self.metrics["launched"] += 1
        return run

    def _guarded(self, run: RunRecord) -> RunRecord:
        try:
            while run.run_id in self._paused:
                time.sleep(0.2)
            run.state = RunState.RUNNING
            run = self._work(run)
            if run.state in (RunState.RUNNING, RunState.STARTING):
                run.state = RunState.COMPLETED
            with self._lock:
                self.metrics["completed"] += 1
        except Exception as exc:
            run.state = RunState.FAILED
            run.error = f"{type(exc).__name__}: {exc}"[:400]
            with self._lock:
                self.metrics["failed"] += 1
        finally:
            run.completed_at = time.time()
            try:
                self._checkpoint(run)
            except Exception:
                pass
            with self._lock:
                self._futures.pop(run.run_id, None)
        return run

    def pause(self, run_id: str) -> bool:
        with self._lock:
            if run_id in self._futures:
                self._paused.add(run_id)
                return True
            return False

    def resume(self, run_id: str) -> bool:
        with self._lock:
            if run_id in self._paused:
                self._paused.discard(run_id)
                return True
            return False

    def terminate(self, run_id: str) -> bool:
        """Cooperative terminate: pause + mark cancelled; worker exits wait."""
        with self._lock:
            self._paused.discard(run_id)
            fut = self._futures.get(run_id)
            if fut is None:
                return False
            self.metrics["terminated"] += 1
            return fut.cancel()

    def running(self) -> List[str]:
        with self._lock:
            return list(self._futures)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait, cancel_futures=True)


class ProactiveAgent:
    """Observe + suggest only. Findings are notifications, never actions."""

    def __init__(self, checks: Optional[List[Callable[[], List[Dict[str, Any]]]]] = None) -> None:
        self._checks = checks or []

    def add_check(self, fn: Callable[[], List[Dict[str, Any]]]) -> None:
        self._checks.append(fn)

    def scan(self) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for fn in self._checks:
            try:
                for f in fn():
                    f.setdefault("kind", "suggestion")
                    findings.append(f)
            except Exception:
                continue
        return findings
