from __future__ import annotations

import logging

from aetheros_automation.browser.base import BrowserAutomation

log = logging.getLogger(__name__)


class EdgeAutomation(BrowserAutomation):
    @property
    def browser_type(self) -> str:
        return "edge"

    async def _get_playwright(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. Install it with: pip install playwright && playwright install msedge"
            )
        p = await async_playwright().start()
        return p

    def _get_channel(self) -> str | None:
        return "msedge"
