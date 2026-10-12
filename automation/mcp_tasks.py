"""
MCP Tasks extension adapter (Master 13 Phases 55-58).

Integrates MCP servers that support the Tasks extension WITHOUT assuming any
server does:

- :func:`server_supports_tasks` inspects a server's advertised capabilities;
- :func:`normalize_mcp_task` maps MCP task state onto the canonical
  AutomationState set while PRESERVING the raw MCP payload under
  ``mcp`` (nothing is lost);
- :func:`poll_task` implements bounded exponential-backoff polling for
  environments without push notifications;
- :func:`request_cancellation` propagates user cancellation; when the server
  lacks ``tasks/cancel``, returns ``"unsupported"`` so the caller can mark
  cancellation pending and stop orchestrating safely.

Aetheros' internal run store remains authoritative for Aetheros-owned
workflows; this adapter only mirrors remote task state for observability
and gating. No live wiring ships here — hosts opt in by passing their own
client callable.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# MCP Tasks state → AutomationState (Master 13 Phase 2).
MCP_STATE_MAP = {
    "working": "running",
    "input_required": "waiting_approval",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}

DEFAULT_POLL_INTERVAL = 2.0
MAX_POLL_INTERVAL = 60.0


def server_supports_tasks(capabilities: Optional[Dict[str, Any]]) -> bool:
    """Whether a server's capabilities advertise the Tasks extension."""
    if not isinstance(capabilities, dict):
        return False
    tasks = capabilities.get("tasks")
    return isinstance(tasks, dict) or tasks is True


def normalize_mcp_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Map one MCP task record onto the AetherOS envelope.

    Returns {task_id, status, mcp} where ``status`` is an AutomationState
    value and ``mcp`` retains the untouched source record (Phase 56: no
    MCP-specific information is lost).
    """
    if not isinstance(task, dict):
        return {"task_id": "", "status": "unknown", "mcp": {}}
    status = str(task.get("status") or "").strip().lower()
    mapped = MCP_STATE_MAP.get(status, "unknown")
    return {
        "task_id": str(task.get("taskId") or task.get("id") or ""),
        "status": mapped,
        "message": str(task.get("statusMessage") or ""),
        "mcp": task,
    }


def poll_task(
    fetch: Callable[[], Optional[Dict[str, Any]]],
    *,
    until_terminal: bool = True,
    interval: float = DEFAULT_POLL_INTERVAL,
    max_interval: float = MAX_POLL_INTERVAL,
    timeout: float = 300.0,
) -> Optional[Dict[str, Any]]:
    """Bounded polling of one remote task (Phase 57).

    ``fetch()`` returns the raw MCP task dict or None on transient failure.
    Backoff doubles per miss up to ``max_interval``; total wall time is capped
    by ``timeout`` so a wedged server can never pin a worker thread.
    """
    deadline = time.monotonic() + max(1.0, timeout)
    delay = max(0.2, interval)
    while True:
        try:
            task = fetch()
        except Exception:
            logger.debug("MCP task fetch failed", exc_info=True)
            task = None
        if task is not None:
            normalized = normalize_mcp_task(task)
            if not until_terminal or normalized["status"] in (
                "completed", "failed", "cancelled", "unknown",
            ):
                return normalized
        if time.monotonic() >= deadline:
            return None
        time.sleep(delay)
        delay = min(delay * 2, max_interval)


def request_cancellation(
    cancel_fn: Optional[Callable[[str], Any]], task_id: str
) -> str:
    """Propagate cancellation (Phase 58).

    Returns ``"sent"`` when ``tasks/cancel`` was invoked successfully,
    ``"failed"`` when it errored, or ``"unsupported"`` when no cancel
    capability is wired — callers then mark cancellation pending locally and
    simply stop further orchestration.
    """
    if cancel_fn is None:
        return "unsupported"
    try:
        result = cancel_fn(task_id)
        if isinstance(result, dict) and result.get("error"):
            return "failed"
        return "sent"
    except Exception:
        logger.warning("tasks/cancel failed for %s", task_id, exc_info=True)
        return "failed"
