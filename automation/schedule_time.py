"""
Timezone-aware scheduling helpers for automations (Master 13 Phases 6-8, 67).

Timezone semantics:

- ``timezone`` on an automation is an IANA identifier (e.g. ``Asia/Kolkata``).
  When unset, the scheduler's configured timezone (``aetheros_time``) applies,
  exactly as before Master 13.
- ``cron`` schedules are wall-clock schedules: the next occurrence is computed
  with the base time expressed in the automation's zone, so ``0 9 * * *``
  stays at 09:00 local across DST transitions. zoneinfo resolves ambiguous
  fall-back times to the first occurrence (fold=0); nonexistent spring-forward
  wall times are shifted forward to the next real instant.
- ``interval`` schedules are absolute-duration schedules ("every 2h" = every
  7200 measured seconds) and are intentionally DST-immune.
- ``once`` schedules store an absolute offset-aware timestamp and need no
  conversion.

Missed-run policy semantics (evaluated when a due run is found stale):

- ``catch_up`` (default): fire if late by <= half a period (clamped
  120 s - 2 h), else fast-forward. This is the historical behavior.
- ``skip`` / ``run_next_interval``: never fire late; realign to the next
  boundary. One-shots past their grace window expire instead of firing.
- ``run_on_start``: run once immediately after restart even if late, bounded
  by ``missed_policy_max_age_hours`` (default 24 h), then resume schedule.
- ``ask_user``: same as run_on_start but the delivery carries a note asking
  the user whether to keep this policy (headless runs cannot prompt inline).

No behavior changes silently: policies only apply when explicitly configured
per automation or via config.yaml ``automation.*`` defaults.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


def resolve_zone(name: Any) -> Optional[ZoneInfo]:
    """Resolve an IANA zone name; returns None for empty values."""
    if name is None or (isinstance(name, str) and not name.strip()):
        return None
    try:
        return ZoneInfo(str(name).strip())
    except Exception as exc:
        logger.warning("Invalid IANA timezone %r: %s — falling back to default", name, exc)
        return None


def job_zone(job: Dict[str, Any]) -> Optional[ZoneInfo]:
    """Return the ZoneInfo configured on an automation record, if any."""
    return resolve_zone(job.get("timezone"))


def parse_iso_utc(value: str) -> Optional[datetime]:
    """Parse an ISO timestamp into a UTC-aware datetime; None on failure."""
    try:
        dt = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(_utc())


def _utc() -> Any:
    from datetime import timezone

    return timezone.utc


def automation_defaults(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the ``automation:`` section of config.yaml (loaded lazily)."""
    if cfg is None:
        try:
            from aetheros_cli.config import load_config

            cfg = load_config()
        except Exception:
            cfg = {}
    section = cfg.get("automation") if isinstance(cfg, dict) else {}
    return section if isinstance(section, dict) else {}


def effective_missed_policy(
    job: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None
) -> Tuple[str, int]:
    """Resolve (policy, max_late_seconds) from per-job overrides > config > defaults."""
    from automation.model import DEFAULT_MISSED_POLICY, normalize_missed_policy

    defaults = automation_defaults(cfg)
    raw = job.get("missed_policy") or defaults.get("missed_policy") or DEFAULT_MISSED_POLICY
    policy = normalize_missed_policy(raw)
    max_age_raw = job.get("missed_policy_max_age_seconds")
    if isinstance(max_age_raw, (int, float)) and max_age_raw > 0:
        max_late = int(max_age_raw)
    else:
        hours = defaults.get("missed_policy_max_age_hours", 24)
        try:
            max_late = max(1, int(float(hours) * 3600))
        except (TypeError, ValueError):
            max_late = 24 * 3600
    return policy, max_late


def decide_missed_run(
    job: Dict[str, Any],
    *,
    kind: str,
    lateness_seconds: float,
    grace_seconds: int,
    now: Optional[datetime] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str]]:
    """Decide what to do with one stale due run.

    Returns ``(action, note)`` where action is one of:

    - ``fire``          — include the run in due jobs. A non-None ``note``
                          marks a policy-recovered late run; callers attach it
                          to the delivery so nothing runs silently.
    - ``fast_forward``  — skip this run; next_run_at moves to the future.
    - ``expire``        — disable the one-shot automation entirely.

    ``grace_seconds`` is the caller-computed catch-up tolerance (half period,
    clamped) for recurring kinds and the one-shot grace for ``once``.
    Never raises on valid input; unknown kinds fire (legacy behavior).
    """
    policy, max_late = effective_missed_policy(job, cfg)

    if kind in {"cron", "interval"}:
        if lateness_seconds <= grace_seconds:
            return "fire", None
        if policy == "catch_up":
            return "fast_forward", None
        if policy in {"skip", "run_next_interval"}:
            return "fast_forward", None
        if lateness_seconds <= max_late:
            label = "ask_user" if policy == "ask_user" else policy
            note = (
                f"[missed-schedule] This run was missed while AetherOS was offline "
                f"(late by {int(lateness_seconds)}s; policy={label})."
            )
            if policy == "ask_user":
                note += (
                    " Keeping this policy? Adjust it any time with "
                    "`aetheros automation policy <name> --set catch_up`."
                )
            return "fire", note
        return "fast_forward", None

    if kind == "once":
        if lateness_seconds > grace_seconds and policy in {"skip", "run_next_interval"}:
            return (
                "expire",
                f"One-shot expired {int(lateness_seconds)}s past schedule "
                f"(missed_policy={policy})",
            )
        return "fire", None

    return "fire", None


def preview_next_runs(
    schedule: Any,
    count: int = 5,
    tz_name: Optional[str] = None,
    base: Optional[str] = None,
) -> List[datetime]:
    """Preview upcoming execution times for a schedule (Master 13 Phase 67).

    Respects the automation timezone; returns aware datetimes expressed in
    that zone (or the scheduler default when no zone is set). Uses the same
    ``compute_next_run`` implementation as the live scheduler so previews can
    never drift from reality.
    """
    if count < 1:
        count = 1
    from cron.jobs import compute_next_run

    zone = resolve_zone(tz_name)
    if isinstance(schedule, str):
        from cron.jobs import parse_schedule

        schedule = parse_schedule(schedule)

    runs: List[datetime] = []
    last_run_at = base
    seen = set()
    for _ in range(count):
        nxt_iso = compute_next_run(schedule, last_run_at=last_run_at, tz=zone)
        if not nxt_iso:
            break
        nxt = datetime.fromisoformat(nxt_iso)
        if nxt.isoformat() in seen:
            break
        seen.add(nxt.isoformat())
        if zone is not None:
            nxt = nxt.astimezone(zone)
        runs.append(nxt)
        last_run_at = nxt_iso
    return runs
