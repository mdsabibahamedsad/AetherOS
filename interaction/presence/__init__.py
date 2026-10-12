"""Presence awareness package for AetherOS interaction layer."""

from interaction.presence.activity_detector import (
    ActivityDetector,
    ActivityEvent,
    ActivityType,
    ActivityState,
)
from interaction.presence.idle_monitor import (
    IdleMonitor,
    IdleEvent,
    IdleState,
)
from interaction.presence.focus_mode import (
    FocusMode,
    FocusConfig,
    FocusEvent,
    FocusState,
)
from interaction.presence.context_detector import (
    ContextDetector,
    WorkspaceContext,
    ContextEvent,
)

__all__ = [
    "ActivityDetector",
    "ActivityEvent",
    "ActivityType",
    "ActivityState",
    "IdleMonitor",
    "IdleEvent",
    "IdleState",
    "FocusMode",
    "FocusConfig",
    "FocusEvent",
    "FocusState",
    "ContextDetector",
    "WorkspaceContext",
    "ContextEvent",
]
