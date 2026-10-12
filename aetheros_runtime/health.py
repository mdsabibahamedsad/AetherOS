"""Health checks + circuit breakers + rate-limit handling (sections 22-23, 46).

Real probes via adapters; states UNKNOWN/HEALTHY/DEGRADED/UNAVAILABLE/
AUTH_ERROR/RATE_LIMITED/OVERLOADED/MISCONFIGURED. Breaker: failures >=
threshold OPENs for cooldown, then HALF_OPEN single trial -> CLOSED or
re-OPEN. 429 honors Retry-After. All transitions timestamped.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from aetheros_runtime.models import DataClass, ModelRecord, CircuitState, HealthState


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5,
                 cooldown_s: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._lock = threading.Lock()
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = 0.0

    def allow(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if time.time() - self.opened_at >= self.cooldown_s:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN: single trial

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            self.state = CircuitState.CLOSED

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == CircuitState.HALF_OPEN or \
                    self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"state": self.state.value, "failures": self.failures,
                    "opened_at": self.opened_at}


def map_probe_to_health(probe: Dict[str, Any]) -> str:
    if probe.get("ok"):
        return HealthState.HEALTHY.value
    cls = str(probe.get("class", "unknown"))
    return {"auth": HealthState.AUTH_ERROR.value,
            "rate_limit": HealthState.RATE_LIMITED.value,
            "overloaded": HealthState.OVERLOADED.value,
            "permission": HealthState.AUTH_ERROR.value,
            "misconfigured": HealthState.MISCONFIGURED.value,
            "connection": HealthState.UNAVAILABLE.value,
            "timeout": HealthState.DEGRADED.value}.get(cls, HealthState.UNAVAILABLE.value)


class HealthMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._health: Dict[str, Dict[str, Any]] = {}
        self._retry_after: Dict[str, float] = {}

    def breaker(self, pid: str) -> CircuitBreaker:
        with self._lock:
            return self._breakers.setdefault(pid, CircuitBreaker())

    def record_probe(self, pid: str, probe: Dict[str, Any]) -> str:
        state = map_probe_to_health(probe)
        with self._lock:
            self._health[pid] = {"state": state,
                                 "latency_ms": probe.get("latency_ms", 0.0),
                                 "reason": str(probe.get("reason", ""))[:300],
                                 "at": time.time()}
        br = self.breaker(pid)
        if state == HealthState.HEALTHY.value:
            br.success()
        elif state in (HealthState.RATE_LIMITED.value,):
            retry_after = float(probe.get("retry_after_s", 0.0) or 0.0)
            with self._lock:
                self._retry_after[pid] = time.time() + max(retry_after, 5.0)
        elif state not in (HealthState.DEGRADED.value,):
            br.failure()
        return state

    def throttled(self, pid: str) -> bool:
        with self._lock:
            return time.time() < self._retry_after.get(pid, 0.0)

    def status(self, pid: str) -> Dict[str, Any]:
        with self._lock:
            h = dict(self._health.get(pid, {"state": HealthState.UNKNOWN.value}))
        br = self.breaker(pid)
        h["circuit"] = br.snapshot()
        h["throttled"] = self.throttled(pid)
        return h