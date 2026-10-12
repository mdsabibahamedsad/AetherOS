"""Widget system — widget registry, definition, rendering."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WidgetDefinition:
    id: str
    name: str
    description: str
    category: str = "general"
    icon: str = "widget"
    default_size: str = "medium"
    min_size: str = "small"
    max_size: str = "large"
    refresh_interval: int = 0
    requires_auth: bool = False
    permissions: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)
    render_fn: Optional[Callable] = None
    data_fn: Optional[Callable] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class WidgetRegistry:
    def __init__(self):
        self._widgets: dict[str, WidgetDefinition] = {}

    def register(self, widget: WidgetDefinition) -> None:
        self._widgets[widget.id] = widget
        logger.debug("Registered widget: %s", widget.id)

    def register_class(self, **kwargs) -> WidgetDefinition:
        w = WidgetDefinition(**kwargs)
        self._widgets[w.id] = w
        return w

    def get(self, widget_id: str) -> Optional[WidgetDefinition]:
        return self._widgets.get(widget_id)

    def list(self, category: str = None) -> list[WidgetDefinition]:
        if category:
            return [w for w in self._widgets.values() if w.category == category]
        return list(self._widgets.values())

    def unregister(self, widget_id: str) -> bool:
        return self._widgets.pop(widget_id, None) is not None

    def get_data(self, widget_id: str, config: dict = None) -> Any:
        widget = self._widgets.get(widget_id)
        if widget and widget.data_fn:
            return widget.data_fn(config or {})
        return None

    def render(self, widget_id: str, config: dict = None) -> Any:
        widget = self._widgets.get(widget_id)
        if widget and widget.render_fn:
            return widget.render_fn(config or {})
        return None

    def get_categories(self) -> list[str]:
        cats = set()
        for w in self._widgets.values():
            cats.add(w.category)
        return sorted(cats)

    @property
    def count(self) -> int:
        return len(self._widgets)


DEFAULT_WIDGETS = [
    WidgetDefinition(
        id="system_status", name="System Status",
        description="CPU, memory, disk usage overview",
        category="system", icon="monitor",
        data_fn=lambda c: {"cpu": 0, "memory": 0, "disk": 0},
    ),
    WidgetDefinition(
        id="agent_activity", name="Agent Activity",
        description="Recent agent executions and status",
        category="agents", icon="bot",
        refresh_interval=5,
    ),
    WidgetDefinition(
        id="workflow_status", name="Workflow Status",
        description="Running and recent workflow executions",
        category="workflows", icon="workflow",
        refresh_interval=10,
    ),
    WidgetDefinition(
        id="connection_health", name="Connection Health",
        description="Status of all service connections",
        category="connect", icon="link",
    ),
    WidgetDefinition(
        id="knowledge_stats", name="Knowledge Stats",
        description="Knowledge graph entities and relations",
        category="knowledge", icon="brain",
    ),
    WidgetDefinition(
        id="scheduled_jobs", name="Scheduled Jobs",
        description="Upcoming and running cron jobs",
        category="system", icon="clock",
    ),
    WidgetDefinition(
        id="recent_messages", name="Recent Messages",
        description="Latest conversation messages",
        category="chat", icon="message",
    ),
    WidgetDefinition(
        id="memory_usage", name="Memory Usage",
        description="Token usage and context stats",
        category="system", icon="database",
    ),
    WidgetDefinition(
        id="plugin_updates", name="Plugin Updates",
        description="Available updates for installed plugins",
        category="hub", icon="package",
    ),
    WidgetDefinition(
        id="service_health", name="Service Health",
        description="API service availability and latency",
        category="connect", icon="activity",
    ),
    WidgetDefinition(
        id="recent_audit", name="Recent Audit Events",
        description="Latest security audit log entries",
        category="security", icon="shield",
    ),
    WidgetDefinition(
        id="analytics_overview", name="Analytics Overview",
        description="Usage statistics and trends",
        category="analytics", icon="chart",
    ),
]
