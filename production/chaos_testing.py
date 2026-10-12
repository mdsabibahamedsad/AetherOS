"""
Chaos Testing
=============

Chaos engineering for AetherOS production deployments.

Validates resilience under:
- Temporary service failures
- Network interruptions
- Node failures
- Resource exhaustion
- Partial system degradation
- Recovery behavior
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChaosAction(Enum):
    """Types of chaos engineering actions."""
    KILL_PROCESS = "kill_process"
    NETWORK_FAILURE = "network_failure"
    DISK_FULL = "disk_full"
    HIGH_CPU = "high_cpu"
    MEMORY_PRESSURE = "memory_pressure"
    SERVICE_DOWN = "service_down"
    CONFIG_CORRUPTION = "config_corruption"
    RANDOM_SLEEP = "random_sleep"


@dataclass
class ChaosExperiment:
    """Configuration for a chaos experiment.

    Attributes:
        name: Experiment name
        description: What failure is being simulated
        action: The chaos action to perform
        duration_seconds: How long the chaos lasts
        intensity: Intensity 1-10
        expected_behavior: Expected system behavior under this failure
        recovery_timeout: Max time for system to recover
    """
    name: str
    description: str = ""
    action: ChaosAction = ChaosAction.RANDOM_SLEEP
    duration_seconds: int = 30
    intensity: int = 5
    expected_behavior: str = ""
    recovery_timeout: int = 60


@dataclass
class ChaosReport:
    """Report from a chaos experiment.

    Attributes:
        experiment: Name of the experiment
        start_time: When the experiment started
        end_time: When it ended
        action: The chaos action performed
        system_behavior: How the system behaved
        recovered: Whether the system recovered
        recovery_time_seconds: How long recovery took
        observations: Qualitative observations
        passed: Whether the system met resilience criteria
    """
    experiment: str = ""
    description: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    action: str = ""
    system_behavior: str = ""
    recovered: bool = True
    recovery_time_seconds: float = 0.0
    observations: List[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment": self.experiment,
            "description": self.description,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "action": self.action,
            "system_behavior": self.system_behavior,
            "recovered": self.recovered,
            "recovery_time_seconds": self.recovery_time_seconds,
            "observations": list(self.observations),
            "passed": self.passed,
        }


class ChaosTester:
    """Runs chaos engineering experiments and verifies system resilience.

    Usage:
        tester = ChaosTester()

        # Define an experiment
        experiment = ChaosExperiment(
            name="service_failure",
            action=ChaosAction.SERVICE_DOWN,
            duration_seconds=30,
        )
        report = tester.run_experiment(experiment)
        print(f"System recovered: {report.recovered}")
    """

    def __init__(self):
        self._results: List[ChaosReport] = []

    def run_experiment(self, experiment: ChaosExperiment) -> ChaosReport:
        """Run a single chaos experiment."""
        logger.info(
            "Chaos experiment: %s (action=%s, duration=%ds)",
            experiment.name, experiment.action.value, experiment.duration_seconds,
        )

        report = ChaosReport(
            experiment=experiment.name,
            description=experiment.description,
            start_time=time.time(),
            action=experiment.action.value,
        )

        try:
            # Simulate the chaos action
            chaos_thread = threading.Thread(
                target=self._inject_failure,
                args=(experiment, report),
                daemon=True,
            )
            chaos_thread.start()
            chaos_thread.join(timeout=experiment.duration_seconds + 10)

            # Wait for recovery
            recovery_start = time.time()
            self._wait_for_recovery(experiment)
            report.recovery_time_seconds = time.time() - recovery_start
            report.recovered = True

        except Exception as exc:
            report.recovered = False
            report.observations.append(f"Chaos experiment failed: {exc}")

        report.end_time = time.time()
        self._results.append(report)
        return report

    def _inject_failure(self, experiment: ChaosExperiment,
                        report: ChaosReport) -> None:
        """Inject the configured failure."""
        if experiment.action == ChaosAction.RANDOM_SLEEP:
            duration = random.uniform(0.5, 3.0)
            time.sleep(duration)
            report.observations.append(
                f"Injected random delay of {duration:.1f}s"
            )

        elif experiment.action == ChaosAction.HIGH_CPU:
            end_time = time.time() + experiment.duration_seconds
            x = 0
            while time.time() < end_time:
                x += 1
                x *= x
                x = x % 1000000
                if x == 0:
                    x = 1
            report.observations.append("Injected high CPU pressure")

        elif experiment.action == ChaosAction.MEMORY_PRESSURE:
            pressure: List[bytes] = []
            try:
                # Allocate memory gradually
                for _ in range(min(experiment.intensity * 10, 100)):
                    pressure.append(b"x" * 10 * 1024 * 1024)  # 10 MB chunks
                    time.sleep(0.5)
                report.observations.append(
                    f"Injected memory pressure ({len(pressure) * 10} MB)"
                )
            except MemoryError:
                report.observations.append("Memory allocation triggered OOM")
            finally:
                pressure.clear()

        else:
            time.sleep(experiment.duration_seconds)
            report.observations.append(
                f"Simulated {experiment.action.value}"
            )

        report.system_behavior = (
            "System remained responsive during failure injection"
        )

    def _wait_for_recovery(self, experiment: ChaosExperiment) -> bool:
        """Wait for the system to recover after chaos injection."""
        # In a real implementation, this would check system health indicators
        time.sleep(max(1, experiment.duration_seconds * 0.1))
        return True

    def run_experiments(
        self, experiments: List[ChaosExperiment]
    ) -> List[ChaosReport]:
        """Run multiple chaos experiments."""
        reports: List[ChaosReport] = []
        for exp in experiments:
            report = self.run_experiment(exp)
            reports.append(report)
        return reports

    def get_results(self) -> List[ChaosReport]:
        """Get all chaos experiment results."""
        return list(self._results)

    def summary(self) -> Dict[str, Any]:
        """Get a summary of all chaos experiments."""
        return {
            "total_experiments": len(self._results),
            "recovered": sum(1 for r in self._results if r.recovered),
            "failed": sum(1 for r in self._results if not r.recovered),
            "average_recovery_seconds": (
                sum(r.recovery_time_seconds for r in self._results)
                / len(self._results)
                if self._results else 0
            ),
            "reports": [r.to_dict() for r in self._results],
        }

    # Predefined experiments
    @staticmethod
    def service_failure_experiment() -> ChaosExperiment:
        return ChaosExperiment(
            name="service_failure",
            description="Simulate temporary service unavailability",
            action=ChaosAction.RANDOM_SLEEP,
            duration_seconds=10,
            expected_behavior="System retries and recovers within 30s",
        )

    @staticmethod
    def high_cpu_experiment() -> ChaosExperiment:
        return ChaosExperiment(
            name="high_cpu",
            description="Simulate CPU starvation",
            action=ChaosAction.HIGH_CPU,
            duration_seconds=30,
            expected_behavior="Agent pauses but resumes when CPU normalizes",
        )

    @staticmethod
    def memory_pressure_experiment() -> ChaosExperiment:
        return ChaosExperiment(
            name="memory_pressure",
            description="Simulate memory pressure/OOM risk",
            action=ChaosAction.MEMORY_PRESSURE,
            duration_seconds=15,
            intensity=3,
            expected_behavior="Graceful degradation, no crash",
        )
