"""
Audit Logging
=============

Tamper-evident, exportable audit logging for:
- Authentication events
- Authorization decisions
- Policy changes
- Plugin lifecycle events
- Workflow execution
- Administrative actions
- Approval outcomes
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditEvent(enum.Enum):
    # Authentication
    USER_LOGIN = "auth:login"
    USER_LOGOUT = "auth:logout"
    USER_LOGIN_FAILED = "auth:login_failed"
    TOKEN_CREATED = "auth:token_created"
    TOKEN_REVOKED = "auth:token_revoked"

    # Authorization
    ACCESS_GRANTED = "authz:granted"
    ACCESS_DENIED = "authz:denied"
    ROLE_ASSIGNED = "authz:role_assigned"
    ROLE_REVOKED = "authz:role_revoked"

    # Policy
    POLICY_CREATED = "policy:created"
    POLICY_UPDATED = "policy:updated"
    POLICY_DELETED = "policy:deleted"
    POLICY_EVALUATED = "policy:evaluated"
    POLICY_EXCEPTION = "policy:exception"

    # Plugin lifecycle
    PLUGIN_INSTALLED = "plugin:installed"
    PLUGIN_REMOVED = "plugin:removed"
    PLUGIN_ENABLED = "plugin:enabled"
    PLUGIN_DISABLED = "plugin:disabled"
    PLUGIN_UPDATED = "plugin:updated"

    # Workflow
    WORKFLOW_STARTED = "workflow:started"
    WORKFLOW_COMPLETED = "workflow:completed"
    WORKFLOW_FAILED = "workflow:failed"
    WORKFLOW_APPROVED = "workflow:approved"
    WORKFLOW_REJECTED = "workflow:rejected"

    # Administration
    ORG_CREATED = "admin:org_created"
    ORG_UPDATED = "admin:org_updated"
    ORG_DELETED = "admin:org_deleted"
    USER_CREATED = "admin:user_created"
    USER_DISABLED = "admin:user_disabled"
    USER_DELETED = "admin:user_deleted"
    SETTINGS_CHANGED = "admin:settings_changed"

    # Approvals
    APPROVAL_REQUESTED = "approval:requested"
    APPROVAL_APPROVED = "approval:approved"
    APPROVAL_REJECTED = "approval:rejected"
    APPROVAL_ESCALATED = "approval:escalated"

    # Secrets
    SECRET_ACCESSED = "secret:accessed"
    SECRET_ROTATED = "secret:rotated"
    SECRET_PROVIDER_CHANGED = "secret:provider_changed"

    # Governance
    COMPLIANCE_CHECK = "governance:compliance_check"
    RETENTION_ENFORCED = "governance:retention_enforced"


@dataclass
class AuditLogEntry:
    """A single audit log entry with tamper-evident chaining."""
    event: AuditEvent
    actor_id: str
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: str = ""
    user_agent: str = ""
    org_id: str = ""

    # Tamper-evident chain
    previous_hash: str = ""
    entry_hash: str = ""
    sequence: int = 0

    def compute_hash(self) -> str:
        """Compute the cryptographic hash of this entry."""
        payload = (
            f"{self.id}|{self.event.value}|{self.actor_id}|{self.resource}|"
            f"{json.dumps(self.details, sort_keys=True)}|"
            f"{self.timestamp.isoformat()}|{self.previous_hash}|{self.sequence}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event": self.event.value,
            "actor_id": self.actor_id,
            "resource": self.resource,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "org_id": self.org_id,
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash or self.compute_hash(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class AuditLog:
    """Tamper-evident audit log with cryptographic chaining.

    Each entry contains the hash of the previous entry, forming a
    chain that makes retroactive modification detectable.
    """

    def __init__(self) -> None:
        self._entries: List[AuditLogEntry] = []
        self._sequence: int = 0

    def record(
        self,
        event: AuditEvent,
        actor_id: str,
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
        org_id: str = "",
        ip_address: str = "",
    ) -> AuditLogEntry:
        """Record a new audit log entry."""
        import uuid

        self._sequence += 1
        previous_hash = self._entries[-1].entry_hash if self._entries else ""

        entry = AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            event=event,
            actor_id=actor_id,
            resource=resource,
            details=details or {},
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            org_id=org_id,
            previous_hash=previous_hash,
            sequence=self._sequence,
        )
        entry.entry_hash = entry.compute_hash()
        self._entries.append(entry)
        return entry

    def query(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[AuditEvent] = None,
        actor_id: Optional[str] = None,
        org_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditLogEntry]:
        """Query audit log entries with optional filters."""
        results = list(self._entries)

        if event_type:
            results = [e for e in results if e.event == event_type]
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        if org_id:
            results = [e for e in results if e.org_id == org_id]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        results.sort(key=lambda e: e.sequence, reverse=True)
        return results[offset:offset + limit]

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain.

        Returns True if the chain is intact (no tampering detected).
        """
        for i, entry in enumerate(self._entries):
            expected_previous = ""
            if i > 0:
                expected_previous = self._entries[i - 1].entry_hash
            if entry.previous_hash != expected_previous:
                logger.error(
                    "Audit chain broken at entry %s (seq %d): "
                    "expected previous_hash %s, got %s",
                    entry.id, entry.sequence,
                    expected_previous, entry.previous_hash,
                )
                return False
            if entry.entry_hash != entry.compute_hash():
                logger.error(
                    "Audit entry %s (seq %d) has been tampered with",
                    entry.id, entry.sequence,
                )
                return False
        return True

    def count(self) -> int:
        return len(self._entries)


class AuditExporter:
    """Export audit logs in various formats."""

    def __init__(self, audit_log: AuditLog) -> None:
        self._log = audit_log

    def to_json(self, entries: Optional[List[AuditLogEntry]] = None) -> str:
        """Export entries as a JSON array."""
        entries = entries or self._log._entries
        return json.dumps([e.to_dict() for e in entries], indent=2, default=str)

    def to_json_lines(self, entries: Optional[List[AuditLogEntry]] = None) -> str:
        """Export entries as newline-delimited JSON."""
        entries = entries or self._log._entries
        return "\n".join(json.dumps(e.to_dict(), default=str) for e in entries)
