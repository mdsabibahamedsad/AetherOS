"""AetherOS Universal Tool Calling & Computer Control Engine.

Architecture::

    tool_runtime/
        __init__.py             Package exports
        interface.py            Universal Tool Interface (ABC)
        manager.py              Tool Runtime Manager (register, load, unload, health)
        permission.py           Permission System (risk levels, approval)
        safety.py               Safety Engine (destructive action protection)
        planner.py              Execution Planner (goal -> plan -> run -> verify -> rollback)
        dashboard.py            Execution Dashboard
        observability.py        Metrics & Observability
        filesystem/             Filesystem Runtime
        terminal/               Terminal Runtime (PowerShell, CMD, Bash, Zsh, Fish)
        python/                 Python Runtime (isolated execution, venv, packages)
        browser/                Browser Runtime (tabs, navigation, DOM, screenshots)
        desktop/                Desktop Runtime (apps, window mgmt, clipboard, mouse)
        git/                    Git Runtime (clone, commit, branch, merge, push, pull)
        rest/                   REST API Runtime (GET, POST, PUT, PATCH, DELETE, OAuth)
        database/               Database Runtime (SQLite, PG, MySQL, MSSQL, Mongo, Redis)
        plugins/                Plugin Runtime (discovery, hot-reload, sandbox)
        chaining/               Tool Chaining Engine (cross-runtime workflows)
        testing/                Comprehensive test suite

Integration with existing AetherOS::
    - Wraps tools/registry.py as the base ToolRegistry
    - Adds universal interface on top of existing tool system
    - Adds permission layer that existing approval.py feeds into
    - Adds execution planning and cross-runtime chaining
"""

from __future__ import annotations

from tool_runtime.interface import (
    ToolInterface,
    ToolResult,
    ToolStatus,
    ToolRiskLevel,
    ToolCategory,
    ToolMetadata,
)
from tool_runtime.manager import (
    ToolRuntimeManager,
    get_runtime_manager,
    RuntimeState,
)
from tool_runtime.permission import (
    PermissionSystem,
    PermissionResult,
    RiskLevel,
    get_permission_system,
)
from tool_runtime.safety import (
    SafetyEngine,
    SafetyCheck,
    SafetyVerdict,
    DestructiveAction,
    get_safety_engine,
)
from tool_runtime.planner import (
    ExecutionPlanner,
    ExecutionPlan,
    PlanStep,
    PlanStatus,
    get_execution_planner,
)
from tool_runtime.dashboard import (
    ExecutionDashboard,
    DashboardEntry,
    get_execution_dashboard,
)
from tool_runtime.observability import (
    ObservabilityCollector,
    MetricPoint,
    get_observability_collector,
)

__all__ = [
    "ToolInterface",
    "ToolResult",
    "ToolStatus",
    "ToolRiskLevel",
    "ToolCategory",
    "ToolMetadata",
    "ToolRuntimeManager",
    "get_runtime_manager",
    "RuntimeState",
    "PermissionSystem",
    "PermissionResult",
    "RiskLevel",
    "get_permission_system",
    "SafetyEngine",
    "SafetyCheck",
    "SafetyVerdict",
    "DestructiveAction",
    "get_safety_engine",
    "ExecutionPlanner",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    "get_execution_planner",
    "ExecutionDashboard",
    "DashboardEntry",
    "get_execution_dashboard",
    "ObservabilityCollector",
    "MetricPoint",
    "get_observability_collector",
]
