"""
Audit Logging for AetherOS
==========================

Record all security-relevant events:
    - Permission Grants/Denials
    - Plugin Installations
    - Workflow Execution
    - Automation Actions
    - Security Events
    - Authentication Events

Usage::

    from aetheros_security.audit import AuditLogger

    logger = AuditLogger()
    logger.log("permission_granted", user="plugin-x", permission="filesystem:read")
    entries = logger.get_recent(100)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_REVOKED = "permission_revoked"
    PLUGIN_INSTALLED = "plugin_installed"
    PLUGIN_REMOVED = "plugin_removed"
    PLUGIN_UPDATED = "plugin_updated"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    AUTOMATION_TRIGGERED = "automation_triggered"
    SECURITY_ALERT = "security_alert"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    SECRET_CREATED = "secret_created"
    SECRET_ACCESSED = "secret_accessed"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


class AuditSeverity(Enum):
    """Audit event severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """An audit log entry."""
    event_type: AuditEventType
    timestamp: float
    severity: AuditSeverity = AuditSeverity.INFO
    user: str = ""
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    session_id: str = ""
    message: str = ""


class AuditLogger:
    """Logs security-relevant events.

    Usage::

        audit = AuditLogger()

        # Log an event
        audit.log(
            AuditEventType.PERMISSION_GRANTED,
            user="my-plugin",
            permission="filesystem:read",
        )

        # Get recent entries
        entries = audit.get_recent(100)

        # Export audit log
        audit.export("audit_log.json")
    """

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._log_file = self._get_log_file()
        self._load_entries()

    def _get_log_file(self) -> Path:
        """Get the audit log file path."""
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home() / "audit.jsonl"

    def _load_entries(self) -> None:
        """Load entries from disk."""
        if not self._log_file.exists():
            return

        try:
            with open(self._log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        entry = AuditEntry(
                            event_type=AuditEventType(data["event_type"]),
                            timestamp=data["timestamp"],
                            severity=AuditSeverity(data.get("severity", "info")),
                            user=data.get("user", ""),
                            source=data.get("source", ""),
                            details=data.get("details", {}),
                            ip_address=data.get("ip_address", ""),
                            session_id=data.get("session_id", ""),
                            message=data.get("message", ""),
                        )
                        self._entries.append(entry)
        except Exception as exc:
            logger.warning("Could not load audit log: %s", exc)

    def _save_entry(self, entry: AuditEntry) -> None:
        """Save an entry to disk."""
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "event_type": entry.event_type.value,
                "timestamp": entry.timestamp,
                "severity": entry.severity.value,
                "user": entry.user,
                "source": entry.source,
                "details": entry.details,
                "ip_address": entry.ip_address,
                "session_id": entry.session_id,
                "message": entry.message,
            }

            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as exc:
            logger.warning("Could not save audit entry: %s", exc)

    def log(
        self,
        event_type: AuditEventType,
        *,
        severity: AuditSeverity = AuditSeverity.INFO,
        user: str = "",
        source: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: str = "",
        session_id: str = "",
        message: str = "",
    ) -> None:
        """Log an audit event.

        Args:
            event_type: Type of event.
            severity: Event severity.
            user: User performing the action.
            source: Source of the event.
            details: Additional details.
            ip_address: User's IP address.
            session_id: Session ID.
            message: Human-readable message.
        """
        entry = AuditEntry(
            event_type=event_type,
            timestamp=time.time(),
            severity=severity,
            user=user,
            source=source,
            details=details or {},
            ip_address=ip_address,
            session_id=session_id,
            message=message,
        )

        self._entries.append(entry)
        self._save_entry(entry)

        # Log to standard logger
        log_fn = {
            AuditSeverity.INFO: logger.info,
            AuditSeverity.WARNING: logger.warning,
            AuditSeverity.ERROR: logger.error,
            AuditSeverity.CRITICAL: logger.critical,
        }.get(severity, logger.info)

        log_fn(
            "Audit: %s | user=%s | %s",
            event_type.value,
            user,
            message or details,
        )

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit entries.

        Args:
            limit: Maximum number of entries.

        Returns:
            List of recent entries.
        """
        entries = self._entries[-limit:]
        return [
            {
                "event_type": e.event_type.value,
                "timestamp": e.timestamp,
                "severity": e.severity.value,
                "user": e.user,
                "source": e.source,
                "details": e.details,
                "message": e.message,
            }
            for e in reversed(entries)
        ]

    def search(
        self,
        event_type: Optional[AuditEventType] = None,
        user: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search audit entries.

        Args:
            event_type: Filter by event type.
            user: Filter by user.
            start_time: Filter by start time.
            end_time: Filter by end time.
            limit: Maximum number of entries.

        Returns:
            Matching entries.
        """
        results = self._entries

        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if user:
            results = [e for e in results if e.user == user]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        return [
            {
                "event_type": e.event_type.value,
                "timestamp": e.timestamp,
                "severity": e.severity.value,
                "user": e.user,
                "details": e.details,
            }
            for e in results[-limit:]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics."""
        type_counts = {}
        severity_counts = {}
        user_counts = {}

        for entry in self._entries:
            # Count by type
            t = entry.event_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

            # Count by severity
            s = entry.severity.value
            severity_counts[s] = severity_counts.get(s, 0) + 1

            # Count by user
            if entry.user:
                user_counts[entry.user] = user_counts.get(entry.user, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_type": type_counts,
            "by_severity": severity_counts,
            "by_user": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def export(self, output_path: str) -> bool:
        """Export audit log to JSON.

        Args:
            output_path: Output file path.

        Returns:
            True if successful.
        """
        try:
            entries = [
                {
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp,
                    "severity": e.severity.value,
                    "user": e.user,
                    "source": e.source,
                    "details": e.details,
                    "ip_address": e.ip_address,
                    "session_id": e.session_id,
                    "message": e.message,
                }
                for e in self._entries
            ]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)

            return True
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            return False

    def clear(self, before_timestamp: Optional[float] = None) -> int:
        """Clear audit entries.

        Args:
            before_timestamp: Only clear entries before this timestamp.

        Returns:
            Number of entries cleared.
        """
        if before_timestamp:
            original_count = len(self._entries)
            self._entries = [
                e for e in self._entries
                if e.timestamp >= before_timestamp
            ]
            return original_count - len(self._entries)
        else:
            count = len(self._entries)
            self._entries.clear()
            return count


# Global audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Return the global AuditLogger singleton.

    AETHEROS_HOME is per-profile (and per-test), so a singleton that caches
    its path from first construction would silently write audit events to the
    wrong profile's log after a home switch. Rebuild when the home moves.
    """
    global _audit_logger
    from aetheros_constants import get_aetheros_home
    expected = get_aetheros_home() / "audit.jsonl"
    if _audit_logger is None or _audit_logger._log_file != expected:
        _audit_logger = AuditLogger()
    return _audit_logger
