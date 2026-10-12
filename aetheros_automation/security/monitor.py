from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_MONITOR_DIR = os.path.expanduser("~/.aetheros/automation")
_LOG_FILE = os.path.join(_MONITOR_DIR, "activity_log.json")


class ActivityMonitor:
    """Record, query, and export every notable action the engine takes.

    Logs are kept in memory and flushed to
    ``~/.aetheros/automation/activity_log.json``.  Call :meth:`export_logs`
    to write a standalone copy.
    """

    def __init__(self) -> None:
        os.makedirs(_MONITOR_DIR, exist_ok=True)
        self._entries: list[_LogEntry] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def log_action(self, action: str, details: dict[str, Any]) -> None:
        """Persist a single action record."""
        await self._ensure_loaded()
        entry = _LogEntry(
            id=uuid.uuid4().hex[:12],
            action=action,
            details=details,
            timestamp=time.time(),
        )
        self._entries.append(entry)
        await self._persist()
        logger.debug("Logged action %s  id=%s", action, entry.id)

    async def get_logs(
        self,
        filter_action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return logged actions, newest first, optionally filtered."""
        await self._ensure_loaded()
        entries = self._entries
        if filter_action:
            entries = [e for e in entries if e.action == filter_action]
        return [
            {"id": e.id, "action": e.action, "details": e.details, "timestamp": e.timestamp}
            for e in reversed(entries[-limit:])
        ]

    async def get_statistics(self) -> dict[str, Any]:
        """Aggregate summary of all logged actions."""
        await self._ensure_loaded()
        total = len(self._entries)
        action_counts: dict[str, int] = {}
        for e in self._entries:
            action_counts[e.action] = action_counts.get(e.action, 0) + 1

        start = self._entries[0].timestamp if self._entries else 0.0
        end = self._entries[-1].timestamp if self._entries else 0.0
        duration = end - start if start and end else 0.0

        return {
            "total_actions": total,
            "unique_actions": len(action_counts),
            "action_counts": action_counts,
            "first_entry": start,
            "last_entry": end,
            "timespan_seconds": round(duration, 2),
            "actions_per_minute": (
                round(total / (duration / 60), 2) if duration > 0 else 0.0
            ),
        }

    async def export_logs(self, path: str) -> None:
        """Write a standalone JSON copy of all activity logs to *path*."""
        await self._ensure_loaded()
        data = [
            {"id": e.id, "action": e.action, "details": e.details, "timestamp": e.timestamp}
            for e in self._entries
        ]
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, path, {"logs": data})
        logger.info("Exported %d log entries to %s", len(self._entries), path)

    async def emergency_stop(self) -> None:
        """Kill all tracked actions and log the stop event.

        This is a soft stop – it flags the state but does not send OS-level
        signals.  The caller is responsible for actually tearing down running
        subprocesses.
        """
        await self._ensure_loaded()
        await self.log_action("emergency_stop", {"triggered_at": time.time()})
        logger.warning("EMERGENCY STOP triggered")

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load)

    def _load(self) -> None:
        if not os.path.isfile(_LOG_FILE):
            return
        try:
            with open(_LOG_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            logger.exception("Failed to load activity log")
            return

        for raw in data.get("logs", []):
            self._entries.append(
                _LogEntry(
                    id=raw.get("id", uuid.uuid4().hex[:12]),
                    action=raw.get("action", ""),
                    details=raw.get("details", {}),
                    timestamp=raw.get("timestamp", 0.0),
                )
            )

    async def _persist(self) -> None:
        data = {
            "logs": [
                {"id": e.id, "action": e.action, "details": e.details, "timestamp": e.timestamp}
                for e in self._entries
            ]
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, _LOG_FILE, data)


class _LogEntry:
    __slots__ = ("id", "action", "details", "timestamp")

    def __init__(
        self,
        id: str,
        action: str,
        details: dict[str, Any],
        timestamp: float,
    ) -> None:
        self.id = id
        self.action = action
        self.details = details
        self.timestamp = timestamp


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


class EmergencyStop:
    """High-level trigger that ties :class:`ActivityMonitor` to the engine.

    Usage::

        stop = EmergencyStop(monitor)
        await stop.trigger()
    """

    def __init__(self, monitor: ActivityMonitor) -> None:
        self._monitor = monitor
        self._triggered = False

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    async def trigger(self) -> None:
        """Log the stop and set the internal flag."""
        self._triggered = True
        await self._monitor.emergency_stop()

    async def reset(self) -> None:
        """Clear the triggered state."""
        self._triggered = False
