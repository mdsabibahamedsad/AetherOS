from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Callable

from aetheros_automation.models.models import TaskStatus

logger = logging.getLogger(__name__)


class TaskMonitor:
    """Subscribe to an engine or orchestrator's events and keep a live
    aggregate view of task activity: counts by status, recent tasks, and
    progress snapshots.

    Connect by registering this monitor's callbacks with the source::

        monitor = TaskMonitor()
        engine.on("task.created", monitor.on_task_created)
        engine.on("task.started", monitor.on_task_started)
        engine.on("task.completed", monitor.on_task_completed)
        engine.on("task.failed", monitor.on_task_failed)
    """

    def __init__(self, max_history: int = 500) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = max_history
        self._listeners: list[Callable[[str, dict[str, Any]], None]] = []
        self._started_at = time.time()

    # ── event subscriptions (registered as handlers on the source) ──

    def on_task_created(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.PENDING.value, event="created", data=data)

    def on_task_started(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.RUNNING.value, event="started", data=data)

    def on_task_completed(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.COMPLETED.value, event="completed", data=data)

    def on_task_failed(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.FAILED.value, event="failed", data=data)

    def on_task_blocked(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.BLOCKED.value, event="blocked", data=data)

    def on_task_cancelled(self, data: dict[str, Any]) -> None:
        self._touch(data.get("task_id", ""), status=TaskStatus.CANCELLED.value, event="cancelled", data=data)

    # ── direct tracking ─────────────────────────────────────────

    def track(self, task_id: str, name: str = "", status: str = "pending", progress: float = 0.0, **extra: Any) -> None:
        entry = self._tasks.setdefault(
            task_id,
            {
                "task_id": task_id,
                "name": name,
                "status": status,
                "progress": progress,
                "events": 0,
                "created_at": time.time(),
                "last_update": time.time(),
            },
        )
        entry.update(extra)
        entry["status"] = status
        entry["progress"] = max(0.0, min(100.0, progress))
        entry["events"] += 1
        entry["last_update"] = time.time()
        self._notify("update", dict(entry))

    def update_progress(self, task_id: str, progress: float) -> None:
        if task_id in self._tasks:
            self.track(task_id, progress=progress)

    def mark_status(self, task_id: str, status: str) -> None:
        if task_id in self._tasks:
            self.track(task_id, status=status)

    def set_status(self, task_id: str, status: str) -> None:
        self.track(task_id, status=status)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        entry = self._tasks.get(task_id)
        return dict(entry) if entry else None

    def get_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        entries = list(self._tasks.values())
        if status:
            entries = [e for e in entries if e["status"] == status]
        return sorted(entries, key=lambda e: e["created_at"])

    # ── aggregation ─────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = defaultdict(int)
        for entry in self._tasks.values():
            by_status[entry["status"]] += 1
        running = [e for e in self._tasks.values() if e["status"] == TaskStatus.RUNNING.value]
        return {
            "total_tasks": len(self._tasks),
            "by_status": dict(sorted(by_status.items())),
            "running_tasks": len(running),
            "completed_tasks": by_status.get(TaskStatus.COMPLETED.value, 0),
            "failed_tasks": by_status.get(TaskStatus.FAILED.value, 0),
            "uptime_seconds": round(time.time() - self._started_at, 2),
            "active_agents": len(self._get_active_agents()),
        }

    def get_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._history[-limit:]))

    def snapshot(self) -> dict[str, Any]:
        return {
            "summary": self.get_summary(),
            "tasks": [dict(e) for e in self._tasks.values()],
            "activity": self.get_activity(),
        }

    # ── listener support ────────────────────────────────────────

    def on_update(self, listener: Callable[[str, dict[str, Any]], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, event: str, data: dict[str, Any]) -> None:
        for listener in self._listeners:
            try:
                listener(event, data)
            except Exception:
                logger.exception("Monitor listener failed")

    # ── helpers ─────────────────────────────────────────────────

    def _touch(self, task_id: str, status: str, event: str, data: dict[str, Any]) -> None:
        if not task_id:
            return
        entry = self._tasks.setdefault(
            task_id,
            {
                "task_id": task_id,
                "name": data.get("name", ""),
                "status": status,
                "progress": 0.0,
                "events": 0,
                "created_at": time.time(),
                "last_update": time.time(),
            },
        )
        entry["status"] = status
        entry["events"] += 1
        entry["last_update"] = time.time()
        if status == TaskStatus.COMPLETED.value:
            entry["progress"] = 100.0
        history_item = {
            "task_id": task_id,
            "event": event,
            "status": status,
            "timestamp": time.time(),
        }
        history_item.update({k: v for k, v in data.items() if k != "task_id"})
        self._history.append(history_item)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self._notify(event, dict(entry))

    def _get_active_agents(self) -> dict[str, Any]:
        active: dict[str, Any] = {}
        for entry in self._tasks.values():
            agent = entry.get("agent_id")
            if agent:
                active[agent] = entry.get("role", "")
        return active

    def on_agent_started(self, data: dict[str, Any]) -> None:
        agent_id = data.get("agent_id", "")
        if not agent_id:
            return
        task_id = data.get("task_id", "")
        entry = self._tasks.setdefault(
            task_id or agent_id,
            {
                "task_id": task_id or agent_id,
                "name": data.get("name", ""),
                "agent_id": agent_id,
                "role": data.get("role", ""),
                "status": TaskStatus.RUNNING.value,
                "progress": 0.0,
                "events": 0,
                "created_at": time.time(),
                "last_update": time.time(),
            },
        )
        entry["agent_id"] = agent_id
        entry["last_update"] = time.time()
        entry["events"] += 1
        self._notify("agent_started", dict(entry))
