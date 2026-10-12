from __future__ import annotations

import os
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class JarvisContext:
    current_project: Optional[str] = None
    current_project_path: Optional[str] = None
    current_branch: Optional[str] = None
    current_provider: Optional[str] = None
    current_model: Optional[str] = None
    open_chats: list[str] = field(default_factory=list)
    recent_actions: list[dict] = field(default_factory=list)
    running_tasks: list[str] = field(default_factory=list)
    active_agent: Optional[str] = None
    open_files: list[str] = field(default_factory=list)
    terminal_cwd: Optional[str] = None
    is_idle: bool = True
    idle_started_at: Optional[float] = None
    idle_duration: float = 0.0
    last_activity_at: float = 0.0
    session_started_at: float = 0.0

    MAX_RECENT_ACTIONS = 50


class ContextEngine:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "jarvis" / "context.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ctx = JarvisContext(session_started_at=time.time(), last_activity_at=time.time())
        self._listeners: list[callable] = []
        self._load()

    def on_change(self, listener: callable) -> callable:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify(self):
        for listener in self._listeners:
            try:
                listener(self._ctx)
            except Exception:
                pass

    def _load(self):
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text())
                for key, value in data.items():
                    if hasattr(self._ctx, key):
                        setattr(self._ctx, key, value)
                self._ctx.session_started_at = time.time()
        except Exception as e:
            logger.debug(f"Could not load context: {e}")

    def _save(self):
        try:
            self._storage_path.write_text(json.dumps(asdict(self._ctx), indent=2))
        except Exception as e:
            logger.debug(f"Could not save context: {e}")

    @property
    def context(self) -> JarvisContext:
        return self._ctx

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._ctx, key):
                setattr(self._ctx, key, value)
        self._ctx.last_activity_at = time.time()
        self._notify()
        self._save()

    def log_action(self, action: str, details: Optional[dict] = None):
        entry = {
            "timestamp": time.time(),
            "action": action,
            "details": details or {},
        }
        self._ctx.recent_actions.insert(0, entry)
        self._ctx.recent_actions = self._ctx.recent_actions[:self._ctx.MAX_RECENT_ACTIONS]
        self._ctx.last_activity_at = time.time()
        self._save()

    def mark_idle(self, is_idle: bool):
        self._ctx.is_idle = is_idle
        if is_idle and self._ctx.idle_started_at is None:
            self._ctx.idle_started_at = time.time()
        elif not is_idle:
            self._ctx.idle_started_at = None
            self._ctx.idle_duration = 0.0
        self._save()

    def get_idle_duration(self) -> float:
        if self._ctx.is_idle and self._ctx.idle_started_at:
            self._ctx.idle_duration = time.time() - self._ctx.idle_started_at
            return self._ctx.idle_duration
        return 0.0

    def reset(self):
        self._ctx = JarvisContext(session_started_at=time.time(), last_activity_at=time.time())
        self._notify()
        self._save()

    def to_dict(self) -> dict:
        return asdict(self._ctx)

    def set_project(self, path: Optional[str]):
        if path:
            self._ctx.current_project_path = path
            self._ctx.current_project = Path(path).name
            git_dir = Path(path) / ".git"
            if git_dir.exists():
                try:
                    import subprocess
                    branch = subprocess.check_output(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=path, stderr=subprocess.DEVNULL, timeout=5
                    ).decode().strip()
                    self._ctx.current_branch = branch
                except Exception:
                    pass
        else:
            self._ctx.current_project_path = None
            self._ctx.current_project = None
            self._ctx.current_branch = None
        self._save()

    def set_model(self, provider: str, model: str):
        self._ctx.current_provider = provider
        self._ctx.current_model = model
        self._save()

    def track_open_file(self, filepath: str):
        if filepath not in self._ctx.open_files:
            self._ctx.open_files.append(filepath)
            self._ctx.open_files = self._ctx.open_files[-20:]
        self._save()

    def set_terminal_cwd(self, cwd: str):
        self._ctx.terminal_cwd = cwd
        self._save()
