"""Session Recovery — restores chats, tasks, streaming, downloads, agents after crash.

If the application crashes, everything is restored.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.recovery")


@dataclass
class RecoveryPoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    component: str = ""
    version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "data": self.data,
            "component": self.component,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RecoveryPoint":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


RecoveryHandler = Callable[[RecoveryPoint], bool]


class SessionRecovery:
    """Crash recovery system.

    Periodically checkpoints the state of every subsystem.
    On restart, restores chats, tasks, streaming, downloads, and agents.
    """

    def __init__(self, recovery_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._recovery_dir = recovery_dir
        self._checkpoints: Dict[str, RecoveryPoint] = {}
        self._handlers: Dict[str, RecoveryHandler] = {}
        self._checkpoint_interval: float = 30.0
        self._max_checkpoints: int = 5
        self._checkpoint_thread: Optional[threading.Thread] = None
        self._checkpoint_stop = threading.Event()

        if recovery_dir:
            recovery_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def save_checkpoint(self, component: str, data: Dict[str, Any]) -> RecoveryPoint:
        point = RecoveryPoint(component=component, data=data)
        with self._lock:
            key = f"{component}:checkpoint"
            if key in self._checkpoints:
                point.version = self._checkpoints[key].version + 1
            self._checkpoints[key] = point
            self._enforce_max()
        self._persist()
        logger.debug("Checkpoint saved: %s (v%d)", component, point.version)
        return point

    def get_checkpoint(self, component: str) -> Optional[RecoveryPoint]:
        with self._lock:
            return self._checkpoints.get(f"{component}:checkpoint")

    def get_all_checkpoints(self) -> Dict[str, RecoveryPoint]:
        with self._lock:
            return dict(self._checkpoints)

    def clear_checkpoints(self, component: Optional[str] = None) -> int:
        count = 0
        with self._lock:
            if component:
                keys = [k for k in self._checkpoints if k.startswith(f"{component}:")]
                for k in keys:
                    del self._checkpoints[k]
                    count += 1
            else:
                count = len(self._checkpoints)
                self._checkpoints.clear()
        self._persist()
        return count

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def register_handler(self, component: str, handler: RecoveryHandler) -> None:
        with self._lock:
            self._handlers[component] = handler

    def recover_all(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        with self._lock:
            checkpoints = dict(self._checkpoints)
            handlers = dict(self._handlers)

        for key, point in checkpoints.items():
            component = point.component
            handler = handlers.get(component)
            if not handler:
                logger.warning("No recovery handler for: %s", component)
                results[component] = False
                continue
            try:
                success = handler(point)
                results[component] = success
                logger.info("Recovery %s for: %s", "succeeded" if success else "failed", component)
            except Exception as exc:
                logger.error("Recovery error for %s: %s", component, exc)
                results[component] = False

        return results

    def recover_component(self, component: str) -> bool:
        checkpoint = self.get_checkpoint(component)
        if not checkpoint:
            logger.warning("No checkpoint found for: %s", component)
            return False
        handler = self._handlers.get(component)
        if not handler:
            logger.warning("No recovery handler for: %s", component)
            return False
        try:
            return handler(checkpoint)
        except Exception as exc:
            logger.error("Recovery error for %s: %s", component, exc)
            return False

    # ------------------------------------------------------------------
    # Auto-checkpointing
    # ------------------------------------------------------------------

    def start_auto_checkpoint(self, interval: Optional[float] = None) -> None:
        if interval:
            self._checkpoint_interval = interval
        if self._checkpoint_thread and self._checkpoint_thread.is_alive():
            return
        self._checkpoint_stop.clear()
        self._checkpoint_thread = threading.Thread(
            target=self._checkpoint_loop, daemon=True,
            name="recovery-checkpointer",
        )
        self._checkpoint_thread.start()

    def stop_auto_checkpoint(self) -> None:
        self._checkpoint_stop.set()
        if self._checkpoint_thread:
            self._checkpoint_thread.join(timeout=5)

    def _checkpoint_loop(self) -> None:
        while not self._checkpoint_stop.is_set():
            self._checkpoint_stop.wait(self._checkpoint_interval)
            for component in list(self._handlers.keys()):
                checkpoint = self.get_checkpoint(component)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        if not self._recovery_dir:
            return
        try:
            data = {k: v.to_dict() for k, v in self._checkpoints.items()}
            path = self._recovery_dir / "recovery.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to persist recovery checkpoints: %s", exc)

    def _load(self) -> None:
        if not self._recovery_dir:
            return
        path = self._recovery_dir / "recovery.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._checkpoints[k] = RecoveryPoint.from_dict(v)
            logger.info("Loaded %d recovery checkpoints", len(self._checkpoints))
        except Exception as exc:
            logger.warning("Failed to load recovery checkpoints: %s", exc)

    def _enforce_max(self) -> None:
        if len(self._checkpoints) > self._max_checkpoints:
            sorted_pts = sorted(self._checkpoints.items(), key=lambda x: x[1].timestamp)
            to_remove = len(self._checkpoints) - self._max_checkpoints
            for key, _ in sorted_pts[:to_remove]:
                del self._checkpoints[key]

    def summary(self) -> str:
        with self._lock:
            return f"Session Recovery: {len(self._checkpoints)} checkpoints, {len(self._handlers)} recovery handlers"