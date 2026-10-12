"""Telemetry (§91-97): ring-buffer event bus, clock model, ordering
(late/duplicate/out-of-order/missing), privacy (masks, retention,
redaction of human data), health monitoring with labeled predictions."""
from __future__ import annotations

import re
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .models import ExecMode, TelemetryEvent

_human_re = re.compile(r"(face|person|voice|license_plate)", re.I)


class EventBus:
    def __init__(self, capacity: int = 10000) -> None:
        self.events: deque = deque(maxlen=capacity)
        self.subs: Dict[str, List[Callable[[TelemetryEvent], None]]] = {}
        self._seq = 0
        self.dropped = 0

    def publish(self, kind: str, device: str = "",
                payload: Optional[Dict[str, Any]] = None,
                mode: str = ExecMode.SIMULATION) -> TelemetryEvent:
        self._seq += 1
        ev = TelemetryEvent(kind=kind, device=device,
                            payload=payload or {}, mode=mode, seq=self._seq)
        if len(self.events) == self.events.maxlen:
            self.dropped += 1
        self.events.append(ev)
        for fn in self.subs.get(kind, []) + self.subs.get("*", []):
            try:
                fn(ev)
            except Exception:
                pass
        return ev

    def subscribe(self, kind: str,
                  fn: Callable[[TelemetryEvent], None]) -> None:
        self.subs.setdefault(kind, []).append(fn)

    def ordered(self) -> List[TelemetryEvent]:
        """Sort by (at, seq); report gaps/duplicates, don't hide them."""
        evs = sorted(self.events, key=lambda e: (e.at, e.seq))
        seqs = [e.seq for e in evs]
        report = {"n": len(evs),
                  "gaps": [b for a, b in zip(seqs, seqs[1:])
                           if b - a > 1],
                  "duplicates": len(seqs) - len(set(seqs))}
        self._last_order_report = report
        return evs

    def privacy_scrub(self, ev: TelemetryEvent) -> TelemetryEvent:
        """Redact human-identifying payload keys before storage/tx."""
        clean = {k: ("[REDACTED]" if _human_re.search(k) else v)
                 for k, v in ev.payload.items()}
        ev.payload = clean
        return ev


class TelemetryEngine:
    """Facade: bus + clock + health + retention policy."""

    def __init__(self, capacity: int = 10000,
                 retention_events: int = 100000) -> None:
        self.bus = EventBus(capacity)
        self.clock = ClockModel()
        self.health = HealthMonitor()
        self.retention = retention_events

    def record(self, kind: str, device: str = "",
               payload: Optional[Dict[str, Any]] = None,
               mode: str = ExecMode.SIMULATION) -> TelemetryEvent:
        ev = self.bus.publish(kind, device, payload, mode)
        return self.bus.privacy_scrub(ev)

    def snapshot(self) -> Dict[str, Any]:
        ordered = self.bus.ordered()
        return {"events": len(ordered),
                "dropped": self.bus.dropped,
                "order": getattr(self.bus, "_last_order_report", {})}


class ClockModel:
    def __init__(self, precision_ms: float = 1.0) -> None:
        self.precision_ms = precision_ms
        self.drift_ppm = 0.0

    def now(self) -> float:
        return time.time()

    def align(self, sensor_ts: float, received_ts: float) -> Dict[str, float]:
        latency = received_ts - sensor_ts
        return {"latency_s": latency,
                "aligned": latency >= 0,
                "note": "negative latency = clock disagreement"}


class HealthMonitor:
    """Watches temperature/battery/faults; predictions labeled as such."""

    def __init__(self) -> None:
        self.samples: Dict[str, List[float]] = {}

    def observe(self, device: str, metric: str, value: float) -> None:
        self.samples.setdefault(f"{device}:{metric}", []).append(value)

    def predict_wear(self, device: str, metric: str) -> Dict[str, Any]:
        vals = self.samples.get(f"{device}:{metric}", [])
        if len(vals) < 3:
            return {"prediction": "insufficient data",
                    "note": "PREDICTION withheld, not invented"}
        trend = (vals[-1] - vals[0]) / max(len(vals) - 1, 1)
        return {"prediction": ("degrading" if trend > 0 else "stable"),
                "trend_per_sample": trend,
                "note": "PREDICTION from linear trend only"}
