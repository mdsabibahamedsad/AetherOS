from __future__ import annotations

import os
import sys
from typing import Any

from aetheros_voice.computer.screenshot import ScreenshotCapture


class ScreenUnderstanding:
    def __init__(self):
        self._screenshot = ScreenshotCapture()
        self._last_context: str = ""

    async def analyze(self, screenshot_path: str | None = None) -> str:
        if screenshot_path is None:
            screenshot_path = await self._screenshot.capture()
        if not screenshot_path or not os.path.exists(screenshot_path):
            return "No screenshot available"
        import base64
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "Describe what is on this screen in detail. List all visible UI elements, text, buttons, and their approximate positions."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ]},
                ],
                max_tokens=1000,
            )
            self._last_context = response.choices[0].message.content
            return self._last_context
        except ImportError:
            return "OpenAI not available for screen analysis"
        except Exception as e:
            return f"Screen analysis failed: {e}"

    async def read_webpage(self) -> str:
        return "Webpage content not available without browser context"

    async def find_error(self, screenshot_path: str | None = None) -> str:
        context = await self.analyze(screenshot_path)
        if "error" in context.lower() or "failed" in context.lower() or "exception" in context.lower():
            return f"Potential error detected: {context[:500]}"
        return "No obvious errors detected on screen"

    @property
    def last_context(self) -> str:
        return self._last_context
