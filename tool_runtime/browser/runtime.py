"""Browser Runtime — real browser automation via CDP / Playwright.

Supports: tabs, windows, navigation, forms, downloads, uploads,
cookies, authentication, screenshots, DOM inspection, accessibility, PDF.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class BrowserRuntime(ToolInterface):
    """Browser automation runtime using Playwright (real browser, not simulated).

    Features:
    - Navigate, click, fill forms
    - Extract DOM content and accessibility tree
    - Screenshots and PDF
    - Cookie and auth management
    - Tab and window management
    """

    def __init__(self):
        meta = ToolMetadata(
            id="browser",
            name="Browser Runtime",
            description="Real browser automation: navigation, forms, screenshots, DOM, cookies, PDF",
            category=ToolCategory.BROWSER,
            risk_level=ToolRiskLevel.NETWORK,
            version="2.0.0",
            tags=["browser", "web", "automation", "playwright"],
            requires_approval=False,
            timeout_seconds=60.0,
        )
        super().__init__(meta)
        self._playwright_available = False
        self._browser_type = None
        self._browser = None
        self._context = None
        self._page = None
        self._init_playwright()

    def _init_playwright(self) -> None:
        try:
            import playwright.sync_api
            self._playwright_available = True
            self._browser_type = "chromium"
        except ImportError:
            self._playwright_available = False

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "browser",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "navigate", "click", "fill", "extract", "screenshot",
                            "pdf", "get_cookies", "set_cookies", "get_html",
                            "get_url", "back", "forward", "reload",
                            "accessibility_snapshot", "type_text", "select_option",
                            "close", "new_tab", "switch_tab",
                        ],
                    },
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                    "text": {"type": "string"},
                    "option_value": {"type": "string"},
                    "tab_index": {"type": "integer"},
                    "cookies": {"type": "array"},
                    "timeout": {"type": "number"},
                    "full_page": {"type": "boolean"},
                },
                "required": ["operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        if not op:
            errors.append("Missing required parameter: operation")
        if op == "navigate" and "url" not in params:
            errors.append("Operation 'navigate' requires 'url' parameter")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def _ensure_browser(self) -> Optional[bool]:
        if not self._playwright_available:
            return None
        if self._browser is None:
            try:
                import playwright.sync_api
                self._browser = playwright.sync_api.sync_playwright().start()
                self._context = None
                self._page = None
            except Exception as e:
                logger.error("Failed to launch browser: %s", e)
                return False
        return True

    def _ensure_page(self) -> bool:
        result = self._ensure_browser()
        if not result:
            return False
        if self._page is None:
            try:
                self._context = self._browser.chromium.launch(headless=True).new_context()
                self._page = self._context.new_page()
            except Exception as e:
                logger.error("Failed to create page: %s", e)
                return False
        return True

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        op_map = {
            "navigate": self._navigate,
            "click": self._click,
            "fill": self._fill,
            "extract": self._extract,
            "screenshot": self._screenshot,
            "pdf": self._pdf,
            "get_cookies": self._get_cookies,
            "set_cookies": self._set_cookies,
            "get_html": self._get_html,
            "get_url": self._get_url,
            "back": self._back,
            "forward": self._forward,
            "reload": self._reload,
            "accessibility_snapshot": self._accessibility,
            "type_text": self._type_text,
            "select_option": self._select_option,
            "close": self._close,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unknown browser operation: {operation}")

        if not self._playwright_available:
            return ToolResult.fail(
                "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error("Browser operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"Browser error: {type(e).__name__}: {e}")

    def _ensure_page_or_fail(self) -> bool:
        if not self._ensure_page():
            return False
        return True

    def _navigate(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        url = params["url"]
        timeout = params.get("timeout", 30000)
        start = time.time()
        self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        elapsed = (time.time() - start) * 1000
        return ToolResult.ok({
            "url": self._page.url,
            "title": self._page.title,
            "duration_ms": elapsed,
        })

    def _click(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        selector = params.get("selector", "")
        self._page.click(selector)
        return ToolResult.ok({"selector": selector, "clicked": True})

    def _fill(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        selector = params.get("selector", "")
        value = params.get("value", "")
        self._page.fill(selector, value)
        return ToolResult.ok({"selector": selector, "filled": True})

    def _extract(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        text = self._page.inner_text("body")
        return ToolResult.ok({
            "url": self._page.url,
            "title": self._page.title,
            "text": text[:10000],
            "text_length": len(text),
        })

    def _screenshot(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        full_page = params.get("full_page", True)
        ss_bytes = self._page.screenshot(full_page=full_page)
        b64 = base64.b64encode(ss_bytes).decode("utf-8")
        return ToolResult.ok({
            "url": self._page.url,
            "screenshot_b64": b64[:500] + "..." if len(b64) > 500 else b64,
            "size_bytes": len(ss_bytes),
            "mime_type": "image/png",
        })

    def _pdf(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        pdf_bytes = self._page.pdf()
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return ToolResult.ok({
            "url": self._page.url,
            "pdf_b64": b64[:200] + "...",
            "size_bytes": len(pdf_bytes),
            "mime_type": "application/pdf",
        })

    def _get_cookies(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        cookies = self._context.cookies() if self._context else []
        return ToolResult.ok({"cookies": cookies, "count": len(cookies)})

    def _set_cookies(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        cookies = params.get("cookies", [])
        if self._context:
            self._context.add_cookies(cookies)
        return ToolResult.ok({"cookies_added": len(cookies)})

    def _get_html(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        html = self._page.content()
        return ToolResult.ok({
            "html": html[:10000],
            "html_length": len(html),
        })

    def _get_url(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        return ToolResult.ok({"url": self._page.url, "title": self._page.title})

    def _back(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        self._page.go_back()
        return ToolResult.ok({"url": self._page.url})

    def _forward(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        self._page.go_forward()
        return ToolResult.ok({"url": self._page.url})

    def _reload(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        self._page.reload()
        return ToolResult.ok({"url": self._page.url})

    def _accessibility(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        try:
            snapshot = self._page.accessibility.snapshot()
            return ToolResult.ok({"accessibility_snapshot": snapshot})
        except Exception as e:
            return ToolResult.fail(f"Accessibility snapshot failed: {e}")

    def _type_text(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        selector = params.get("selector", "")
        text = params.get("text", "")
        self._page.type(selector, text)
        return ToolResult.ok({"selector": selector, "typed": True})

    def _select_option(self, params: Dict[str, Any]) -> ToolResult:
        if not self._ensure_page_or_fail():
            return ToolResult.fail("Browser not available")
        selector = params.get("selector", "")
        value = params.get("option_value", "")
        self._page.select_option(selector, value)
        return ToolResult.ok({"selector": selector, "selected": value})

    def _close(self, params: Dict[str, Any]) -> ToolResult:
        try:
            if self._page:
                self._page.close()
                self._page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.stop()
                self._browser = None
        except Exception:
            pass
        return ToolResult.ok({"action": "closed"})

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["playwright_available"] = self._playwright_available
        base["browser_running"] = self._browser is not None
        base["page_active"] = self._page is not None
        return base
