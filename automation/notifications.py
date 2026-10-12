"""
Automation notification preferences (Master 13 Phases 59-61).

Config (config.yaml → automation.notifications)::

    notifications:
      events: []                 # empty = default set below
      quiet_hours: {start: null, end: null}   # "22:30" / "07:00" local time
      min_priority: normal       # low | normal | important

Critical events (quarantine, waiting-approval) ALWAYS notify — security and
gating information is never silenced by preferences.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_EVENTS = (
    "automation.waiting_approval",
    "automation.quarantined",
    "automation.failed",
    "automation.cancelled",
    "automation.blocked",
)

CRITICAL_EVENTS = frozenset({
    "automation.quarantined",
    "automation.waiting_approval",
})

PRIORITIES = ("low", "normal", "important")


def _settings(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if cfg is None:
        try:
            from aetheros_cli.config import load_config

            cfg = load_config()
        except Exception:
            cfg = {}
    section = cfg.get("automation", {}) if isinstance(cfg, dict) else {}
    prefs = section.get("notifications", {}) if isinstance(section.get("notifications"), dict) else {}
    return {
        "events": prefs.get("events") or [],
        "quiet_start": (prefs.get("quiet_hours") or {}).get("start"),
        "quiet_end": (prefs.get("quiet_hours") or {}).get("end"),
        "min_priority": str(prefs.get("min_priority") or "normal").strip().lower(),
    }


def _parse_hhmm(value: Any) -> Optional[Tuple[int, int]]:
    if not value or not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return (hour, minute)
    return None


def _in_quiet_window(now: datetime, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
    minutes_now = now.hour * 60 + now.minute
    start_m, end_m = start[0] * 60 + start[1], end[0] * 60 + end[1]
    if start_m == end_m:
        return False
    if start_m < end_m:
        return start_m <= minutes_now < end_m
    # Window wraps midnight (e.g. 22:30 → 07:00).
    return minutes_now >= start_m or minutes_now < end_m


def should_notify(event_type: str, cfg: Optional[Dict[str, Any]] = None,
                  now: Optional[datetime] = None) -> bool:
    """Whether one automation event should reach the user right now.

    Critical security/gating events (quarantine, waiting-approval) always
    return True — neither an explicit allowlist nor quiet hours may silence
    them (Phase 61: never bypass critical notifications).
    """
    settings = _settings(cfg)
    event_type = str(event_type or "")

    if event_type in CRITICAL_EVENTS:
        return True

    allowlist = [e for e in settings["events"] if e]
    if allowlist:
        matched = any(
            event_type == pattern
            or (pattern.endswith("*") and event_type.startswith(pattern[:-1]))
            for pattern in allowlist
        )
        if not matched:
            return False
    elif event_type not in DEFAULT_EVENTS:
        return False

    now = now or datetime.now()
    start = _parse_hhmm(settings["quiet_start"])
    end = _parse_hhmm(settings["quiet_end"])
    if start and end and _in_quiet_window(now, start, end):
        logger.debug("Suppressed %s during quiet hours", event_type)
        return False
    return True


def retention_days(cfg: Optional[Dict[str, Any]] = None) -> int:
    """History/run-record retention for pruning (Phase 72)."""
    if cfg is None:
        try:
            from aetheros_cli.config import load_config

            cfg = load_config()
        except Exception:
            cfg = {}
    section = cfg.get("automation", {}) if isinstance(cfg, dict) else {}
    history = section.get("history", {}) if isinstance(section.get("history"), dict) else {}
    try:
        days = int(history.get("retention_days", 30))
    except (TypeError, ValueError):
        days = 30
    return max(1, days)
