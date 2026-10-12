"""Execution Dashboard.

Provides real-time visibility into:
- Running tools
- Execution history
- Duration
- Logs
- Errors
- Artifacts
- Permissions
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager
from tool_runtime.observability import ObservabilityCollector, get_observability_collector

logger = logging.getLogger(__name__)


@dataclass
class DashboardEntry:
    """A single entry in the execution dashboard."""
    request_id: str
    tool_name: str
    status: str
    duration_ms: float
    success: bool
    error: Optional[str]
    timestamp: str
    category: str
    risk_level: str
    params_preview: str = ""


class ExecutionDashboard:
    """Real-time execution dashboard for tool runtime.

    Features:
    - Currently running executions
    - Execution history with filtering
    - Duration tracking
    - Error aggregation
    - Artifact tracking
    - Permission audit trail
    """

    def __init__(self):
        self._manager: Optional[ToolRuntimeManager] = None
        self._observability: Optional[ObservabilityCollector] = None
        self._lock = threading.RLock()
        self._artifacts: Dict[str, List[Dict[str, Any]]] = {}
        self._permission_audit: List[Dict[str, Any]] = []
        self._max_audit = 5000

    @property
    def manager(self) -> ToolRuntimeManager:
        if self._manager is None:
            self._manager = get_runtime_manager()
        return self._manager

    @property
    def observability(self) -> ObservabilityCollector:
        if self._observability is None:
            self._observability = get_observability_collector()
        return self._observability

    def get_snapshot(self) -> Dict[str, Any]:
        """Get a full dashboard snapshot."""
        manager_state = self.manager.health_check()
        metrics = self.manager.get_metrics()
        obs_metrics = self.observability.get_metrics()

        return {
            "runtime": manager_state,
            "metrics": metrics,
            "observability": obs_metrics,
            "running": self.get_running(),
            "recent_history": self.get_recent(limit=20),
            "artifacts_count": sum(len(v) for v in self._artifacts.values()),
            "permission_audit_count": len(self._permission_audit),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_running(self) -> List[Dict[str, Any]]:
        """Get currently running executions."""
        manager_state = self.manager.health_check()
        history = self.manager.get_history(limit=50)
        return [
            {
                "tool_name": h["tool_name"],
                "timestamp": h["timestamp"],
                "duration_ms": h["duration_ms"],
            }
            for h in history
            if h.get("status") in ("running", "pending")
        ]

    def get_recent(
        self,
        limit: int = 20,
        tool_name: Optional[str] = None,
        success_only: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self.manager.get_history(
            limit=limit,
            tool_name=tool_name,
            success_only=success_only,
        )

    def get_execution_detail(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific execution."""
        history = self.manager.get_history(limit=10000)
        for h in history:
            if h["request_id"] == request_id:
                detail = dict(h)
                art = self._artifacts.get(request_id, [])
                if art:
                    detail["artifacts"] = art
                return detail
        return None

    def record_artifact(
        self,
        request_id: str,
        name: str,
        path: str,
        size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> None:
        """Record an artifact produced by a tool execution."""
        with self._lock:
            if request_id not in self._artifacts:
                self._artifacts[request_id] = []
            self._artifacts[request_id].append({
                "name": name,
                "path": path,
                "size_bytes": size_bytes,
                "mime_type": mime_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def record_permission_check(
        self,
        tool_name: str,
        allowed: bool,
        reason: Optional[str],
        requires_approval: bool = False,
    ) -> None:
        """Record a permission check for audit trail."""
        entry = {
            "tool_name": tool_name,
            "allowed": allowed,
            "reason": reason,
            "requires_approval": requires_approval,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._permission_audit.append(entry)
            if len(self._permission_audit) > self._max_audit:
                self._permission_audit = self._permission_audit[-self._max_audit:]

    def get_permission_audit(
        self,
        limit: int = 100,
        denied_only: bool = False,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self._permission_audit)
        if denied_only:
            entries = [e for e in entries if not e["allowed"]]
        return entries[-limit:]

    def get_error_summary(self) -> Dict[str, Any]:
        """Aggregate error information."""
        history = self.manager.get_history(limit=10000)
        failures = [h for h in history if not h["success"]]
        error_by_tool: Dict[str, int] = {}
        for f in failures:
            tn = f["tool_name"]
            error_by_tool[tn] = error_by_tool.get(tn, 0) + 1
        return {
            "total_failures": len(failures),
            "failure_rate": round(len(failures) / max(len(history), 1) * 100, 2),
            "errors_by_tool": error_by_tool,
        }

    def clear_history(self) -> None:
        """Clear all dashboard data."""
        with self._lock:
            self._artifacts.clear()
            self._permission_audit.clear()


# Global singleton
_dashboard_instance: Optional[ExecutionDashboard] = None


def get_execution_dashboard() -> ExecutionDashboard:
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = ExecutionDashboard()
    return _dashboard_instance
