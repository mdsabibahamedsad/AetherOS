from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from aetheros_automation.models.models import BrowserConfig

log = logging.getLogger(__name__)


class BrowserAutomation(ABC):
    def __init__(self, config: BrowserConfig | None = None):
        self._config = config or BrowserConfig()
        self._page = None
        self._browser = None
        self._context = None

    @property
    @abstractmethod
    def browser_type(self) -> str: ...

    async def _ensure_page(self):
        if self._page is None:
            await self._launch()

    async def _launch(self):
        p = await self._get_playwright()
        channel = self._get_channel()
        launch_options = {
            "headless": self._config.headless,
            "timeout": int(self._config.timeout * 1000),
        }
        if channel:
            launch_options["channel"] = channel
        if self._config.user_data_dir:
            launch_options["user_data_dir"] = self._config.user_data_dir
        if self._config.proxy:
            launch_options["proxy"] = {"server": self._config.proxy}

        self._browser = await p.chromium.launch(**launch_options)
        self._context = await self._browser.new_context(
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            }
        )
        self._page = await self._context.new_page()

    @abstractmethod
    async def _get_playwright(self): ...

    def _get_channel(self) -> str | None:
        return None

    async def navigate(self, url: str):
        await self._ensure_page()
        await self._page.goto(url, wait_until="networkidle")

    async def click(self, selector: str):
        await self._ensure_page()
        await self._page.click(selector)

    async def type_text(self, selector: str, text: str):
        await self._ensure_page()
        await self._page.fill(selector, text)

    async def get_text(self, selector: str) -> str:
        await self._ensure_page()
        el = await self._page.query_selector(selector)
        if el is None:
            return ""
        return await el.inner_text()

    async def get_html(self) -> str:
        await self._ensure_page()
        return await self._page.content()

    async def get_url(self) -> str:
        await self._ensure_page()
        return self._page.url

    async def screenshot(self) -> bytes:
        await self._ensure_page()
        return await self._page.screenshot(full_page=True)

    async def execute_js(self, script: str) -> Any:
        await self._ensure_page()
        return await self._page.evaluate(script)

    async def login(
        self,
        url: str,
        username: str,
        password: str,
        username_sel: str,
        password_sel: str,
        submit_sel: str,
    ):
        await self.navigate(url)
        await self.type_text(username_sel, username)
        await self.type_text(password_sel, password)
        await self.click(submit_sel)
        await self._page.wait_for_load_state("networkidle")

    async def fill_form(self, fields: dict):
        await self._ensure_page()
        for selector, value in fields.items():
            await self._page.fill(selector, str(value))

    async def upload_file(self, selector: str, file_path: str):
        await self._ensure_page()
        file_input = await self._page.query_selector(selector)
        if file_input:
            await file_input.set_input_files(Path(file_path).absolute().as_posix())

    async def download_file(self, url: str, dest_path: str):
        await self._ensure_page()
        async with self._page.expect_download() as download_info:
            await self._page.goto(url, wait_until="networkidle")
        download = await download_info.value
        await download.save_as(dest_path)

    async def extract_data(self, selectors: dict) -> dict:
        await self._ensure_page()
        result = {}
        for name, selector in selectors.items():
            try:
                el = await self._page.query_selector(selector)
                if el is not None:
                    result[name] = await el.inner_text()
                else:
                    result[name] = None
            except Exception as e:
                log.warning("extract_data %s failed: %s", name, e)
                result[name] = None
        return result

    async def read_page(self) -> str:
        await self._ensure_page()
        return await self._page.evaluate(
            "() => document.body.innerText"
        )

    async def search(self, query: str) -> str:
        await self.navigate(f"https://www.google.com/search?q={query}")
        return await self.read_page()

    async def generate_pdf(self, path: str):
        await self._ensure_page()
        await self._page.pdf(path=path)

    async def wait_for_element(self, selector: str, timeout: float = 30):
        await self._ensure_page()
        await self._page.wait_for_selector(selector, timeout=timeout * 1000)

    async def scroll_to(self, selector: str):
        await self._ensure_page()
        await self._page.evaluate(
            f"document.querySelector('{selector}')?.scrollIntoView({{behavior: 'smooth', block: 'center'}})"
        )

    async def hover(self, selector: str):
        await self._ensure_page()
        await self._page.hover(selector)

    async def get_cookies(self) -> list[dict]:
        await self._ensure_page()
        return await self._context.cookies()

    async def set_cookies(self, cookies: list[dict]):
        await self._ensure_page()
        await self._context.add_cookies(cookies)

    async def close(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                log.warning("Error closing browser: %s", e)
        self._page = None
        self._context = None
        self._browser = None
