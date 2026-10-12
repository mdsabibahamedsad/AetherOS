"""Global Application State Manager for AetherOS.

Provides centralized state management for all system components:
agent, gateway, provider, runtime, memory, UI, and persistent state.

Thread-safe. Supports change listeners and persistence.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class AppState(Enum):
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ComponentState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class StateEntry:
    value: Any
    timestamp: float = field(default_factory=time.time)
    source: str = ""


StateChangeCallback = Callable[[str, Any, Any], None]


class StateManager:
    """Thread-safe global state manager.

    Manages state for:
    - Application lifecycle (AppState)
    - Component states (ComponentState per component)
    - Global key-value store
    - Persistent state synchronized to disk
    """

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._app_state: AppState = AppState.INITIALIZING
        self._component_states: Dict[str, ComponentState] = {}
        self._store: Dict[str, StateEntry] = {}
        self._listeners: Dict[str, List[StateChangeCallback]] = {}
        self._persist_path = persist_path
        self._persist_dirty = False
        self._persist_timer: Optional[threading.Timer] = None

        if self._persist_path and self._persist_path.exists():
            self._load_persistent()

    # ------------------------------------------------------------------
    # Application state
    # ------------------------------------------------------------------

    @property
    def app_state(self) -> AppState:
        return self._app_state

    @app_state.setter
    def app_state(self, new_state: AppState) -> None:
        with self._lock:
            old = self._app_state
            self._app_state = new_state
            self._notify("_app_state", old.value, new_state.value)

    @property
    def is_running(self) -> bool:
        return self._app_state == AppState.RUNNING

    @property
    def is_initialized(self) -> bool:
        return self._app_state not in (AppState.INITIALIZING, AppState.STARTING)

    # ------------------------------------------------------------------
    # Component states
    # ------------------------------------------------------------------

    def set_component_state(self, component: str, state: ComponentState) -> None:
        with self._lock:
            old = self._component_states.get(component)
            self._component_states[component] = state
            self._notify(f"component.{component}", old.value if old else None, state.value)

    def get_component_state(self, component: str) -> ComponentState:
        return self._component_states.get(component, ComponentState.UNINITIALIZED)

    def component_is_ready(self, component: str) -> bool:
        return self._component_states.get(component) == ComponentState.READY

    @property
    def all_components_ready(self) -> bool:
        with self._lock:
            return all(
                s == ComponentState.READY
                for s in self._component_states.values()
            )

    @property
    def component_states(self) -> Dict[str, ComponentState]:
        with self._lock:
            return dict(self._component_states)

    # ------------------------------------------------------------------
    # Key-value store
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any, source: str = "") -> None:
        with self._lock:
            old = self._store.get(key)
            self._store[key] = StateEntry(value=value, source=source)
            self._notify(key, old.value if old else None, value)
            self._mark_dirty()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._store.get(key)
            return entry.value if entry else default

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                old = self._store.pop(key)
                self._notify(key, old.value, None)
                self._mark_dirty()
                return True
            return False

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return {k: e.value for k, e in self._store.items()}

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._mark_dirty()

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def update(self, mapping: Dict[str, Any], source: str = "") -> None:
        with self._lock:
            for key, value in mapping.items():
                old = self._store.get(key)
                self._store[key] = StateEntry(value=value, source=source)
                self._notify(key, old.value if old else None, value)
            self._mark_dirty()

    def snapshot(self) -> Dict[str, Any]:
        """Return a complete snapshot of all state."""
        with self._lock:
            return {
                "app_state": self._app_state.value,
                "components": {
                    k: v.value for k, v in self._component_states.items()
                },
                "store": {k: e.value for k, e in self._store.items()},
            }

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def on_change(self, key: str, callback: StateChangeCallback) -> None:
        with self._lock:
            if key not in self._listeners:
                self._listeners[key] = []
            self._listeners[key].append(callback)

    def on_any_change(self, callback: StateChangeCallback) -> None:
        with self._lock:
            if "*" not in self._listeners:
                self._listeners["*"] = []
            self._listeners["*"].append(callback)

    def remove_listener(self, key: str, callback: StateChangeCallback) -> None:
        with self._lock:
            listeners = self._listeners.get(key, [])
            if callback in listeners:
                listeners.remove(callback)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist_now(self) -> None:
        """Synchronously persist state to disk."""
        if not self._persist_path:
            return
        with self._lock:
            data = self.snapshot()
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._persist_path.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                tmp.replace(self._persist_path)
                self._persist_dirty = False
            except OSError:
                pass

    def _load_persistent(self) -> None:
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            store = data.get("store", {})
            for k, v in store.items():
                self._store[k] = StateEntry(value=v, source="persist")
        except (json.JSONDecodeError, OSError):
            pass

    def _mark_dirty(self) -> None:
        if not self._persist_path:
            return
        if not self._persist_dirty:
            self._persist_dirty = True
            self._schedule_persist()

    def _schedule_persist(self) -> None:
        if self._persist_timer and self._persist_timer.is_alive():
            return
        self._persist_timer = threading.Timer(5.0, self.persist_now)
        self._persist_timer.daemon = True
        self._persist_timer.start()

    def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        for pattern in (key, "*"):
            listeners = self._listeners.get(pattern, [])
            for cb in listeners:
                try:
                    cb(key, old_value, new_value)
                except Exception:
                    pass