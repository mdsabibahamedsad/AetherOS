from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.RESEARCH

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        topic = task.metadata.get("topic", task.description)
        logger.info("Research agent researching: %s", topic[:80])

        result = await self.research(topic)

        formatted = json.dumps(result, indent=2)
        task.metadata["research_result"] = result
        return formatted

    async def research(self, topic: str) -> dict:
        logger.info("Gathering information on: %s", topic[:80])
        sources: list[dict] = []
        key_findings: list[str] = []

        import re
        urls = re.findall(r"https?://[^\s,;)'\"<>]+", topic)
        for url in urls[:5]:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code == 200:
                        sources.append({"url": url, "status": resp.status_code})
                        text = self._clean_html(resp.text)
                        lines = [l.strip() for l in text.split(". ") if len(l.strip()) > 40]
                        key_findings.extend(lines[:3])
            except ImportError:
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        sources.append({"url": url, "status": resp.status})
                except Exception:
                    sources.append({"url": url, "status": "error"})
            except Exception:
                sources.append({"url": url, "status": "error"})

        if not key_findings:
            sentences = [s.strip() for s in re.split(r"[.!?\n]", topic) if len(s.strip()) > 20]
            key_findings = sentences[:5]

        summary = self._generate_summary(topic, key_findings, sources)

        return {
            "topic": topic,
            "summary": summary,
            "sources": sources,
            "key_findings": key_findings[:5],
            "finding_count": len(key_findings),
            "source_count": len(sources),
        }

    def _generate_summary(self, topic: str, findings: list[str], sources: list[dict]) -> str:
        src_info = f" from {len(sources)} source(s)" if sources else ""
        if findings:
            top = findings[0][:200]
            return f"Research on '{topic[:100]}'{src_info}. Key finding: {top}"
        return f"Research conducted on '{topic[:100]}'{src_info}. No specific findings extracted."

    def _clean_html(self, html: str) -> str:
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


AgentRegistry.register(AgentRole.RESEARCH, ResearchAgent)
