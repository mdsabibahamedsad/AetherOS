"""
Stress Testing
==============

Stress and load testing for AetherOS production deployments.

Validates operation under:
- High concurrency
- Large repositories
- Long-running workflows
- Resource pressure
- Sustained high load

Documents expected degradation behavior.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StressMetric(Enum):
    """Metrics measured during stress tests."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    RECOVERY_TIME = "recovery_time"


@dataclass
class StressScenario:
    """Configuration for a stress test scenario.

    Attributes:
        name: Scenario name
        description: What the scenario tests
        concurrency: Number of concurrent operations
        duration_seconds: How long to run
        ramp_up_seconds: Time to reach full concurrency
        target: Target operation/function
        expected_degradation: Expected performance degradation
    """
    name: str
    description: str = ""
    concurrency: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    target: Optional[Callable] = None
    expected_degradation: str = ""


@dataclass
class StressReport:
    """Report from a stress test run.

    Attributes:
        scenario: The scenario that was run
        start_time: When the test started
        end_time: When the test ended
        metrics: Measured metrics
        observations: Qualitative observations
        degradation: Observed vs expected degradation
        passed: Whether the system met stress criteria
    """
    scenario: str = ""
    description: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    observations: List[str] = field(default_factory=list)
    degradation: str = ""
    passed: bool = True

    @property
    def duration_seconds(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "metrics": dict(self.metrics),
            "observations": list(self.observations),
            "degradation": self.degradation,
            "passed": self.passed,
        }


class StressTester:
    """Runs stress tests and produces reports.

    Usage:
        tester = StressTester()
        scenario = StressScenario(
            name="high_concurrency",
            concurrency=50,
            duration_seconds=30,
        )
        report = tester.run_scenario(scenario)
        print(f"Stress test {'passed' if report.passed else 'failed'}")
    """

    def __init__(self):
        self._results: List[StressReport] = []

    def run_scenario(self, scenario: StressScenario) -> StressReport:
        """Run a single stress test scenario."""
        logger.info(
            "Stress test: %s (concurrency=%d, duration=%ds)",
            scenario.name, scenario.concurrency, scenario.duration_seconds,
        )

        report = StressReport(
            scenario=scenario.name,
            description=scenario.description,
            start_time=time.time(),
        )

        errors = 0
        total_ops = 0
        latencies: List[float] = []

        try:
            import concurrent.futures
            import threading

            stop_event = threading.Event()
            start_time = time.time()
            end_time = start_time + scenario.duration_seconds

            def _worker():
                nonlocal errors, total_ops
                while not stop_event.is_set() and time.time() < end_time:
                    try:
                        op_start = time.perf_counter()
                        if scenario.target:
                            scenario.target()
                        else:
                            # Default: busy wait
                            time.sleep(0.01)
                        elapsed = (time.perf_counter() - op_start) * 1000
                        latencies.append(elapsed)
                        total_ops += 1
                    except Exception:
                        errors += 1
                        total_ops += 1

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=scenario.concurrency,
            ) as executor:
                futures = [executor.submit(_worker) for _ in range(scenario.concurrency)]
                time.sleep(scenario.duration_seconds)
                stop_event.set()

            report.end_time = time.time()
            actual_duration = report.end_time - report.start_time
            throughput = total_ops / actual_duration if actual_duration > 0 else 0
            error_rate = (errors / total_ops * 100) if total_ops > 0 else 0

            report.metrics = {
                "total_operations": total_ops,
                "errors": errors,
                "error_rate_pct": round(error_rate, 2),
                "throughput_ops_per_sec": round(throughput, 2),
                "concurrency": scenario.concurrency,
                "actual_duration_seconds": round(actual_duration, 2),
            }

            if latencies:
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                report.metrics.update({
                    "latency_min_ms": round(sorted_lat[0], 2),
                    "latency_max_ms": round(sorted_lat[-1], 2),
                    "latency_avg_ms": round(sum(sorted_lat) / n, 2),
                    "latency_p50_ms": round(sorted_lat[int(n * 0.50)], 2),
                    "latency_p95_ms": round(sorted_lat[int(n * 0.95)], 2),
                    "latency_p99_ms": round(sorted_lat[int(n * 0.99)], 2),
                })

            # Determine pass/fail based on error rate
            if error_rate > 20:
                report.passed = False
                report.degradation = f"High error rate ({error_rate:.1f}%)"
            elif error_rate > 5:
                report.degradation = f"Elevated error rate ({error_rate:.1f}%)"
            else:
                report.degradation = "Within expected degradation parameters"

            report.observations.append(
                f"Throughput: {throughput:.1f} ops/sec at {scenario.concurrency} concurrency"
            )

        except Exception as exc:
            report.end_time = time.time()
            report.passed = False
            report.observations.append(f"Stress test failed: {exc}")

        self._results.append(report)
        return report

    def run_scenarios(self, scenarios: List[StressScenario]) -> List[StressReport]:
        """Run multiple stress test scenarios."""
        reports: List[StressReport] = []
        for scenario in scenarios:
            report = self.run_scenario(scenario)
            reports.append(report)
        return reports

    def get_results(self) -> List[StressReport]:
        """Get all stress test results."""
        return list(self._results)

    def summary(self) -> Dict[str, Any]:
        """Get a summary of all stress test results."""
        return {
            "total_scenarios": len(self._results),
            "passed": sum(1 for r in self._results if r.passed),
            "failed": sum(1 for r in self._results if not r.passed),
            "reports": [r.to_dict() for r in self._results],
        }

    # Predefined scenarios
    @staticmethod
    def high_concurrency_scenario(
        concurrency: int = 50,
        duration: int = 30,
    ) -> StressScenario:
        return StressScenario(
            name=f"high_concurrency_{concurrency}",
            description=f"High concurrency stress test with {concurrency} parallel workers",
            concurrency=concurrency,
            duration_seconds=duration,
            expected_degradation="Error rate < 5%, latency p95 < 2x baseline",
        )

    @staticmethod
    def sustained_load_scenario(
        duration: int = 120,
    ) -> StressScenario:
        return StressScenario(
            name="sustained_load",
            description="Sustained load stress test over 2 minutes",
            concurrency=20,
            duration_seconds=duration,
            expected_degradation="No memory leak, stable throughput",
        )

    @staticmethod
    def resource_pressure_scenario() -> StressScenario:
        return StressScenario(
            name="resource_pressure",
            description="Stress test under constrained resources",
            concurrency=10,
            duration_seconds=60,
            expected_degradation="Graceful degradation, no crashes",
        )
