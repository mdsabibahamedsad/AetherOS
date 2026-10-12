from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HealthStatus:
    subsystem: str
    status: str = "unknown"
    message: str = ""
    last_seen: float = 0.0
    uptime: float = 0.0
    metrics: dict = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


class HealthChecker:
    def __init__(self, interval: float = 10.0):
        self._interval = interval
        self._checks: dict[str, Callable] = {}
        self._statuses: dict[str, HealthStatus] = {}
        self._task: asyncio.Task | None = None
        self._start_times: dict[str, float] = {}
        self._running = False

    def register_check(self, subsystem: str, check_fn: Callable):
        self._checks[subsystem] = check_fn
        self._start_times[subsystem] = time.time()

    def record_health(self, subsystem: str, status: str, message: str = "", metrics: dict | None = None):
        now = time.time()
        uptime = now - self._start_times.get(subsystem, now)
        self._statuses[subsystem] = HealthStatus(
            subsystem=subsystem, status=status, message=message,
            last_seen=now, uptime=uptime, metrics=metrics or {},
        )

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while self._running:
            for sub, check_fn in self._checks.items():
                try:
                    result = check_fn()
                    if asyncio.iscoroutine(result):
                        result = await result
                    if isinstance(result, dict):
                        self.record_health(sub, result.get("status", "healthy"), result.get("message", ""), result.get("metrics"))
                    elif result:
                        self.record_health(sub, "healthy")
                    else:
                        self.record_health(sub, "unhealthy", "check returned false")
                except Exception as e:
                    self.record_health(sub, "unhealthy", str(e))
            await asyncio.sleep(self._interval)

    def get_status(self, subsystem: str) -> HealthStatus | None:
        return self._statuses.get(subsystem)

    def all_statuses(self) -> dict[str, HealthStatus]:
        return dict(self._statuses)

    def unhealthy(self) -> dict[str, HealthStatus]:
        return {k: v for k, v in self._statuses.items() if not v.is_healthy}
