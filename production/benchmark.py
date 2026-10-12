"""
Benchmark Suite
===============

Repeatable benchmark suites for measuring AetherOS performance.

Benchmarks cover:
- Startup time
- Memory usage
- Workflow execution
- Parallel agent coordination
- Repository analysis
- Plugin loading
- Distributed execution
- Engineering throughput

Results are published in machine-readable JSON format.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run.

    Attributes:
        name: Benchmark name
        description: Description of what was measured
        duration_seconds: Wall-clock duration
        metrics: Key-value metrics from the benchmark
        metadata: Run metadata (date, host, version, etc.)
        success: Whether the benchmark completed successfully
        error: Error message if benchmark failed
    """
    name: str
    description: str = ""
    duration_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class BenchmarkSuite:
    """A collection of related benchmarks.

    Attributes:
        name: Suite name
        description: Suite description
        benchmarks: List of benchmark results
        start_time: When the suite started
        end_time: When the suite ended
    """
    name: str
    description: str = ""
    benchmarks: List[BenchmarkResult] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def add_result(self, result: BenchmarkResult) -> None:
        self.benchmarks.append(result)

    @property
    def total_duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return sum(b.duration_seconds for b in self.benchmarks)

    @property
    def success_count(self) -> int:
        return sum(1 for b in self.benchmarks if b.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for b in self.benchmarks if not b.success)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "total_duration_seconds": self.total_duration,
            "benchmark_count": len(self.benchmarks),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "benchmarks": [b.to_dict() for b in self.benchmarks],
        }

    def save(self, path: str) -> Path:
        """Save benchmark results to a JSON file."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        logger.info("Benchmark suite saved to %s", output)
        return output

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "BenchmarkSuite":
        """Load a benchmark suite from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        suite = cls(name=data["name"], description=data.get("description", ""))
        suite.start_time = data.get("start_time")
        suite.end_time = data.get("end_time")
        for b_data in data.get("benchmarks", []):
            suite.add_result(BenchmarkResult(**b_data))
        return suite


