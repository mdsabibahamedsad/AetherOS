"""Durable scheduler (sections 4-5, 23-28, 51-52, 65-71).

Virtual-clock driven: `tick(now)` advances schedules, applies missed-run
policies, enforces concurrency keys/resource locks, idempotency, retry
with backoff+jitter, recursion depth + cycle detection, rate limits.
State persists in AutonomyStore — restart reconciles via `reconcile()`.
No in-memory-only timers; no excessive polling (tick is caller-driven).
"""

from __future__ import annotations

import hashlib
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import (
    AutomationDefinition, MissedPolicy, RunRecord, RunState,
)
from aetheros_autonomy.schedule import CanonicalSchedule, next_run
from aetheros_autonomy.store import AutonomyStore
from aetheros_autonomy.triggers import eval_condition

RunFn = Callable[[AutomationDefinition, RunRecord], RunRecord]


class VirtualClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start or time.time()

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now


class Scheduler:
    MAX_CAUSAL_DEPTH = 5

    def __init__(self, store: AutonomyStore, run_fn: Optional[RunFn] = None, *,
                 clock: Optional[VirtualClock] = None,
                 emergency_stop: Optional[Callable[[], bool]] = None,
                 safe_mode: Optional[Callable[[], bool]] = None) -> None:
        self._store = store
        self._run_fn = run_fn or (lambda a, r: r)
        self._clock = clock
        self._estop = emergency_stop or (lambda: False)
        self._safemode = safe_mode or (lambda: False)
        self._lock = threading.Lock()
        self._locks: Dict[str, str] = {}  # concurrency_key -> run_id
        self._counts: Dict[str, List[float]] = {}  # rate-limit windows
        self.metrics = {"ticks": 0, "due": 0, "started": 0, "skipped": 0,
                        "retries": 0, "duplicates": 0, "recursion_blocked": 0}

    def now(self) -> float:
        return self._clock.now if self._clock else time.time()

    # -- scheduling ----------------------------------------------------
    def schedule_next(self, auto: AutomationDefinition, after_ts: float) -> float:
        sched = CanonicalSchedule.from_dict(auto.trigger.get("schedule", {}))
        try:
            nxt = next_run(sched, after_ts)
        except ValueError:
            nxt = 0.0
        auto.next_run = nxt
        return nxt

    def reconcile(self) -> Dict[str, int]:
        """Post-restart: recompute next_run, apply missed-run policies."""
        now = self.now()
        out = {"resumed": 0, "skipped": 0, "queued": 0}
        for auto in self._store.list_autos():
            if not auto.enabled:
                continue
            if auto.trigger.get("kind") != "schedule":
                continue
            if auto.next_run and auto.next_run < now:
                pol = MissedPolicy(str(auto.missed_policy or "skip"))
                if pol == MissedPolicy.SKIP:
                    self.schedule_next(auto, now)
                    out["skipped"] += 1
                elif pol in (MissedPolicy.RUN_ON_START, MissedPolicy.RUN_LATEST_ONLY):
                    self._fire(auto, "missed_run", causal=[])
                    self.schedule_next(auto, now)
                    out["queued"] += 1
                elif pol == MissedPolicy.ASK_USER:
                    auto.metadata["missed_pending"] = True
                    self.schedule_next(auto, now)
                    out["skipped"] += 1
                else:  # CATCH_UP: single compensating run, never a dangerous backlog
                    self._fire(auto, "catch_up", causal=[])
                    self.schedule_next(auto, now)
                    out["queued"] += 1
                self._store.save_auto(auto)
            elif not auto.next_run:
                self.schedule_next(auto, now)
                self._store.save_auto(auto)
                out["resumed"] += 1
        return out

    def tick(self) -> List[RunRecord]:
        """Advance once. Returns runs started this tick."""
        if self._estop():
            return []
        now = self.now()
        started: List[RunRecord] = []
        with self._lock:
            self.metrics["ticks"] += 1
            autos = [a for a in self._store.list_autos()
                     if a.enabled and a.trigger.get("kind") == "schedule"
                     and a.next_run and a.next_run <= now]
        # Coalesce persistence: one write for the whole tick burst.
        with self._store.batched():
            for auto in autos:
                if self._estop():
                    break
                with self._lock:
                    self.metrics["due"] += 1
                    run = self._fire(auto, "schedule_due", causal=[])
                if run is not None:
                    started.append(run)
                self.schedule_next(auto, now)
                auto.last_run = now
                self._store.save_auto(auto)
        return started

    # -- firing ----------------------------------------------------------
    def fire_event(self, auto: AutomationDefinition, event_kind: str,
                   causal: Optional[List[str]] = None) -> Optional[RunRecord]:
        with self._lock:
            return self._fire(auto, event_kind, causal or [])

    def _fire(self, auto: AutomationDefinition, kind: str,
              causal: List[str]) -> Optional[RunRecord]:
        # Recursion defense: causal chain depth + cycle detection + cooldown.
        if auto.id in causal or len(causal) >= self.MAX_CAUSAL_DEPTH:
            self.metrics["recursion_blocked"] += 1
            return None
        # Rate limiting: max 10 fires/min per automation.
        now = self.now()
        window = [t for t in self._counts.get(auto.id, []) if now - t < 60.0]
        if len(window) >= 10:
            self.metrics["skipped"] += 1
            return None
        window.append(now)
        self._counts[auto.id] = window
        # Concurrency key handling.
        key = auto.concurrency_key
        if key and key in self._locks:
            pol = auto.concurrency_policy
            if pol == "skip":
                self.metrics["skipped"] += 1
                return None
            if pol == "cancel":
                return None
            # queue/merge: record follows after lock release (single pending)
        # Idempotency: same automation+window never double-fires.
        idem_key = f"{auto.id}:{kind}:{int(now // 60)}"
        if self._store.find_by_idempotency(idem_key) is not None:
            self.metrics["duplicates"] += 1
            return None
        run = RunRecord(automation_id=auto.id, trigger_kind=kind,
                        idempotency_key=idem_key,
                        causal_chain=[*causal, auto.id])
        self._store.save_run(run)
        if key:
            self._locks[key] = run.run_id
        self.metrics["started"] += 1
        try:
            run.state = RunState.RUNNING
            run.started_at = now
            run = self._run_fn(auto, run)
        except Exception as exc:
            run.state = RunState.FAILED
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            run.failure_kind = "tool_failure"
        finally:
            if key and self._locks.get(key) == run.run_id:
                self._locks.pop(key, None)
            run.completed_at = self.now()
            self._store.save_run(run)
        return run

    # -- retry -------------------------------------------------------------
    def backoff_for(self, attempt: int, base_s: float, max_s: float,
                    jitter: bool) -> float:
        delay = min(max_s, base_s * (2.0 ** max(0, attempt - 1)))
        if jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay

    def should_retry(self, run: RunRecord, auto: AutomationDefinition) -> bool:
        if run.failure_kind in auto.retry_policy.non_retryable:
            return False
        if run.failure_kind not in auto.retry_policy.retryable:
            return False
        destructive = any("destructive" in str(s) for s in auto.workflow)
        if destructive:
            return False  # never retry destructive actions blindly
        return run.attempt < auto.retry_policy.max_attempts
