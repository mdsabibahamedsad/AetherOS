"""MCP/A2A performance benchmarks (PERF-MCP-*, PERF-A2A-*)."""

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


@register_benchmark("mcp", "PERF-MCP-001")
class MCPToolDiscoveryBenchmark(BenchmarkHarness):
    """PERF-MCP-001: MCP tool discovery latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MCP-001",
            name="MCP Tool Discovery",
            category="mcp",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._client = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            # Would import MCP client
            pass
        except Exception as e:
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._client:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'MCP client not configured')}

        timer = PrecisionTimer()
        timer.start()
        # tools = self._client.list_tools()
        return {"discovery_ms": timer.stop()}

    def get_metric_units(self) -> Dict[str, str]:
        return {"discovery_ms": "ms"}


@register_benchmark("mcp", "PERF-MCP-002")
class MCPInvocationBenchmark(BenchmarkHarness):
    """PERF-MCP-002: MCP tool invocation latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MCP-002",
            name="MCP Tool Invocation",
            category="mcp",
            warmup_iterations=5,
            measurement_iterations=50,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires MCP server"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "invocation_ms": "ms",
            "serialization_ms": "ms",
            "network_ms": "ms",
        }


@register_benchmark("mcp", "PERF-MCP-003")
class MCPStreamingBenchmark(BenchmarkHarness):
    """PERF-MCP-003: MCP streaming performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MCP-003",
            name="MCP Streaming",
            category="mcp",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires MCP server with streaming"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "first_chunk_ms": "ms",
            "chunk_interval_ms": "ms",
            "total_stream_ms": "ms",
        }


@register_benchmark("a2a", "PERF-A2A-001")
class A2ADiscoveryBenchmark(BenchmarkHarness):
    """PERF-A2A-001: A2A agent discovery."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-A2A-001",
            name="A2A Agent Discovery",
            category="a2a",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires A2A network"}

    def get_metric_units(self) -> Dict[str, str]:
        return {"discovery_ms": "ms"}


@register_benchmark("a2a", "PERF-A2A-002")
class A2ATaskSubmissionBenchmark(BenchmarkHarness):
    """PERF-A2A-002: A2A task submission latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-A2A-002",
            name="A2A Task Submission",
            category="a2a",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires A2A agent"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "submit_ms": "ms",
            "ack_ms": "ms",
            "total_ms": "ms",
        }


@register_benchmark("a2a", "PERF-A2A-003")
class A2AStreamingBenchmark(BenchmarkHarness):
    """PERF-A2A-003: A2A task streaming updates."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-A2A-003",
            name="A2A Streaming Updates",
            category="a2a",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires A2A agent with streaming"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "first_update_ms": "ms",
            "update_interval_ms": "ms",
            "completion_ms": "ms",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    # All MCP/A2A benchmarks require external infrastructure
    for bench_id in ["PERF-MCP-001", "PERF-MCP-002", "PERF-A2A-001"]:
        category = "mcp" if "MCP" in bench_id else "a2a"
        harness = REGISTRY.get(category, bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))