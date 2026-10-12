"""
Schedule conflict detection for automations (Master 13 Phase 69).

Conflicts are DETECTED AND REPORTED, never auto-blocked — the same event may
legitimately feed several automations, and workdir jobs already serialize by
design. The caller (CLI dry-run/show) decides how to present them.

Kinds reported:

- ``duplicate_schedule``   two or more enabled automations share an identical
  parsed schedule (same kind + parameters). Often intentional copies; worth
  confirming.
- ``workdir_overlap``      two or more enabled automations declare the same
  ``workdir`` and their next runs fall within ``WINDOW_SECONDS`` of each
  other. They run serially in the sequential pool, so combined latency adds.
- ``event_fanout``         two or more enabled automations carry an event
  trigger subscribing to the same event type with no payload filters. One
  noisy event then fans out into N runs (each still gated by cooldown,
  breaker, rate cap).

Pure module: no I/O beyond reading the records passed in.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

WINDOW_SECONDS = 120


def _schedule_key(job: Dict[str, Any]) -> Optional[str]:
    schedule = job.get("schedule")
    if not isinstance(schedule, dict) or not schedule.get("kind"):
        return None
    kind = schedule.get("kind")
    if kind == "interval":
        return f"interval:{schedule.get('minutes')}"
    if kind == "cron":
        return f"cron:{schedule.get('expr')}"
    if kind == "once":
        return None  # one-shots cannot recur-conflict
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    return dt


def _enabled(job: Dict[str, Any]) -> bool:
    return bool(job.get("enabled", True)) and not job.get("quarantined")


def find_conflicts(
    jobs: List[Dict[str, Any]],
    *,
    window_seconds: int = WINDOW_SECONDS,
) -> List[Dict[str, Any]]:
    """Return a list of conflict descriptors across enabled automations."""
    enabled = [j for j in jobs or [] if _enabled(j)]
    conflicts: List[Dict[str, Any]] = []

    # duplicate_schedule
    by_schedule: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for job in enabled:
        key = _schedule_key(job)
        if key:
            by_schedule[key].append(job)
    for key, group in sorted(by_schedule.items()):
        if len(group) > 1:
            conflicts.append({
                "kind": "duplicate_schedule",
                "refs": [str(j.get("id")) for j in group],
                "names": [str(j.get("name") or j.get("id")) for j in group],
                "detail": f"{len(group)} automations share schedule {key}",
            })

    # workdir_overlap (next runs within window of each other)
    by_workdir: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for job in enabled:
        workdir = str(job.get("workdir") or "").strip()
        nxt = _parse_dt(job.get("next_run_at"))
        if workdir and nxt is not None:
            by_workdir[workdir].append((nxt, job))
    for workdir, entries in sorted(by_workdir.items()):
        if len(entries) < 2:
            continue
        entries.sort(key=lambda pair: pair[0])
        clustered: List[Dict[str, Any]] = []
        cluster_times: List[datetime] = []
        for nxt, job in entries:
            if cluster_times and (nxt - min(cluster_times)).total_seconds() <= window_seconds:
                clustered.append(job)
                cluster_times.append(nxt)
            else:
                if len(clustered) > 1:
                    break
                clustered = [job]
                cluster_times = [nxt]
        if len(clustered) > 1:
            conflicts.append({
                "kind": "workdir_overlap",
                "refs": [str(j.get("id")) for j in clustered],
                "names": [str(j.get("name") or j.get("id")) for j in clustered],
                "detail": (
                    f"{len(clustered)} automations share workdir {workdir!r} with "
                    f"runs within {window_seconds}s — they will serialize"
                ),
            })

    # event_fanout (same event type, unfiltered)
    by_event: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for job in enabled:
        trigger = job.get("trigger")
        if not isinstance(trigger, dict) or trigger.get("kind") != "event":
            continue
        if trigger.get("filters"):
            continue
        for event_type in trigger.get("event_types") or []:
            by_event[str(event_type)].append(job)
    for event_type, group in sorted(by_event.items()):
        if len(group) > 1:
            conflicts.append({
                "kind": "event_fanout",
                "refs": [str(j.get("id")) for j in group],
                "names": [str(j.get("name") or j.get("id")) for j in group],
                "detail": (
                    f"{len(group)} unfiltered automations fire on '{event_type}' "
                    f"— one event triggers all of them"
                ),
            })

    return conflicts


def conflicts_for(
    ref_id: str, jobs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Conflicts that involve one specific automation id."""
    return [
        c for c in find_conflicts(jobs)
        if str(ref_id) in (c.get("refs") or [])
    ]
