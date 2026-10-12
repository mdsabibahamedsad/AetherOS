from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from typing import Optional

from core.jarvis.engine import JarvisEngine

logger = logging.getLogger(__name__)

_engine: Optional[JarvisEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> Optional[JarvisEngine]:
    global _engine
    with _engine_lock:
        return _engine


def boot_sequence(storage_dir: Optional[Path] = None) -> JarvisEngine:
    global _engine
    with _engine_lock:
        if _engine is not None:
            return _engine

        engine = JarvisEngine(storage_dir=storage_dir)

        engine.memory.seed_default()

        engine.scheduler.schedule(
            "System Health Check",
            ScheduleType.INTERVAL,
            interval_seconds=60,
            handler=lambda: _health_check(engine),
            metadata={"category": "system"},
        )

        engine.scheduler.schedule(
            "Memory Cleanup",
            ScheduleType.DAILY,
            handler=lambda: _memory_cleanup(engine),
            metadata={"category": "maintenance"},
        )

        _engine = engine
        return engine


def shutdown_sequence():
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.stop()
            _engine = None


def initialize_engine(storage_dir: Optional[Path] = None) -> JarvisEngine:
    engine = boot_sequence(storage_dir=storage_dir)
    engine.start()
    print("[Jarvis] Engine initialized and running")
    return engine


def shutdown_engine():
    shutdown_sequence()
    print("[Jarvis] Engine shutdown complete")


def _health_check(engine: JarvisEngine):
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        if cpu > 90:
            engine.notifications.notify(
                "High CPU Usage",
                f"CPU at {cpu}% - checking for issues",
                level="warning",
                source="scheduler",
            )
        if mem.percent > 90:
            engine.notifications.notify(
                "High Memory Usage",
                f"Memory at {mem.percent}%",
                level="warning",
                source="scheduler",
            )
    except Exception:
        pass


def _memory_cleanup(engine: JarvisEngine):
    old_entries = engine.memory.search("", limit=1000)
    cutoff = time.time() - (30 * 24 * 3600)
    for entry in old_entries:
        if entry.timestamp < cutoff and entry.type not in ("preference", "system"):
            engine.memory.forget(entry.key)
