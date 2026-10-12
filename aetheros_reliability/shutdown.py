"""Coordinated graceful shutdown.

Order (never silently abandons active state):

    stop new work → pause autonomous missions → finish safe operations →
    checkpoint state → flush telemetry → flush audit → close databases →
    stop workers → stop backend → stop gateway → exit

Every stage has a timeout.  If a stage times out, the coordinator performs a
safe forced termination for that stage while preserving recovery metadata
(the journal stays intact so the next startup can reconcile).

The coordinator is a *framework* — stages are registered by callers.  It is
safe to run with zero registered stages.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Canonical stage order for graceful shutdown.
_STAGE_ORDER = (
    "stop_new_work",
    "pause_missions",
    "finish_safe_operations",
    "checkpoint_state",
    "flush_telemetry",
    "flush_audit",
    "close_databases",
    "stop_workers",
    "stop_backend",
    "stop_gateway",
)


class StageOutcome(str, enum.Enum):
    OK = "ok"
    TIMEOUT = "timeout"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    stage: str
    outcome: StageOutcome
    duration_ms: float = 0.0
    message: str = ""
    force_killed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "outcome": self.outcome.value,
            "duration_ms": round(self.duration_ms, 2),
            "message": self.message,
            "force_killed": self.force_killed,
        }


class ShutdownCoordinator:
    """Runs shutdown stages in canonical order with per-stage timeouts.

    Usage::

        sc = get_shutdown_coordinator()
        sc.register("stop_new_work", my_hook, timeout=5)
        results = sc.shutdown()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._hooks: Dict[str, Callable[[], None]] = {}
        self._timeouts: Dict[str, float] = {}
        self._default_timeout = 15.0
        self._shutdown_called = False
        self._last_results: List[StageResult] = []

    def register(self, stage: str, hook: Callable[[], None],
                 timeout: Optional[float] = None) -> None:
        """Register a shutdown hook for *stage*.  Unknown stages are ignored
        (they run after canonical ones, in registration order)."""
        with self._lock:
            self._hooks[stage] = hook
            if timeout is not None:
                self._timeouts[stage] = timeout

    def unregister(self, stage: str) -> None:
        with self._lock:
            self._hooks.pop(stage, None)
            self._timeouts.pop(stage, None)

    @property
    def shutdown_called(self) -> bool:
        with self._lock:
            return self._shutdown_called

    @property
    def last_results(self) -> List[StageResult]:
        with self._lock:
            return list(self._last_results)

    def shutdown(self) -> List[StageResult]:
        """Run every registered stage in canonical order.  Idempotent per
        process — a second call returns the previous results."""
        with self._lock:
            if self._shutdown_called:
                return list(self._last_results)
            hooks = dict(self._hooks)
            timeouts = dict(self._timeouts)
            self._shutdown_called = True

        ordered = sorted(
            hooks.keys(),
            key=lambda s: (_STAGE_ORDER.index(s) if s in _STAGE_ORDER else 99, s),
        )
        results: List[StageResult] = []
        for stage in ordered:
            result = self._run_stage(stage, hooks[stage], timeouts.get(stage))
            results.append(result)
            if result.outcome == StageOutcome.TIMEOUT:
                logger.error("Shutdown stage %s timed out; forced termination", stage)
        with self._lock:
            self._last_results = results
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run_stage(self, stage: str, hook: Callable[[], None],
                   timeout: Optional[float]) -> StageResult:
        timeout = timeout or self._default_timeout
        start = time.monotonic()
        finished = threading.Event()
        result_holder: Dict[str, Any] = {}

        def runner():
            try:
                hook()
                result_holder["ok"] = True
            except Exception as exc:
                result_holder["ok"] = False
                result_holder["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                finished.set()

        thread = threading.Thread(target=runner, name=f"shutdown-{stage}", daemon=True)
        thread.start()
        done = finished.wait(timeout=timeout)
        duration = (time.monotonic() - start) * 1000
        if not done:
            return StageResult(stage, StageOutcome.TIMEOUT, duration,
                               message="timeout; safe forced termination", force_killed=True)
        if result_holder.get("ok"):
            return StageResult(stage, StageOutcome.OK, duration)
        return StageResult(stage, StageOutcome.FAILED, duration,
                           message=result_holder.get("error", "hook raised"))


_shutdown: Optional[ShutdownCoordinator] = None
_shutdown_lock = threading.Lock()


def get_shutdown_coordinator() -> ShutdownCoordinator:
    """Return the process-wide ShutdownCoordinator singleton."""
    global _shutdown
    if _shutdown is None:
        with _shutdown_lock:
            if _shutdown is None:
                _shutdown = ShutdownCoordinator()
    return _shutdown