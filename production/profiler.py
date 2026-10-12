"""
Built-in Profiling Tools
========================

Provides profiling capabilities for:
- CPU usage (sampling and instrumentation)
- Memory allocation (heap and per-call)
- I/O operations (read/write patterns)
- Workflow bottlenecks
- Agent utilization
- Scheduler efficiency

Profiles can be exported as structured reports for analysis.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


class ProfileType(Enum):
    """Types of profiling that can be performed."""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    WORKFLOW = "workflow"
    AGENT = "agent"
    SCHEDULER = "scheduler"
    FULL = "full"


@dataclass
class ProfileSample:
    """A single profiling data point."""
    timestamp: float = field(default_factory=time.time)
    value: float = 0.0
    label: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileResult:
    """Result of a profiling session.

    Attributes:
        profile_type: Type of profiling performed
        duration_seconds: How long the profiling ran
        samples: Collected data samples
        summary: Statistical summary of the profile
        bottlenecks: Identified bottlenecks
        recommendations: Optimization recommendations
    """
    profile_type: ProfileType
    duration_seconds: float = 0.0
    samples: List[ProfileSample] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ProfileReport:
    """A comprehensive profiling report."""
    profiler: str = ""
    results: List[ProfileResult] = field(default_factory=list)
    total_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: ProfileResult) -> None:
        self.results.append(result)
        self.total_duration += result.duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profiler": self.profiler,
            "total_duration_seconds": self.total_duration,
            "result_count": len(self.results),
            "results": [
                {
                    "type": r.profile_type.value,
                    "duration": r.duration_seconds,
                    "summary": r.summary,
                    "bottlenecks": r.bottlenecks,
                }
                for r in self.results
            ],
        }


class CpuProfiler:
    """CPU usage profiler using sampling methodology."""

    def __init__(self, sampling_interval: float = 0.1):
        self._interval = sampling_interval
        self._samples: List[ProfileSample] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start CPU profiling."""
        self._samples.clear()
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> ProfileResult:
        """Stop CPU profiling and return results."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

        if not self._samples:
            return ProfileResult(
                profile_type=ProfileType.CPU,
                duration_seconds=0.0,
                summary={"message": "No CPU samples collected"},
            )

        values = [s.value for s in self._samples]
        duration = self._samples[-1].timestamp - self._samples[0].timestamp

        return ProfileResult(
            profile_type=ProfileType.CPU,
            duration_seconds=duration,
            samples=list(self._samples),
            summary={
                "samples": len(self._samples),
                "min_cpu": min(values),
                "max_cpu": max(values),
                "avg_cpu": sum(values) / len(values),
                "median_cpu": sorted(values)[len(values) // 2],
            },
            bottlenecks=self._find_bottlenecks(values),
        )

    def _sample_loop(self) -> None:
        """Background sampling loop."""
        try:
            import psutil
            process = psutil.Process()
            while self._running:
                try:
                    cpu = process.cpu_percent(interval=0)
                    self._samples.append(ProfileSample(
                        value=cpu,
                        label="cpu_percent",
                    ))
                except Exception:
                    pass
                time.sleep(self._interval)
        except ImportError:
            self._samples.append(ProfileSample(
                value=0.0,
                label="psutil_not_available",
                details={"message": "Install psutil for CPU profiling"},
            ))

    def _find_bottlenecks(self, values: List[float]) -> List[Dict[str, Any]]:
        """Identify CPU bottlenecks from samples."""
        bottlenecks: List[Dict[str, Any]] = []
        avg_cpu = sum(values) / len(values) if values else 0

        if avg_cpu > 80:
            bottlenecks.append({
                "severity": "critical",
                "message": f"Average CPU usage is {avg_cpu:.1f}% — system may be CPU-bound",
                "suggestion": "Consider reducing concurrent operations or scaling horizontally",
            })
        elif avg_cpu > 50:
            bottlenecks.append({
                "severity": "warning",
                "message": f"Average CPU usage is {avg_cpu:.1f}% — monitor for bottlenecks",
                "suggestion": "Review running workflows and agent concurrency",
            })

        return bottlenecks


class MemoryProfiler:
    """Memory allocation profiler."""

    def __init__(self):
        self._snapshots: List[ProfileSample] = []
        self._tracked_objects: Dict[str, int] = {}

    @contextmanager
    def track(self, label: str) -> Iterator[None]:
        """Context manager to track memory in a code block."""
        before = self._get_memory_usage()
        yield
        after = self._get_memory_usage()
        delta = after - before
        self._snapshots.append(ProfileSample(
            value=delta,
            label=label,
            details={"before_mb": before, "after_mb": after, "delta_mb": delta},
        ))

    def snapshot(self, label: str = "") -> ProfileSample:
        """Take a memory snapshot."""
        usage = self._get_memory_usage()
        sample = ProfileSample(value=usage, label=label or "snapshot")
        self._snapshots.append(sample)
        return sample

    def result(self) -> ProfileResult:
        """Get profiling results."""
        if not self._snapshots:
            return ProfileResult(
                profile_type=ProfileType.MEMORY,
                duration_seconds=0.0,
            )

        values = [s.value for s in self._snapshots]
        duration = self._snapshots[-1].timestamp - self._snapshots[0].timestamp

        return ProfileResult(
            profile_type=ProfileType.MEMORY,
            duration_seconds=duration,
            samples=list(self._snapshots),
            summary={
                "snapshots": len(self._snapshots),
                "min_mb": min(values),
                "max_mb": max(values),
                "current_mb": values[-1] if values else 0,
                "total_allocated_mb": sum(max(v, 0) for v in values),
            },
            recommendations=self._generate_recommendations(values),
        )

    def _get_memory_usage(self) -> float:
        """Get current RSS memory in MB."""
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0

    def _generate_recommendations(self, values: List[float]) -> List[str]:
        """Generate recommendations based on memory profile."""
        recs: List[str] = []
        if values and max(values) > 500:
            recs.append("High memory usage detected — consider reducing session history cache")
        if values and len(values) > 100:
            recs.append("Frequent memory allocations detected — review object lifecycle")
        return recs


class IoProfiler:
    """I/O operations profiler."""

    def __init__(self):
        self._io_samples: List[ProfileSample] = []
        self._start_io_counters: Optional[Dict[str, int]] = None

    def start(self) -> None:
        """Start I/O profiling."""
        self._io_samples.clear()
        self._start_io_counters = self._get_io_counters()

    def stop(self) -> ProfileResult:
        """Stop I/O profiling and return results."""
        end_counters = self._get_io_counters()
        if not self._start_io_counters or not end_counters:
            return ProfileResult(
                profile_type=ProfileType.IO,
                duration_seconds=0.0,
                summary={"message": "I/O counters not available (install psutil)"},
            )

        read_bytes = end_counters.get("read_bytes", 0) - self._start_io_counters.get("read_bytes", 0)
        write_bytes = end_counters.get("write_bytes", 0) - self._start_io_counters.get("write_bytes", 0)
        read_count = end_counters.get("read_count", 0) - self._start_io_counters.get("read_count", 0)
        write_count = end_counters.get("write_count", 0) - self._start_io_counters.get("write_count", 0)

        return ProfileResult(
            profile_type=ProfileType.IO,
            samples=self._io_samples,
            summary={
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "read_count": read_count,
                "write_count": write_count,
                "total_io_mb": (read_bytes + write_bytes) / (1024 * 1024),
            },
            recommendations=self._generate_io_recommendations(read_bytes, write_bytes),
        )

    def _get_io_counters(self) -> Optional[Dict[str, int]]:
        """Get current I/O counters."""
        try:
            import psutil
            io = psutil.Process().io_counters()
            return {
                "read_bytes": io.read_bytes,
                "write_bytes": io.write_bytes,
                "read_count": io.read_count,
                "write_count": io.write_count,
            }
        except (ImportError, AttributeError):
            return None

    def _generate_io_recommendations(self, read_bytes: int, write_bytes: int) -> List[str]:
        """Generate I/O recommendations."""
        recs: List[str] = []
        total_mb = (read_bytes + write_bytes) / (1024 * 1024)
        if total_mb > 100:
            recs.append(f"High I/O volume ({total_mb:.0f} MB) — consider reducing log verbosity")
        if write_bytes > 50 * 1024 * 1024:
            recs.append("High write volume — review state persistence interval")
        return recs


class Profiler:
    """Unified profiler that orchestrates CPU, memory, and I/O profiling."""

    def __init__(self):
        self.cpu = CpuProfiler()
        self.memory = MemoryProfiler()
        self.io = IoProfiler()
        self._reports: List[ProfileReport] = []

    def profile_cpu(self, duration: float = 5.0) -> ProfileResult:
        """Profile CPU usage for a specified duration."""
        self.cpu.start()
        time.sleep(duration)
        return self.cpu.stop()

    def profile_memory(self, fn: Optional[Callable] = None) -> ProfileResult:
        """Profile memory usage. Optionally profile a specific function."""
        if fn:
            with self.memory.track(fn.__name__):
                fn()
        else:
            self.memory.snapshot("baseline")
        return self.memory.result()

    def profile_io(self, duration: float = 5.0) -> ProfileResult:
        """Profile I/O operations for a specified duration."""
        self.io.start()
        time.sleep(duration)
        return self.io.stop()

    def profile_all(self, duration: float = 5.0) -> ProfileReport:
        """Run all profilers and return a combined report."""
        report = ProfileReport(profiler="production.profiler")

        cpu_result = self.profile_cpu(duration)
        report.add_result(cpu_result)

        memory_result = self.profile_memory()
        report.add_result(memory_result)

        io_result = self.profile_io(duration)
        report.add_result(io_result)

        self._reports.append(report)
        return report

    def get_reports(self) -> List[ProfileReport]:
        """Get all profiling reports generated so far."""
        return list(self._reports)

    def reset(self) -> None:
        """Reset all profilers and clear reports."""
        self.cpu = CpuProfiler()
        self.memory = MemoryProfiler()
        self.io = IoProfiler()
        self._reports.clear()
