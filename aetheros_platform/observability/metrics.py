"""Metrics — counters, gauges, histograms with label support."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    name: str
    help_text: str
    type: str
    labels: dict = field(default_factory=dict)


class CounterMetric(Metric):
    def __init__(self, name: str, help_text: str = "",
                 labels: dict = None):
        super().__init__(name=name, help_text=help_text, type="counter",
                         labels=labels or {})
        self._value: float = 0.0

    def inc(self, value: float = 1.0):
        self._value += value

    def get(self) -> float:
        return self._value


class GaugeMetric(Metric):
    def __init__(self, name: str, help_text: str = "",
                 labels: dict = None):
        super().__init__(name=name, help_text=help_text, type="gauge",
                         labels=labels or {})
        self._value: float = 0.0

    def set(self, value: float):
        self._value = value

    def inc(self, value: float = 1.0):
        self._value += value

    def dec(self, value: float = 1.0):
        self._value -= value

    def get(self) -> float:
        return self._value


class HistogramMetric(Metric):
    def __init__(self, name: str, help_text: str = "",
                 buckets: list[float] = None,
                 labels: dict = None):
        super().__init__(name=name, help_text=help_text, type="histogram",
                         labels=labels or {})
        self.buckets = sorted(buckets or [
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
        ])
        self._counts: dict[str, int] = {str(b): 0 for b in self.buckets}
        self._counts["+Inf"] = 0
        self._sum: float = 0.0
        self._count: int = 0

    def observe(self, value: float):
        self._sum += value
        self._count += 1
        for b in self.buckets:
            if value <= b:
                self._counts[str(b)] += 1
        self._counts["+Inf"] += 1

    def get(self) -> dict:
        return {
            "count": self._count,
            "sum": self._sum,
            "buckets": {str(k): v for k, v in self._counts.items()},
        }


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: dict[str, Metric] = {}
        self._default_labels: dict[str, str] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.add_metric(CounterMetric("requests_total", "Total requests"))
        self.add_metric(CounterMetric("errors_total", "Total errors"))
        self.add_metric(GaugeMetric("memory_usage_bytes", "Memory usage"))
        self.add_metric(GaugeMetric("cpu_usage_percent", "CPU usage"))
        self.add_metric(GaugeMetric("active_sessions", "Active sessions"))
        self.add_metric(
            HistogramMetric("request_duration_seconds", "Request duration"))

    def add_metric(self, metric: Metric):
        with self._lock:
            self._metrics[metric.name] = metric

    def get_metric(self, name: str) -> Optional[Metric]:
        with self._lock:
            return self._metrics.get(name)

    def counter(self, name: str) -> Optional[CounterMetric]:
        m = self.get_metric(name)
        if isinstance(m, CounterMetric):
            return m
        return None

    def gauge(self, name: str) -> Optional[GaugeMetric]:
        m = self.get_metric(name)
        if isinstance(m, GaugeMetric):
            return m
        return None

    def histogram(self, name: str) -> Optional[HistogramMetric]:
        m = self.get_metric(name)
        if isinstance(m, HistogramMetric):
            return m
        return None

    def inc(self, name: str, value: float = 1.0):
        m = self.get_metric(name)
        if isinstance(m, (CounterMetric, GaugeMetric)):
            m.inc(value)

    def gauge_set(self, name: str, value: float):
        m = self.get_metric(name)
        if isinstance(m, GaugeMetric):
            m.set(value)

    def observe(self, name: str, value: float):
        m = self.get_metric(name)
        if isinstance(m, HistogramMetric):
            m.observe(value)

    def snapshot(self) -> dict:
        with self._lock:
            result = {}
            for name, metric in self._metrics.items():
                if isinstance(metric, CounterMetric):
                    result[name] = {"type": "counter", "value": metric.get()}
                elif isinstance(metric, GaugeMetric):
                    result[name] = {"type": "gauge", "value": metric.get()}
                elif isinstance(metric, HistogramMetric):
                    result[name] = {"type": "histogram", **metric.get()}
            return result

    def export_prometheus(self) -> str:
        lines = []
        with self._lock:
            for name, metric in self._metrics.items():
                help_escaped = metric.help_text.replace('"', '\\"')
                lines.append(f"# HELP {name} {help_escaped}")
                lines.append(f"# TYPE {name} {metric.type}")
                if isinstance(metric, CounterMetric):
                    lines.append(f"{name} {metric.get()}")
                elif isinstance(metric, GaugeMetric):
                    lines.append(f"{name} {metric.get()}")
                elif isinstance(metric, HistogramMetric):
                    d = metric.get()
                    for bucket, count in d["buckets"].items():
                        lines.append(
                            f'{name}_bucket{{le="{bucket}"}} {count}')
                    lines.append(f"{name}_count {d['count']}")
                    lines.append(f"{name}_sum {d['sum']}")
        return "\n".join(lines)

    def close(self):
        self._metrics.clear()
