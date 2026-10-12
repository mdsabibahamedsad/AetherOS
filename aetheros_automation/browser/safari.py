from __future__ import annotations

import logging

from aetheros_automation.browser.base import BrowserAutomation

log = logging.getLogger(__name__)


class SafariAutomation(BrowserAutomation):
    @property
    def browser_type(self) -> str:
        return "safari"

    async def _get_playwright(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. Install it with: pip install playwright && playwright install webkit"
            )
        p = await async_playwright().start()
        return p

    async def _launch(self):
        p = await self._get_playwright()
        launch_options = {
            "headless": self._config.headless,
            "timeout": int(self._config.timeout * 1000),
        }
        if self._config.proxy:
            launch_options["proxy"] = {"server": self._config.proxy}

        self._browser = await p.webkit.launch(**launch_options)
        self._context = await self._browser.new_context(
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            }
        )
        self._page = await self._context.new_page()
