from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class MicCalibrationResult:
    noise_floor: float = 0.0
    peak_level: float = 0.0
    recommended_gain: float = 1.0
    ambient_noise: str = "quiet"
    sample_count: int = 0
    duration: float = 0.0


class MicCalibration:
    def __init__(self):
        self._calibrated = False
        self._result: MicCalibrationResult | None = None

    async def calibrate(self, audio_samples: list[bytes]) -> MicCalibrationResult:
        max_peak = 0.0
        total_rms = 0.0
        count = 0
        start = time.time()

        for chunk in audio_samples:
            import struct
            if len(chunk) >= 2:
                samples = struct.unpack(f"<{len(chunk)//2}h", chunk[:len(chunk) - len(chunk) % 2])
                rms = sum(s * s for s in samples) / len(samples) ** 0.5
                peak = max(abs(s) for s in samples)
                total_rms += rms
                max_peak = max(max_peak, peak)
                count += len(samples)

        avg_rms = total_rms / max(count, 1)
        normalized_rms = avg_rms / 32768.0

        if normalized_rms < 0.01:
            ambient = "quiet"
            gain = 2.0
        elif normalized_rms < 0.05:
            ambient = "moderate"
            gain = 1.5
        elif normalized_rms < 0.15:
            ambient = "noisy"
            gain = 1.0
        else:
            ambient = "loud"
            gain = 0.5

        self._result = MicCalibrationResult(
            noise_floor=normalized_rms,
            peak_level=max_peak / 32768.0,
            recommended_gain=gain,
            ambient_noise=ambient,
            sample_count=count,
            duration=time.time() - start,
        )
        self._calibrated = True
        return self._result

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    @property
    def result(self) -> MicCalibrationResult | None:
        return self._result

    def reset(self):
        self._calibrated = False
        self._result = None
