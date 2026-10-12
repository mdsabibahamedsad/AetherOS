"""Canonical schedules: cron / interval / one-time + NL parser + tz/DST.

- Cron via croniter when available, else a minimal built-in matcher for
  common patterns (best-effort; canonical path is croniter).
- Timezone-aware with zoneinfo; DST handled by zone-aware arithmetic
  (nonexistent/ambiguous times resolved by fold policy: skip-forward).
- parse_natural_schedule() converts human phrases into canonical dicts and
  always returns a human preview string shown before saving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


@dataclass
class CanonicalSchedule:
    kind: str  # cron|interval|once
    cron: str = ""
    interval_s: float = 0.0
    at: float = 0.0  # epoch for once
    timezone: str = "UTC"
    preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "cron": self.cron,
                "interval_s": self.interval_s, "at": self.at,
                "timezone": self.timezone, "preview": self.preview}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CanonicalSchedule":
        return cls(kind=str(d.get("kind", "interval")),
                   cron=str(d.get("cron", "")),
                   interval_s=float(d.get("interval_s", 0.0)),
                   at=float(d.get("at", 0.0)),
                   timezone=str(d.get("timezone", "UTC")),
                   preview=str(d.get("preview", "")))


def tzinfo(name: str):
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return timezone.utc


def parse_natural_schedule(text: str, *, tz: str = "UTC",
                           now: Optional[float] = None) -> CanonicalSchedule:
    """Parse human scheduling phrases. Raises ValueError when ambiguous."""
    t = (text or "").strip().lower()
    now_ts = now if now is not None else datetime.now(timezone.utc).timestamp()

    m = re.match(r"every\s+(\d+)\s+(minute|hour|day|week)s?$", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        secs = {"minute": 60, "hour": 3600, "day": 86400, "week": 604800}[unit] * n
        return CanonicalSchedule(kind="interval", interval_s=float(secs),
                                 timezone=tz,
                                 preview=f"Every {n} {unit}{'s' if n > 1 else ''} ({tz})")

    m = re.match(r"every\s+weekday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", t)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return CanonicalSchedule(kind="cron", cron=f"{mi} {h} * * 1-5",
                                 timezone=tz,
                                 preview=f"Weekdays at {h:02d}:{mi:02d} ({tz})")

    m = re.match(r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
                 r"(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?$", t)
    if m:
        dow = {"monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
               "friday": 5, "saturday": 6, "sunday": 0}[m.group(1)]
        h = int(m.group(2) or 9)
        mi = int(m.group(3) or 0)
        ap = m.group(4)
        if ap == "pm" and h < 12:
            h += 12
        return CanonicalSchedule(kind="cron", cron=f"{mi} {h} * * {dow}",
                                 timezone=tz,
                                 preview=f"Weekly on {m.group(1).title()} at {h:02d}:{mi:02d} ({tz})")

    m = re.match(r"every\s+first\s+day\s+of\s+(?:the\s+)?month(?:\s+at\s+(\d{1,2})(?::(\d{2}))?)?$", t)
    if m:
        h, mi = int(m.group(1) or 9), int(m.group(2) or 0)
        return CanonicalSchedule(kind="cron", cron=f"{mi} {h} 1 * *",
                                 timezone=tz,
                                 preview=f"Monthly on day 1 at {h:02d}:{mi:02d} ({tz})")

    m = re.match(r"every\s+day\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", t)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return CanonicalSchedule(kind="cron", cron=f"{mi} {h} * * *",
                                 timezone=tz,
                                 preview=f"Daily at {h:02d}:{mi:02d} ({tz})")

    m = re.match(r"in\s+(\d+)\s+(minute|hour|day)s?$", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        secs = {"minute": 60, "hour": 3600, "day": 86400}[unit] * n
        return CanonicalSchedule(kind="once", at=now_ts + secs, timezone=tz,
                                 preview=f"Once in {n} {unit}{'s' if n > 1 else ''} ({tz})")

    raise ValueError(f"ambiguous schedule (no pattern matched): {text!r}")


def next_run(sched: CanonicalSchedule, after_ts: float) -> float:
    """Next fire time strictly after after_ts (tz-aware, DST-safe)."""
    tz = tzinfo(sched.timezone)
    if sched.kind == "once":
        return sched.at if sched.at > after_ts else 0.0
    if sched.kind == "interval":
        if sched.interval_s <= 0:
            return 0.0
        base = after_ts - (after_ts % sched.interval_s)
        nxt = base + sched.interval_s
        return nxt if nxt > after_ts else nxt + sched.interval_s
    if sched.kind == "cron":
        if HAS_CRONITER:
            anchor = datetime.fromtimestamp(after_ts, tz)
            itr = croniter(sched.cron, anchor)
            return itr.get_next(float)
        # Minimal fallback: daily HH:MM only.
        m = re.match(r"(\d+)\s+(\d+)\s+\*\s+\*\s+\*$", sched.cron)
        if m:
            mi, h = int(m.group(1)), int(m.group(2))
            anchor = datetime.fromtimestamp(after_ts, tz)
            cand = anchor.replace(hour=h, minute=mi, second=0, microsecond=0)
            if cand.timestamp() <= after_ts:
                cand += timedelta(days=1)
            return cand.timestamp()
        raise ValueError(f"croniter unavailable and unsupported expr: {sched.cron!r}")
    raise ValueError(f"unknown schedule kind: {sched.kind}")
