"""
Mission Dashboard — visualizer for multi-agent orchestration state.

Provides structured data types and aggregation for building real-time
dashboards showing running agents, task graphs, timelines, logs,
artifacts, memory, current plans, and execution progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MissionStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MissionDashboardData:
    mission_id: str = ""
    mission_name: str = ""
    goal: str = ""
    status: MissionStatus = MissionStatus.PENDING
    progress_pct: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_seconds: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    agents: List[Dict[str, Any]] = field(default_factory=list)
    task_graph: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    plan: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentDashboardInfo:
    agent_id: str = ""
    name: str = ""
    type: str = ""
    status: str = ""
    health: str = ""
    current_task: str = ""
    total_tasks_completed: int = 0
    uptime_seconds: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    version: str = ""
    last_heartbeat: Optional[float] = None
    error: str = ""


@dataclass
class TimelineEvent:
    timestamp: float = 0.0
    event_type: str = ""
    agent_id: str = ""
    description: str = ""
    severity: str = "info"
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardStats:
    total_missions: int = 0
    active_missions: int = 0
    total_agents: int = 0
    running_agents: int = 0
    healthy_agents: int = 0
    pending_approvals: int = 0
    total_alerts: int = 0
    unresolved_alerts: int = 0
    total_artifacts: int = 0
    lessons_learned: int = 0
    average_mission_duration: float = 0.0
    success_rate: float = 0.0


def create_dashboard_from_kernel(kernel) -> Dict[str, Any]:
    dashboard = {
        "kernel_version": "2.0.0",
        "uptime": (kernel._boot_time and (__import__("time").time() - kernel._boot_time)) or 0,
        "running": kernel.is_running(),
    }
    stats = DashboardStats()
    if kernel.agent_manager:
        mgr_stats = kernel.agent_manager.get_stats()
        stats.total_agents = mgr_stats.get("total_agents", 0)
        stats.running_agents = mgr_stats.get("running", 0)
        stats.healthy_agents = mgr_stats.get("healthy", 0)
        dashboard["agents"] = {
            "total": stats.total_agents,
            "running": stats.running_agents,
            "healthy": stats.healthy_agents,
            "by_type": mgr_stats.get("by_type", {}),
        }
        dashboard["agent_list"] = [
            {"id": a.metadata.id, "name": a.metadata.name, "type": a.metadata.type,
             "status": a.status.value, "health": a.health.value}
            for a in kernel.agent_manager.list_agents()
        ]
    if kernel.inter_agent:
        bus_stats = kernel.inter_agent.get_stats()
        dashboard["communication"] = {
            "agents_registered": bus_stats.get("agents_registered", 0),
            "messages_in_flight": bus_stats.get("messages_in_flight", 0),
            "active_handoffs": bus_stats.get("active_handoffs", 0),
            "shared_memory_entries": bus_stats.get("shared_memory_entries", 0),
        }
    if kernel.planner:
        plans = kernel.planner.list_plans()
        dashboard["plans"] = {
            "active": len(kernel.planner.list_plans(status=__import__("kernel.planner").PlanStatus.APPROVED)),
            "total": len(plans),
            "recent": [
                {"id": p.id, "goal": p.goal[:60], "status": p.status.value,
                 "steps": len(p.steps), "progress": kernel.planner.get_progress(p.id)}
                for p in plans[-5:]
            ],
        }
    if kernel.supervisor:
        sup_stats = kernel.supervisor.get_stats()
        stats.total_alerts = sup_stats.get("total_alerts", 0)
        stats.unresolved_alerts = sup_stats.get("unresolved_alerts", 0)
        dashboard["supervisor"] = {
            "monitored_agents": sup_stats.get("monitored_agents", 0),
            "total_alerts": stats.total_alerts,
            "unresolved_alerts": stats.unresolved_alerts,
            "recent_alerts": [
                {"id": a.id, "message": a.message[:80], "severity": a.severity.name,
                 "category": a.category.value, "resolved": a.resolved}
                for a in kernel.supervisor.get_alerts(limit=10)
            ],
        }
    if kernel.approvals:
        app_stats = kernel.approvals.get_stats()
        stats.pending_approvals = app_stats.get("pending", 0)
        dashboard["approvals"] = {
            "pending": stats.pending_approvals,
            "total": app_stats.get("total_requests", 0),
            "approved": app_stats.get("approved", 0),
            "denied": app_stats.get("denied", 0),
            "queue": [
                {"id": r.id, "action": r.action.value, "description": r.description[:60],
                 "agent_id": r.agent_id, "priority": r.priority.name,
                 "created_at": r.created_at}
                for r in kernel.approvals.list_pending()[:10]
            ],
        }
    if kernel.artifacts:
        art_stats = kernel.artifacts.get_stats()
        stats.total_artifacts = art_stats.get("total_artifacts", 0)
        dashboard["artifacts"] = {
            "total": stats.total_artifacts,
            "total_versions": art_stats.get("total_versions", 0),
            "by_type": art_stats.get("by_type", {}),
        }
    if kernel.reflection:
        ref_stats = kernel.reflection.get_stats()
        stats.lessons_learned = ref_stats.get("total_lessons", 0)
        stats.success_rate = ref_stats.get("success_rate", 0.0)
        dashboard["reflection"] = {
            "total_analyses": ref_stats.get("total_analyses", 0),
            "success_rate": stats.success_rate,
            "lessons": stats.lessons_learned,
            "applied_lessons": ref_stats.get("applied_lessons", 0),
            "recent_lessons": [
                {"title": l.title, "category": l.category.value, "severity": l.severity.name}
                for l in kernel.reflection.get_lessons(limit=5)
            ],
        }
    if kernel.executor:
        exec_stats = kernel.executor.get_stats()
        dashboard["executor"] = exec_stats
    if kernel.permissions:
        perm_stats = kernel.permissions.get_stats()
        dashboard["permissions"] = perm_stats
    dashboard["stats"] = {
        "total_agents": stats.total_agents,
        "running_agents": stats.running_agents,
        "pending_approvals": stats.pending_approvals,
        "unresolved_alerts": stats.unresolved_alerts,
        "total_artifacts": stats.total_artifacts,
        "success_rate": stats.success_rate,
        "lessons_learned": stats.lessons_learned,
    }
    return dashboard