"""Jarvis Mode — performance guard.

Enforces background resource limits and battery-aware behavior so the Jarvis
runtime stays responsive and low-footprint: wake detection must be
low-latency, speech streaming must not block the loop, and background work
throttles on battery and under load.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceGuard:
    """Battery-aware, resource-bounded execution policy.

    Exposes capability flags that the rest of the runtime consults before
    starting expensive background work (proactive scanning, briefing
    generation, mission coordination).
    """

    DEFAULT_LIMITS = {
        "max_cpu_percent": 60.0,
        "max_memory_percent": 80.0,
        "max_background_threads": 4,
        "proactive_min_interval_seconds": 300.0,
        "wake_detect_max_frames": 256,
    }

    def __init__(self, limits: Optional[Dict[str, float]] = None) -> None:
        self._limits: Dict[str, float] = {**self.DEFAULT_LIMITS, **(limits or {})}
        self._lock = threading.RLock()
        self._battery_threshold: float = 20.0
        self._last_proactive_run: Dict[str, float] = {}
        self._started_at = time.time()

    # ------------------------------------------------------------------
    # Battery
    # ------------------------------------------------------------------

    def battery_percent(self) -> Optional[float]:
        """Return battery level (0-100) or None when on mains/unknown."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return None
            return float(battery.percent)
        except Exception:
            return None

    def is_on_battery(self) -> bool:
        try:
            import psutil
            battery = psutil.sensors_battery()
            return bool(battery is not None and not battery.power_plugged)
        except Exception:
            return False

    def battery_saver_active(self) -> bool:
        percent = self.battery_percent()
        return percent is not None and percent <= self._battery_threshold

    # ------------------------------------------------------------------
    # System load
    # ------------------------------------------------------------------

    def system_load_high(self) -> bool:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            return cpu >= self._limits["max_cpu_percent"] or mem >= self._limits["max_memory_percent"]
        except Exception:
            return False

    def can_run_background(self) -> bool:
        """Gate for heavy background work."""
        if self.battery_saver_active():
            return False
        if self.system_load_high():
            return False
        return True

    # ------------------------------------------------------------------
    # Throttling
    # ------------------------------------------------------------------

    def should_run_proactive(self, kind: str = "default") -> bool:
        """Cooldown gate for repeated proactive work of the same kind."""
        interval = self._limits.get("proactive_min_interval_seconds", self.DEFAULT_LIMITS["proactive_min_interval_seconds"])
        with self._lock:
            last = self._last_proactive_run.get(kind, 0.0)
            now = time.time()
            if now - last >= interval:
                self._last_proactive_run[kind] = now
                return True
            return False

    def throttle(self, kind: str, min_interval_seconds: float) -> bool:
        with self._lock:
            last = self._last_proactive_run.get(kind, 0.0)
            now = time.time()
            if now - last >= min_interval_seconds:
                self._last_proactive_run[kind] = now
                return True
            return False

    def set_limits(self, limits: Dict[str, float]) -> None:
        with self._lock:
            self._limits.update(limits or {})

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "on_battery": self.is_on_battery(),
            "battery_percent": self.battery_percent(),
            "battery_saver_active": self.battery_saver_active(),
            "system_load_high": self.system_load_high(),
            "can_run_background": self.can_run_background(),
            "uptime_seconds": round(time.time() - self._started_at, 1),
            "limits": dict(self._limits),
        }
