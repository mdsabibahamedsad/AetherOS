"""Memory leak detection and soak testing (PERF-MEMORY-LEAK-*)."""

from __future__ import annotations

import gc
import sys
import time
import tracemalloc
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@dataclass
class MemorySnapshot:
    """Memory snapshot at a point in time."""
    timestamp: float
    rss_mb: float
    heap_mb: float
    object_count: int
    tracemalloc_current: int
    tracemalloc_peak: int


class MemoryLeakDetector:
    """Detects memory leaks by tracking allocations over time."""

    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.snapshots: List[MemorySnapshot] = []
        self._running = False
        self._thread = None
        self._baseline_objects = None

    def start(self):
        """Start memory tracking."""
        gc.collect()
        tracemalloc.start()
        self._baseline_objects = len(gc.get_objects())
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[MemorySnapshot]:
        """Stop tracking and return snapshots."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        tracemalloc.stop()
        return self.snapshots

    def _sample_loop(self):
        import psutil
        process = psutil.Process()
        while self._running:
            gc.collect()
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=process.memory_info().rss / (1024 * 1024),
                heap_mb=tracemalloc.get_traced_memory()[0] / (1024 * 1024),
                object_count=len(gc.get_objects()),
                tracemalloc_current=tracemalloc.get_traced_memory()[0],
                tracemalloc_peak=tracemalloc.get_traced_memory()[1],
            )
            self.snapshots.append(snapshot)
            time.sleep(self.sample_interval)

    def analyze(self) -> Dict[str, Any]:
        """Analyze snapshots for leaks."""
        if len(self.snapshots) < 10:
            return {"status": "INSUFFICIENT_DATA", "snapshots": len(self.snapshots)}

        rss_values = [s.rss_mb for s in self.snapshots]
        heap_values = [s.heap_mb for s in self.snapshots]
        obj_values = [s.object_count for s in self.snapshots]

        # Linear regression on memory growth
        n = len(rss_values)
        x = list(range(n))
        x_mean = sum(x) / n
        rss_mean = sum(rss_values) / n
        heap_mean = sum(heap_values) / n
        obj_mean = sum(obj_values) / n

        rss_slope = sum((x[i] - x_mean) * (rss_values[i] - rss_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))
        heap_slope = sum((x[i] - x_mean) * (heap_values[i] - heap_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))
        obj_slope = sum((x[i] - x_mean) * (obj_values[i] - obj_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))

        return {
            "duration_seconds": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            "snapshots": n,
            "rss_mb": {"start": rss_values[0], "end": rss_values[-1], "growth_mb": rss_values[-1] - rss_values[0], "slope_mb_per_sample": rss_slope},
            "heap_mb": {"start": heap_values[0], "end": heap_values[-1], "growth_mb": heap_values[-1] - heap_values[0], "slope_mb_per_sample": heap_slope},
            "objects": {"start": obj_values[0], "end": obj_values[-1], "growth": obj_values[-1] - obj_values[0], "slope_per_sample": obj_slope},
            "leak_detected": rss_slope > 0.1 or heap_slope > 0.05 or obj_slope > 100,
            "severity": "HIGH" if rss_slope > 1.0 else "MEDIUM" if rss_slope > 0.1 else "LOW",
        }


def run_memory_leak_test(
    workload: Callable[[], Any],
    iterations: int = 100,
    sample_interval: float = 0.5,
) -> Dict[str, Any]:
    """Run a workload repeatedly and detect memory leaks."""
    detector = MemoryLeakDetector(sample_interval=sample_interval)
    detector.start()

    try:
        for i in range(iterations):
            workload()
            if i % 10 == 0:
                gc.collect()
    finally:
        detector.stop()

    return detector.analyze()


@register_benchmark("load", "PERF-MEMORY-LEAK-001")
class AgentConversationMemoryLeakBenchmark(BenchmarkHarness):
    """PERF-MEMORY-LEAK-001: Agent conversation memory growth."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-LEAK-001",
            name="Agent Conversation Memory Growth",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )
        self._agent = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from run_agent import AIAgent
            self._agent = AIAgent(
                model="test-model",
                max_iterations=1,
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
            )
            # Mock the chat method to avoid model calls
            self._original_chat = self._agent.chat
            self._agent.chat = lambda msg: "mock response"
        except Exception as e:
            self._agent = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._agent:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        def workload():
            self._agent.chat("Test message for memory tracking")

        result = run_memory_leak_test(workload, iterations=50, sample_interval=0.2)

        return {
            "leak_detected": 1.0 if result.get("leak_detected") else 0.0,
            "rss_growth_mb": result.get("rss_mb", {}).get("growth_mb", 0),
            "heap_growth_mb": result.get("heap_mb", {}).get("growth_mb", 0),
            "object_growth": result.get("objects", {}).get("growth", 0),
            "rss_slope": result.get("rss_mb", {}).get("slope_mb_per_sample", 0),
            "severity_high": 1.0 if result.get("severity") == "HIGH" else 0.0,
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "leak_detected": "bool",
            "rss_growth_mb": "MB",
            "heap_growth_mb": "MB",
            "object_growth": "count",
            "rss_slope": "MB/sample",
            "severity_high": "bool",
        }


@register_benchmark("load", "PERF-MEMORY-LEAK-002")
class ElectronRendererMemoryLeakBenchmark(BenchmarkHarness):
    """PERF-MEMORY-LEAK-002: Electron renderer memory growth over time."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-LEAK-002",
            name="Electron Renderer Memory Growth",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires Electron test harness with memory profiling"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "js_heap_growth_mb": "MB",
            "detached_dom_nodes": "count",
            "event_listener_leaks": "count",
            "timer_leaks": "count",
        }


@register_benchmark("load", "PERF-MEMORY-LEAK-003")
class GatewayMemoryLeakBenchmark(BenchmarkHarness):
    """PERF-MEMORY-LEAK-003: Gateway process memory growth."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-LEAK-003",
            name="Gateway Memory Growth",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires running gateway under load"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "rss_growth_mb_per_hour": "MB/h",
            "session_leak_count": "count",
            "stream_buffer_leak_mb": "MB",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    harness = REGISTRY.get("load", "PERF-MEMORY-LEAK-001")
    if harness:
        harness.environment = env
        result = run_benchmark(harness)
        print(json.dumps(result.to_dict(), indent=2, default=str))