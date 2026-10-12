from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from aetheros_automation.browser.base import BrowserAutomation
from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    url: str
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0


@dataclass
class ResearchFinding:
    id: str
    fact: str
    source_url: str
    confidence: float = 1.0
    category: str = "general"


@dataclass
class ResearchSession:
    id: str
    query: str
    sources: list[ResearchSource] = field(default_factory=list)
    findings: list[ResearchFinding] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    report: str = ""
    status: str = "in_progress"
    created_at: str = ""
    completed_at: str = ""


class ResearchMode:
    def __init__(self, browser_facade, ai_assistant):
        self._browser_facade = browser_facade
        self._ai_assistant = ai_assistant
        self._sessions: dict[str, ResearchSession] = {}

    async def start_research(self, query: str, urls: list[str] | None = None) -> ResearchSession:
        session = ResearchSession(
            id=str(uuid.uuid4()),
            query=query,
            status="in_progress",
            created_at=datetime.utcnow().isoformat(),
        )
        self._sessions[session.id] = session
        logger.info("Research session started: %s - %s", session.id, query)

        if urls:
            for url in urls:
                source = await self._analyze_source(url, query)
                session.sources.append(source)

        return session

    async def add_source(self, session_id: str, url: str) -> ResearchSource | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        source = await self._analyze_source(url, session.query)
        session.sources.append(source)
        return source

    async def _analyze_source(self, url: str, query: str) -> ResearchSource:
        source = ResearchSource(url=url)
        browser = self._browser_facade.browser_manager._sessions.get(
            self._browser_facade.active_browser_id
        )
        if browser is not None:
            try:
                await browser.navigate(url)
                page_text = await browser.read_page()
                title = await browser.execute_js("() => document.title")
                source.title = title if isinstance(title, str) else url
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]
                source.snippet = " ".join(lines[:5])[:300]
            except Exception as e:
                logger.warning("Failed to analyze source %s: %s", url, e)
        return source

    def extract_findings(self, session_id: str) -> list[ResearchFinding]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return session.findings

    def add_finding(self, session_id: str, fact: str, source_url: str, category: str = "general", confidence: float = 1.0) -> ResearchFinding | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        finding = ResearchFinding(
            id=str(uuid.uuid4()),
            fact=fact,
            source_url=source_url,
            confidence=confidence,
            category=category,
        )
        session.findings.append(finding)
        return finding

    def detect_contradictions(self, session_id: str) -> list[dict]:
        session = self._sessions.get(session_id)
        if session is None or len(session.findings) < 2:
            return []
        contradictions = []
        findings_text = {f.id: f.fact.lower() for f in session.findings}
        for i, f1 in enumerate(session.findings):
            for f2 in session.findings[i + 1 :]:
                f1_words = set(f1.fact.lower().split())
                f2_words = set(f2.fact.lower().split())
                if f1.source_url != f2.source_url:
                    overlap = len(f1_words & f2_words) / max(len(f1_words | f2_words), 1)
                    if overlap > 0.3:
                        contradictions.append({
                            "finding_a": {"fact": f1.fact, "source": f1.source_url},
                            "finding_b": {"fact": f2.fact, "source": f2.source_url},
                            "overlap": round(overlap, 2),
                        })
        session.contradictions = contradictions
        return contradictions

    def generate_report(self, session_id: str) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            return "Session not found."
        report_parts = [f"# Research Report: {session.query}", ""]
        report_parts.append(f"**Sources consulted:** {len(session.sources)}")
        report_parts.append(f"**Findings:** {len(session.findings)}")
        report_parts.append("")
        categories = {}
        for f in session.findings:
            categories.setdefault(f.category, []).append(f)
        for cat, findings in categories.items():
            report_parts.append(f"## {cat.title()}")
            for f in findings:
                report_parts.append(f"- {f.fact} (confidence: {f.confidence:.0%}) [source]({f.source_url})")
            report_parts.append("")
        if session.contradictions:
            report_parts.append("## Contradictions Detected")
            for c in session.contradictions:
                report_parts.append(f"- Discrepancy between [source A]({c['finding_a']['source']}) and [source B]({c['finding_b']['source']}) ({c['overlap']:.0%} overlap)")
            report_parts.append("")
        report = "\n".join(report_parts)
        session.report = report
        session.status = "completed"
        session.completed_at = datetime.utcnow().isoformat()
        return report

    def save_to_knowledge_hub(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or not session.report:
            return False
        try:
            from aetheros_automation.knowledge.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            kb.add_entry(
                title=f"Research: {session.query}",
                content=session.report,
                tags=["research", "browser", "automated"],
                source="browser_research",
            )
            return True
        except Exception as e:
            logger.warning("Failed to save to knowledge hub: %s", e)
            return False

    def get_session(self, session_id: str) -> ResearchSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[ResearchSession]:
        return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
