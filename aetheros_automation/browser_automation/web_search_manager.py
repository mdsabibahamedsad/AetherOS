from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SearchProvider:
    name: str
    url: str
    search_url: str
    suggestions_url: str = ""
    icon: str = "search"


DEFAULT_PROVIDERS = [
    SearchProvider("Google", "https://www.google.com", "https://www.google.com/search?q={query}", icon="google"),
    SearchProvider("Bing", "https://www.bing.com", "https://www.bing.com/search?q={query}", icon="bing"),
    SearchProvider("DuckDuckGo", "https://duckduckgo.com", "https://duckduckgo.com/?q={query}", icon="duckduckgo"),
    SearchProvider("Brave", "https://search.brave.com", "https://search.brave.com/search?q={query}", icon="brave"),
    SearchProvider("SearXNG", "", "https://searx.be/search?q={query}", icon="search"),
]


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class WebSearchManager:
    def __init__(self):
        self._providers: dict[str, SearchProvider] = {}
        self._active_provider: str = "Google"
        self._search_history: list[dict] = []
        self._init_providers()

    def _init_providers(self):
        for p in DEFAULT_PROVIDERS:
            self._providers[p.name.lower()] = p

    def get_providers(self) -> list[SearchProvider]:
        return list(self._providers.values())

    def get_active_provider(self) -> SearchProvider | None:
        return self._providers.get(self._active_provider.lower())

    def set_active_provider(self, name: str) -> bool:
        key = name.lower()
        if key in self._providers:
            self._active_provider = name
            return True
        for p in self._providers.values():
            if p.name.lower() == key:
                self._active_provider = p.name
                return True
        return False

    def add_provider(self, name: str, url: str, search_url: str, suggestions_url: str = ""):
        self._providers[name.lower()] = SearchProvider(name, url, search_url, suggestions_url)

    def remove_provider(self, name: str) -> bool:
        key = name.lower()
        if key in self._providers and key not in [p.name.lower() for p in DEFAULT_PROVIDERS]:
            del self._providers[key]
            if self._active_provider.lower() == key and self._providers:
                self._active_provider = next(iter(self._providers.values())).name
            return True
        return False

    def get_search_url(self, query: str) -> str:
        provider = self.get_active_provider()
        if provider is None:
            return f"https://www.google.com/search?q={query}"
        return provider.search_url.replace("{query}", query.replace(" ", "+"))

    def record_search(self, query: str, results_count: int = 0):
        self._search_history.append({
            "query": query,
            "provider": self._active_provider,
            "results_count": results_count,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self._search_history) > 500:
            self._search_history = self._search_history[-500:]

    def get_search_history(self, limit: int = 50) -> list[dict]:
        return self._search_history[-limit:]

    def clear_search_history(self):
        self._search_history.clear()

    def get_suggestions(self, partial: str) -> list[str]:
        from urllib.parse import quote

        provider = self.get_active_provider()
        if provider and provider.suggestions_url:
            try:
                import urllib.request

                url = provider.suggestions_url.replace("{query}", quote(partial))
                resp = urllib.request.urlopen(url, timeout=3)
                data = json.loads(resp.read().decode())
                if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                    return data[1]
            except Exception:
                pass
        return []

    def extract_search_results_from_html(self, html: str) -> list[SearchResult]:
        results = []
        try:
            from html.parser import HTMLParser

            class SearchParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._results = []
                    self._in_link = False
                    self._current_title = ""
                    self._current_url = ""

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "a" and "href" in attrs_dict:
                        href = attrs_dict["href"]
                        if href.startswith("http") and "google" not in href:
                            self._in_link = True
                            self._current_url = href

                def handle_data(self, data):
                    if self._in_link:
                        self._current_title += data

                def handle_endtag(self, tag):
                    if tag == "a" and self._in_link:
                        self._results.append(
                            SearchResult(title=self._current_title.strip(), url=self._current_url)
                        )
                        self._in_link = False
                        self._current_title = ""

            parser = SearchParser()
            parser.feed(html)
            results = parser._results[:20]
        except Exception:
            pass
        return results
