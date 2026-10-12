from __future__ import annotations

import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class Span:
    name: str
    start_time: float
    end_time: float | None = None
    attributes: dict = field(default_factory=dict)
    parent_id: str | None = None
    span_id: str = ""
    trace_id: str = ""
    status: str = "ok"
    error: str = ""


class Tracer:
    def __init__(self):
        self._spans: list[Span] = []
        self._max_spans = 10000

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Generator[Span, None, None]:
        span = Span(
            name=name,
            start_time=time.time(),
            span_id=str(uuid.uuid4())[:8],
            trace_id=str(uuid.uuid4())[:8],
            attributes=attrs,
        )
        try:
            yield span
            span.status = "ok"
        except Exception as e:
            span.status = "error"
            span.error = str(e)
            raise
        finally:
            span.end_time = time.time()
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans.pop(0)

    def get_spans(self, limit: int = 100) -> list[dict]:
        return [
            {
                "name": s.name,
                "duration": (s.end_time or time.time()) - s.start_time,
                "status": s.status,
                "error": s.error,
                "attrs": s.attributes,
            }
            for s in self._spans[-limit:]
        ]

    def clear(self):
        self._spans.clear()


_TRACER = Tracer()


def get_tracer() -> Tracer:
    return _TRACER


@dataclass
class Metric:
    name: str
    value: float
    tags: dict = field(default_factory=dict)
    timestamp: float = 0.0


class MetricsRegistry:
    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, amount: float = 1.0, tags: dict | None = None):
        self._counters[name] += amount

    def gauge(self, name: str, value: float):
        self._gauges[name] = value

    def observe(self, name: str, value: float):
        self._histograms[name].append(value)
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-500:]

    def snapshot(self) -> dict:
        hists = {}
        for k, v in self._histograms.items():
            hists[k] = {"min": min(v), "max": max(v), "avg": sum(v) / len(v), "count": len(v)} if v else {}
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": hists,
        }

    def clear(self):
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


_METRICS = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    return _METRICS
