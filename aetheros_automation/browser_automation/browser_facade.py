from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.browser.manager import BrowserManager
from aetheros_automation.browser.base import BrowserAutomation
from aetheros_automation.browser_automation.tab_manager import TabManager
from aetheros_automation.browser_automation.bookmark_manager import BookmarkManager
from aetheros_automation.browser_automation.history_manager import HistoryManager
from aetheros_automation.browser_automation.download_manager import DownloadManager
from aetheros_automation.browser_automation.web_search_manager import WebSearchManager
from aetheros_automation.browser_automation.browser_workflow_engine import BrowserWorkflowEngine
from aetheros_automation.browser_automation.ai_browser_assistant import AIBrowserAssistant
from aetheros_automation.browser_automation.research_mode import ResearchMode
from aetheros_automation.browser_automation.computer_use_manager import ComputerUseManager
from aetheros_automation.browser_automation.page_analyzer import PageAnalyzer
from aetheros_automation.browser_automation.prompt_injection_protection import PromptInjectionProtection
from aetheros_automation.browser_automation.browser_permissions import BrowserPermissions

logger = logging.getLogger(__name__)


class BrowserFacade:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.tab_manager = TabManager(self.browser_manager)
        self.bookmark_manager = BookmarkManager()
        self.history_manager = HistoryManager()
        self.download_manager = DownloadManager()
        self.web_search_manager = WebSearchManager()
        self.workflow_engine = BrowserWorkflowEngine(self)
        self.ai_assistant = AIBrowserAssistant(self)
        self.research_mode = ResearchMode(self, self.ai_assistant)
        self.computer_use = ComputerUseManager()
        self.page_analyzer = PageAnalyzer()
        self.prompt_injection = PromptInjectionProtection()
        self.browser_permissions = BrowserPermissions()
        self._active_browser_id: str = ""
        self._private_mode: bool = False

    @property
    def active_browser_id(self) -> str:
        return self._active_browser_id

    @active_browser_id.setter
    def active_browser_id(self, value: str):
        self._active_browser_id = value

    @property
    def private_mode(self) -> bool:
        return self._private_mode

    @private_mode.setter
    def private_mode(self, value: bool):
        self._private_mode = value

    async def create_session(
        self, browser_type: str = "chrome", headless: bool = False, private: bool = False
    ) -> str:
        from aetheros_automation.models.models import BrowserConfig

        config = BrowserConfig(browser_type=browser_type, headless=headless)
        browser = self.browser_manager.create_browser(browser_type, config)
        self.tab_manager.create_tab(browser)
        self._private_mode = private
        logger.info("Browser session created: type=%s headless=%s private=%s", browser_type, headless, private)
        return browser

    async def close_session(self, session_id: str):
        await self.browser_manager.close_browser(session_id)
        self.tab_manager.clear_session(session_id)
        logger.info("Browser session closed: %s", session_id)

    async def close_all_sessions(self):
        await self.browser_manager.close_all()
        self.tab_manager.clear_all()
        logger.info("All browser sessions closed")

    def get_status(self) -> dict[str, Any]:
        sessions = self.browser_manager.list_sessions()
        active_tabs = self.tab_manager.get_all_tabs()
        return {
            "sessions": len(sessions),
            "active_tabs": len(active_tabs),
            "active_browser": self._active_browser_id,
            "private_mode": self._private_mode,
            "bookmarks": self.bookmark_manager.count(),
            "downloads": self.download_manager.count(),
            "history": self.history_manager.count(),
            "search_providers": len(self.web_search_manager.get_providers()),
        }
