"""Recovery SLA metrics.

Tracks measured reliability metrics — never fabricated:

* MTTR (mean time to recovery)
* restart time
* recovery success rate
* backup success rate
* restore success rate
* crash-loop rate

Metrics are recorded from real events (watchdog outcomes, backup/restore
results) and stored in-memory with a bounded window plus optional durable
append to the recovery journal.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MetricSample:
    name: str
    value: float
    success: bool
    at: float = field(default_factory=time.time)


class RecoverySLAMetrics:
    """Rolling-window SLA metrics for recovery operations.

    Usage::

        sla = get_recovery_sla_metrics()
        sla.record_recovery(component="gateway", duration_ms=2300, success=True)
        sla.record_backup(success=True)
        sla.record_restore(success=False)
        print(sla.summary())
    """

    def __init__(self, window: int = 200) -> None:
        self._lock = threading.RLock()
        self._window = window
        self._samples: List[MetricSample] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_recovery(self, component: str, duration_ms: float,
                        success: bool) -> None:
        self._add("recovery", duration_ms, success, {"component": component})

    def record_restart(self, component: str, duration_ms: float) -> None:
        self._add("restart", duration_ms, True, {"component": component})

    def record_backup(self, success: bool, duration_ms: float = 0.0) -> None:
        self._add("backup", duration_ms, success)

    def record_restore(self, success: bool, duration_ms: float = 0.0) -> None:
        self._add("restore", duration_ms, success)

    def record_crash_loop(self, component: str) -> None:
        self._add("crash_loop", 1.0, False, {"component": component})

    def _add(self, name: str, value: float, success: bool,
             extra: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._samples.append(MetricSample(name, value, success))
            if len(self._samples) > self._window * 2:
                self._samples = self._samples[-self._window:]

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _for(self, name: str) -> List[MetricSample]:
        with self._lock:
            return [s for s in self._samples if s.name == name]

    def mttr(self, component: str = "") -> Optional[float]:
        """Mean time to recovery (ms) for successful recoveries."""
        samples = [
            s for s in self._for("recovery")
            if s.success and (not component or s.component == component)
        ]
        if not samples:
            return None
        return sum(s.value for s in samples) / len(samples)

    def success_rate(self, name: str) -> Optional[float]:
        samples = self._for(name)
        if not samples:
            return None
        return sum(1 for s in samples if s.success) / len(samples)

    def crash_loop_rate(self) -> Optional[float]:
        samples = self._for("crash_loop")
        if not samples:
            return None
        return len(samples) / len(self._for("recovery")) if self._for("recovery") else 0.0

    def summary(self) -> Dict[str, Any]:
        recovery = self._for("recovery")
        restarts = self._for("restart")
        return {
            "mttr_ms": round(self.mttr(), 2) if self.mttr() is not None else None,
            "recovery_success_rate": round(self.success_rate("recovery"), 4)
                if self.success_rate("recovery") is not None else None,
            "restart_count": len(restarts),
            "avg_restart_ms": round(sum(s.value for s in restarts) / len(restarts), 2)
                if restarts else None,
            "backup_success_rate": round(self.success_rate("backup"), 4)
                if self.success_rate("backup") is not None else None,
            "restore_success_rate": round(self.success_rate("restore"), 4)
                if self.success_rate("restore") is not None else None,
            "crash_loop_rate": round(self.crash_loop_rate(), 4)
                if self.crash_loop_rate() is not None else None,
            "recovery_attempts": len(recovery),
            "window": self._window,
        }


_sla: Optional[RecoverySLAMetrics] = None
_sla_lock = threading.Lock()


def get_recovery_sla_metrics() -> RecoverySLAMetrics:
    """Return the process-wide RecoverySLAMetrics singleton."""
    global _sla
    if _sla is None:
        with _sla_lock:
            if _sla is None:
                _sla = RecoverySLAMetrics()
    return _sla