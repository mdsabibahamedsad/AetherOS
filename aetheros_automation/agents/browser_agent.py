from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class BrowserAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.BROWSER

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        desc = task.description.lower()
        logger.info("Browser agent executing: %s", task.name)

        url = task.metadata.get("url", "")
        instructions = task.metadata.get("instructions", desc)

        if not url:
            url = self._extract_url(desc)

        if url:
            return await self.navigate_and_extract(url, instructions)

        return "No URL found in task description or metadata."

    async def navigate_and_extract(self, url: str, instructions: str) -> str:
        logger.info("Navigating to %s", url)
        result_parts: list[str] = [
            f"# Browser Action\nURL: {url}\nInstructions: {instructions}\n",
        ]
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AetherosBrowser/1.0)"}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                content = resp.text
                result_parts.append(f"Status: {resp.status_code}")
                result_parts.append(f"Content length: {len(content)} chars")
        except ImportError:
            result_parts.append("httpx not available; using urllib")
            try:
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    content = resp.read().decode("utf-8", errors="replace")
                    result_parts.append(f"Status: {resp.status}")
                    result_parts.append(f"Content length: {len(content)} chars")
            except Exception as e:
                result_parts.append(f"Error fetching URL: {e}")
                return "\n".join(result_parts)
        except Exception as e:
            result_parts.append(f"Error fetching URL: {e}")
            return "\n".join(result_parts)

        extracted = self._extract_text(content, instructions)
        result_parts.append(f"\n## Extracted Content\n{extracted[:3000]}")
        return "\n".join(result_parts)

    def _extract_url(self, text: str) -> str:
        import re
        match = re.search(r"https?://[^\s,;)'\"<>]+", text)
        return match.group(0) if match else ""

    def _extract_text(self, html: str, instructions: str) -> str:
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        lines = text.split(". ")
        relevant: list[str] = []
        keywords = instructions.lower().split() if instructions else []
        for line in lines:
            if not keywords or any(kw in line.lower() for kw in keywords):
                relevant.append(line.strip())
        return ". ".join(relevant[:50])


AgentRegistry.register(AgentRole.BROWSER, BrowserAgent)
