"""Telemetry pipeline — event ingestion, batching, export."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    event_type: str
    source: str
    data: dict = field(default_factory=dict)
    timestamp: str = ""
    tags: list[str] = field(default_factory=list)
    user_id: str = ""
    session_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["timestamp"]:
            d["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return d


class TelemetryPipeline:
    def __init__(self, batch_size: int = 50,
                 flush_interval: float = 5.0,
                 max_queue: int = 10000):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self._exporters: list[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stats = {"enqueued": 0, "exported": 0, "dropped": 0}

    def add_exporter(self, exporter: Callable):
        self._exporters.append(exporter)

    def emit(self, event: TelemetryEvent):
        try:
            self._queue.put_nowait(event)
            with self._lock:
                self._stats["enqueued"] += 1
        except queue.Full:
            with self._lock:
                self._stats["dropped"] += 1
            logger.warning("Telemetry queue full, dropping event")

    def emit_event(self, event_type: str, source: str,
                    data: dict = None, tags: list[str] = None,
                    user_id: str = "", session_id: str = ""):
        event = TelemetryEvent(
            event_type=event_type, source=source,
            data=data or {}, tags=tags or [],
            user_id=user_id, session_id=session_id,
        )
        self.emit(event)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Telemetry pipeline started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        self._flush_all()
        logger.info("Telemetry pipeline stopped")

    def _run(self):
        batch: list[TelemetryEvent] = []
        last_flush = time.time()
        while self._running:
            try:
                event = self._queue.get(timeout=0.5)
                batch.append(event)
                if len(batch) >= self.batch_size:
                    self._export_batch(batch)
                    batch = []
                    last_flush = time.time()
            except queue.Empty:
                if batch and (time.time() - last_flush) >= self.flush_interval:
                    self._export_batch(batch)
                    batch = []
                    last_flush = time.time()
        if batch:
            self._export_batch(batch)

    def _flush_all(self):
        batch = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if batch:
            self._export_batch(batch)

    def _export_batch(self, batch: list[TelemetryEvent]):
        if not batch:
            return
        data = [e.to_dict() for e in batch]
        for exporter in self._exporters:
            try:
                exporter(data)
            except Exception as e:
                logger.error("Telemetry export error: %s", e)
        with self._lock:
            self._stats["exported"] += len(batch)

    def get_stats(self) -> dict:
        with self._lock:
            return {
                **self._stats,
                "queue_size": self._queue.qsize(),
                "exporters": len(self._exporters),
            }

    def close(self):
        self.stop()
        self._exporters.clear()
