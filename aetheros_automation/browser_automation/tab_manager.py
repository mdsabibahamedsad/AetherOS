from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from aetheros_automation.browser.base import BrowserAutomation

logger = logging.getLogger(__name__)


@dataclass
class Tab:
    id: str
    session_id: str
    url: str
    title: str
    pinned: bool = False
    loading: bool = False
    group: str = ""
    order: int = 0


class TabManager:
    def __init__(self, browser_manager):
        self._browser_manager = browser_manager
        self._tabs: dict[str, list[Tab]] = {}
        self._active_tab: dict[str, str] = {}

    def create_tab(self, browser: BrowserAutomation, url: str = "about:blank", pinned: bool = False) -> Tab:
        session_id = self._find_session_id(browser)
        tab_id = str(uuid.uuid4())
        tab = Tab(
            id=tab_id,
            session_id=session_id,
            url=url,
            title="New Tab",
            pinned=pinned,
            order=len(self._tabs.get(session_id, [])),
        )
        if session_id not in self._tabs:
            self._tabs[session_id] = []
        self._tabs[session_id].append(tab)
        self._active_tab[session_id] = tab_id
        logger.debug("Tab created: %s in session %s", tab_id, session_id)
        return tab

    def _find_session_id(self, browser: BrowserAutomation) -> str:
        for sid, b in self._browser_manager._sessions.items():
            if b is browser:
                return sid
        return str(uuid.uuid4())

    def get_tab(self, session_id: str, tab_id: str) -> Tab | None:
        tabs = self._tabs.get(session_id, [])
        for tab in tabs:
            if tab.id == tab_id:
                return tab
        return None

    def get_active_tab(self, session_id: str) -> Tab | None:
        tab_id = self._active_tab.get(session_id)
        if not tab_id:
            return None
        return self.get_tab(session_id, tab_id)

    def set_active_tab(self, session_id: str, tab_id: str) -> bool:
        tab = self.get_tab(session_id, tab_id)
        if tab is None:
            return False
        self._active_tab[session_id] = tab_id
        return True

    def close_tab(self, session_id: str, tab_id: str) -> bool:
        tabs = self._tabs.get(session_id, [])
        for i, tab in enumerate(tabs):
            if tab.id == tab_id:
                tabs.pop(i)
                if self._active_tab.get(session_id) == tab_id:
                    if tabs:
                        self._active_tab[session_id] = tabs[-1].id
                    else:
                        self._active_tab.pop(session_id, None)
                return True
        return False

    def restore_tab(self, session_id: str, tab_id: str) -> Tab | None:
        stored = getattr(self, "_closed_tabs", {}).get(session_id, [])
        for i, tab in enumerate(stored):
            if tab.id == tab_id:
                tab.loading = False
                self._tabs.setdefault(session_id, []).append(tab)
                stored.pop(i)
                self._active_tab[session_id] = tab.id
                return tab
        return None

    def duplicate_tab(self, session_id: str, tab_id: str) -> Tab | None:
        original = self.get_tab(session_id, tab_id)
        if original is None:
            return None
        browser = self._browser_manager._sessions.get(session_id)
        if browser is None:
            return None
        new_tab = self.create_tab(browser, original.url, False)
        new_tab.title = original.title
        return new_tab

    def toggle_pin_tab(self, session_id: str, tab_id: str) -> bool:
        tab = self.get_tab(session_id, tab_id)
        if tab is None:
            return False
        tab.pinned = not tab.pinned
        return True

    def set_tab_group(self, session_id: str, tab_ids: list[str], group_name: str):
        for tab_id in tab_ids:
            tab = self.get_tab(session_id, tab_id)
            if tab:
                tab.group = group_name

    def get_tabs_by_group(self, session_id: str) -> dict[str, list[Tab]]:
        groups: dict[str, list[Tab]] = {}
        for tab in self._tabs.get(session_id, []):
            g = tab.group or "_ungrouped"
            groups.setdefault(g, []).append(tab)
        return groups

    def get_all_tabs(self) -> list[Tab]:
        result = []
        for tabs in self._tabs.values():
            result.extend(tabs)
        return result

    def clear_session(self, session_id: str):
        self._tabs.pop(session_id, None)
        self._active_tab.pop(session_id, None)

    def clear_all(self):
        self._tabs.clear()
        self._active_tab.clear()
