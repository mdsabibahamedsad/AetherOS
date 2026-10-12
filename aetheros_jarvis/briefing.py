"""Jarvis Mode — daily briefing.

Generates a morning summary from real data sources: today's agenda, pending
tasks, project status, calendar events, recent activity, and reminders.
Weather is optional (included only when a source is configured). The briefing
is produced on demand and cached; it never fabricates data it doesn't have.
"""

from __future__ import annotations

import logging
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_jarvis.models import BriefingSection, DailyBriefing

logger = logging.getLogger(__name__)


class DailyBriefingEngine:
    """Builds a :class:`DailyBriefing` from injected or discovered sources.

    Call :meth:`generate` for a fresh briefing. Sections that have no data
    render an explicit empty message rather than invented content.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else None
        self._lock = threading.RLock()
        self._calendar: List[Dict[str, Any]] = []
        self._tasks: List[Dict[str, Any]] = []
        self._emails: List[Dict[str, Any]] = []
        self._activity: List[str] = []
        self._project_status: List[str] = []
        self._reminders: List[str] = []
        self._weather: Optional[str] = None
        self._last: Optional[DailyBriefing] = None

    # ------------------------------------------------------------------
    # Data sources
    # ------------------------------------------------------------------

    def set_calendar(self, events: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._calendar = list(events)

    def set_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._tasks = list(tasks)

    def set_emails(self, emails: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._emails = list(emails)

    def set_activity(self, activity: List[str]) -> None:
        with self._lock:
            self._activity = list(activity)

    def set_project_status(self, status: List[str]) -> None:
        with self._lock:
            self._project_status = list(status)

    def set_reminders(self, reminders: List[str]) -> None:
        with self._lock:
            self._reminders = list(reminders)

    def set_weather(self, weather: str) -> None:
        """Set weather line (optional — only included when provided)."""
        with self._lock:
            self._weather = weather

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, today: Optional[date] = None) -> DailyBriefing:
        with self._lock:
            today = today or date.today()
            sections = [
                self._agenda(),
                self._pending_tasks(),
                self._project_status_section(),
                self._emails_section(),
                self._recent_activity(),
                self._reminders_section(),
            ]
            if self._weather:
                sections.append(BriefingSection(title="Weather", items=[self._weather], empty_message=""))
            briefing = DailyBriefing(
                date=today.isoformat(),
                sections=sections,
            )
            self._last = briefing
            return briefing

    def _agenda(self) -> BriefingSection:
        items = []
        for event in self._calendar:
            start = event.get("start", "")
            title = event.get("title", "event")
            if start:
                items.append(f"{start[:16].replace('T', ' ')} — {title}")
            else:
                items.append(title)
        return BriefingSection(title="Today's Agenda", items=items, empty_message="No events on your calendar.")

    def _pending_tasks(self) -> BriefingSection:
        items = []
        for task in self._tasks:
            title = task.get("title", "task")
            due = task.get("due", "")
            status = task.get("status", "pending")
            if status == "done":
                continue
            line = f"{title}"
            if due:
                line += f" (due {due[:10]})"
            items.append(line)
        return BriefingSection(title="Pending Tasks", items=items, empty_message="No pending tasks.")

    def _project_status_section(self) -> BriefingSection:
        return BriefingSection(
            title="Project Status",
            items=list(self._project_status),
            empty_message="No project status recorded.",
        )

    def _emails_section(self) -> BriefingSection:
        items = []
        for email in self._emails:
            subject = email.get("subject", "email")
            sender = email.get("from", "unknown")
            items.append(f"From {sender}: {subject}")
        return BriefingSection(title="Important Emails", items=items, empty_message="No important emails.")

    def _recent_activity(self) -> BriefingSection:
        return BriefingSection(
            title="Recent Activity",
            items=list(self._activity),
            empty_message="No recent activity recorded.",
        )

    def _reminders_section(self) -> BriefingSection:
        return BriefingSection(
            title="Reminders",
            items=list(self._reminders),
            empty_message="No reminders set.",
        )

    def to_markdown(self) -> str:
        if self._last is None:
            return "# Daily Briefing\n\nNo briefing generated yet."
        return self._last.to_markdown()

    def last(self) -> Optional[DailyBriefing]:
        with self._lock:
            return self._last

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "generated": self._last is not None,
                "calendar_events": len(self._calendar),
                "tasks": len(self._tasks),
                "emails": len(self._emails),
                "weather": self._weather is not None,
            }
