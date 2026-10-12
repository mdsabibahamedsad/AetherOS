"""AetherOS Autonomous Background Agent + Automation OS."""

from aetheros_autonomy.models import (
    ActionRisk, ApprovalPolicy, AutoState, AutoType, AutomationDefinition,
    AutonomyLevel, ChangeClass, GLOBAL_LIMITS, MissedPolicy, NotifyMode,
    ResourceLimits, RetryPolicy, RunRecord, RunState,
    RISK_DEFAULT_APPROVAL, RISK_MIN_AUTONOMY,
)
from aetheros_autonomy.schedule import (
    CanonicalSchedule, next_run, parse_natural_schedule,
)
from aetheros_autonomy.store import AutonomyStore, find_secrets, scan_definition
from aetheros_autonomy.triggers import TriggerEngine, eval_condition
from aetheros_autonomy.scheduler import Scheduler, VirtualClock
from aetheros_autonomy.workflow import WorkflowEngine
from aetheros_autonomy.watchers import (
    ChangeClass as WatcherChangeClass, FileEvent, FileWatcher,
    RepoWatcher, WebWatcher, classify_change,
)
from aetheros_autonomy.runtime import (
    BackgroundAgentRuntime, ProactiveAgent,
)
from aetheros_autonomy.notify import DigestEngine, Notification, NotificationCenter
from aetheros_autonomy.safety import AutonomyEngine, ScopedApproval
from aetheros_autonomy.templates import TEMPLATES
from aetheros_autonomy.service import AutomationService

__all__ = [
    "ActionRisk", "ApprovalPolicy", "AutoState", "AutoType",
    "AutomationDefinition", "AutonomyLevel", "ChangeClass", "GLOBAL_LIMITS",
    "MissedPolicy", "NotifyMode", "ResourceLimits", "RetryPolicy",
    "RunRecord", "RunState", "RISK_DEFAULT_APPROVAL", "RISK_MIN_AUTONOMY",
    "CanonicalSchedule", "next_run", "parse_natural_schedule",
    "AutonomyStore", "find_secrets", "scan_definition",
    "TriggerEngine", "eval_condition",
    "Scheduler", "VirtualClock",
    "WorkflowEngine",
    "FileEvent", "FileWatcher", "RepoWatcher", "WebWatcher", "classify_change",
    "BackgroundAgentRuntime", "ProactiveAgent",
    "DigestEngine", "Notification", "NotificationCenter",
    "AutonomyEngine", "ScopedApproval",
    "TEMPLATES",
    "AutomationService",
]
