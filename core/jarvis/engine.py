from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Any

from core.jarvis.observer import SystemObserver, ObserverEvent, EventType
from core.jarvis.reasoning import ReasoningEngine, ReasoningResult
from core.jarvis.planner import TaskPlanner, TaskGraph, TaskStatus, ExecutionMode
from core.jarvis.executor import UnifiedExecutor, ExecutorTask
from core.jarvis.memory import PersistentMemory, MemoryEntry
from core.jarvis.context import ContextEngine, JarvisContext
from core.jarvis.autonomy import AutonomyController, AutonomyLevel
from core.jarvis.skills import SkillsManager
from core.jarvis.scheduler import BackgroundScheduler, ScheduleType
from core.jarvis.notifications import NotificationCenter, NotificationLevel, NotificationSource

logger = logging.getLogger(__name__)


class EnginePhase:
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    LEARNING = "learning"
    ERROR = "error"


class JarvisEngine:
    def __init__(self, storage_dir: Optional[Path] = None):
        self._storage = storage_dir or Path.home() / ".aetheros" / "jarvis"
        self._storage.mkdir(parents=True, exist_ok=True)

        self.notifications = NotificationCenter()
        self.observer = SystemObserver(self._storage / "observer")
        self.reasoning = ReasoningEngine()
        self.planner = TaskPlanner()
        self.executor = UnifiedExecutor()
        self.memory = PersistentMemory(self._storage / "memory.json")
        self.context = ContextEngine(self._storage / "context.json")
        self.autonomy = AutonomyController(self.notifications)
        self.skills = SkillsManager()
        self.scheduler = BackgroundScheduler(self._storage / "scheduler.json")

        self._phase = EnginePhase.IDLE
        self._running = False
        self._pause = False
        self._cycle_count = 0
        self._cycle_interval = 2.0
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._state_listeners: list[Callable] = []
        self._active_graph_id: Optional[str] = None

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def on_state_change(self, listener: Callable) -> Callable:
        self._state_listeners.append(listener)
        return lambda: self._state_listeners.remove(listener)

    def _notify_state(self):
        state = self.get_state()
        for listener in self._state_listeners:
            try:
                listener(state)
            except Exception:
                pass

    def get_state(self) -> dict:
        return {
            "phase": self._phase,
            "cycleCount": self._cycle_count,
            "isRunning": self._running,
            "activeGraphId": self._active_graph_id,
            "uptime": time.time() - self._started_at if hasattr(self, "_started_at") else 0,
        }

    def _set_phase(self, phase: str):
        self._phase = phase
        self._notify_state()

    def _observe(self):
        self._set_phase(EnginePhase.OBSERVING)
        ctx = self.context.context

        idle_duration = self.context.get_idle_duration()
        if idle_duration > 120 and self.autonomy.enabled:
            self.observer.emit(ObserverEvent(
                type=EventType.USER_IDLE,
                data={"duration": idle_duration},
            ))

    def _think(self):
        self._set_phase(EnginePhase.THINKING)
        events = self.observer.recent_events[:5]

        for event in events:
            if self._pause:
                return
            result = self.reasoning.reason(event)
            if result and self.autonomy.enabled:
                self.autonomy.evaluate(result)

    def _plan(self):
        self._set_phase(EnginePhase.PLANNING)
        if self._active_graph_id:
            return

        pending = self.autonomy.get_pending()
        for suggestion in pending:
            if self._pause:
                return
            if suggestion.result.suggestions and self.autonomy.level in (
                AutonomyLevel.FULL, AutonomyLevel.SEMI
            ):
                first = suggestion.result.suggestions[0]
                if first.priority >= 7:
                    graph = self.planner.create_graph(first.title, priority=first.priority)
                    self._active_graph_id = graph.id
                    self.planner.start_graph(graph.id)
                    self.context.log_action(f"Started plan: {first.title}")
                    break

    def _execute(self):
        self._set_phase(EnginePhase.EXECUTING)
        if not self._active_graph_id:
            return

        status = self.planner.get_graph_status(self._active_graph_id)
        total = status["total"]
        if total == 0:
            return
        if status["completed"] + status["failed"] >= total:
            self._active_graph_id = None
            return

        ready_nodes = self.planner.get_ready_nodes(self._active_graph_id)
        for node in ready_nodes:
            if self._pause:
                return
            self.planner.update_node_status(self._active_graph_id, node.id, TaskStatus.RUNNING)
            task = self.executor.create_task("plan_node", node.label, {
                "node_id": node.id, "graph_id": self._active_graph_id,
            })
            self.notifications.notify(
                f"Executing: {node.label}",
                node.description[:100],
                level=NotificationLevel.INFO,
                source=NotificationSource.TASK,
            )
            import threading as _t
            _t.Thread(target=self._execute_node, args=(node.id, task.id), daemon=True).start()

    def _execute_node(self, node_id: str, task_id: str):
        if not self._active_graph_id:
            return
        try:
            progress = 0
            while progress < 100:
                if self._pause:
                    return
                progress += 10
                self.planner.update_node_progress(self._active_graph_id, node_id, progress)
                time.sleep(0.5)

            self.planner.update_node_status(
                self._active_graph_id, node_id, TaskStatus.COMPLETED,
                result={"task_id": task_id, "completed_at": time.time()},
            )
            self.executor.complete_task(task_id, {"success": True})
        except Exception as e:
            self.planner.update_node_status(
                self._active_graph_id, node_id, TaskStatus.FAILED,
                result={"error": str(e)},
            )
            self.executor.fail_task(task_id, str(e))

    def _learn(self):
        self._set_phase(EnginePhase.LEARNING)
        if not self._active_graph_id:
            return

        status = self.planner.get_graph_status(self._active_graph_id)
        total = status["total"]
        if total == 0:
            return
        if status["completed"] + status["failed"] >= total:
            graph = self.planner.get_graph(self._active_graph_id)
            if graph:
                self.memory.remember(
                    key=f"plan:{graph.goal}",
                    content={
                        "goal": graph.goal,
                        "total_nodes": status["total"],
                        "completed": status["completed"],
                        "failed": status["failed"],
                        "duration": (graph.completed_at or time.time()) - (graph.started_at or graph.created_at),
                    },
                    type="execution",
                    tags=["plan", graph.goal[:20].lower()],
                )

                if status["failed"] == 0:
                    self.notifications.notify(
                        f"Plan Complete: {graph.goal}",
                        "All tasks completed successfully",
                        level=NotificationLevel.SUCCESS,
                        source=NotificationSource.SYSTEM,
                    )
                else:
                    self.notifications.notify(
                        f"Plan Partial: {graph.goal}",
                        f"{status['failed']} task(s) failed",
                        level=NotificationLevel.WARNING,
                        source=NotificationSource.SYSTEM,
                    )
            self._active_graph_id = None

    def _cycle(self):
        if self._pause or not self._running:
            return
        try:
            self._observe()
            if self._pause:
                return
            self._think()
            if self._pause:
                return
            self._plan()
            if self._pause:
                return
            self._execute()
            if self._pause:
                return
            self._learn()

            self._cycle_count += 1
            self._set_phase(EnginePhase.IDLE)
        except Exception as e:
            self._set_phase(EnginePhase.ERROR)
            self.notifications.notify(
                "Engine Error",
                str(e),
                level=NotificationLevel.ERROR,
                source=NotificationSource.SYSTEM,
            )
            logger.exception("Jarvis engine cycle error")

    def _loop(self):
        while self._running:
            if not self._pause:
                self._cycle()
            time.sleep(self._cycle_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._pause = False
        self._started_at = time.time()

        self.observer.start()
        self.scheduler.start()
        self.context.update(is_idle=False)
        self.skills.load_builtin()

        self._thread = threading.Thread(target=self._loop, daemon=True, name="jarvis-engine")
        self._thread.start()

        self.notifications.notify(
            "Jarvis Engine Started",
            "AI engine now running",
            level=NotificationLevel.SUCCESS,
            source=NotificationSource.SYSTEM,
        )
        self._set_phase(EnginePhase.IDLE)

    def stop(self):
        self._running = False
        self._pause = True
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self.observer.stop()
        self.scheduler.stop()
        self._set_phase(EnginePhase.IDLE)
        self.notifications.notify(
            "Jarvis Engine Stopped",
            "AI engine has been stopped",
            level=NotificationLevel.INFO,
            source=NotificationSource.SYSTEM,
        )

    def pause(self):
        self._pause = True
        self._running = False
        self.notifications.notify(
            "Jarvis Engine Paused",
            "Engine cycle paused",
            level=NotificationLevel.INFO,
            source=NotificationSource.SYSTEM,
        )

    def resume(self):
        self._pause = False
        self._running = True
        self.notifications.notify(
            "Jarvis Engine Resumed",
            "Engine cycle resumed",
            level=NotificationLevel.INFO,
            source=NotificationSource.SYSTEM,
        )

    def execute_command(self, command: str):
        self.context.log_action(f"Command: {command}")
        self.observer.emit(ObserverEvent(
            type=EventType.USER_ACTIVITY,
            data={"command": command},
        ))

        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ("research", "search", "find")):
            gid = self.planner.create_research_plan(command)
        elif any(w in cmd_lower for w in ("code", "implement", "build", "fix", "test")):
            gid = self.planner.create_code_plan(command)
        elif any(w in cmd_lower for w in ("deploy", "release")):
            gid = self.planner.create_deploy_plan(command)
        else:
            graph = self.planner.create_graph(command)
            gid = graph.id
            n1 = self.planner.add_node(gid, "Understand", f"Understand the request: {command}",
                                       priority=8, estimated_duration=5.0)
            n2 = self.planner.add_node(gid, "Respond", "Generate response",
                                       dependencies=[n1.id] if n1 else None,
                                       priority=7, estimated_duration=3.0)

        self._active_graph_id = gid
        self.planner.start_graph(gid)
        self.notifications.notify(
            "Task Started",
            f"Processing: {command[:60]}...",
            level=NotificationLevel.INFO,
            source=NotificationSource.TASK,
        )

    def get_stats(self) -> dict:
        ctx = self.context.context
        return {
            "tasks": self.planner.get_graph_status(self._active_graph_id) if self._active_graph_id else {"total": 0, "running": 0, "queued": 0, "completed": 0, "failed": 0, "paused": 0},
            "notifications": self.notifications.get_stats(),
            "skills": self.skills.get_stats(),
            "memory": self.memory.get_stats(),
            "engine": self.get_state(),
            "autonomy": self.autonomy.state,
        }
