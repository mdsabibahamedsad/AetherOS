from __future__ import annotations

import os
import re
import psutil
import time
import json
import logging
import threading
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    USER_ACTIVITY = "user:activity"
    USER_IDLE = "user:idle"
    USER_CLIPBOARD = "user:clipboard"
    FILE_CHANGED = "file:changed"
    FILE_OPENED = "file:opened"
    PROJECT_DETECTED = "project:detected"
    BRANCH_CHANGED = "branch:changed"
    TERMINAL_OPENED = "terminal:opened"
    TERMINAL_COMMAND = "terminal:command"
    APP_OPENED = "app:opened"
    APP_CLOSED = "app:closed"
    BROWSER_URL = "browser:url"
    GIT_COMMIT = "git:commit"
    GIT_PUSH = "git:push"
    SYSTEM_LOAD = "system:load"
    SYSTEM_ERROR = "system:error"
    NOTIFICATION = "notification"
    AGENT_STARTED = "agent:started"
    AGENT_COMPLETED = "agent:completed"
    MCP_EVENT = "mcp:event"
    GATEWAY_EVENT = "gateway:event"
    PROVIDER_CHANGED = "provider:changed"
    MODEL_CHANGED = "model:changed"
    TASK_STARTED = "task:started"
    TASK_COMPLETED = "task:completed"
    CUSTOM = "custom"


@dataclass
class ObserverEvent:
    type: EventType | str
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = "observer"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


EventHandler = Callable[[ObserverEvent], None]


class SystemObserver:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "jarvis" / "observer"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._handlers: dict[str, list[EventHandler]] = {}
        self._recent_events: list[ObserverEvent] = []
        self._max_recent = 100
        self._poll_interval = 2.0
        self._idle_threshold = 120.0
        self._last_user_activity = time.time()
        self._last_cpu_check = 0.0
        self._last_cpu_value = 0.0
        self._known_processes: set[str] = set()
        self._clipboard_history: list[str] = []
        self._max_clipboard = 10

    @property
    def recent_events(self) -> list[ObserverEvent]:
        with self._lock:
            return list(self._recent_events)

    def on(self, event_type: str | EventType, handler: EventHandler) -> Callable:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._handlers.setdefault(key, []).append(handler)
        return lambda: self._handlers[key].remove(handler)

    def emit(self, event: ObserverEvent):
        with self._lock:
            self._recent_events.insert(0, event)
            if len(self._recent_events) > self._max_recent:
                self._recent_events = self._recent_events[:self._max_recent]

        key = event.type.value if isinstance(event.type, EventType) else event.type
        for handler in self._handlers.get(key, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Observer handler error: {e}")
        for handler in self._handlers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Observer wildcard handler error: {e}")

    def record_user_activity(self, activity_type: str = "input", details: Optional[dict] = None):
        self._last_user_activity = time.time()
        self.emit(ObserverEvent(
            type=EventType.USER_ACTIVITY,
            data={"activity": activity_type, "details": details or {}},
        ))

    def _check_clipboard(self):
        try:
            import pyperclip
            content = pyperclip.paste()
            if content and (not self._clipboard_history or self._clipboard_history[0] != content):
                self._clipboard_history.insert(0, content)
                if len(self._clipboard_history) > self._max_clipboard:
                    self._clipboard_history = self._clipboard_history[:self._max_clipboard]
                is_code = bool(re.search(r'(def |class |import |function|const |let |var )', content[:500]))
                self.emit(ObserverEvent(
                    type=EventType.USER_CLIPBOARD,
                    data={
                        "content": content[:200],
                        "length": len(content),
                        "is_code": is_code,
                        "lines": content.count("\n") + 1,
                    },
                ))
        except Exception:
            pass

    def _check_system_resources(self):
        now = time.time()
        if now - self._last_cpu_check < 5.0:
            return
        self._last_cpu_check = now
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            self.emit(ObserverEvent(
                type=EventType.SYSTEM_LOAD,
                data={
                    "cpu": cpu,
                    "memory_percent": mem.percent,
                    "memory_used": mem.used,
                    "memory_total": mem.total,
                    "memory_available": mem.available,
                },
            ))
        except Exception:
            pass

    def _check_processes(self):
        try:
            watcher_apps = {
                "Code.exe": "vscode",
                "chrome.exe": "chrome",
                "firefox.exe": "firefox",
                "brave.exe": "brave",
                "WindowsTerminal.exe": "terminal",
                "powershell.exe": "terminal",
                "cmd.exe": "terminal",
                "Discord.exe": "discord",
                "Slack.exe": "slack",
                "notion.exe": "notion",
                "spotify.exe": "spotify",
                "explorer.exe": "explorer",
            }
            current: set[str] = set()
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                    if name in watcher_apps:
                        current.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            new_apps = current - self._known_processes
            closed_apps = self._known_processes - current

            for app in new_apps:
                friendly = watcher_apps.get(app, app)
                self.emit(ObserverEvent(
                    type=EventType.APP_OPENED,
                    data={"app": app, "friendly": friendly},
                ))

            for app in closed_apps:
                friendly = watcher_apps.get(app, app)
                self.emit(ObserverEvent(
                    type=EventType.APP_CLOSED,
                    data={"app": app, "friendly": friendly},
                ))

            self._known_processes = current
        except Exception:
            pass

    def _check_idle(self):
        idle_time = time.time() - self._last_user_activity
        if idle_time > self._idle_threshold:
            self.emit(ObserverEvent(
                type=EventType.USER_IDLE,
                data={"duration": idle_time, "threshold": self._idle_threshold},
            ))

    def _check_git(self):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git_root = result.stdout.strip()
                branch_result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                    cwd=git_root,
                )
                if branch_result.returncode == 0:
                    branch = branch_result.stdout.strip()
                    self.emit(ObserverEvent(
                        type=EventType.PROJECT_DETECTED,
                        data={"path": git_root, "branch": branch},
                    ))
        except Exception:
            pass

    def _tick(self):
        while self._running:
            try:
                self._check_clipboard()
                self._check_system_resources()
                self._check_processes()
                self._check_idle()
                self._check_git()
            except Exception as e:
                logger.debug(f"Observer tick error: {e}")
            time.sleep(self._poll_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tick, daemon=True, name="jarvis-observer")
        self._thread.start()
        self.emit(ObserverEvent(
            type=EventType.CUSTOM,
            data={"message": "Observer started", "poll_interval": self._poll_interval},
            source="system",
        ))

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def simulate_event(self, event_type: str, data: Optional[dict] = None):
        self.emit(ObserverEvent(
            type=EventType(event_type) if event_type in EventType.__members__ else EventType.CUSTOM,
            data=data or {},
            source="simulation",
        ))
