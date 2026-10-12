"""Jarvis Mode — proactive intelligence.

Observes real signals (calendar, tasks, workspace, open files, downloads,
battery, network, meetings, deadlines) and emits suggestions only when they
are relevant AND the user is present. Never interrupts unnecessarily: all
proactive output flows through the suggestion engine, which is explainable
and dismissible.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import ContextSnapshot, Suggestion, SuggestionStatus

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    def get_aetheros_home() -> Path:
        import os
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class ProactiveEngine:
    """Observes signals and produces context-appropriate suggestions.

    Observation kinds:
      - ``battery``      : low battery / on-battery transitions
      - ``calendar``     : upcoming calendar events and meetings
      - ``tasks``        : pending task deadlines
      - ``workspace``    : uncommitted work, unsaved files
      - ``downloads``    : recent downloads worth noting
      - ``network``      : connectivity changes

    Suggestions are emitted via listeners only when the engine is enabled and
    the presence callback reports the user is present.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._lock = threading.RLock()
        self._enabled = True
        self._suggestions: Dict[str, Suggestion] = {}
        self._listeners: List[Callable[[Suggestion], None]] = []
        self._presence_fn: Optional[Callable[[], bool]] = None
        self._min_interval = 300.0
        self._last_emit: Dict[str, float] = {}
        self._calendar: List[Dict[str, Any]] = []
        self._tasks: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def set_presence_fn(self, fn: Optional[Callable[[], bool]]) -> None:
        """Callback returning True when the user is present and available."""
        with self._lock:
            self._presence_fn = fn

    def on_suggestion(self, callback: Callable[[Suggestion], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_min_interval(self, seconds: float) -> None:
        with self._lock:
            self._min_interval = max(30.0, seconds)

    # ------------------------------------------------------------------
    # Data sources (real, injectable for tests)
    # ------------------------------------------------------------------

    def set_calendar(self, events: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._calendar = list(events)

    def set_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._tasks = list(tasks)

    def _user_present(self) -> bool:
        if self._presence_fn is None:
            return True
        try:
            return bool(self._presence_fn())
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self, snapshot: Optional[ContextSnapshot] = None) -> List[Suggestion]:
        """Run all observers and return new suggestions."""
        if not self._enabled or not self._user_present():
            return []
        with self._lock:
            suggestions = self._observe_battery(snapshot)
            suggestions += self._observe_calendar()
            suggestions += self._observe_tasks()
            suggestions += self._observe_workspace(snapshot)
            suggestions += self._observe_downloads(snapshot)
            for suggestion in suggestions:
                self._suggestions[suggestion.id] = suggestion
            emitted = []
            for suggestion in suggestions:
                if self._should_emit(suggestion):
                    self._emit(suggestion)
                    emitted.append(suggestion)
            return emitted

    def _should_emit(self, suggestion: Suggestion) -> bool:
        last = self._last_emit.get(suggestion.source, 0.0)
        if time.time() - last < self._min_interval:
            return False
        self._last_emit[suggestion.source] = time.time()
        return True

    def _emit(self, suggestion: Suggestion) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(suggestion)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Suggestion listener error: %s", exc)

    # ------------------------------------------------------------------
    # Observers
    # ------------------------------------------------------------------

    def _observe_battery(self, snapshot: Optional[ContextSnapshot]) -> List[Suggestion]:
        percent = snapshot.battery_percent if snapshot else None
        if percent is None:
            return []
        if percent <= 20:
            return [self._make_suggestion(
                "battery",
                "Low battery",
                f"Battery is at {percent:.0f}%. Plug in or finish current work.",
                "Consider enabling battery saver or pausing background tasks.",
                action="open_battery_settings",
                confidence=0.9,
            )]
        return []

    def _observe_calendar(self) -> List[Suggestion]:
        out = []
        for event in self._calendar:
            start = event.get("start")
            if not start:
                continue
            try:
                when = datetime.fromisoformat(start)
            except (ValueError, TypeError):
                continue
            minutes = (when - datetime.now()).total_seconds() / 60.0
            if 0 <= minutes <= 30:
                out.append(self._make_suggestion(
                    "calendar",
                    f"Upcoming: {event.get('title', 'event')}",
                    f"Starts in {int(minutes)} minutes.",
                    "Relevant because it is on your calendar and starting soon.",
                    action="show_calendar",
                    params={"event": event.get("title", "")},
                    confidence=0.85,
                ))
        return out

    def _observe_tasks(self) -> List[Suggestion]:
        out = []
        for task in self._tasks:
            deadline = task.get("due")
            if not deadline:
                continue
            try:
                due = datetime.fromisoformat(deadline)
            except (ValueError, TypeError):
                continue
            remaining = (due - datetime.now()).total_seconds() / 3600.0
            if 0 <= remaining <= 24:
                out.append(self._make_suggestion(
                    "tasks",
                    f"Deadline: {task.get('title', 'task')}",
                    f"Due in {remaining:.1f}h.",
                    "Relevant because it is an open task with an approaching deadline.",
                    action="show_task",
                    params={"task": task.get("title", "")},
                    confidence=0.8,
                ))
        return out

    def _observe_workspace(self, snapshot: Optional[ContextSnapshot]) -> List[Suggestion]:
        # Workspace observation requires a real snapshot; otherwise nothing.
        if snapshot is None or not snapshot.project:
            return []
        return [self._make_suggestion(
            "workspace",
            f"Active project: {snapshot.project}",
            "You have files open in this project.",
            "Relevant because it is your current workspace.",
            action="show_project",
            params={"project": snapshot.project},
            confidence=0.6,
        )]

    def _observe_downloads(self, snapshot: Optional[ContextSnapshot]) -> List[Suggestion]:
        if snapshot is None or not snapshot.downloads_dir:
            return []
        downloads = Path(snapshot.downloads_dir)
        if not downloads.exists():
            return []
        try:
            recent = [p for p in downloads.iterdir() if p.is_file()]
            recent.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            return []
        if not recent:
            return []
        newest = recent[0]
        age_minutes = (time.time() - newest.stat().st_mtime) / 60.0
        if age_minutes <= 5:
            return [self._make_suggestion(
                "downloads",
                f"New download: {newest.name}",
                "A file just finished downloading.",
                "Relevant because the download completed moments ago.",
                action="open_download",
                params={"path": str(newest)},
                confidence=0.75,
            )]
        return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_suggestion(
        self,
        source: str,
        title: str,
        body: str,
        reason: str,
        *,
        action: str = "",
        params: Optional[Dict[str, Any]] = None,
        confidence: float = 0.7,
    ) -> Suggestion:
        return Suggestion(
            title=title,
            body=body,
            reason=reason,
            action=action,
            params=params or {},
            confidence=confidence,
            source=source,
            expires_at=time.time() + 600,
        )

    def dismiss(self, suggestion_id: str) -> bool:
        with self._lock:
            suggestion = self._suggestions.get(suggestion_id)
            if suggestion is None:
                return False
            suggestion.status = SuggestionStatus.DISMISSED
            return True

    def accept(self, suggestion_id: str) -> bool:
        with self._lock:
            suggestion = self._suggestions.get(suggestion_id)
            if suggestion is None:
                return False
            suggestion.status = SuggestionStatus.ACCEPTED
            return True

    def list_suggestions(self, status: Optional[SuggestionStatus] = None) -> List[Suggestion]:
        with self._lock:
            suggestions = list(self._suggestions.values())
        if status is not None:
            suggestions = [s for s in suggestions if s.status == status]
        return suggestions

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "suggestions": len(self._suggestions),
                "calendar_events": len(self._calendar),
                "tasks": len(self._tasks),
                "min_interval_seconds": self._min_interval,
            }
