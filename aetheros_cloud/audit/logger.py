"""Audit logger — tracks user, agent, workflow, auth, and API activity."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_cloud.models import AuditEntry, generate_id, now

logger = logging.getLogger(__name__)


class AuditLogger:
    """Immutable audit log with filtering and export.

    Writes to local JSON file; syncs to cloud via SyncEngine when configured.
    """

    def __init__(self, data_dir: Optional[Path] = None, max_entries: int = 10000):
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "audit"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._max_entries = max_entries
        self._entries: List[AuditEntry] = []
        self._load()

    def log(
        self,
        event: str,
        actor_id: str = "",
        actor_type: str = "user",
        target_type: str = "",
        target_id: str = "",
        action: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: str = "",
        user_agent: str = "",
        workspace_id: str = "",
        severity: str = "info",
    ) -> AuditEntry:
        entry = AuditEntry(
            id=generate_id("audit"),
            event=event,
            actor_id=actor_id,
            actor_type=actor_type,
            target_type=target_type,
            target_id=target_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            workspace_id=workspace_id,
            severity=severity,
            created_at=now(),
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._persist()
        if severity in ("warning", "error", "critical"):
            logger.log(logging.WARNING if severity == "warning" else logging.ERROR,
                       "Audit [%s] %s: %s by %s", severity, event, str(details)[:120], actor_id)
        return entry

    def query(
        self,
        event: Optional[str] = None,
        actor_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        severity: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        results = self._entries
        if event:
            results = [e for e in results if e.event == event]
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        if workspace_id:
            results = [e for e in results if e.workspace_id == workspace_id]
        if severity:
            results = [e for e in results if e.severity == severity]
        if target_type:
            results = [e for e in results if e.target_type == target_type]
        return results[offset:offset + limit]

    def count(
        self,
        event: Optional[str] = None,
        actor_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> int:
        return len(self.query(event=event, actor_id=actor_id, workspace_id=workspace_id, severity=severity))

    def export(self, format: str = "json") -> str:
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        if format == "json":
            return json.dumps([ser(e) for e in self._entries], indent=2, default=str)
        elif format == "csv":
            lines = ["id,event,actor_id,actor_type,severity,created_at"]
            for e in self._entries:
                lines.append(f"{e.id},{e.event},{e.actor_id},{e.actor_type},{e.severity},{e.created_at}")
            return "\n".join(lines)
        return ""

    def clear(self, older_than: Optional[float] = None):
        if older_than:
            self._entries = [e for e in self._entries if e.created_at >= older_than]
        else:
            self._entries = []
        self._persist()

    def _persist(self):
        path = self._data_dir / "audit_log.json"
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        path.write_text(json.dumps([ser(e) for e in self._entries], default=str))

    def _load(self):
        path = self._data_dir / "audit_log.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                entry = AuditEntry(
                    id=d.get("id", ""),
                    event=d.get("event", ""),
                    actor_id=d.get("actor_id", ""),
                    actor_type=d.get("actor_type", "user"),
                    target_type=d.get("target_type", ""),
                    target_id=d.get("target_id", ""),
                    action=d.get("action", ""),
                    details=d.get("details", {}),
                    ip_address=d.get("ip_address", ""),
                    user_agent=d.get("user_agent", ""),
                    workspace_id=d.get("workspace_id", ""),
                    severity=d.get("severity", "info"),
                    created_at=d.get("created_at", 0.0),
                )
                self._entries.append(entry)
        except Exception as e:
            logger.error("Failed to load audit log: %s", e)
