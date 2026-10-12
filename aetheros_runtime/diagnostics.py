"""Diagnostics — runtime logs, performance, memory usage, provider latency, tool latency, crash reports.

Comprehensive runtime telemetry and monitoring.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.diagnostics")


@dataclass
class MetricSnapshot:
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0
    open_fds: int = 0
    provider_latency_ms: Dict[str, float] = field(default_factory=dict)
    tool_latency_ms: Dict[str, float] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "thread_count": self.thread_count,
            "open_fds": self.open_fds,
            "provider_latency_ms": self.provider_latency_ms,
            "tool_latency_ms": self.tool_latency_ms,
            "custom_metrics": self.custom_metrics,
        }


MetricProvider = Callable[[], Dict[str, Any]]


class Diagnostics:
    """Runtime diagnostics and telemetry.

    Tracks:
    - CPU and memory usage
    - Thread count and file descriptors
    - Per-provider latency
    - Per-tool latency
    - Crash reports
    - Custom metrics
    """

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._log_dir = log_dir
        self._snapshots: List[MetricSnapshot] = []
        self._max_snapshots: int = 1000
        self._provider_latency: Dict[str, List[float]] = {}
        self._tool_latency: Dict[str, List[float]] = {}
        self._crash_reports: List[Dict[str, Any]] = []
        self._metric_providers: Dict[str, MetricProvider] = {}
        self._collect_interval: float = 60.0
        self._collect_thread: Optional[threading.Thread] = None
        self._collect_stop = threading.Event()
        self._log_file: Optional[Path] = None

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = log_dir / "runtime.log"
            self._setup_file_logging()

    # ------------------------------------------------------------------
    # Metric collection
    # ------------------------------------------------------------------

    def collect(self) -> MetricSnapshot:
        snapshot = MetricSnapshot()
        try:
            import psutil
            process = psutil.Process()
            snapshot.cpu_percent = process.cpu_percent(interval=0.1)
            snapshot.memory_mb = process.memory_info().rss / (1024 * 1024)
            snapshot.thread_count = process.num_threads()
        except ImportError:
            pass
        except Exception:
            pass

        with self._lock:
            snapshot.provider_latency_ms = {
                p: (sum(l) / len(l) if l else 0.0) for p, l in self._provider_latency.items()
            }
            snapshot.tool_latency_ms = {
                t: (sum(l) / len(l) if l else 0.0) for t, l in self._tool_latency.items()
            }
            for name, provider in self._metric_providers.items():
                try:
                    snapshot.custom_metrics[name] = provider()
                except Exception:
                    pass

        with self._lock:
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)

        return snapshot

    def start_auto_collect(self, interval: Optional[float] = None) -> None:
        if interval:
            self._collect_interval = interval
        if self._collect_thread and self._collect_thread.is_alive():
            return
        self._collect_stop.clear()
        self._collect_thread = threading.Thread(
            target=self._collect_loop, daemon=True,
            name="diagnostics-collector",
        )
        self._collect_thread.start()

    def stop_auto_collect(self) -> None:
        self._collect_stop.set()
        if self._collect_thread:
            self._collect_thread.join(timeout=5)

    def _collect_loop(self) -> None:
        while not self._collect_stop.is_set():
            self.collect()
            self._collect_stop.wait(self._collect_interval)

    # ------------------------------------------------------------------
    # Latency tracking
    # ------------------------------------------------------------------

    def record_provider_latency(self, provider: str, latency_ms: float) -> None:
        with self._lock:
            if provider not in self._provider_latency:
                self._provider_latency[provider] = []
            self._provider_latency[provider].append(latency_ms)
            if len(self._provider_latency[provider]) > 100:
                self._provider_latency[provider].pop(0)

    def record_tool_latency(self, tool: str, latency_ms: float) -> None:
        with self._lock:
            if tool not in self._tool_latency:
                self._tool_latency[tool] = []
            self._tool_latency[tool].append(latency_ms)
            if len(self._tool_latency[tool]) > 100:
                self._tool_latency[tool].pop(0)

    def get_provider_stats(self, provider: str) -> Dict[str, float]:
        with self._lock:
            latencies = self._provider_latency.get(provider, [])
            if not latencies:
                return {"avg": 0, "min": 0, "max": 0, "count": 0}
            return {
                "avg": sum(latencies) / len(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "count": len(latencies),
            }

    def get_tool_stats(self, tool: str) -> Dict[str, float]:
        with self._lock:
            latencies = self._tool_latency.get(tool, [])
            if not latencies:
                return {"avg": 0, "min": 0, "max": 0, "count": 0}
            return {
                "avg": sum(latencies) / len(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "count": len(latencies),
            }

    # ------------------------------------------------------------------
    # Crash reports
    # ------------------------------------------------------------------

    def report_crash(self, component: str, error: str, traceback: str = "") -> Dict[str, Any]:
        report = {
            "component": component,
            "error": error,
            "traceback": traceback,
            "timestamp": time.time(),
            "snapshot": self.collect().to_dict(),
        }
        with self._lock:
            self._crash_reports.append(report)
        logger.error("Crash reported: %s: %s", component, error)
        return report

    def get_crash_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._crash_reports[-limit:])

    def clear_crash_reports(self) -> None:
        with self._lock:
            self._crash_reports.clear()

    # ------------------------------------------------------------------
    # Custom metrics
    # ------------------------------------------------------------------

    def register_metric_provider(self, name: str, provider: MetricProvider) -> None:
        with self._lock:
            self._metric_providers[name] = provider

    # ------------------------------------------------------------------
    # Performance summary
    # ------------------------------------------------------------------

    def get_latest_snapshot(self) -> Optional[MetricSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def get_snapshot_history(self, limit: int = 10) -> List[MetricSnapshot]:
        with self._lock:
            return list(self._snapshots[-limit:])

    def get_performance_summary(self) -> Dict[str, Any]:
        latest = self.get_latest_snapshot()
        with self._lock:
            return {
                "current": latest.to_dict() if latest else {},
                "provider_latency": {
                    p: self.get_provider_stats(p) for p in list(self._provider_latency.keys())
                },
                "tool_latency": {
                    t: self.get_tool_stats(t) for t in list(self._tool_latency.keys())
                },
                "crash_count": len(self._crash_reports),
                "snapshot_count": len(self._snapshots),
            }

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _setup_file_logging(self) -> None:
        if not self._log_file:
            return
        try:
            handler = logging.FileHandler(str(self._log_file), encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            handler.setFormatter(formatter)
            logging.getLogger("aetheros_runtime").addHandler(handler)
        except Exception as exc:
            logger.warning("Failed to setup file logging: %s", exc)

    def get_log_content(self, max_lines: int = 100) -> str:
        if not self._log_file or not self._log_file.exists():
            return ""
        try:
            lines = self._log_file.read_text(encoding="utf-8").split("\n")
            return "\n".join(lines[-max_lines:])
        except Exception:
            return ""

    def summary(self) -> str:
        s = self.get_performance_summary()
        return (
            f"Diagnostics: {s['snapshot_count']} snapshots, "
            f"{len(s['provider_latency'])} providers tracked, "
            f"{len(s['tool_latency'])} tools tracked, "
            f"{s['crash_count']} crashes"
        )