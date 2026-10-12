"""
UI Extensions for AetherOS
==========================

UI extension points for customizing the AetherOS interface.

Extension points:
    - Sidebar: Side panel extensions
    - Status Bar: Status bar items
    - Toolbar: Toolbar buttons and menus
    - Dashboard: Dashboard cards and widgets
    - Settings: Settings panels
    - Panels: Additional UI panels
    - Context Menu: Right-click menu items

Usage::

    from aetheros_developer_platform.ui_extensions import UIExtensionManager

    manager = UIExtensionManager()
    manager.register_sidebar("my-panel", "My Panel", render_fn)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIExtensionType(Enum):
    """Types of UI extensions."""
    SIDEBAR = "sidebar"
    STATUS_BAR = "status_bar"
    TOOLBAR = "toolbar"
    DASHBOARD = "dashboard"
    SETTINGS = "settings"
    PANEL = "panel"
    CONTEXT_MENU = "context_menu"
    NOTIFICATION = "notification"
    MODAL = "modal"


@dataclass
class UIExtension:
    """A UI extension definition."""
    name: str
    extension_type: UIExtensionType
    title: str = ""
    description: str = ""
    icon: str = ""
    position: str = "left"
    render_fn: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    permissions: List[str] = field(default_factory=list)


class UIExtensionManager:
    """Manages UI extensions for AetherOS.

    Usage::

        manager = UIExtensionManager()

        # Register a sidebar panel
        @manager.register_sidebar("my-panel", "My Panel")
        def render_my_panel(ctx):
            return "<div>My Panel</div>"

        # Register a dashboard card
        @manager.register_dashboard("my-card", "My Card")
        def render_my_card(ctx):
            return {"title": "My Card", "content": "..."}
    """

    def __init__(self) -> None:
        self._extensions: Dict[str, UIExtension] = {}

    def register_sidebar(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        icon: str = "",
        position: str = "left",
    ) -> Callable:
        """Register a sidebar extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.SIDEBAR,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                icon=icon,
                position=position,
            )
            self._extensions[name] = ext
            logger.info("Registered sidebar extension: %s", name)
            return func
        return decorator

    def register_status_bar(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        position: str = "right",
        priority: int = 0,
    ) -> Callable:
        """Register a status bar extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.STATUS_BAR,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                position=position,
                config={"priority": priority},
            )
            self._extensions[name] = ext
            logger.info("Registered status bar extension: %s", name)
            return func
        return decorator

    def register_toolbar(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        icon: str = "",
        position: str = "left",
    ) -> Callable:
        """Register a toolbar extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.TOOLBAR,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                icon=icon,
                position=position,
            )
            self._extensions[name] = ext
            logger.info("Registered toolbar extension: %s", name)
            return func
        return decorator

    def register_dashboard(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        size: str = "medium",
        row: int = 0,
        col: int = 0,
    ) -> Callable:
        """Register a dashboard extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.DASHBOARD,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                config={"size": size, "row": row, "col": col},
            )
            self._extensions[name] = ext
            logger.info("Registered dashboard extension: %s", name)
            return func
        return decorator

    def register_settings(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        section: str = "general",
    ) -> Callable:
        """Register a settings extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.SETTINGS,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                config={"section": section},
            )
            self._extensions[name] = ext
            logger.info("Registered settings extension: %s", name)
            return func
        return decorator

    def register_context_menu(
        self,
        name: str,
        title: str,
        render_fn: Optional[Callable] = None,
        *,
        context: str = "global",
    ) -> Callable:
        """Register a context menu extension."""
        def decorator(func: Callable) -> Callable:
            ext = UIExtension(
                name=name,
                extension_type=UIExtensionType.CONTEXT_MENU,
                title=title,
                render_fn=func if render_fn is None else render_fn,
                config={"context": context},
            )
            self._extensions[name] = ext
            logger.info("Registered context menu extension: %s", name)
            return func
        return decorator

    def get_extension(self, name: str) -> Optional[UIExtension]:
        """Get an extension by name."""
        return self._extensions.get(name)

    def list_extensions(
        self,
        extension_type: Optional[UIExtensionType] = None,
        enabled_only: bool = True,
    ) -> List[UIExtension]:
        """List all extensions."""
        extensions = list(self._extensions.values())
        if extension_type:
            extensions = [e for e in extensions if e.extension_type == extension_type]
        if enabled_only:
            extensions = [e for e in extensions if e.enabled]
        return extensions

    def enable(self, name: str) -> bool:
        """Enable an extension."""
        ext = self._extensions.get(name)
        if ext:
            ext.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable an extension."""
        ext = self._extensions.get(name)
        if ext:
            ext.enabled = False
            return True
        return False

    def unregister(self, name: str) -> bool:
        """Unregister an extension."""
        if name in self._extensions:
            del self._extensions[name]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get extension statistics."""
        stats = {
            "total": len(self._extensions),
            "enabled": sum(1 for e in self._extensions.values() if e.enabled),
            "by_type": {},
        }
        for ext_type in UIExtensionType:
            count = sum(1 for e in self._extensions.values() if e.extension_type == ext_type)
            if count > 0:
                stats["by_type"][ext_type.value] = count
        return stats


# Global UI extension manager
_ui_manager: Optional[UIExtensionManager] = None


def get_ui_extension_manager() -> UIExtensionManager:
    """Return the global UIExtensionManager singleton."""
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = UIExtensionManager()
    return _ui_manager
