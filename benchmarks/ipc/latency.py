"""IPC performance benchmarks (PERF-IPC-*)."""

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


@register_benchmark("ipc", "PERF-IPC-001")
class IPCRoundTripBenchmark(BenchmarkHarness):
    """PERF-IPC-001: IPC round-trip latency.

    Measures: renderer → preload → main → preload → renderer
    """

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-IPC-001",
            name="IPC Round-Trip Latency",
            category="ipc",
            warmup_iterations=10,
            measurement_iterations=100,
            environment=environment,
        )
        self._ipc_channel = None

    def setup(self) -> None:
        """Setup IPC test channel."""
        # In real implementation, this would create an Electron test
        # harness with a dedicated IPC channel for benchmarking
        pass

    def measure_once(self) -> Dict[str, float]:
        # This requires a running Electron app with test IPC channel
        # For now, return BLOCKED
        return {
            "blocked": 1.0,
            "reason": "Requires Electron test harness with IPC channel",
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "round_trip_ms": "ms",
            "serialization_ms": "ms",
            "deserialization_ms": "ms",
        }


@register_benchmark("ipc", "PERF-IPC-002")
class IPCPayloadSizeBenchmark(BenchmarkHarness):
    """PERF-IPC-002: IPC throughput vs payload size.

    Tests payload sizes: 1KB, 10KB, 100KB, 1MB, 10MB
    """

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-IPC-002",
            name="IPC Payload Size Throughput",
            category="ipc",
            warmup_iterations=5,
            measurement_iterations=20,
            environment=environment,
        )
        self.payload_sizes = [1024, 10240, 102400, 1048576, 10485760]

    def measure_once(self) -> Dict[str, float]:
        # Requires Electron test harness
        return {
            "blocked": 1.0,
            "reason": "Requires Electron test harness with IPC channel",
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "latency_1kb_ms": "ms",
            "latency_10kb_ms": "ms",
            "latency_100kb_ms": "ms",
            "latency_1mb_ms": "ms",
            "latency_10mb_ms": "ms",
            "throughput_mbps": "MB/s",
        }


@register_benchmark("ipc", "PERF-IPC-003")
class IPCSerializationBenchmark(BenchmarkHarness):
    """PERF-IPC-003: IPC serialization/deserialization overhead."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-IPC-003",
            name="IPC Serialization Overhead",
            category="ipc",
            warmup_iterations=10,
            measurement_iterations=100,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Test JSON serialization of typical IPC payloads
        test_payloads = [
            {"type": "tool_result", "tool": "read_file", "data": "x" * 1000},
            {"type": "agent_event", "event": "token", "data": "x" * 100},
            {"type": "transcript_update", "messages": [{"role": "user", "content": "x" * 500}] * 10},
            {"type": "memory_result", "entries": [{"id": j, "content": "x" * 200} for j in range(50)]},
        ]

        results = {}
        import json as json_module

        for i, payload in enumerate(test_payloads):
            # Serialize
            timer = PrecisionTimer()
            timer.start()
            serialized = json_module.dumps(payload)
            serialize_ms = timer.stop()

            # Deserialize
            timer.start()
            json_module.loads(serialized)
            deserialize_ms = timer.stop()

            results[f"payload_{i}_serialize_ms"] = serialize_ms
            results[f"payload_{i}_deserialize_ms"] = deserialize_ms
            results[f"payload_{i}_size_bytes"] = float(len(serialized))

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "payload_*_serialize_ms": "ms",
            "payload_*_deserialize_ms": "ms",
            "payload_*_size_bytes": "bytes",
        }


@register_benchmark("ipc", "PERF-IPC-004")
class IPCBatchBenchmark(BenchmarkHarness):
    """PERF-IPC-004: Batched IPC vs individual calls."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-IPC-004",
            name="IPC Batching Efficiency",
            category="ipc",
            warmup_iterations=5,
            measurement_iterations=20,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Would compare: 10 individual IPC calls vs 1 batched call
        return {
            "blocked": 1.0,
            "reason": "Requires Electron test harness with batch IPC support",
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "individual_10_calls_ms": "ms",
            "batched_1_call_ms": "ms",
            "speedup_factor": "ratio",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    # Only run serialization benchmark (others need Electron)
    from benchmarks.core.runner import REGISTRY
    harness = REGISTRY.get("ipc", "PERF-IPC-003")
    if harness:
        harness.environment = env
        result = run_benchmark(harness)
        print(json.dumps(result.to_dict(), indent=2, default=str))