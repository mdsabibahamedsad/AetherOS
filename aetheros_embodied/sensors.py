"""Sensors (§11-13, §94): quality-tagged readings, calibration,
uncertainty-weighted fusion, failure detection. Unavailable sensors
return UNAVAILABLE — never fabricated values."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SensorReading:
    value: Any = None
    unit: str = ""
    timestamp: float = field(default_factory=time.time)
    accuracy: float = 0.0  # +/- in unit
    resolution: float = 0.0
    noise: float = 0.0
    confidence: float = 0.0
    source: str = ""
    mode: str = "OBSERVED"
    quality: str = "ok"  # ok|stale|missing|corrupt|outlier|drifting|inconsistent


@dataclass
class CalibrationProfile:
    sensor_id: str
    version: str = "v1"
    calibrated_at: float = field(default_factory=time.time)
    reference_standard: str = ""
    error: float = 0.0
    valid_until: float = 0.0  # 0 = no expiry


class SensorAdapter:
    kind = "base"

    def __init__(self, sensor_id: str) -> None:
        self.sensor_id = sensor_id
        self.available = False

    def read(self) -> SensorReading:
        if not self.available:
            return SensorReading(source=self.sensor_id, mode="UNAVAILABLE",
                                 quality="missing", confidence=0.0)
        raise NotImplementedError

    def health(self) -> Dict[str, Any]:
        return {"sensor": self.sensor_id, "available": self.available}


class ReplaySensorAdapter(SensorAdapter):
    """Replays recorded readings. Mode is REPLAY, always labeled."""
    kind = "replay"

    def __init__(self, sensor_id: str,
                 recording: List[Dict[str, Any]]) -> None:
        super().__init__(sensor_id)
        self.available = True
        self.recording = recording
        self.idx = 0

    def read(self) -> SensorReading:
        if self.idx >= len(self.recording):
            return SensorReading(source=self.sensor_id, mode="REPLAY",
                                 quality="missing", confidence=0.0)
        rec = self.recording[self.idx]
        self.idx += 1
        return SensorReading(value=rec.get("value"), unit=rec.get("unit", ""),
                             accuracy=rec.get("accuracy", 0.0),
                             confidence=rec.get("confidence", 0.8),
                             source=self.sensor_id, mode="REPLAY")


class LambdaSensorAdapter(SensorAdapter):
    """Wraps a callable source (tests, file readers, drivers)."""
    kind = "lambda"

    def __init__(self, sensor_id: str, fn: Callable[[], Dict[str, Any]],
                 unit: str = "") -> None:
        super().__init__(sensor_id)
        self.available = True
        self.fn = fn
        self.unit = unit

    def read(self) -> SensorReading:
        try:
            d = self.fn()
        except Exception:
            return SensorReading(source=self.sensor_id, mode="OBSERVED",
                                 quality="corrupt", confidence=0.0)
        return SensorReading(value=d.get("value"), unit=self.unit,
                             accuracy=d.get("accuracy", 0.0),
                             confidence=d.get("confidence", 0.9),
                             source=self.sensor_id, mode="OBSERVED")


class SensorFusionEngine:
    """Inverse-variance weighted fusion. Disagreement beyond tolerance
    yields STATE_UNCERTAIN, never a silent pick."""

    def __init__(self, disagreement_tol: float = 0.5) -> None:
        self.adapters: Dict[str, SensorAdapter] = {}
        self.calibrations: Dict[str, CalibrationProfile] = {}
        self.disagreement_tol = disagreement_tol

    def attach(self, adapter: SensorAdapter) -> None:
        self.adapters[adapter.sensor_id] = adapter

    def calibrate(self, profile: CalibrationProfile) -> None:
        self.calibrations[profile.sensor_id] = profile

    def calibration_ok(self, sensor_id: str,
                       required: bool) -> bool:
        prof = self.calibrations.get(sensor_id)
        if not required:
            return True
        if prof is None:
            return False
        return not (prof.valid_until and time.time() > prof.valid_until)

    def read_all(self, key: str = "value") -> List[SensorReading]:
        return [a.read() for a in self.adapters.values()]

    def fuse_numeric(self, readings: List[SensorReading]) -> Dict[str, Any]:
        good = [r for r in readings
                if r.quality == "ok" and isinstance(r.value, (int, float))]
        if not good:
            return {"status": "UNAVAILABLE",
                    "reason": "no usable readings — not fabricated"}
        vals = [float(r.value) for r in good]
        if max(vals) - min(vals) > self.disagreement_tol:
            return {"status": "STATE_UNCERTAIN",
                    "values": vals,
                    "reason": "sensors disagree beyond tolerance"}
        weights = []
        for r in good:
            var = max(r.accuracy, 1e-9) ** 2 + max(r.noise, 0.0) ** 2
            weights.append(r.confidence / var)
        total = sum(weights) or 1.0
        fused = sum(v * w for v, w in zip(vals, weights)) / total
        unc = (sum(1.0 / max(w, 1e-12) for w in weights) ** 0.5) / len(weights)
        return {"status": "FUSED", "value": fused,
                "uncertainty": unc, "n": len(good),
                "modes": sorted({r.mode for r in good})}

    @staticmethod
    def check_quality(r: SensorReading, max_age_s: float = 2.0,
                      expected_range: Optional[tuple] = None) -> SensorReading:
        if time.time() - r.timestamp > max_age_s:
            r.quality = "stale"
        elif expected_range and isinstance(r.value, (int, float)):
            lo, hi = expected_range
            if not (lo <= r.value <= hi):
                r.quality = "outlier"
        return r
