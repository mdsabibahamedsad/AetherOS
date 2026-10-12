"""Panel management — layouts, panel definitions, grid system."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PanelDefinition:
    id: str
    widget_id: str
    title: str
    x: int = 0
    y: int = 0
    width: int = 2
    height: int = 1
    config: dict = field(default_factory=dict)
    visible: bool = True


@dataclass
class PanelLayout:
    id: str
    name: str
    description: str = ""
    panels: list[PanelDefinition] = field(default_factory=list)
    columns: int = 4
    gap: int = 2
    theme: str = "default"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class PanelManager:
    def __init__(self, db_path: Optional[str] = None):
        self._layouts: dict[str, PanelLayout] = {}
        self._active_layout: Optional[str] = None
        if db_path:
            self._load(db_path)
        else:
            self._init_default()

    def _init_default(self):
        default = PanelLayout(
            id="default",
            name="Default",
            description="Default dashboard layout",
            columns=4,
            panels=[
                PanelDefinition("p1", "system_status", "System Status",
                                x=0, y=0, width=2, height=1),
                PanelDefinition("p2", "agent_activity", "Agent Activity",
                                x=2, y=0, width=2, height=1),
                PanelDefinition("p3", "workflow_status", "Workflow Status",
                                x=0, y=1, width=2, height=1),
                PanelDefinition("p4", "connection_health", "Connection Health",
                                x=2, y=1, width=1, height=1),
                PanelDefinition("p5", "scheduled_jobs", "Scheduled Jobs",
                                x=3, y=1, width=1, height=1),
                PanelDefinition("p6", "knowledge_stats", "Knowledge Stats",
                                x=0, y=2, width=1, height=1),
                PanelDefinition("p7", "memory_usage", "Memory Usage",
                                x=1, y=2, width=1, height=1),
                PanelDefinition("p8", "recent_audit", "Recent Audit",
                                x=2, y=2, width=1, height=1),
                PanelDefinition("p9", "analytics_overview", "Analytics",
                                x=3, y=2, width=1, height=1),
            ],
        )
        self._layouts["default"] = default
        self._active_layout = "default"

    def _load(self, db_path: str):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS dashboard_layouts "
                         "(id TEXT PRIMARY KEY, data TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS dashboard_active "
                         "(key TEXT PRIMARY KEY, value TEXT)")
            cursor = conn.execute("SELECT data FROM dashboard_layouts")
            for row in cursor.fetchall():
                data = json.loads(row[0])
                layout = PanelLayout(**data)
                self._layouts[layout.id] = layout
            cursor = conn.execute(
                "SELECT value FROM dashboard_active WHERE key='active_layout'")
            row = cursor.fetchone()
            if row:
                self._active_layout = row[0]
            conn.close()
        except Exception as e:
            logger.warning("Failed to load dashboard layouts: %s", e)
        if not self._layouts:
            self._init_default()

    def save(self, db_path: str):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS dashboard_layouts "
                         "(id TEXT PRIMARY KEY, data TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS dashboard_active "
                         "(key TEXT PRIMARY KEY, value TEXT)")
            for lid, layout in self._layouts.items():
                data = json.dumps({
                    "id": layout.id, "name": layout.name,
                    "description": layout.description,
                    "panels": [p.__dict__ for p in layout.panels],
                    "columns": layout.columns, "gap": layout.gap,
                    "theme": layout.theme,
                    "created_at": layout.created_at,
                    "updated_at": layout.updated_at,
                }, default=str)
                conn.execute("INSERT OR REPLACE INTO dashboard_layouts "
                             "(id, data) VALUES (?, ?)", (lid, data))
            conn.execute("INSERT OR REPLACE INTO dashboard_active "
                         "(key, value) VALUES ('active_layout', ?)",
                         (self._active_layout or "",))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to save dashboard layouts: %s", e)

    def create_layout(self, layout: PanelLayout) -> None:
        self._layouts[layout.id] = layout

    def get_layout(self, layout_id: str = None) -> Optional[PanelLayout]:
        lid = layout_id or self._active_layout
        return self._layouts.get(lid) if lid else None

    def list_layouts(self) -> list[PanelLayout]:
        return list(self._layouts.values())

    def delete_layout(self, layout_id: str) -> bool:
        if layout_id == "default":
            return False
        return self._layouts.pop(layout_id, None) is not None

    def set_active(self, layout_id: str) -> bool:
        if layout_id in self._layouts:
            self._active_layout = layout_id
            return True
        return False

    def add_panel(self, layout_id: str, panel: PanelDefinition) -> bool:
        layout = self._layouts.get(layout_id)
        if not layout:
            return False
        layout.panels.append(panel)
        layout.updated_at = datetime.utcnow().isoformat() + "Z"
        return True

    def remove_panel(self, layout_id: str, panel_id: str) -> bool:
        layout = self._layouts.get(layout_id)
        if not layout:
            return False
        layout.panels = [p for p in layout.panels if p.id != panel_id]
        layout.updated_at = datetime.utcnow().isoformat() + "Z"
        return True

    def update_panel(self, layout_id: str, panel_id: str,
                      updates: dict) -> bool:
        layout = self._layouts.get(layout_id)
        if not layout:
            return False
        for p in layout.panels:
            if p.id == panel_id:
                for k, v in updates.items():
                    if hasattr(p, k):
                        setattr(p, k, v)
                layout.updated_at = datetime.utcnow().isoformat() + "Z"
                return True
        return False

    def to_dict(self, layout_id: str = None) -> dict:
        layout = self.get_layout(layout_id)
        if not layout:
            return {}
        return {
            "id": layout.id, "name": layout.name,
            "description": layout.description,
            "columns": layout.columns, "gap": layout.gap, "theme": layout.theme,
            "panels": [p.__dict__ for p in layout.panels],
        }
