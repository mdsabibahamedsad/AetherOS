"""System tray — tray icon, menu, actions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrayAction:
    id: str
    label: str
    callback: Optional[Callable] = None
    icon: str = ""
    enabled: bool = True
    checked: bool = False
    separator_after: bool = False


@dataclass
class TrayMenu:
    actions: list[TrayAction] = field(default_factory=list)
    default_action: Optional[str] = None


class TrayManager:
    def __init__(self):
        self._menu = TrayMenu()
        self._visible = False
        self._tooltip: str = "AetherOS"
        self._icon: str = "default"

    def set_tooltip(self, text: str):
        self._tooltip = text

    def set_icon(self, icon_name: str):
        self._icon = icon_name

    def add_action(self, action: TrayAction):
        self._menu.actions.append(action)

    def remove_action(self, action_id: str) -> bool:
        initial = len(self._menu.actions)
        self._menu.actions = [
            a for a in self._menu.actions if a.id != action_id]
        return len(self._menu.actions) < initial

    def set_default(self, action_id: str):
        self._menu.default_action = action_id

    def show(self):
        self._visible = True

    def hide(self):
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def get_state(self) -> dict:
        return {
            "visible": self._visible,
            "tooltip": self._tooltip,
            "icon": self._icon,
            "menu": [
                {"id": a.id, "label": a.label, "icon": a.icon,
                 "enabled": a.enabled, "checked": a.checked,
                 "separator_after": a.separator_after}
                for a in self._menu.actions
            ],
            "default_action": self._menu.default_action,
        }

    def trigger(self, action_id: str) -> bool:
        for action in self._menu.actions:
            if action.id == action_id and action.callback:
                try:
                    action.callback()
                    return True
                except Exception as e:
                    logger.error("Tray action error: %s", e)
                    return False
        return False

    def close(self):
        self._menu.actions.clear()
        self._visible = False
