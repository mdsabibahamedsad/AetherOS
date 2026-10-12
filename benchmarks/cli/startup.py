"""CLI/TUI performance benchmarks (PERF-CLI-*, PERF-TUI-*)."""

from __future__ import annotations

import json
import subprocess
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


@register_benchmark("cli", "PERF-CLI-001")
class CLIColdStartBenchmark(BenchmarkHarness):
    """PERF-CLI-001: CLI cold startup time."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-CLI-001",
            name="CLI Cold Startup",
            category="cli",
            warmup_iterations=0,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        timer = PrecisionTimer()
        timer.start()

        result = subprocess.run(
            [sys.executable, "-m", "aetheros", "--help"],
            capture_output=True,
            timeout=30,
        )

        elapsed = timer.stop()
        return {
            "startup_time_ms": elapsed,
            "exit_code": float(result.returncode),
            "stdout_bytes": float(len(result.stdout)),
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {"startup_time_ms": "ms", "exit_code": "code", "stdout_bytes": "bytes"}


@register_benchmark("cli", "PERF-CLI-002")
class CLICommandDispatchBenchmark(BenchmarkHarness):
    """PERF-CLI-002: CLI command dispatch latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-CLI-002",
            name="CLI Command Dispatch",
            category="cli",
            warmup_iterations=5,
            measurement_iterations=50,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        commands = ["--help", "skills list", "config show"]
        results = {}

        for cmd in commands:
            args = [sys.executable, "-m", "aetheros"] + cmd.split()
            timer = PrecisionTimer()
            timer.start()
            result = subprocess.run(args, capture_output=True, timeout=10)
            results[f"cmd_{cmd.replace(' ', '_')}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in ["cmd___help_ms", "cmd_skills_list_ms", "cmd_config_show_ms"]}


@register_benchmark("cli", "PERF-CLI-003")
class CLIInteractiveStartupBenchmark(BenchmarkHarness):
    """PERF-CLI-003: CLI interactive mode startup."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-CLI-003",
            name="CLI Interactive Startup",
            category="cli",
            warmup_iterations=0,
            measurement_iterations=5,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Start CLI and send exit command
        timer = PrecisionTimer()
        timer.start()

        proc = subprocess.Popen(
            [sys.executable, "-m", "aetheros"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for prompt
        stdout, _ = proc.communicate(input="/exit\n", timeout=10)
        elapsed = timer.stop()

        return {
            "startup_time_ms": elapsed,
            "prompt_detected": 1.0 if ">" in stdout or "λ" in stdout else 0.0,
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {"startup_time_ms": "ms", "prompt_detected": "bool"}


@register_benchmark("tui", "PERF-TUI-001")
class TUIColdStartBenchmark(BenchmarkHarness):
    """PERF-TUI-001: TUI (--tui) cold startup."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-TUI-001",
            name="TUI Cold Startup",
            category="tui",
            warmup_iterations=0,
            measurement_iterations=5,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        timer = PrecisionTimer()
        timer.start()

        proc = subprocess.Popen(
            [sys.executable, "-m", "aetheros", "--tui"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for TUI to be ready (simplified)
        time.sleep(3)
        elapsed = timer.stop()

        proc.terminate()
        proc.wait(timeout=5)

        return {"startup_time_ms": elapsed}

    def get_metric_units(self) -> Dict[str, str]:
        return {"startup_time_ms": "ms"}


@register_benchmark("tui", "PERF-TUI-002")
class TUIStreamingBenchmark(BenchmarkHarness):
    """PERF-TUI-002: TUI token streaming performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-TUI-002",
            name="TUI Token Streaming",
            category="tui",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Requires running TUI with agent
        return {"blocked": 1.0, "reason": "Requires running TUI with agent"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "tokens_per_second": "tok/s",
            "frame_time_ms": "ms",
            "cpu_percent": "%",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in ["PERF-CLI-001", "PERF-CLI-002", "PERF-CLI-003", "PERF-TUI-001"]:
        category = "cli" if "CLI" in bench_id else "tui"
        harness = REGISTRY.get(category, bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))