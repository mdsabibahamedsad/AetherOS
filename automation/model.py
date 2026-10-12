"""
AutomationDefinition model — the normalized view over a durable cron job.

Aetheros stores automations in the cron job store (``jobs.json``); this
module defines the Master-13 additive fields carried on that record and the
pure logic that normalizes, validates and derives lifecycle state from it.
It deliberately operates on plain dicts with no imports from ``cron`` so it
can be used from anywhere (including ``cron/``) without import cycles.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


class AutomationState:
    """Canonical automation lifecycle states (Master 13 Phase 2).

    The cron store keeps its own coarse ``state`` strings for backward
    compatibility; :func:`lifecycle_of` derives the richer canonical state
    additively from all fields on the record.
    """

    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    ENABLED = "enabled"
    DISABLED = "disabled"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    QUARANTINED = "quarantined"


ALL_STATES = frozenset(
    getattr(AutomationState, n)
    for n in dir(AutomationState)
    if not n.startswith("_") and n.isupper()
)

MISSED_POLICIES = (
    "catch_up",
    "skip",
    "run_on_start",
    "run_next_interval",
    "ask_user",
)

DEFAULT_MISSED_POLICY = "catch_up"

RESOURCE_LIMIT_KEYS = ("max_runtime_seconds", "max_turns")

BREAKER_KEYS = ("failure_threshold", "cooldown_seconds")

WATCHED_FIELDS = (
    "prompt",
    "schedule",
    "skills",
    "script",
    "deliver",
    "workdir",
    "model",
    "provider",
    "base_url",
    "enabled_toolsets",
    "no_agent",
    "timezone",
    "missed_policy",
    "resource_limits",
    "breaker",
    "trigger",
    "workflow",
)


def normalize_missed_policy(value: Any, default: str = DEFAULT_MISSED_POLICY) -> str:
    """Validate a missed-schedule policy value; return the canonical form."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    policy = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if policy not in MISSED_POLICIES:
        raise ValueError(
            f"Invalid missed_policy {value!r}. Use one of: {', '.join(MISSED_POLICIES)}"
        )
    return policy


def normalize_timezone(value: Any) -> Optional[str]:
    """Validate an IANA timezone identifier; empty/None returns None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    name = str(value).strip()
    try:
        ZoneInfo(name)
    except Exception as exc:
        raise ValueError(f"Invalid IANA timezone {value!r}: {exc}") from exc
    return name


def normalize_resource_limits(value: Any) -> Optional[Dict[str, int]]:
    """Normalize a resource_limits mapping to known positive-integer keys."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("resource_limits must be a mapping")
    limits: Dict[str, int] = {}
    for key in RESOURCE_LIMIT_KEYS:
        raw = value.get(key)
        if raw is None or raw == "":
            continue
        try:
            num = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"resource_limits.{key} must be an integer") from None
        if num <= 0:
            raise ValueError(f"resource_limits.{key} must be positive")
        limits[key] = num
    unknown = set(value.keys()) - set(RESOURCE_LIMIT_KEYS)
    if unknown:
        raise ValueError(
            f"Unknown resource limit(s): {', '.join(sorted(unknown))}. "
            f"Supported: {', '.join(RESOURCE_LIMIT_KEYS)}"
        )
    return limits or None


