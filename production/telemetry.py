"""
Telemetry Pipeline
==================

Structured telemetry pipeline for AetherOS production deployments.

Provides:
- Event collection and routing
- Structured telemetry events
- Multiple exporter backends
- Configurable sampling and batching
- Integration with existing kernel telemetry
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TelemetryEventType(Enum):
    """Types of telemetry events."""
    AGENT_ACTION = "agent.action"
    TOOL_CALL = "tool.call"
    MODEL_REQUEST = "model.request"
    ERROR = "error"
    PERFORMANCE = "performance"
    LIFECYCLE = "lifecycle"
    CUSTOM = "custom"


@dataclass
class TelemetryEvent:
    """A structured telemetry event.

    Attributes:
        event_type: Type of event
        name: Event name
        value: Numeric value (if applicable)
        unit: Unit of measurement
        tags: Tag dictionary for dimensionality
        timestamp: When the event occurred
        source: Source component
        metadata: Additional metadata
    """
    event_type: TelemetryEventType
    name: str
    value: float = 0.0
    unit: str = "count"
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "aetheros"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }


class TelemetryExporter:
    """Base class for telemetry exporters.

    Subclasses implement the export() method to send events
    to different backends (console, file, HTTP, etc.).
    """

    def export(self, event: TelemetryEvent) -> None:
        """Export a single telemetry event."""
        raise NotImplementedError

    def export_batch(self, events: List[TelemetryEvent]) -> None:
        """Export a batch of telemetry events."""
        for event in events:
            self.export(event)

    def flush(self) -> None:
        """Flush any buffered events."""
        pass

    def close(self) -> None:
        """Clean up exporter resources."""
        pass


class ConsoleExporter(TelemetryExporter):
    """Export telemetry to console stdout."""

    def export(self, event: TelemetryEvent) -> None:
        logger.debug("[TELEMETRY] %s: %s = %s %s",
                     event.event_type.value, event.name, event.value, event.unit)


class FileExporter(TelemetryExporter):
    """Export telemetry to a JSONL file."""

    def __init__(self, path: str):
        self._path = path
        self._file: Optional[Any] = None
        self._lock = threading.Lock()

    def export(self, event: TelemetryEvent) -> None:
        with self._lock:
            if self._file is None:
                import os
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                self._file = open(self._path, "a", encoding="utf-8")
            self._file.write(json.dumps(event.to_dict()) + "\n")
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class TelemetryPipeline:
    """Main telemetry pipeline — collects, processes, and exports events.

    Usage:
        pipeline = TelemetryPipeline()
        pipeline.add_exporter(ConsoleExporter())

        # Record an event
        pipeline.record(
            TelemetryEventType.TOOL_CALL,
            "web_search.execution",
            value=1.5,
            unit="seconds",
            tags={"tool": "web_search", "result": "success"},
        )

        pipeline.close()
    """

    def __init__(self, buffer_size: int = 100):
        self._exporters: List[TelemetryExporter] = []
        self._buffer: List[TelemetryEvent] = []
        self._buffer_size = buffer_size
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_events = 0

    def add_exporter(self, exporter: TelemetryExporter) -> None:
        """Register a telemetry exporter."""
        self._exporters.append(exporter)

    def remove_exporter(self, exporter: TelemetryExporter) -> bool:
        try:
            self._exporters.remove(exporter)
            return True
        except ValueError:
            return False

    def record(
        self,
        event_type: TelemetryEventType,
        name: str,
        value: float = 0.0,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None,
        source: str = "aetheros",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEvent:
        """Record a telemetry event."""
        event = TelemetryEvent(
            event_type=event_type,
            name=name,
            value=value,
            unit=unit,
            tags=tags or {},
            source=source,
            metadata=metadata or {},
        )

        with self._lock:
            self._buffer.append(event)
            self._total_events += 1

            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()

        return event

    def flush(self) -> None:
        """Flush the event buffer to all exporters."""
        self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Internal buffer flush."""
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()

        for exporter in self._exporters:
            try:
                exporter.export_batch(batch)
            except Exception as exc:
                logger.warning("Telemetry exporter failed: %s", exc)

    def close(self) -> None:
        """Flush remaining events and close all exporters."""
        self.flush()
        for exporter in self._exporters:
            try:
                exporter.close()
            except Exception:
                pass
        self._exporters.clear()

    @property
    def total_events(self) -> int:
        return self._total_events

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def stats(self) -> Dict[str, Any]:
        return {
            "total_events": self._total_events,
            "buffered_events": len(self._buffer),
            "exporter_count": len(self._exporters),
            "uptime_seconds": self.uptime_seconds,
        }

    # ------------------------------------------------------------------
    # Integration with existing kernel telemetry
    # ------------------------------------------------------------------

    def integrate_with_kernel(self) -> None:
        """Connect to the kernel's existing TelemetryCollector."""
        try:
            from kernel.telemetry import TelemetryCollector

            def kernel_exporter(point: Any) -> None:
                """Bridge from kernel MetricPoint to telemetry event."""
                self.record(
                    TelemetryEventType.PERFORMANCE,
                    name=point.name,
                    value=point.value,
                    unit=point.unit,
                    tags=point.labels.copy(),
                    source="kernel",
                )

            # Get the existing kernel telemetry instance
            if TelemetryCollector._instance:
                TelemetryCollector._instance.add_exporter(kernel_exporter)
                logger.info("Telemetry: integrated with kernel TelemetryCollector")
        except (ImportError, AttributeError):
            logger.warning("Telemetry: could not integrate with kernel TelemetryCollector")