class BenchmarkRunner:
    """Runs benchmarks and collects structured results.

    Usage:
        runner = BenchmarkRunner()
        suite = BenchmarkSuite(name="startup", description="Startup benchmarks")

        # Add a benchmark
        result = runner.benchmark(
            "startup_time",
            lambda: kernel.boot(),
            iterations=3,
        )
        suite.add_result(result)
    """

    def __init__(self, output_dir: str = "/tmp/aetheros-benchmarks"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def benchmark(
        self,
        name: str,
        fn: Callable,
        description: str = "",
        iterations: int = 5,
        warmup: int = 1,
        setup_fn: Optional[Callable] = None,
        teardown_fn: Optional[Callable] = None,
    ) -> BenchmarkResult:
        """Run a benchmark with multiple iterations.

        Args:
            name: Benchmark name
            fn: The function to benchmark
            description: Description of the benchmark
            iterations: Number of measurement iterations
            warmup: Number of warmup iterations (not measured)
            setup_fn: Optional setup function called before each iteration
            teardown_fn: Optional teardown function called after each iteration

        Returns:
            BenchmarkResult with timing and metrics
        """
        logger.info("Running benchmark: %s (%d iterations)", name, iterations)

        # Warmup
        for _ in range(warmup):
            if setup_fn:
                setup_fn()
            fn()
            if teardown_fn:
                teardown_fn()

        # Measurement
        times: List[float] = []
        errors: List[str] = []

        for i in range(iterations):
            try:
                if setup_fn:
                    setup_fn()
                start = time.perf_counter()
                fn()
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                if teardown_fn:
                    teardown_fn()
            except Exception as exc:
                errors.append(f"Iteration {i}: {exc}")
                logger.warning("Benchmark '%s' iteration %d failed: %s", name, i, exc)

        if not times and errors:
            return BenchmarkResult(
                name=name,
                description=description,
                success=False,
                error=f"All {iterations} iterations failed: {errors[0]}",
            )

        metrics = self._compute_metrics(times)

        result = BenchmarkResult(
            name=name,
            description=description,
            duration_seconds=sum(times),
            metrics={
                "iterations": len(times),
                "min_ms": metrics["min"] * 1000,
                "max_ms": metrics["max"] * 1000,
                "avg_ms": metrics["avg"] * 1000,
                "median_ms": metrics["median"] * 1000,
                "p95_ms": metrics["p95"] * 1000,
                "p99_ms": metrics["p99"] * 1000,
                "total_seconds": sum(times),
                "total_ms": sum(times) * 1000,
            },
            metadata={
                "warmup_iterations": warmup,
                "failed_iterations": len(errors),
                "error_count": len(errors),
            },
            success=len(errors) == 0,
        )

        return result

    def _compute_metrics(self, times: List[float]) -> Dict[str, float]:
        """Compute statistical metrics from timing data."""
        if not times:
            return {"min": 0, "max": 0, "avg": 0, "median": 0, "p95": 0, "p99": 0}

        sorted_times = sorted(times)
        n = len(sorted_times)
        return {
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "avg": sum(sorted_times) / n,
            "median": sorted_times[n // 2],
            "p95": sorted_times[int(n * 0.95)] if n >= 20 else sorted_times[-1],
            "p99": sorted_times[int(n * 0.99)] if n >= 100 else sorted_times[-1],
        }

    def run_suite(self, suite: BenchmarkSuite) -> BenchmarkSuite:
        """Finalize a benchmark suite by recording timestamps.

        Note: Individual benchmarks are executed via ``benchmark()`` and
        their results are added to the suite before calling this method.
        This method simply records start/end timestamps for the suite's
        metadata. Use ``run_benchmarks()`` for the standard workflow.
        """
        suite.start_time = time.time()
        suite.end_time = time.time()
        return suite


# Predefined benchmark builders

def benchmark_startup() -> BenchmarkSuite:
    """Benchmark AetherOS startup time."""
    suite = BenchmarkSuite(
        name="startup",
        description="Measure AetherOS kernel and component startup times",
    )
    return suite


def benchmark_memory() -> BenchmarkSuite:
    """Benchmark memory usage at various stages."""
    suite = BenchmarkSuite(
        name="memory",
        description="Memory usage benchmarks for kernel, agents, and tools",
    )
    return suite


def benchmark_workflow() -> BenchmarkSuite:
    """Benchmark workflow execution throughput."""
    suite = BenchmarkSuite(
        name="workflow",
        description="Workflow execution performance benchmarks",
    )
    return suite


def benchmark_plugin_loading() -> BenchmarkSuite:
    """Benchmark plugin loading performance."""
    suite = BenchmarkSuite(
        name="plugin_loading",
        description="Plugin discovery and loading benchmarks",
    )
    return suite


def run_benchmarks(suites: Optional[List[BenchmarkSuite]] = None,
                   output_dir: str = "/tmp/aetheros-benchmarks") -> List[BenchmarkSuite]:
    """Run all or specified benchmark suites.

    Args:
        suites: List of benchmark suites to run. If None, runs standard suites.
        output_dir: Directory for JSON results output.

    Returns:
        List of completed BenchmarkSuite objects.
    """
    runner = BenchmarkRunner(output_dir=output_dir)

    if suites is None:
        suites = [
            benchmark_startup(),
            benchmark_memory(),
            benchmark_workflow(),
            benchmark_plugin_loading(),
        ]

    results: List[BenchmarkSuite] = []
    for suite in suites:
        logger.info("Running benchmark suite: %s", suite.name)
        suite.start_time = time.time()
        runner.run_suite(suite)
        suite.end_time = time.time()

        # Save results
        output_path = Path(output_dir) / f"{suite.name}_{int(time.time())}.json"
        suite.save(str(output_path))
        results.append(suite)

        logger.info(
            "Suite '%s': %d benchmarks, %.2fs total, %d passed, %d failed",
            suite.name, len(suite.benchmarks), suite.total_duration,
            suite.success_count, suite.failure_count,
        )

    return results
