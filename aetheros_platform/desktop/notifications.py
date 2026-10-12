"""Native notifications — send, queue, manage desktop notifications."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    id: str
    title: str
    body: str
    icon: str = ""
    urgency: str = "normal"
    actions: list[dict] = field(default_factory=list)
    timeout_ms: int = 5000
    silent: bool = False
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    read: bool = False
    category: str = "general"


class NotificationService:
    def __init__(self, max_history: int = 500):
        self._history: list[Notification] = []
        self._max_history = max_history
        self._listeners: list[callable] = []

    def on_notification(self, listener: callable):
        self._listeners.append(listener)

    def notify(self, notification: Notification):
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        for listener in self._listeners:
            try:
                listener(notification)
            except Exception as e:
                logger.error("Notification listener error: %s", e)
        logger.info("Notification: %s - %s", notification.title,
                     notification.body[:60])

    def send(self, title: str, body: str, icon: str = "",
              urgency: str = "normal", category: str = "general",
              timeout_ms: int = 5000, silent: bool = False) -> Notification:
        import uuid
        notification = Notification(
            id=str(uuid.uuid4()), title=title, body=body,
            icon=icon, urgency=urgency, timeout_ms=timeout_ms,
            silent=silent, category=category,
        )
        self.notify(notification)
        return notification

    def mark_read(self, notification_id: str) -> bool:
        for n in self._history:
            if n.id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_read(self):
        for n in self._history:
            n.read = True

    def get_history(self, limit: int = 50,
                     unread_only: bool = False) -> list[dict]:
        notifications = self._history
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        return [n.__dict__ for n in notifications[-limit:]]

    def get_unread_count(self) -> int:
        return sum(1 for n in self._history if not n.read)

    def clear(self):
        self._history.clear()

    def get_stats(self) -> dict:
        return {
            "total": len(self._history),
            "unread": self.get_unread_count(),
            "categories": len(set(n.category for n in self._history)),
        }

    def close(self):
        self._history.clear()
        self._listeners.clear()


# ---------------------------------------------------------------------------
# Toast action validation (Master 64.1 A2)
#
# Notification action payloads are UNTRUSTED INPUT. Approving task123 must
# verify against live state: the task exists, still awaits approval, the
# caller is authorized, the grant has not expired, the capability still
# matches, and policy still permits. The notification itself is never
# proof of authorization.
# ---------------------------------------------------------------------------

#: Actions the toast layer may ever carry. Anything else is rejected.
TOAST_ACTION_ALLOWLIST = frozenset({
    "approve", "deny", "open", "view", "stop", "retry", "dismiss",
})

#: Actions that resolve an approval MUST re-authorize (never trust payload).
APPROVAL_ACTIONS = frozenset({"approve", "deny"})


@dataclass
class ToastActionRequest:
    action_id: str
    task_id: str = ""
    agent_id: str = ""
    resource_id: str = ""
    user_id: str = ""
    expires_at: float = 0.0
    capability: str = ""


@dataclass
class ToastActionDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def validate_toast_action(
    req: ToastActionRequest,
    *,
    now: float | None = None,
    task_state: dict | None = None,
    is_authorized: bool = False,
    policy_permits: bool = True,
) -> ToastActionDecision:
    """Validate a toast action against live state.

    `task_state` is the caller's live record for `req.task_id` (keys:
    status, capability). Pure function — the Electron/backend caller
    supplies real state; tests inject fixtures.
    """
    import time as _time

    now = now if now is not None else _time.time()
    reasons: list[str] = []

    if req.action_id not in TOAST_ACTION_ALLOWLIST:
        return ToastActionDecision(False, [f"unknown action '{req.action_id}'"])
    if req.action_id in ("open", "view", "dismiss"):
        return ToastActionDecision(True, ["navigation-only action"])
    if not req.task_id:
        return ToastActionDecision(False, ["task-bound action without task_id"])
    if req.expires_at and now > req.expires_at:
        return ToastActionDecision(False, ["action expired"])
    if task_state is None:
        return ToastActionDecision(False, ["task not found"])
    if task_state.get("status") != "awaiting_approval" and req.action_id in APPROVAL_ACTIONS:
        reasons.append(f"task status is '{task_state.get('status')}', not awaiting_approval")
        return ToastActionDecision(False, reasons)
    if req.capability and task_state.get("capability") and \
            req.capability != task_state.get("capability"):
        return ToastActionDecision(False, ["capability mismatch — re-approval required"])
    if not is_authorized:
        return ToastActionDecision(False, ["caller not authorized for this task"])
    if not policy_permits:
        return ToastActionDecision(False, ["policy no longer permits execution"])
    return ToastActionDecision(True, ["live state verified"])
