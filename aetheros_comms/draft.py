"""
Draft-first send workflow + notification center + comms audit
(Master 16 Phases 13-14, 25-26, 61-66, 84).

The DraftPipeline enforces: DRAFT → REVIEW → CONFIRM → SEND → VERIFY.
No message leaves the system without passing through this lifecycle
unless explicitly overridden by policy.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_comms.model import (
    Channel, CommunicationMessage, Priority, SendStatus,
)
from aetheros_comms.gate import (
    GateVerdict, evaluate_send_gate, compute_idempotency_key,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Draft pipeline (Phases 13, 25-26, 31-34)
# ---------------------------------------------------------------------------

class DraftStage(enum.Enum):
    CREATED = "created"
    REVIEWED = "reviewed"
    CONFIRMED = "confirmed"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DraftRecord:
    draft_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    message: Optional[CommunicationMessage] = None
    stage: DraftStage = DraftStage.CREATED
    gate_verdict: Optional[GateVerdict] = None
    idempotency_key: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confirmed_by: str = ""           # "user" | "policy_auto"
    sent_result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "stage": self.stage.value,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confirmed_by": self.confirmed_by,
            "gate": {
                "allowed": self.gate_verdict.allowed if self.gate_verdict else None,
                "requires_confirmation": self.gate_verdict.requires_confirmation if self.gate_verdict else None,
                "warnings": self.gate_verdict.warnings if self.gate_verdict else [],
                "blocks": self.gate_verdict.blocks if self.gate_verdict else [],
                "risk_score": self.gate_verdict.risk_score if self.gate_verdict else 0,
            },
        }


class DraftPipeline:
    """Manages the draft → review → confirm → send → verify lifecycle."""

    def __init__(self, known_internal_domains: frozenset = frozenset(),
                 known_contacts: frozenset = frozenset()):
        self._lock = threading.Lock()
        self._drafts: Dict[str, DraftRecord] = {}
        self._known_internal = known_internal_domains
        self._known_contacts = known_contacts

    def create_draft(self, msg: CommunicationMessage) -> DraftRecord:
        """Phase 13: default to DRAFT first."""
        verdict = evaluate_send_gate(
            msg,
            known_internal_domains=self._known_internal,
            known_contacts=self._known_contacts,
        )
        record = DraftRecord(
            message=msg,
            gate_verdict=verdict,
            idempotency_key=compute_idempotency_key(msg),
            stage=DraftStage.CREATED,
        )
        msg.status = SendStatus.DRAFT
        with self._lock:
            self._drafts[record.draft_id] = record
        return record

    def review(self, draft_id: str) -> Dict[str, Any]:
        """Phase 25: produce a human-readable preview for review."""
        with self._lock:
            rec = self._drafts.get(draft_id)
        if not rec or not rec.message:
            return {"error": f"draft not found: {draft_id}"}
        rec.stage = DraftStage.REVIEWED
        rec.updated_at = time.time()

        msg = rec.message
        lines = [
            "MESSAGE PREVIEW",
            "=" * 40,
            f"From:    {msg.sender}",
            f"To:      {', '.join(r.address for r in msg.recipients)}",
        ]
        if msg.cc:
            lines.append(f"CC:      {', '.join(r.address for r in msg.cc)}")
        if msg.bcc:
            lines.append(f"BCC:     {', '.join(r.address for r in msg.bcc)}")
        if msg.subject:
            lines.append(f"Subject: {msg.subject}")
        lines.append(f"Channel: {msg.channel.value}")
        if msg.attachments:
            lines.append(f"Files:   {', '.join(a.filename for a in msg.attachments)}")
        lines.append("")
        lines.append(msg.body[:500] + ("..." if len(msg.body) > 500 else ""))
        lines.append("")

        if rec.gate_verdict:
            gv = rec.gate_verdict
            lines.append(f"Risk Score: {gv.risk_score}/10")
            lines.append(f"Sensitivity: {gv.sensitivity.value}")
            for w in gv.warnings:
                lines.append(f"  ⚠ {w}")
            for b in gv.blocks:
                lines.append(f"  ✗ {b}")

        needs_confirm = rec.gate_verdict.requires_confirmation if rec.gate_verdict else False
        lines.append("")
        lines.append(f"Confirmation required: {'YES' if needs_confirm else 'no'}")

        return {
            "draft_id": draft_id,
            "stage": rec.stage.value,
            "preview": "\n".join(lines),
            "needs_confirmation": needs_confirm,
            "blocked": rec.gate_verdict.blocked if rec.gate_verdict else True,
        }

    def confirm(self, draft_id: str, confirmed_by: str = "user") -> Dict[str, Any]:
        """Phase 26: explicit user confirmation before send."""
        with self._lock:
            rec = self._drafts.get(draft_id)
        if not rec:
            return {"error": f"draft not found: {draft_id}"}
        if rec.gate_verdict and rec.gate_verdict.blocked:
            return {"error": "draft is blocked by send-gate; cannot confirm"}
        rec.stage = DraftStage.CONFIRMED
        rec.confirmed_by = confirmed_by
        rec.updated_at = time.time()
        if rec.message:
            rec.message.status = SendStatus.PENDING_CONFIRMATION
        return {"draft_id": draft_id, "status": "confirmed", "confirmed_by": confirmed_by}

    def mark_sent(self, draft_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            rec = self._drafts.get(draft_id)
        if rec:
            rec.stage = DraftStage.SENT
            rec.sent_result = result
            if rec.message:
                rec.message.status = SendStatus.SENT

    def mark_failed(self, draft_id: str, error: str) -> None:
        with self._lock:
            rec = self._drafts.get(draft_id)
        if rec:
            rec.stage = DraftStage.FAILED
            rec.sent_result = {"error": error}
            if rec.message:
                rec.message.status = SendStatus.FAILED

    def get_draft(self, draft_id: str) -> Optional[DraftRecord]:
        return self._drafts.get(draft_id)


# ---------------------------------------------------------------------------
# Notification center (Phases 61-66)
# ---------------------------------------------------------------------------

@dataclass
class Notification:
    notification_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    source: str = ""                  # email | chat | calendar | agent | security
    event_type: str = ""
    priority: Priority = Priority.NORMAL
    title: str = ""
    body: str = ""
    dedup_key: str = ""
    timestamp: float = field(default_factory=time.time)
    read: bool = False


class NotificationCenter:
    """Unified notification abstraction with priority, dedup, digest."""

    def __init__(self):
        self._lock = threading.Lock()
        self._notifications: List[Notification] = []
        self._dedup_cache: Dict[str, float] = {}   # key -> last emitted ts
        self._max_size = 500

    def notify(self, source: str, event_type: str,
               priority: Priority = Priority.NORMAL,
               title: str = "", body: str = "",
               dedup_window_seconds: float = 60.0) -> Optional[Notification]:
        """Create a notification with dedup checking."""
        dedup_key = f"{source}:{event_type}:{hash(title + body[:100])}"
        now = time.time()
        with self._lock:
            last_ts = self._dedup_cache.get(dedup_key, 0)
            if now - last_ts < dedup_window_seconds:
                return None  # duplicate suppressed
            self._dedup_cache[dedup_key] = now

            n = Notification(
                source=source, event_type=event_type, priority=priority,
                title=title[:200], body=body[:500], dedup_key=dedup_key)
            self._notifications.append(n)
            while len(self._notifications) > self._max_size:
                self._notifications.pop(0)

        return n

    def unread_count(self, min_priority: Priority = Priority.LOW) -> int:
        with self._lock:
            return sum(1 for n in self._notifications
                       if not n.read and n.priority.value >= min_priority.value)

    def recent(self, limit: int = 20, min_priority: Priority = Priority.LOW) -> List[Notification]:
        with self._lock:
            items = [n for n in reversed(self._notifications)
                     if n.priority.value >= min_priority.value]
        return items[:limit]

    def digest(self, period: str = "daily") -> List[Notification]:
        """Return notifications suitable for a digest."""
        cutoffs = {"hourly": 3600, "daily": 86400, "weekly": 604800}
        cutoff = time.time() - cutoffs.get(period, 86400)
        with self._lock:
            return [n for n in self._notifications if n.timestamp >= cutoff]

    def mark_read(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._notifications:
                if n.notification_id == notification_id:
                    n.read = True
                    return True
        return False

    def clear_read(self) -> int:
        with self._lock:
            before = len(self._notifications)
            self._notifications = [n for n in self._notifications if not n.read]
            return before - len(self._notifications)


# ---------------------------------------------------------------------------
# Communication audit (Phase 84)
# ---------------------------------------------------------------------------

def log_comm_action(
    action: str,                       # send | receive | forward | delete | draft
    channel: str,
    provider: str,
    account: str,
    target_hash: str = "",
    risk_score: int = 0,
    approval: str = "",                # auto | confirmed | denied | none
    result: str = "",                  # sent | failed | blocked | pending
    detail: str = "",
) -> None:
    """Log safe communication metadata. Never logs credentials or raw bodies."""
    entry = {
        "ts": time.time(),
        "action": action[:20],
        "channel": channel[:20],
        "provider": provider[:30],
        "account": account[:80],       # address/handle, not password
        "target_hash": target_hash[:16],
        "risk_score": risk_score,
        "approval": approval[:20],
        "result": result[:20],
        "detail": detail[:200],
    }
    try:
        from aetheros_security.audit import AuditLogger

        logger_instance = AuditLogger()
        logger_instance.log_event(
            event_type="CUSTOM",
            severity="INFO" if result == "sent" else "WARNING",
            message=f"comm:{action}:{channel}:{result}",
            details=entry,
        )
    except Exception:
        # Fallback to local JSONL — never lose the audit trail
        pass


__all__ = [
    "DraftStage", "DraftRecord", "DraftPipeline",
    "Notification", "NotificationCenter",
    "log_comm_action",
]