def normalize_breaker(value: Any) -> Optional[Dict[str, int]]:
    """Normalize a per-automation breaker config mapping."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("breaker must be a mapping")
    breaker: Dict[str, int] = {}
    for key in BREAKER_KEYS:
        raw = value.get(key)
        if raw is None or raw == "":
            continue
        try:
            num = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"breaker.{key} must be an integer") from None
        if num <= 0:
            raise ValueError(f"breaker.{key} must be positive")
        breaker[key] = num
    return breaker or None


def breaker_settings(job: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """Resolve effective breaker thresholds (per-job overrides > config > defaults)."""
    defaults = {"failure_threshold": 5, "cooldown_seconds": 3600, "quarantine_after_opens": 3}
    section = cfg.get("automation", {}) if isinstance(cfg, dict) else {}
    global_breaker = section.get("breaker", {}) if isinstance(section.get("breaker"), dict) else {}
    resolved = dict(defaults)
    for key in ("failure_threshold", "cooldown_seconds", "quarantine_after_opens"):
        value = global_breaker.get(key)
        if isinstance(value, (int, float)) and value > 0:
            resolved[key] = int(value)
    per_job = job.get("breaker") if isinstance(job.get("breaker"), dict) else {}
    for key in ("failure_threshold", "cooldown_seconds"):
        value = per_job.get(key)
        if isinstance(value, (int, float)) and value > 0:
            resolved[key] = int(value)
    return resolved


def _breaker_open(job: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> bool:
    opened_at = job.get("breaker_opened_at")
    if not opened_at:
        return False
    from automation.schedule_time import parse_iso_utc

    opened = parse_iso_utc(opened_at)
    if opened is None:
        return True
    cooldown = breaker_settings(job, cfg)["cooldown_seconds"]
    from datetime import datetime, timezone

    age = (datetime.now(timezone.utc) - opened).total_seconds()
    return age < cooldown


def lifecycle_of(
    job: Dict[str, Any],
    running_ids: Optional[Iterable[str]] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> str:
    """Derive the canonical automation lifecycle state from a job record.

    Most-specific conditions win. The derivation is additive — records that
    predate Master 13 (no new fields) map onto the same states as before.
    """
    if job.get("quarantined"):
        return AutomationState.QUARANTINED
    if _breaker_open(job, cfg):
        return AutomationState.BLOCKED
    state = str(job.get("state") or "").strip()
    enabled = job.get("enabled", True)
    if state == "paused" or not enabled:
        return AutomationState.PAUSED if state == "paused" else AutomationState.DISABLED
    if running_ids is not None and job.get("id") in set(running_ids):
        return AutomationState.RUNNING
    if state == "error":
        return AutomationState.FAILED
    if state == "completed":
        return AutomationState.COMPLETED
    return AutomationState.ENABLED


def definition_fingerprint(job: Dict[str, Any]) -> str:
    """Stable hash over the fields that constitute the automation definition."""
    payload = {key: job.get(key) for key in WATCHED_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_automation(job: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return a list of human-readable problems; empty list means valid."""
    problems: List[str] = []
    schedule = job.get("schedule")
    if not isinstance(schedule, dict) or not schedule.get("kind"):
        problems.append("schedule is missing or unparsed")
    else:
        kind = schedule.get("kind")
        if kind == "cron":
            try:
                import croniter  # noqa: F401
            except ImportError:
                problems.append(
                    "cron schedule requires the 'croniter' package in this environment"
                )
    try:
        normalize_timezone(job.get("timezone"))
    except ValueError as exc:
        problems.append(str(exc))
    try:
        normalize_missed_policy(job.get("missed_policy"), default="")
    except ValueError as exc:
        problems.append(str(exc))
    try:
        normalize_resource_limits(job.get("resource_limits"))
    except ValueError as exc:
        problems.append(str(exc))
    try:
        normalize_breaker(job.get("breaker"))
    except ValueError as exc:
        problems.append(str(exc))
    try:
        from automation.triggers import normalize_trigger

        normalize_trigger(job.get("trigger"))
    except ValueError as exc:
        problems.append(str(exc))
    try:
        from automation.workflow import normalize_workflow

        normalize_workflow(job.get("workflow"))
    except ValueError as exc:
        problems.append(str(exc))
    has_prompt = bool(str(job.get("prompt") or "").strip())
    has_script = bool(str(job.get("script") or "").strip())
    if job.get("no_agent"):
        if not has_script:
            problems.append("no_agent automations require a script")
    elif not has_prompt and not has_script:
        problems.append("automation needs a prompt or a script")
    workdir = job.get("workdir")
    if workdir and not re.match(r"^~|^[A-Za-z]:[/\\]|^/", str(workdir)):
        problems.append(f"workdir {workdir!r} must be an absolute path")
    return problems
