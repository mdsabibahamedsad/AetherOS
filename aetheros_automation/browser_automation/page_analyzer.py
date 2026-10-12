from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aetheros_automation.browser.base import BrowserAutomation

logger = logging.getLogger(__name__)


@dataclass
class PageAnalysis:
    url: str
    title: str
    text_content: str
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    prices: list[str] = field(default_factory=list)
    headings: list[dict[str, str]] = field(default_factory=list)
    meta_description: str = ""
    language: str = ""
    word_count: int = 0
    reading_time_minutes: int = 0


class PageAnalyzer:
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
    PRICE_REGEX = re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

    async def analyze_page(self, browser: BrowserAutomation) -> PageAnalysis:
        url = await browser.get_url()
        html = await browser.get_html()
        text = await browser.read_page()

        title = ""
        meta_desc = ""
        import re as re_module

        m = re_module.search(r"<title[^>]*>([^<]+)</title>", html, re_module.IGNORECASE)
        if m:
            title = m.group(1).strip()

        m = re_module.search(
            r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html,
            re_module.IGNORECASE,
        )
        if m:
            meta_desc = m.group(1).strip()

        words = text.split()
        word_count = len(words)
        reading_time = max(1, round(word_count / 200))

        analysis = PageAnalysis(
            url=url,
            title=title,
            text_content=text,
            meta_description=meta_desc,
            word_count=word_count,
            reading_time_minutes=reading_time,
        )

        analysis.emails = list(set(self.EMAIL_REGEX.findall(text)))
        analysis.phone_numbers = list(set(self.PHONE_REGEX.findall(text)))
        analysis.prices = list(set(self.PRICE_REGEX.findall(text)))
        analysis.headings = self._extract_headings(html)
        analysis.links = await self._extract_links(browser)
        analysis.images = list({
            m.group(1)
            for m in re_module.finditer(
                r'<img[^>]+src=["\']([^"\']+)["\']', html, re_module.IGNORECASE
            )
        })

        return analysis

    async def _extract_links(self, browser: BrowserAutomation) -> list[dict[str, str]]:
        links = await browser.execute_js(
            "() => Array.from(document.querySelectorAll('a[href]')).map(a => ({href: a.href, text: a.innerText.trim().slice(0, 200)}))"
        )
        if isinstance(links, list):
            return [l for l in links if l.get("href", "").startswith("http")]
        return []

    def _extract_headings(self, html: str) -> list[dict[str, str]]:
        import re as re_module

        headings = []
        for tag in ["h1", "h2", "h3", "h4"]:
            for m in re_module.finditer(
                rf"<{tag}[^>]*>([^<]+)</{tag}>", html, re_module.IGNORECASE
            ):
                headings.append({"level": tag, "text": m.group(1).strip()})
        return headings

    async def extract_tables(self, browser: BrowserAutomation) -> list[list[list[str]]]:
        tables = await browser.execute_js(
            """() => Array.from(document.querySelectorAll('table')).map(table =>
                Array.from(table.querySelectorAll('tr')).map(row =>
                    Array.from(row.querySelectorAll('th, td')).map(cell => cell.innerText.trim())
                )
            )"""
        )
        if isinstance(tables, list):
            return tables
        return []

    async def extract_articles(self, browser: BrowserAutomation) -> list[dict[str, str]]:
        articles = await browser.execute_js(
            """() => Array.from(document.querySelectorAll('article')).map(article => ({
                title: (article.querySelector('h1, h2, h3')?.innerText || '').trim(),
                content: article.innerText.trim().slice(0, 5000),
                url: location.href
            }))"""
        )
        if isinstance(articles, list):
            return articles
        return []

    def generate_summary(self, analysis: PageAnalysis, max_sentences: int = 5) -> str:
        if analysis.text_content:
            sentences = re.split(r"(?<=[.!?])\s+", analysis.text_content.strip())
            summary_sentences = sentences[:max_sentences]
            return " ".join(summary_sentences)
        return ""

    def extract_key_points(self, analysis: PageAnalysis, max_points: int = 7) -> list[str]:
        points = []
        for h in analysis.headings:
            if h["text"] and len(h["text"]) < 200:
                points.append(h["text"])
        if not points:
            sentences = re.split(r"(?<=[.!?])\s+", analysis.text_content.strip())
            important = [s for s in sentences if len(s) > 30 and len(s) < 300]
            points = important[:max_points]
        return points[:max_points]
