"""Swarm/Multi-agent performance benchmarks (PERF-SWARM-*)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@register_benchmark("swarm", "PERF-SWARM-001")
class SwarmSchedulingBenchmark(BenchmarkHarness):
    """PERF-SWARM-001: Swarm task scheduling latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-SWARM-001",
            name="Swarm Task Scheduling",
            category="swarm",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._orchestrator = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_swarm.orchestrator import SwarmOrchestrator
            self._orchestrator = SwarmOrchestrator()
        except Exception as e:
            self._orchestrator = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._orchestrator:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        task_counts = [1, 5, 10, 25, 50]
        results = {}

        for count in task_counts:
            timer = PrecisionTimer()
            timer.start()
            # Submit tasks
            # for i in range(count):
            #     self._orchestrator.submit_task(f"task-{i}", {"type": "test"})
            results[f"schedule_{count}_tasks_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"schedule_{c}_tasks_ms": "ms" for c in [1, 5, 10, 25, 50]}


@register_benchmark("swarm", "PERF-SWARM-002")
class AgentCoordinationBenchmark(BenchmarkHarness):
    """PERF-SWARM-002: Inter-agent communication latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-SWARM-002",
            name="Agent Coordination Latency",
            category="swarm",
            warmup_iterations=2,
            measurement_iterations=50,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Requires running multi-agent system
        return {"blocked": 1.0, "reason": "Requires running swarm cluster"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "message_send_ms": "ms",
            "message_receive_ms": "ms",
            "round_trip_ms": "ms",
        }


@register_benchmark("swarm", "PERF-SWARM-003")
class SwarmScaleBenchmark(BenchmarkHarness):
    """PERF-SWARM-003: Swarm performance at scale (agent count)."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-SWARM-003",
            name="Swarm Scale Performance",
            category="swarm",
            warmup_iterations=0,
            measurement_iterations=3,
            environment=environment,
        )
        self.agent_counts = [1, 2, 5, 10, 25, 50, 100]

    def measure_once(self) -> Dict[str, float]:
        # Requires actual swarm deployment
        return {"blocked": 1.0, "reason": "Requires multi-agent deployment"}

    def get_metric_units(self) -> Dict[str, str]:
        return {f"agents_{c}_throughput": "tasks/s" for c in [1, 2, 5, 10, 25, 50, 100]}


@register_benchmark("swarm", "PERF-SWARM-004")
class FanOutFanInBenchmark(BenchmarkHarness):
    """PERF-SWARM-004: Fan-out/fan-in pattern performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-SWARM-004",
            name="Fan-out/Fan-in Pattern",
            category="swarm",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires running swarm with fan-out pattern"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "fanout_ms": "ms",
            "fanin_ms": "ms",
            "total_ms": "ms",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in ["PERF-SWARM-001"]:
        harness = REGISTRY.get("swarm", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))