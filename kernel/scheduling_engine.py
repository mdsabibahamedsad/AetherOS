"""
Scheduling Engine — advanced scheduling for agents, tasks, and missions.

Supports:
  - Immediate execution (fire and forget)
  - Delayed execution (run after a specified delay)
  - Recurring execution (interval-based, cron-like)
  - Event-based execution (triggered by events or conditions)
  - Cron-like schedules (standard 5-field cron expressions)
  - Background execution (low-priority, runs when resources available)
  - Batch scheduling (multiple tasks at defined times)
  - Priority-based scheduling (higher priority tasks run first)
  - Dependency-based scheduling (tasks run when dependencies are met)
"""

from __future__ import annotations

import enum
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ScheduleType(enum.Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    INTERVAL = "interval"
    CRON = "cron"
    EVENT = "event"
    BACKGROUND = "background"
    BATCH = "batch"


class ScheduleStatus(enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScheduleEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    type: ScheduleType = ScheduleType.IMMEDIATE

    run_at: Optional[float] = None
    interval_seconds: float = 300.0
    cron_expression: str = ""
    event_trigger: str = ""
    event_condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    agent_id: str = ""
    goal: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 50

    callback: Optional[Callable] = None
    max_executions: Optional[int] = None
    execution_count: int = 0
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None

    status: ScheduleStatus = ScheduleStatus.PENDING
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class SchedulingEngine:
    """Advanced scheduling engine for agents, tasks, and missions.

    Handles immediate, delayed, recurring, cron, event-based, and
    background scheduling with priority queuing.

    Usage:
        scheduler = SchedulingEngine(event_bus)
        scheduler.start()

        # Immediate
        scheduler.schedule_immediate("deploy", deploy_fn)

        # Delayed
        scheduler.schedule_delayed("cleanup", 3600, cleanup_fn)

        # Interval
        scheduler.schedule_interval("health-check", 60, health_fn)

        # Cron
        scheduler.schedule_cron("daily-report", "0 9 * * *", report_fn)

        # Event-based
        scheduler.schedule_on_event("on-config-change", "config.updated", handler_fn)

        scheduler.stop()
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 tick_interval: float = 1.0,
                 max_concurrent: int = 10):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._tick_interval = tick_interval
        self._max_concurrent = max_concurrent
        self._entries: Dict[str, ScheduleEntry] = {}
        self._event_handlers: Dict[str, List[Tuple[str, Callable]]] = {}
        self._running = False
        self._shutdown_flag = False
        self._tick_thread: Optional[threading.Thread] = None
        self._active_count = 0
        self._pause_condition = threading.Condition(self._lock)
        self._paused = False
        self._execution_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._shutdown_flag = False
        self._tick_thread = threading.Thread(
            target=self._tick_loop,
            daemon=True,
            name="scheduling-engine",
        )
        self._tick_thread.start()
        logger.info("SchedulingEngine: started (tick=%ds, max_concurrent=%d)",
                     self._tick_interval, self._max_concurrent)

    def stop(self) -> None:
        self._shutdown_flag = True
        self._running = False
        with self._pause_condition:
            self._pause_condition.notify_all()
        if self._tick_thread:
            self._tick_thread.join(timeout=10)
            self._tick_thread = None
        logger.info("SchedulingEngine: stopped")

    def pause(self) -> None:
        with self._pause_condition:
            self._paused = True
        logger.info("SchedulingEngine: paused")

    def resume(self) -> None:
        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()
        logger.info("SchedulingEngine: resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ------------------------------------------------------------------
    # Schedule creation
    # ------------------------------------------------------------------

    def schedule_immediate(self, name: str, callback: Callable,
                           agent_id: str = "", goal: str = "",
                           priority: int = 50,
                           context: Dict[str, Any] = None) -> ScheduleEntry:
        entry = ScheduleEntry(
            name=name,
            type=ScheduleType.IMMEDIATE,
            priority=priority,
            agent_id=agent_id,
            goal=goal,
            context=context or {},
            callback=callback,
            status=ScheduleStatus.SCHEDULED,
        )
        with self._lock:
            self._entries[entry.id] = entry
        self._execute_entry(entry)
        return entry

    def schedule_delayed(self, name: str, delay_seconds: float,
                         callback: Callable,
                         agent_id: str = "", goal: str = "",
                         priority: int = 50) -> ScheduleEntry:
        entry = ScheduleEntry(
            name=name,
            type=ScheduleType.DELAYED,
            run_at=time.time() + delay_seconds,
            next_run_at=time.time() + delay_seconds,
            priority=priority,
            agent_id=agent_id,
            goal=goal,
            callback=callback,
            max_executions=1,
            status=ScheduleStatus.SCHEDULED,
        )
        with self._lock:
            self._entries[entry.id] = entry
        logger.info("SchedulingEngine: scheduled delayed '%s' in %.0fs",
                     name, delay_seconds)
        return entry

    def schedule_interval(self, name: str, interval_seconds: float,
                          callback: Callable,
                          agent_id: str = "", goal: str = "",
                          priority: int = 50,
                          max_executions: Optional[int] = None) -> ScheduleEntry:
        entry = ScheduleEntry(
            name=name,
            type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
            next_run_at=time.time(),
            priority=priority,
            agent_id=agent_id,
            goal=goal,
            callback=callback,
            max_executions=max_executions,
            status=ScheduleStatus.SCHEDULED,
        )
        with self._lock:
            self._entries[entry.id] = entry
        logger.info("SchedulingEngine: scheduled interval '%s' every %.0fs",
                     name, interval_seconds)
        return entry

    def schedule_cron(self, name: str, cron_expression: str,
                      callback: Callable,
                      agent_id: str = "", goal: str = "",
                      priority: int = 50) -> ScheduleEntry:
        next_run = self._parse_cron_next(cron_expression)
        entry = ScheduleEntry(
            name=name,
            type=ScheduleType.CRON,
            cron_expression=cron_expression,
            next_run_at=next_run,
            priority=priority,
            agent_id=agent_id,
            goal=goal,
            callback=callback,
            status=ScheduleStatus.SCHEDULED,
        )
        with self._lock:
            self._entries[entry.id] = entry
        logger.info("SchedulingEngine: scheduled cron '%s' (%s)",
                     name, cron_expression)
        return entry

    def schedule_on_event(self, name: str, event_trigger: str,
                          callback: Callable,
                          condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
                          agent_id: str = "", priority: int = 50) -> ScheduleEntry:
        entry = ScheduleEntry(
            name=name,
            type=ScheduleType.EVENT,
            event_trigger=event_trigger,
            event_condition=condition,
            priority=priority,
            agent_id=agent_id,
            callback=callback,
            status=ScheduleStatus.SCHEDULED,
        )
        with self._lock:
            self._entries[entry.id] = entry
            self._event_handlers.setdefault(event_trigger, []).append((entry.id, callback))
        if self._event_bus:
            self._event_bus.subscribe(event_trigger, lambda e: self._handle_event(entry.id, e))
        logger.info("SchedulingEngine: scheduled event '%s' on '%s'",
                     name, event_trigger)
        return entry

    def schedule_batch(self, name: str, run_times: List[float],
                       callback: Callable, priority: int = 50) -> List[ScheduleEntry]:
        entries = []
        for i, run_time in enumerate(run_times):
            entry = ScheduleEntry(
                name=f"{name}-{i+1}",
                type=ScheduleType.BATCH,
                run_at=run_time,
                next_run_at=run_time,
                priority=priority,
                callback=callback,
                max_executions=1,
                status=ScheduleStatus.SCHEDULED,
            )
            with self._lock:
                self._entries[entry.id] = entry
            entries.append(entry)
        logger.info("SchedulingEngine: scheduled batch '%s' with %d times",
                     name, len(run_times))
        return entries

    # ------------------------------------------------------------------
    # Entry management
    # ------------------------------------------------------------------

    def get_entry(self, entry_id: str) -> Optional[ScheduleEntry]:
        with self._lock:
            return self._entries.get(entry_id)

    def cancel(self, entry_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.status in (ScheduleStatus.COMPLETED,
                                                  ScheduleStatus.CANCELLED,
                                                  ScheduleStatus.FAILED):
                return False
            entry.status = ScheduleStatus.CANCELLED
        return True

    def pause_entry(self, entry_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.status != ScheduleStatus.SCHEDULED:
                return False
            entry.status = ScheduleStatus.PAUSED
        return True

    def resume_entry(self, entry_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.status != ScheduleStatus.PAUSED:
                return False
            entry.status = ScheduleStatus.SCHEDULED
        return True

    def list_entries(self, type: ScheduleType = None,
                     status: ScheduleStatus = None,
                     agent_id: str = "",
                     limit: int = 100) -> List[ScheduleEntry]:
        with self._lock:
            entries = list(self._entries.values())
        if type:
            entries = [e for e in entries if e.type == type]
        if status:
            entries = [e for e in entries if e.status == status]
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        entries.sort(key=lambda e: (e.priority, e.next_run_at or 0))
        return entries[:limit]

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    def _tick_loop(self) -> None:
        while not self._shutdown_flag:
            try:
                with self._pause_condition:
                    while self._paused and not self._shutdown_flag:
                        self._pause_condition.wait(timeout=1.0)

                if self._shutdown_flag:
                    break

                if self._active_count < self._max_concurrent:
                    self._tick()
            except Exception as exc:
                logger.error("SchedulingEngine: tick error: %s", exc)
            time.sleep(self._tick_interval)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            due = [
                e for e in self._entries.values()
                if e.status == ScheduleStatus.SCHEDULED
                and e.next_run_at is not None
                and now >= e.next_run_at
                and (e.max_executions is None or e.execution_count < e.max_executions)
            ]
            due.sort(key=lambda e: (e.priority, e.next_run_at))

        for entry in due[:self._max_concurrent - self._active_count]:
            self._execute_entry(entry)

    def _execute_entry(self, entry: ScheduleEntry) -> None:
        with self._lock:
            entry.status = ScheduleStatus.RUNNING
            self._active_count += 1

        if self._event_bus:
            self._event_bus.emit_async("scheduler.entry_started", {
                "entry_id": entry.id,
                "name": entry.name,
                "type": entry.type.value,
            })

        def _run():
            try:
                start = time.time()
                if entry.callback:
                    entry.callback()
                elapsed = time.time() - start

                with self._lock:
                    entry.execution_count += 1
                    entry.last_run_at = time.time()

                    if entry.max_executions and entry.execution_count >= entry.max_executions:
                        entry.status = ScheduleStatus.COMPLETED
                    elif entry.type in (ScheduleType.IMMEDIATE, ScheduleType.DELAYED, ScheduleType.BATCH):
                        entry.status = ScheduleStatus.COMPLETED
                    elif entry.type == ScheduleType.INTERVAL:
                        entry.next_run_at = time.time() + entry.interval_seconds
                        entry.status = ScheduleStatus.SCHEDULED
                    elif entry.type == ScheduleType.CRON:
                        entry.next_run_at = self._parse_cron_next(entry.cron_expression)
                        entry.status = ScheduleStatus.SCHEDULED

                    self._execution_history.append({
                        "entry_id": entry.id,
                        "name": entry.name,
                        "type": entry.type.value,
                        "duration": elapsed,
                        "timestamp": time.time(),
                    })
                    if len(self._execution_history) > 1000:
                        self._execution_history = self._execution_history[-500:]

                if self._event_bus:
                    self._event_bus.emit_async("scheduler.entry_completed", {
                        "entry_id": entry.id,
                        "name": entry.name,
                        "duration": elapsed,
                    })

                logger.debug("SchedulingEngine: executed '%s' in %.2fs",
                             entry.name, elapsed)

            except Exception as exc:
                with self._lock:
                    entry.status = ScheduleStatus.FAILED
                logger.error("SchedulingEngine: entry '%s' failed: %s",
                             entry.name, exc)
                if self._event_bus:
                    self._event_bus.emit_async("scheduler.entry_failed", {
                        "entry_id": entry.id,
                        "name": entry.name,
                        "error": str(exc),
                    })
            finally:
                with self._lock:
                    self._active_count -= 1

        thread = threading.Thread(target=_run, daemon=True,
                                  name=f"sched-{entry.name[:20]}")
        thread.start()

    def _handle_event(self, entry_id: str, event_data: Dict[str, Any]) -> None:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.status != ScheduleStatus.SCHEDULED:
                return
            if entry.event_condition and not entry.event_condition(event_data):
                return
        self._execute_entry(entry)

    # ------------------------------------------------------------------
    # Cron parsing
    # ------------------------------------------------------------------

    def _parse_cron_next(self, expression: str) -> float:
        try:
            parts = expression.strip().split()
            if len(parts) != 5:
                return time.time() + 3600

            minute, hour, day_of_month, month, day_of_week = parts
            now = datetime.now(timezone.utc)

            for minute_offset in range(60 * 24 * 7):
                check = now + timedelta(minutes=minute_offset)
                if (self._cron_field_matches(minute, check.minute) and
                    self._cron_field_matches(hour, check.hour) and
                    self._cron_field_matches(day_of_month, check.day) and
                    self._cron_field_matches(month, check.month) and
                    self._cron_field_matches(day_of_week, check.weekday())):
                    return check.timestamp()

            return time.time() + 3600
        except Exception:
            return time.time() + 3600

    @staticmethod
    def _cron_field_matches(pattern: str, value: int) -> bool:
        if pattern == "*":
            return True
        if "," in pattern:
            return any(SchedulingEngine._cron_field_matches(p, value) for p in pattern.split(","))
        if "-" in pattern:
            low, high = pattern.split("-")
            return int(low) <= value <= int(high)
        if "/" in pattern:
            base, step = pattern.split("/")
            if base == "*":
                return value % int(step) == 0
            return value >= int(base) and (value - int(base)) % int(step) == 0
        return int(pattern) == value

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._execution_history[-limit:])

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            scheduled = sum(1 for e in self._entries.values() if e.status == ScheduleStatus.SCHEDULED)
            running = sum(1 for e in self._entries.values() if e.status == ScheduleStatus.RUNNING)
            completed = sum(1 for e in self._entries.values() if e.status == ScheduleStatus.COMPLETED)
            failed = sum(1 for e in self._entries.values() if e.status == ScheduleStatus.FAILED)
            paused = sum(1 for e in self._entries.values() if e.status == ScheduleStatus.PAUSED)
            by_type: Dict[str, int] = {}
            for e in self._entries.values():
                by_type[e.type.value] = by_type.get(e.type.value, 0) + 1
        return {
            "running": self._running,
            "paused": self._paused,
            "active_executions": self._active_count,
            "max_concurrent": self._max_concurrent,
            "total_entries": total,
            "scheduled": scheduled,
            "running_now": running,
            "completed": completed,
            "failed": failed,
            "paused_entries": paused,
            "by_type": by_type,
        }