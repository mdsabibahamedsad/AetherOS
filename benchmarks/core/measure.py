"""Core measurement utilities for AetherOS performance benchmarks.

Provides high-precision timing, resource monitoring, statistical analysis,
and result serialization following Master 71 methodology.
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class EnvironmentInfo:
    """Complete environment fingerprint for benchmark reproducibility."""
    benchmark_version: str = "m71-v1"
    timestamp: float = field(default_factory=time.time)
    os: str = field(default_factory=lambda: f"{platform.system()} {platform.release()}")
    os_platform: str = field(default_factory=platform.platform)
    cpu: str = field(default_factory=platform.processor)
    cpu_count: int = field(default_factory=lambda: os.cpu_count() or 1)
    ram_gb: Optional[float] = None
    gpu: str = "unknown"
    python_version: str = field(default_factory=lambda: sys.version.split()[0] if sys.version else "unknown")
    node_version: Optional[str] = None
    electron_version: Optional[str] = None
    aetheros_version: Optional[str] = None
    build_mode: str = "unknown"
    power_mode: str = "unknown"
    thermal_state: str = "unknown"
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.ram_gb is None:
            self.ram_gb = self._get_ram_gb()
        if self.node_version is None:
            self.node_version = self._get_node_version()
        if self.gpu == "unknown":
            self.gpu = self._get_gpu()

    @staticmethod
    def _get_ram_gb() -> Optional[float]:
        try:
            if PSUTIL_AVAILABLE:
                return round(psutil.virtual_memory().total / (1024 ** 3), 1)
            if hasattr(os, "sysconf"):
                return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3, 1)
        except Exception:
            pass
        try:
            import ctypes
            class _MEM(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong)]
            m = _MEM()
            m.dwLength = ctypes.sizeof(_MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullTotalPhys / 1024 ** 3, 1)
        except Exception:
            return None

    @staticmethod
    def _get_node_version() -> Optional[str]:
        try:
            import subprocess
            out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            return out.stdout.strip() if out.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _get_gpu() -> str:
        try:
            import subprocess
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip().splitlines()[0]
        except Exception:
            pass
        return "none-detected"

    def fingerprint(self) -> str:
        """Generate SHA256 fingerprint for environment comparison."""
        import hashlib
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result."""
    benchmark_id: str
    name: str
    category: str
    status: str  # MEASURED, ESTIMATED, DERIVED, BLOCKED, UNVERIFIED, NOT_APPLICABLE
    iterations: int
    warmup_iterations: int
    metrics: Dict[str, float]
    units: Dict[str, str]
    raw_samples: Dict[str, List[float]] = field(default_factory=dict)
    environment: Optional[EnvironmentInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    commit_hash: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.environment:
            d["environment"] = self.environment.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkResult":
        env_data = data.pop("environment", None)
        env = EnvironmentInfo.from_dict(env_data) if env_data else None
        return cls(environment=env, **{k: v for k, v in data.items() if k in cls.__annotations__})


class PrecisionTimer:
    """High-precision timer using perf_counter_ns for nanosecond resolution."""

    def __init__(self):
        self._start: Optional[int] = None
        self._end: Optional[int] = None
        self._laps: List[int] = []

    def start(self) -> "PrecisionTimer":
        self._start = time.perf_counter_ns()
        self._end = None
        self._laps = []
        return self

    def lap(self) -> float:
        """Record a lap time in milliseconds."""
        now = time.perf_counter_ns()
        if self._start is None:
            self._start = now
        lap_ms = (now - (self._laps[-1] if self._laps else self._start)) / 1_000_000
        self._laps.append(now)
        return lap_ms

    def stop(self) -> float:
        """Stop timer and return elapsed milliseconds."""
        self._end = time.perf_counter_ns()
        if self._start is None:
            return 0.0
        return (self._end - self._start) / 1_000_000

    def elapsed_ms(self) -> float:
        """Current elapsed time in milliseconds."""
        if self._start is None:
            return 0.0
        end = self._end or time.perf_counter_ns()
        return (end - self._start) / 1_000_000

    @property
    def laps_ms(self) -> List[float]:
        if not self._laps or self._start is None:
            return []
        return [(lap - (self._laps[i-1] if i > 0 else self._start)) / 1_000_000
                for i, lap in enumerate(self._laps)]


@contextmanager
def measure_time() -> PrecisionTimer:
    """Context manager for timing a block of code."""
    timer = PrecisionTimer()
    timer.start()
    try:
        yield timer
    finally:
        timer.stop()


class ResourceMonitor:
    """Monitor system resources (CPU, memory, disk, network) during benchmarks."""

    def __init__(self, interval_ms: float = 100.0, pid: Optional[int] = None):
        self.interval_ms = interval_ms
        self.pid = pid or os.getpid()
        self._process = psutil.Process(self.pid) if PSUTIL_AVAILABLE else None
        self._samples: List[Dict[str, Any]] = []
        self._running = False
        self._thread = None

    def start(self) -> "ResourceMonitor":
        if not PSUTIL_AVAILABLE:
            return self
        self._running = True
        self._samples = []
        import threading
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> List[Dict[str, Any]]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        return self._samples

    def _sample_loop(self):
        while self._running:
            try:
                sample = self._sample()
                self._samples.append(sample)
            except Exception:
                pass
            time.sleep(self.interval_ms / 1000.0)

    def _sample(self) -> Dict[str, Any]:
        if not self._process:
            return {}
        try:
            with self._process.oneshot():
                mem = self._process.memory_info()
                cpu = self._process.cpu_percent()
                threads = self._process.num_threads()
                fds = self._process.num_fds() if hasattr(self._process, "num_fds") else 0
                return {
                    "timestamp": time.time(),
                    "rss_mb": mem.rss / (1024 * 1024),
                    "vms_mb": mem.vms / (1024 * 1024),
                    "cpu_percent": cpu,
                    "threads": threads,
                    "fds": fds,
                }
        except Exception:
            return {}

    def summary(self) -> Dict[str, Any]:
        if not self._samples:
            return {}
        rss = [s["rss_mb"] for s in self._samples if "rss_mb" in s]
        cpu = [s["cpu_percent"] for s in self._samples if "cpu_percent" in s]
        return {
            "rss_mb": {"mean": statistics.mean(rss), "max": max(rss), "min": min(rss), "stdev": statistics.stdev(rss) if len(rss) > 1 else 0},
            "cpu_percent": {"mean": statistics.mean(cpu), "max": max(cpu), "min": min(cpu), "stdev": statistics.stdev(cpu) if len(cpu) > 1 else 0},
            "samples": len(self._samples),
        }


class BenchmarkHarness:
    """Base class for performance benchmarks with standardized methodology."""

    def __init__(
        self,
        benchmark_id: str,
        name: str,
        category: str,
        warmup_iterations: int = 3,
        measurement_iterations: int = 10,
        environment: Optional[EnvironmentInfo] = None,
    ):
        self.benchmark_id = benchmark_id
        self.name = name
        self.category = category
        self.warmup_iterations = warmup_iterations
        self.measurement_iterations = measurement_iterations
        self.environment = environment or EnvironmentInfo()
        self._setup_done = False

    def setup(self) -> None:
        """Override to perform one-time setup before benchmarking."""
        self._setup_done = True

    def teardown(self) -> None:
        """Override to perform cleanup after benchmarking."""
        pass

    def warmup(self) -> None:
        """Override to perform warmup iterations."""
        pass

    def measure_once(self) -> Dict[str, float]:
        """Override to perform a single measurement iteration.
        Returns dict of metric_name -> value."""
        raise NotImplementedError

    def get_metric_units(self) -> Dict[str, str]:
        """Override to return metric_name -> unit mapping."""
        return {}

    def run(self) -> BenchmarkResult:
        """Execute full benchmark with warmup and measurement phases."""
        if not self._setup_done:
            self.setup()

        # Warmup phase
        if self.warmup_iterations > 0:
            self.warmup()

        # Measurement phase
        all_samples: Dict[str, List[float]] = {}
        for _ in range(self.measurement_iterations):
            metrics = self.measure_once()
            for k, v in metrics.items():
                all_samples.setdefault(k, []).append(v)

        # Compute aggregated metrics
        aggregated = {}
        for k, samples in all_samples.items():
            aggregated[f"{k}_mean"] = statistics.mean(samples)
            aggregated[f"{k}_median"] = statistics.median(samples)
            aggregated[f"{k}_stdev"] = statistics.stdev(samples) if len(samples) > 1 else 0.0
            aggregated[f"{k}_min"] = min(samples)
            aggregated[f"{k}_max"] = max(samples)
            if len(samples) >= 20:
                sorted_samples = sorted(samples)
                aggregated[f"{k}_p50"] = sorted_samples[len(sorted_samples) // 2]
                aggregated[f"{k}_p95"] = sorted_samples[int(len(sorted_samples) * 0.95)]
                aggregated[f"{k}_p99"] = sorted_samples[int(len(sorted_samples) * 0.99)]

        self.teardown()

        return BenchmarkResult(
            benchmark_id=self.benchmark_id,
            name=self.name,
            category=self.category,
            status="MEASURED",
            iterations=self.measurement_iterations,
            warmup_iterations=self.warmup_iterations,
            metrics=aggregated,
            units=self.get_metric_units(),
            raw_samples=all_samples,
            environment=self.environment,
        )


def run_benchmark(harness: BenchmarkHarness) -> BenchmarkResult:
    """Convenience function to run a benchmark harness."""
    return harness.run()


def percentile(data: List[float], p: float) -> float:
    """Compute percentile (0-100) of data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def mean(data: List[float]) -> float:
    return statistics.mean(data) if data else 0.0


def median(data: List[float]) -> float:
    return statistics.median(data) if data else 0.0


def stdev(data: List[float]) -> float:
    return statistics.stdev(data) if len(data) > 1 else 0.0


def cv(data: List[float]) -> float:
    """Coefficient of variation (stdev/mean) - measures stability."""
    m = mean(data)
    if m == 0:
        return 0.0
    return stdev(data) / m


def detect_outliers_iqr(data: List[float], multiplier: float = 1.5) -> List[float]:
    """Detect outliers using IQR method."""
    if len(data) < 4:
        return []
    sorted_data = sorted(data)
    q1 = percentile(sorted_data, 25)
    q3 = percentile(sorted_data, 75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return [x for x in data if x < lower or x > upper]


def benchmark_stability_report(samples: List[float]) -> Dict[str, Any]:
    """Generate stability report for benchmark samples."""
    if not samples:
        return {"status": "NO_DATA"}
    outliers = detect_outliers_iqr(samples)
    cv_val = cv(samples)
    return {
        "count": len(samples),
        "mean": mean(samples),
        "median": median(samples),
        "stdev": stdev(samples),
        "cv": cv_val,
        "min": min(samples),
        "max": max(samples),
        "p50": percentile(samples, 50),
        "p95": percentile(samples, 95),
        "p99": percentile(samples, 99),
        "outliers_count": len(outliers),
        "outliers": outliers,
        "stability": "STABLE" if cv_val < 0.1 else "UNSTABLE" if cv_val < 0.25 else "NOISY",
    }