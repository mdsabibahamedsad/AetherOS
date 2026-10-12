from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from aetheros_automation.models.models import CalendarEvent

logger = logging.getLogger(__name__)

try:
    import caldav

    _HAS_CALDAV = True
except ImportError:
    _HAS_CALDAV = False
    logger.warning("caldav not available; CalDAV sync disabled")

try:
    from icalendar import Calendar, Event as ICalEvent

    _HAS_ICAL = True
except ImportError:
    _HAS_ICAL = False
    logger.warning("icalendar not available; iCal support disabled")


class CalendarHandler:
    """Manage calendar events with local iCal storage and optional CalDAV sync."""

    def __init__(self) -> None:
        self._caldav_client: caldav.DAVClient | None = None
        self._calendar: caldav.Calendar | None = None
        self._storage_dir: Path = Path.home() / ".aetheros" / "calendar"
        self._events_file: Path = self._storage_dir / "events.json"
        self._events: dict[str, dict[str, Any]] = {}
        self._load_events()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_events(self) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        if self._events_file.exists():
            try:
                raw = self._events_file.read_text(encoding="utf-8")
                self._events = json.loads(raw)
            except Exception as exc:
                logger.warning("Failed to load calendar events: %s", exc)
                self._events = {}
        else:
            self._events = {}

    def _save_events(self) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._events_file.write_text(
            json.dumps(self._events, indent=2, default=str), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # CalDAV
    # ------------------------------------------------------------------

    async def connect_caldav(
        self,
        url: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        url = url or os.getenv("CALDAV_URL", "")
        user = user or os.getenv("CALDAV_USER", "")
        password = password or os.getenv("CALDAV_PASS", "")

        if not _HAS_CALDAV:
            raise ImportError("caldav library is required for CalDAV sync")

        self._caldav_client = caldav.DAVClient(url=url, username=user, password=password)
        principal = self._caldav_client.principal()
        calendars = principal.calendars()
        if calendars:
            self._calendar = calendars[0]
            logger.info("Connected to CalDAV: %s", url)

    @staticmethod
    def _caldav_sync_available() -> bool:
        return _HAS_CALDAV

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def create_event(self, event: CalendarEvent) -> str:
        event_id = str(uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        entry: dict[str, Any] = {
            "id": event_id,
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "attendees": event.attendees,
            "location": event.location,
            "reminders": event.reminders,
            "created_at": now,
            "updated_at": now,
        }

        self._events[event_id] = entry
        self._save_events()

        if self._calendar and _HAS_CALDAV:
            await self._sync_to_caldav(entry)

        logger.info("Created event '%s' (%s)", event.title, event_id)
        return event_id

    async def list_events(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> list[dict[str, Any]]:
        start_dt = _parse_dt(start_date) if start_date else datetime.min
        end_dt = _parse_dt(end_date) if end_date else datetime.max

        results: list[dict[str, Any]] = []
        for entry in self._events.values():
            ev_start = _parse_dt(entry.get("start_time", ""))
            if ev_start and start_dt <= ev_start <= end_dt:
                results.append(entry)
        return sorted(results, key=lambda e: e.get("start_time", ""))

    async def update_event(self, event_id: str, updates: dict[str, Any]) -> None:
        if event_id not in self._events:
            raise ValueError(f"Event {event_id} not found")
        self._events[event_id].update(updates)
        self._events[event_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_events()

        if self._calendar and _HAS_CALDAV:
            await self._sync_to_caldav(self._events[event_id])

        logger.info("Updated event %s", event_id)

    async def delete_event(self, event_id: str) -> None:
        if event_id not in self._events:
            raise ValueError(f"Event {event_id} not found")
        del self._events[event_id]
        self._save_events()

        if self._calendar and _HAS_CALDAV:
            await self._remove_from_caldav(event_id)

        logger.info("Deleted event %s", event_id)

    async def get_upcoming(self, limit: int = 5) -> list[dict[str, Any]]:
        now = datetime.utcnow().isoformat() + "Z"
        upcoming = [
            e for e in self._events.values() if e.get("start_time", "") >= now
        ]
        upcoming.sort(key=lambda e: e.get("start_time", ""))
        return upcoming[:limit]

    async def check_availability(self, time_slot: str) -> bool:
        slot_start = _parse_dt(time_slot)
        slot_end = slot_start + timedelta(hours=1) if slot_start else None
        if not slot_start or not slot_end:
            raise ValueError(f"Invalid time_slot: {time_slot}")

        for entry in self._events.values():
            ev_start = _parse_dt(entry.get("start_time", ""))
            ev_end = _parse_dt(entry.get("end_time", ""))
            if ev_start and ev_end:
                if slot_start < ev_end and slot_end > ev_start:
                    return False
        return True

    @staticmethod
    async def suggest_times(
        attendees: list[str] | None = None,
        duration: int = 30,
        date_range: str | None = None,
    ) -> list[str]:
        start = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        end = start + timedelta(days=7)
        if date_range:
            parts = date_range.split(",")
            if len(parts) == 2:
                start = _parse_dt(parts[0]) or start
                end = _parse_dt(parts[1]) or end

        slots: list[str] = []
        current = start
        while current < end and len(slots) < 5:
            slot_end = current + timedelta(minutes=duration)
            ts = current.isoformat()
            slots.append(ts)
            current += timedelta(hours=1)

        return slots

    async def set_reminder(self, event_id: str, minutes_before: int) -> None:
        if event_id not in self._events:
            raise ValueError(f"Event {event_id} not found")
        reminders = self._events[event_id].get("reminders", [])
        if minutes_before not in reminders:
            reminders.append(minutes_before)
        self._events[event_id]["reminders"] = sorted(reminders)
        self._events[event_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_events()
        logger.info("Set reminder %dmin before event %s", minutes_before, event_id)

    @staticmethod
    async def join_meeting(url: str) -> None:
        if sys.platform == "win32":
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        logger.info("Opened meeting link: %s", url)

    # ------------------------------------------------------------------
    # CalDAV sync
    # ------------------------------------------------------------------

    async def _sync_to_caldav(self, entry: dict[str, Any]) -> None:
        if not self._calendar or not _HAS_CALDAV or not _HAS_ICAL:
            return
        loop = asyncio.get_running_loop()

        def _push() -> None:
            cal = Calendar()
            cal.add("prodid", "-//Aether Automation//aetheros//EN")
            cal.add("version", "2.0")
            ical_event = ICalEvent()
            ical_event.add("uid", entry["id"])
            ical_event.add("summary", entry["title"])
            ical_event.add("description", entry.get("description", ""))
            ical_event.add("location", entry.get("location", ""))
            if entry.get("start_time"):
                ical_event.add("dtstart", _parse_dt(entry["start_time"]))
            if entry.get("end_time"):
                ical_event.add("dtend", _parse_dt(entry["end_time"]))
            for attendee in entry.get("attendees", []):
                ical_event.add("attendee", attendee)
            cal.add_component(ical_event)

            existing = self._calendar.search(uid=entry["id"])
            data_str = cal.to_ical().decode("utf-8")
            if existing:
                existing[0].set_data(data_str)
                existing[0].save()
            else:
                self._calendar.save_event(data_str)

        await loop.run_in_executor(None, _push)

    async def _remove_from_caldav(self, event_id: str) -> None:
        if not self._calendar or not _HAS_CALDAV:
            return
        loop = asyncio.get_running_loop()

        def _remove() -> None:
            existing = self._calendar.search(uid=event_id)
            for ev in existing:
                ev.delete()

        await loop.run_in_executor(None, _remove)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value.rstrip("Z"), fmt)
        except ValueError:
            continue
    return None
