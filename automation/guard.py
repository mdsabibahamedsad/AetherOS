"""
Automation safety guards (Master 13 Phases 27, 45-49, 94).

Four mechanisms, all additive over the cron spine:

- Circuit breaker: consecutive failures open a breaker for a cooldown window;
  repeated openings quarantine the automation. Pure evaluation lives in
  :func:`evaluate_result`; persistence goes through the locked
  ``cron.jobs.apply_job_field_updates`` helper.
- Quarantine: automations that keep tripping the breaker stop being scheduled
  entirely until ``recover`` clears them.
- Emergency stop: a profile-local state file that makes every future tick
  return without dispatching new work. In-flight runs finish naturally.
- Safe mode: config gate that suppresses all external deliveries from
  background automation while still executing and persisting outputs.

No secrets are ever written to any state this module creates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _automation_dir() -> Path:
    from aetheros_constants import get_aetheros_home

    path = get_aetheros_home() / "automation"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


# ---------------------------------------------------------------------------
# Emergency stop (Phase 48)
# ---------------------------------------------------------------------------

ESTOP_FILENAME = ".emergency_stop.json"


def estop_path() -> Path:
    return _automation_dir() / ESTOP_FILENAME


def estop_active() -> Optional[Dict[str, Any]]:
    """Return the active emergency-stop record, or None."""
    path = estop_path()
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("active"):
            return {
                "reason": str(data.get("reason") or ""),
                "at": str(data.get("at") or ""),
            }
    except (OSError, ValueError):
        logger.debug("Failed to read emergency stop state", exc_info=True)
    return None


def set_estop(enabled: bool, reason: str = "") -> Optional[Dict[str, Any]]:
    """Engage or lift the global background-automation emergency stop."""
    path = estop_path()
    if not enabled:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            logger.warning("Failed to clear emergency stop file", exc_info=True)
        return None
    record = {
        "active": True,
        "reason": str(reason or "").strip(),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        path.write_text(json.dumps(record), encoding="utf-8")
    except OSError:
        logger.error("Failed to write emergency stop file", exc_info=True)
    return record


# ---------------------------------------------------------------------------
# Safe mode (Phase 49)
# ---------------------------------------------------------------------------

def safe_mode_enabled(cfg: Optional[Dict[str, Any]] = None) -> bool:
    """Whether background automation must suppress external side effects."""
    from automation.schedule_time import automation_defaults

    section = automation_defaults(cfg)
    return bool(section.get("safe_mode", False))


# ---------------------------------------------------------------------------
# Circuit breaker + quarantine (Phases 27, 94)
# ---------------------------------------------------------------------------

def gate_job(
    job: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Tuple[bool, str, bool]:
    """Decide whether an automation may fire right now.

    Returns ``(allowed, reason, half_open)``. ``half_open`` is True when the
    breaker cooldown elapsed and the caller should clear ``breaker_opened_at``
    so one probe run may execute (failure re-opens immediately because the
    failure streak is still at/above threshold).
    """
    if job.get("quarantined"):
        return False, "quarantined", False
    opened_at = job.get("breaker_opened_at")
    if not opened_at:
        return True, "", False
    opened = _parse_ts(opened_at)
    now = now or datetime.now(timezone.utc)
    cooldown = breaker_cooldown_seconds(job, cfg)
    if opened is None or (now - opened).total_seconds() >= cooldown:
        return True, "cooldown_elapsed", True
    remaining = int(cooldown - (now - opened).total_seconds())
    return False, f"breaker_open ({remaining}s left)", False


def breaker_cooldown_seconds(job: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> int:
    from automation.model import breaker_settings

    return breaker_settings(job, cfg)["cooldown_seconds"]


def evaluate_result(
    job: Dict[str, Any],
    success: bool,
    error: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Compute post-run breaker bookkeeping for one execution.

    Returns ``(updates, action)``; ``updates`` is None when nothing changed.
    Actions:

    - ``reset``      — success cleared the failure streak.
    - ``none``       — ordinary failure below threshold / already handled.
    - ``reopen``     — failure while the breaker was half-open.
    - ``open``       — threshold reached; breaker opens for cooldown.
    - ``quarantine`` — too many openings; automation quarantined.

    This function is pure — it never persists anything itself.
    """
    from automation.model import breaker_settings

    now = now or datetime.now(timezone.utc)
    settings = breaker_settings(job, cfg)

    if success:
        if job.get("failure_streak"):
            return {"failure_streak": 0}, "reset"
        return None, "none"

    streak = int(job.get("failure_streak") or 0) + 1
    updates: Dict[str, Any] = {"failure_streak": streak}

    if job.get("breaker_opened_at"):
        updates["breaker_opened_at"] = now.isoformat()
        return updates, "reopen"

    if streak < settings["failure_threshold"]:
        return updates, "none"

    opens = int(job.get("breaker_opens") or 0) + 1
    updates["breaker_opens"] = opens
    updates["breaker_opened_at"] = now.isoformat()

    if opens >= settings["quarantine_after_opens"]:
        updates["quarantined"] = True
        reason = str(error or "repeated failures").strip().replace("\n", " ")[:200]
        updates["quarantine_reason"] = (
            f"quarantined after {opens} breaker openings; last error: {reason}"
        )
        return updates, "quarantine"

    return updates, "open"


def record_result(
    job_id: str,
    success: bool,
    error: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist breaker bookkeeping after one execution. Returns the action."""
    from cron.jobs import apply_job_field_updates, load_jobs

    snapshot = None
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            snapshot = job
            break
    if snapshot is None:
        return "none"

    updates, action = evaluate_result(snapshot, success, error=error, cfg=cfg)
    if not updates:
        return "none"
    saved = apply_job_field_updates(job_id, updates)
    if saved is None:
        logger.warning("Breaker update lost: job %s vanished mid-update", job_id)
        return "none"
    return action


def recover_automation(ref_id: str) -> bool:
    """Clear quarantine and breaker state so an automation can run again."""
    from cron.jobs import apply_job_field_updates

    updates = {
        "quarantined": False,
        "quarantine_reason": None,
        "breaker_opened_at": None,
        "failure_streak": 0,
    }
    saved = apply_job_field_updates(ref_id, updates)
    return saved is not None


def _parse_ts(value: Any) -> Optional[datetime]:
    from automation.schedule_time import parse_iso_utc

    parsed = parse_iso_utc(value)
    if parsed is not None:
        return parsed
    try:
        naive = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return naive.replace(tzinfo=timezone.utc)


def breaker_notice(action: str, name: str, ref: str, error: Optional[str]) -> Optional[str]:
    """Human-readable notice text for breaker/quarantine transitions."""
    if action == "quarantine":
        return (
            f"⛔ Automation '{name}' has been QUARANTINED after repeated failures.\n"
            f"Last error: {str(error or 'unknown').strip()[:300]}\n"
            f"It will not run again until you inspect it and run:\n"
            f"  aetheros automation recover {ref}"
        )
    if action == "open":
        return (
            f"⚡ Automation '{name}' failed repeatedly — paused via circuit breaker "
            f"for a cooldown period. It will retry automatically afterwards.\n"
            f"Last error: {str(error or 'unknown').strip()[:300]}"
        )
    return None
