"""Embodied benchmarks (§191-197): perception, localization,
navigation, manipulation, planning, simulation, verification,
recovery, safety, long-horizon — in SIMULATION/REPLAY modes.
LIVE_HARDWARE categories report NOT TESTED without hardware."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List


class EmbodiedBenchmarkEngine:
    MODES = ["SIMULATION", "REPLAY", "HARDWARE_IN_LOOP", "LIVE_HARDWARE"]

    def __init__(self, mode: str = "SIMULATION") -> None:
        if mode not in self.MODES:
            raise ValueError(f"unknown mode {mode}")
        self.mode = mode
        self.results: List[Dict[str, Any]] = []

    def run(self, name: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        if self.mode in ("HARDWARE_IN_LOOP", "LIVE_HARDWARE"):
            rec = {"name": name, "mode": self.mode, "status": "NOT_TESTED",
                   "reason": "HARDWARE_UNAVAILABLE — no live rig"}
            self.results.append(rec)
            return rec
        t0 = time.perf_counter()
        try:
            out = fn()
            rec = {"name": name, "mode": self.mode, "status": "PASS"
                   if out.get("passed", True) else "FAIL",
                   "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                   "metrics": out}
        except Exception as exc:
            rec = {"name": name, "mode": self.mode, "status": "ERROR",
                   "reason": f"{type(exc).__name__}: {exc}"}
        self.results.append(rec)
        return rec

    def summary(self) -> Dict[str, Any]:
        by = {}
        for r in self.results:
            by[r["status"]] = by.get(r["status"], 0) + 1
        return {"mode": self.mode, "n": len(self.results), "by_status": by,
                "results": self.results}
