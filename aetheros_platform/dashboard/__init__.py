"""Dashboard & UI Framework — web server, WebSocket, widgets, panels, routes."""

from aetheros_platform.dashboard.server import DashboardServer
from aetheros_platform.dashboard.websocket import WebSocketManager, WSClient
from aetheros_platform.dashboard.widgets import WidgetRegistry, WidgetDefinition
from aetheros_platform.dashboard.panels import PanelManager, PanelLayout, PanelDefinition
from aetheros_platform.dashboard.routes import DashboardAPI, RouteRegistry

__all__ = [
    "DashboardServer", "WebSocketManager", "WSClient",
    "WidgetRegistry", "WidgetDefinition",
    "PanelManager", "PanelLayout", "PanelDefinition",
    "DashboardAPI", "RouteRegistry",
]
