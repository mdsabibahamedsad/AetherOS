"""
Research Mode for AetherOS Intelligence Engine.

Multi-source research that combines findings from:
    - Web search
    - Documentation
    - GitHub
    - Local files
    - Knowledge base

Results are synthesized into comprehensive research reports.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchFinding:
    """A single finding from a research source.

    Attributes:
        source: Source type (web, docs, github, knowledge, file)
        title: Finding title
        content: Finding content/summary
        url: Source URL (if applicable)
        relevance: Relevance score (0.0 - 1.0)
        timestamp: When the finding was retrieved
        metadata: Additional source metadata
    """
    source: str = ""
    title: str = ""
    content: str = ""
    url: str = ""
    relevance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchReport:
    """A complete research report.

    Attributes:
        id: Unique report identifier
        query: The research query
        findings: All findings from all sources
        summary: Synthesized summary
        sections: Organized sections of the report
        depth: Research depth level
        total_sources: Number of sources consulted
        duration: How long the research took
        timestamp: When the report was generated
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    findings: List[ResearchFinding] = field(default_factory=list)
    summary: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    depth: int = 1
    total_sources: int = 0
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ResearchMode:
    """Multi-source research engine.

    Combines web search, documentation lookup, GitHub exploration,
    local file analysis, and knowledge base queries into comprehensive
    research reports.

    Usage::

        research = ResearchMode()

        # Quick research
        report = research.research("Python async patterns")

        # Deep research with recursion
        report = research.deep_research("Kubernetes deployment strategies", depth=2)
    """

    def __init__(self) -> None:
        self._reports: List[ResearchReport] = []

    # ------------------------------------------------------------------
    # Main research methods
    # ------------------------------------------------------------------

    def research(self, query: str,
                 sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run a multi-source research query.

        Args:
            query: The research question or topic
            sources: Sources to search (web, docs, github, knowledge, files)
                     Defaults to all available sources.

        Returns:
            Research report with findings and summary.
        """
        start = time.time()
        available_sources = sources or ["web", "docs", "github", "knowledge", "files"]

        findings = []
        for source in available_sources:
            try:
                source_start = time.time()
                source_findings = self._search_source(source, query)
                for f in source_findings:
                    f.timestamp = time.time()
                findings.extend(source_findings)
                logger.debug("Research source '%s' returned %d results in %.2fs",
                             source, len(source_findings), time.time() - source_start)
            except Exception as exc:
                logger.warning("Research source '%s' failed: %s", source, exc)

        # Sort by relevance, then deduplicate by URL so the same source
        # URL isn't reported twice across different search backends.
        findings.sort(key=lambda f: f.relevance, reverse=True)
        findings = self._dedupe_findings(findings)

        # Track which sources produced no results so the summary is honest
        # about coverage.
        produced = {f.source for f in findings}
        empty_sources = [s for s in available_sources if s not in produced]

        # Synthesize report
        summary = self._synthesize_summary(query, findings, empty_sources)
        sections = self._organize_sections(findings)

        report = ResearchReport(
            query=query,
            findings=findings[:20],  # Keep top 20
            summary=summary,
            sections=sections,
            total_sources=len(available_sources),
            duration=round(time.time() - start, 2),
        )

        self._reports.append(report)

        return self._report_to_dict(report)

    def deep_research(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """Run a deep, iterative research session.

        Explores the topic, then dives deeper into subtopics
        discovered during research.

        Args:
            topic: Research topic
            depth: How deep to recurse (1-3). Each level explores
                   subtopics from the previous level.

        Returns:
            Comprehensive research report with nested findings.
        """
        depth = min(max(depth, 1), 3)  # Clamp to 1-3

        start = time.time()
        all_findings = []
        explored_topics = {topic}
        current_topics = [topic]

        for level in range(depth):
            level_findings = []
            for current_topic in current_topics:
                try:
                    findings = self._research_topic_deep(current_topic, level)
                    level_findings.extend(findings)

                    # Extract subtopics for next level
                    if level < depth - 1:
                        subtopics = self._extract_subtopics(findings)
                        for st in subtopics:
                            if st.lower() not in explored_topics:
                                explored_topics.add(st.lower())
                                current_topics.append(st)
                except Exception as exc:
                    logger.warning("Deep research level %d topic '%s' failed: %s",
                                   level, current_topic, exc)

            all_findings.extend(level_findings)

        all_findings = self._dedupe_findings(all_findings)

        # Synthesize final report
        summary_parts = [f"Deep research on '{topic}' ({depth} level(s))"]
        if all_findings:
            summary_parts.append(f"Found {len(all_findings)} findings across {len(explored_topics)} topics")

        sections = []
        for level in range(depth):
            level_start = level * max(1, len(all_findings) // depth)
            level_end = (level + 1) * max(1, len(all_findings) // depth)
            level_findings = all_findings[level_start:level_end]
            if level_findings:
                sections.append({
                    "title": f"Level {level + 1} Findings",
                    "findings": [
                        {"source": f.source, "title": f.title, "content": f.content[:200]}
                        for f in level_findings[:5]
                    ],
                })

        report = ResearchReport(
            query=topic,
            findings=all_findings,
            summary="\n".join(summary_parts),
            sections=sections,
            depth=depth,
            total_sources=len(explored_topics),
            duration=round(time.time() - start, 2),
        )

        self._reports.append(report)
        return self._report_to_dict(report)

    # ------------------------------------------------------------------
    # Source search implementations
    # ------------------------------------------------------------------

    def _search_source(self, source: str, query: str) -> List[ResearchFinding]:
        """Search a specific source for the query.

        Args:
            source: Source type identifier
            query: Search query

        Returns:
            List of findings from this source
        """
        dispatcher = {
            "web": self._search_web,
            "docs": self._search_docs,
            "github": self._search_github,
            "knowledge": self._search_knowledge,
            "files": self._search_files,
        }

        handler = dispatcher.get(source)
        if handler:
            return handler(query)
        return []

    def _search_web(self, query: str) -> List[ResearchFinding]:
        """Search the web for real information via the configured backend.

        Returns real results from ``web_search_tool``. Never fabricates
        URLs: if no provider is configured, the search fails, or the
        backend returns nothing, an empty list is returned.
        """
        try:
            from tools.web_tools import web_search_tool
            raw = web_search_tool(query, limit=5)
            data = json.loads(raw)
        except Exception as exc:
            logger.debug("Research web search failed: %s", exc)
            return []

        if not data.get("success"):
            logger.debug("Research web search unavailable: %s",
                         data.get("error", "unknown"))
            return []

        web = data.get("data", {}).get("web", [])
        findings = []
        for i, item in enumerate(web):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url or not title:
                continue
            position = item.get("position", i + 1)
            findings.append(ResearchFinding(
                source="web",
                title=title[:200],
                content=(item.get("description") or "")[:300],
                url=url,
                relevance=max(0.1, 1.0 - (position - 1) * 0.15),
                metadata={"position": position},
            ))
        return findings

    def _search_docs(self, query: str) -> List[ResearchFinding]:
        """Search for documentation via a real site-scoped web search.

        Runs the query against a small set of known documentation domains
        and only keeps results the backend actually returned. Results are
        additionally filtered client-side to those documentation domains so
        the ``docs`` source never reports non-documentation URLs (some
        backends ignore the ``site:`` operator). Returns an empty list when
        the backend is unavailable or nothing matches.
        """
        doc_sites = (
            "docs.python.org", "react.dev", "docs.docker.com",
            "kubernetes.io/docs", "docs.aws.amazon.com",
            "learn.microsoft.com", "developer.mozilla.org",
            "dev.mysql.com/doc", "docs.npmjs.com",
        )
        site_query = " OR ".join(f"site:{site}" for site in doc_sites)
        scoped = f"{query} ({site_query})"
        try:
            from tools.web_tools import web_search_tool
            raw = web_search_tool(scoped, limit=5)
            data = json.loads(raw)
        except Exception as exc:
            logger.debug("Research docs search failed: %s", exc)
            return []

        if not data.get("success"):
            return []

        def _is_doc_domain(url: str) -> bool:
            host = url.split("://", 1)[-1].split("/", 1)[0].lower()
            host = host.split(":", 1)[0]
            return any(host == site or host.endswith("." + site)
                       for site in doc_sites)

        findings = []
        for i, item in enumerate(data.get("data", {}).get("web", [])):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url or not title or not _is_doc_domain(url):
                continue
            position = item.get("position", i + 1)
            findings.append(ResearchFinding(
                source="docs",
                title=title[:200],
                content=(item.get("description") or "")[:300],
                url=url,
                relevance=max(0.1, 0.9 - (position - 1) * 0.1),
                metadata={"position": position},
            ))
        return findings

    def _search_github(self, query: str) -> List[ResearchFinding]:
        """Search GitHub for repositories and code via a real scoped search.

        Only results whose URL actually points at github.com are kept, so
        every finding's ``url`` is a real GitHub location.
        """
        try:
            from tools.web_tools import web_search_tool
            raw = web_search_tool(f"{query} site:github.com", limit=5)
            data = json.loads(raw)
        except Exception as exc:
            logger.debug("Research github search failed: %s", exc)
            return []

        if not data.get("success"):
            return []

        findings = []
        for i, item in enumerate(data.get("data", {}).get("web", [])):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url or not title or "github.com" not in url:
                continue
            position = item.get("position", i + 1)
            findings.append(ResearchFinding(
                source="github",
                title=title[:200],
                content=(item.get("description") or "")[:300],
                url=url,
                relevance=max(0.1, 0.8 - (position - 1) * 0.1),
                metadata={"position": position},
            ))
        return findings

    def _search_knowledge(self, query: str) -> List[ResearchFinding]:
        """Search the local knowledge base."""
        try:
            from aetheros_knowledge.search.engine import SearchEngine
            engine = SearchEngine()
            results = engine.hybrid_search(query, top_k=5)
            return [
                ResearchFinding(
                    source="knowledge",
                    title=r.get("title", "Knowledge base result"),
                    content=r.get("content", "")[:300],
                    relevance=r.get("score", 0.5),
                    url=r.get("url", ""),
                    metadata={"score": r.get("score", 0.5)},
                )
                for r in results
            ]
        except Exception:
            return []

    def _search_files(self, query: str) -> List[ResearchFinding]:
        """Search local files for relevant information.

        Uses the built-in ``search_files`` backend against the current
        working directory. Only real matches are reported; no results are
        ever synthesized.
        """
        base = os.getcwd()
        if not query or not os.path.isdir(base):
            return []
        try:
            from tools.file_tools import search_tool
            raw = search_tool(
                pattern=re.escape(query), target="content", path=base,
                limit=20, output_mode="files_only",
                task_id=f"research-{uuid.uuid4().hex[:8]}",
            )
            data = json.loads(raw)
        except Exception as exc:
            logger.debug("Research file search failed: %s", exc)
            return []

        files = data.get("files", [])
        if not isinstance(files, list):
            return []

        findings = []
        for i, fp in enumerate(files):
            fp_str = fp.get("path", "") if isinstance(fp, dict) else str(fp)
            if not fp_str:
                continue
            findings.append(ResearchFinding(
                source="files",
                title=f"Local match: {os.path.basename(fp_str)}",
                content=fp_str[:300],
                url=f"file://{fp_str.replace(os.sep, '/')}",
                relevance=max(0.1, 0.7 - i * 0.1),
                metadata={"path": fp_str},
            ))
        return findings

    # ------------------------------------------------------------------
    # Deep research helpers
    # ------------------------------------------------------------------

    def _research_topic_deep(self, topic: str, level: int) -> List[ResearchFinding]:
        """Research a single topic at a given depth level."""
        sources = ["web", "docs", "github"]
        if level > 0:
            sources.append("knowledge")
        if level > 1:
            sources.append("files")
        findings = []
        for source in sources:
            try:
                findings.extend(self._search_source(source, topic))
            except Exception as exc:
                logger.warning("Deep research source '%s' failed: %s",
                               source, exc)
        return self._dedupe_findings(findings)

    @staticmethod
    def _dedupe_findings(findings: List[ResearchFinding]) -> List[ResearchFinding]:
        """Remove duplicate findings, preferring findings that carry a URL.

        Deduplication key is the lowercased URL when present, otherwise the
        source + title pair. Keeps the highest-relevance representative of
        each duplicate set.
        """
        seen: Dict[str, float] = {}
        unique: List[ResearchFinding] = []
        for f in findings:
            key = f.url.strip().lower() if f.url and f.url.strip() else f"{f.source}|{f.title}".lower()
            if key in seen:
                if f.relevance > seen[key]:
                    # Replace the stored finding with the higher-relevance one.
                    for idx, existing in enumerate(unique):
                        existing_key = (existing.url.strip().lower()
                                        if existing.url and existing.url.strip()
                                        else f"{existing.source}|{existing.title}".lower())
                        if existing_key == key:
                            unique[idx] = f
                            seen[key] = f.relevance
                            break
                continue
            seen[key] = f.relevance
            unique.append(f)
        return unique

    def _extract_subtopics(self, findings: List[ResearchFinding]) -> List[str]:
        """Extract potential subtopics from findings."""
        subtopics = set()
        for f in findings:
            # Extract capitalized phrases as potential subtopics
            words = f.title.split()
            for i, word in enumerate(words):
                if len(word) > 3 and i < len(words) - 1 and word[0].isupper():
                    phrase = f"{word} {words[i+1]}"
                    if len(phrase) < 60:
                        subtopics.add(phrase)
        return list(subtopics)[:3]  # Top 3 subtopics

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from a query."""
        # Filter out common stop words
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for",
                      "of", "with", "and", "or", "is", "are", "was",
                      "how", "what", "why", "when", "where", "which",
                      "best", "should", "can"}
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique[:5]

    # ------------------------------------------------------------------
    # Report synthesis
    # ------------------------------------------------------------------

    def _synthesize_summary(self, query: str,
                            findings: List[ResearchFinding],
                            empty_sources: List[str] = None) -> str:
        """Synthesize findings into a coherent summary."""
        if not findings:
            if empty_sources:
                return (f"No findings for '{query}'. Sources with no results: "
                        f"{', '.join(sorted(empty_sources))}.")
            return f"No findings for '{query}'."

        source_counts = {}
        for f in findings:
            source_counts[f.source] = source_counts.get(f.source, 0) + 1

        sources_str = ", ".join(
            f"{count} from {src}"
            for src, count in source_counts.items()
        )

        summary_parts = [
            f"Research on '{query}':",
            f"Found {len(findings)} findings ({sources_str}).",
        ]

        if empty_sources:
            summary_parts.append(
                "Sources with no results: "
                + ", ".join(sorted(empty_sources)) + "."
            )

        # Top sources by relevance
        top = findings[:3]
        if top:
            summary_parts.append("Key findings:")
            for f in top:
                summary_parts.append(f"  - [{f.source}] {f.title}")

        return "\n".join(summary_parts)

    def _organize_sections(self,
                           findings: List[ResearchFinding]) -> List[Dict[str, Any]]:
        """Organize findings into sections by source."""
        by_source: Dict[str, List[ResearchFinding]] = {}
        for f in findings:
            by_source.setdefault(f.source, []).append(f)

        sections = []
        for source, source_findings in by_source.items():
            sections.append({
                "title": f"{source.capitalize()} Results",
                "source": source,
                "count": len(source_findings),
                "findings": [
                    {
                        "title": f.title,
                        "content": f.content[:200],
                        "url": f.url,
                        "relevance": f.relevance,
                        "metadata": f.metadata,
                    }
                    for f in source_findings[:5]
                ],
            })
        return sections

    def _report_to_dict(self, report: ResearchReport) -> Dict[str, Any]:
        """Convert a ResearchReport to a dict."""
        return {
            "id": report.id,
            "query": report.query,
            "summary": report.summary,
            "sections": report.sections,
            "findings": [
                {
                    "source": f.source,
                    "title": f.title,
                    "content": f.content[:200],
                    "url": f.url,
                    "relevance": f.relevance,
                    "metadata": f.metadata,
                }
                for f in report.findings[:10]
            ],
            "depth": report.depth,
            "total_sources": report.total_sources,
            "duration": report.duration,
            "timestamp": report.timestamp,
        }

    def get_recent_reports(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent research reports."""
        return [self._report_to_dict(r) for r in self._reports[-limit:]]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific report by ID."""
        for r in self._reports:
            if r.id == report_id:
                return self._report_to_dict(r)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get research statistics."""
        return {
            "total_reports": len(self._reports),
            "recent_reports": self.get_recent_reports(3),
            "available_sources": ["web", "docs", "github", "knowledge", "files"],
        }
