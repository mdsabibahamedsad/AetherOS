"""Load testing and soak test infrastructure (PERF-LOAD-*)."""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    ResourceMonitor,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@dataclass
class LoadTestConfig:
    """Configuration for a load test."""
    name: str
    target_func: Callable
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    think_time_ms: int = 100
    target_metrics: List[str] = field(default_factory=lambda: ["latency", "throughput", "error_rate"])


@dataclass
class LoadTestResult:
    """Results from a load test."""
    config: LoadTestConfig
    start_time: float
    end_time: float
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    resource_samples: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        if not self.latencies_ms:
            return {"status": "NO_DATA"}

        sorted_lat = sorted(self.latencies_ms)
        n = len(sorted_lat)
        return {
            "duration_seconds": self.end_time - self.start_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": self.failed_requests / self.total_requests if self.total_requests > 0 else 0,
            "throughput_rps": self.total_requests / (self.end_time - self.start_time) if self.end_time > self.start_time else 0,
            "latency_ms": {
                "mean": sum(sorted_lat) / n,
                "median": sorted_lat[n // 2],
                "p50": sorted_lat[n // 2],
                "p95": sorted_lat[int(n * 0.95)],
                "p99": sorted_lat[int(n * 0.99)],
                "min": sorted_lat[0],
                "max": sorted_lat[-1],
            },
            "resource_usage": self._resource_summary(),
        }

    def _resource_summary(self) -> Dict[str, Any]:
        if not self.resource_samples:
            return {}
        cpu = [s.get("cpu_percent", 0) for s in self.resource_samples if "cpu_percent" in s]
        rss = [s.get("rss_mb", 0) for s in self.resource_samples if "rss_mb" in s]
        return {
            "cpu_percent": {"mean": sum(cpu) / len(cpu) if cpu else 0, "max": max(cpu) if cpu else 0},
            "rss_mb": {"mean": sum(rss) / len(rss) if rss else 0, "max": max(rss) if rss else 0},
        }


class LoadTestRunner:
    """Executes load tests with configurable concurrency and duration."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.result = LoadTestResult(config=config, start_time=0, end_time=0)
        self._stop_event = threading.Event()
        self._resource_monitor = ResourceMonitor(interval_ms=500)

    def run(self) -> LoadTestResult:
        """Run the load test."""
        self.result.start_time = time.time()
        self._resource_monitor.start()

        with ThreadPoolExecutor(max_workers=self.config.concurrent_users) as executor:
            futures = []
            for i in range(self.config.concurrent_users):
                future = executor.submit(self._user_session, i)
                futures.append(future)

            # Wait for all to complete or duration to expire
            start = time.time()
            while time.time() - start < self.config.duration_seconds:
                time.sleep(1)
                # Collect resource samples
                self.result.resource_samples.extend(self._resource_monitor._samples)
                self._resource_monitor._samples.clear()

            self._stop_event.set()

            for future in as_completed(futures):
                try:
                    future.result(timeout=5)
                except Exception as e:
                    self.result.errors.append(str(e))

        self._resource_monitor.stop()
        self.result.resource_samples.extend(self._resource_monitor._samples)
        self.result.end_time = time.time()
        return self.result

    def _user_session(self, user_id: int):
        """Simulate a single user session."""
        # Ramp up
        ramp_delay = (self.config.ramp_up_seconds * user_id) / max(1, self.config.concurrent_users - 1)
        time.sleep(ramp_up)

        while not self._stop_event.is_set():
            timer = PrecisionTimer()
            timer.start()
            try:
                result = self.config.target_func()
                latency = timer.stop()
                self.result.latencies_ms.append(latency)
                self.result.successful_requests += 1
            except Exception as e:
                latency = timer.stop()
                self.result.latencies_ms.append(latency)
                self.result.failed_requests += 1
                self.result.errors.append(str(e))

            self.result.total_requests += 1
            time.sleep(self.config.think_time_ms / 1000.0)


def run_load_test(config: LoadTestConfig) -> LoadTestResult:
    """Convenience function to run a load test."""
    runner = LoadTestRunner(config)
    return runner.run()


# Example load test configurations
def create_api_load_test(target_url: str, concurrent: int = 10, duration: int = 60) -> LoadTestConfig:
    """Create a load test for an API endpoint."""
    import requests

    def make_request():
        response = requests.get(target_url, timeout=10)
        response.raise_for_status()
        return response.json()

    return LoadTestConfig(
        name=f"API Load Test: {target_url}",
        target_func=make_request,
        concurrent_users=concurrent,
        duration_seconds=duration,
    )


def create_agent_task_load_test(agent_factory: Callable, concurrent: int = 5, duration: int = 120) -> LoadTestConfig:
    """Create a load test for agent task execution."""

    def execute_task():
        agent = agent_factory()
        return agent.chat("Perform a simple task")

    return LoadTestConfig(
        name="Agent Task Load Test",
        target_func=execute_task,
        concurrent_users=concurrent,
        duration_seconds=duration,
        think_time_ms=1000,
    )


@register_benchmark("load", "PERF-LOAD-001")
class ConcurrentAgentsBenchmark(BenchmarkHarness):
    """PERF-LOAD-001: Concurrent agent execution."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-LOAD-001",
            name="Concurrent Agent Execution",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,  # Single load test run
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # This would run a full load test
        return {"blocked": 1.0, "reason": "Requires load test configuration"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "throughput_tasks_per_sec": "tasks/s",
            "p50_latency_ms": "ms",
            "p99_latency_ms": "ms",
            "error_rate": "ratio",
        }


@register_benchmark("load", "PERF-LOAD-002")
class APILoadBenchmark(BenchmarkHarness):
    """PERF-LOAD-002: API endpoint load test."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-LOAD-002",
            name="API Load Test",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires running API server"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "rps": "req/s",
            "p50_latency_ms": "ms",
            "p99_latency_ms": "ms",
            "error_rate": "ratio",
        }


@register_benchmark("load", "PERF-LOAD-003")
class SoakTestBenchmark(BenchmarkHarness):
    """PERF-LOAD-003: Long-running soak test for memory/CPU stability."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-LOAD-003",
            name="Soak Test (1 hour)",
            category="load",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Run 1-hour soak test
        # This is a placeholder - real implementation would run for 1+ hours
        return {"blocked": 1.0, "reason": "Soak test requires 1+ hour execution"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "memory_growth_mb_per_hour": "MB/h",
            "cpu_stability_cv": "ratio",
            "error_count": "count",
            "throughput_degradation_pct": "%",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in ["PERF-LOAD-001", "PERF-LOAD-002"]:
        harness = REGISTRY.get("load", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))