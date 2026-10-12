from __future__ import annotations

import logging
import uuid

from aetheros_automation.browser.base import BrowserAutomation
from aetheros_automation.browser.chrome import ChromeAutomation
from aetheros_automation.browser.firefox import FirefoxAutomation
from aetheros_automation.browser.edge import EdgeAutomation
from aetheros_automation.browser.safari import SafariAutomation
from aetheros_automation.browser.brave import BraveAutomation
from aetheros_automation.models.models import BrowserConfig

log = logging.getLogger(__name__)


class BrowserManager:
    _BROWSER_MAP = {
        "chrome": ChromeAutomation,
        "firefox": FirefoxAutomation,
        "edge": EdgeAutomation,
        "safari": SafariAutomation,
        "brave": BraveAutomation,
    }

    def __init__(self):
        self._sessions: dict[str, BrowserAutomation] = {}

    def create_browser(
        self,
        browser_type: str = "chrome",
        config: BrowserConfig | None = None,
    ) -> BrowserAutomation:
        browser_type = browser_type.lower()
        if browser_type not in self._BROWSER_MAP:
            raise ValueError(
                f"Unsupported browser type: {browser_type}. "
                f"Supported types: {', '.join(self._BROWSER_MAP)}"
            )
        cls = self._BROWSER_MAP[browser_type]
        resolved_config = config or BrowserConfig(browser_type=browser_type)
        browser = cls(resolved_config)
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = browser
        log.info("Created %s browser session: %s", browser_type, session_id)
        return browser

    def get_browser(self, session_id: str) -> BrowserAutomation:
        if session_id not in self._sessions:
            raise KeyError(f"No browser session found: {session_id}")
        return self._sessions[session_id]

    async def close_browser(self, session_id: str):
        browser = self._sessions.pop(session_id, None)
        if browser is None:
            log.warning("Session %s not found for closing", session_id)
            return
        await browser.close()
        log.info("Closed browser session: %s", session_id)

    async def close_all(self):
        for session_id in list(self._sessions):
            await self.close_browser(session_id)
        log.info("All browser sessions closed")

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())
