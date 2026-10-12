"""Web operations for research fetching: robots.txt, politeness, cache.

Composes stdlib ``urllib.robotparser`` with a per-host politeness delay and
a SQLite page cache with TTLs driven by a freshness policy that varies by
source type. Live-intent queries ("latest", "today", ...) bypass the cache.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from agent.research.models import SourceType


LIVE_INTENT_TERMS = (
    "latest",
    "today",
    "current",
    "now",
    "this week",
    "right now",
    "just released",
    "newest",
    "breaking",
    "as of",
)


def detect_live_intent(query: str) -> bool:
    lowered = (query or "").lower()
    return any(term in lowered for term in LIVE_INTENT_TERMS)


@dataclass
class FreshnessPolicy:
    """Per-source-type TTL seconds; overridable, never universal.

    Breaking-news-ish sources go stale fast, technical docs moderately,
    historical/academic content stays valid far longer.
    """

    ttl_by_type: Dict[str, float] = field(
        default_factory=lambda: {
            SourceType.NEWS.value: 3600.0,
            SourceType.SOCIAL.value: 3600.0,
            SourceType.OFFICIAL.value: 7 * 86400.0,
            SourceType.TECHNICAL.value: 14 * 86400.0,
            SourceType.ACADEMIC.value: 180 * 86400.0,
            SourceType.GOVERNMENT.value: 90 * 86400.0,
        }
    )
    default_ttl: float = 30 * 86400.0

    def ttl_for(self, source_type: SourceType) -> float:
        return self.ttl_by_type.get(source_type.value, self.default_ttl)


class PolitenessLimiter:
    """Per-host minimum delay between fetches."""

    def __init__(self, min_delay_seconds: float = 1.0):
        self.min_delay = max(0.0, min_delay_seconds)
        self._last_access: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> float:
        """Block until the host may be fetched again; returns waited seconds."""
        if not host or self.min_delay <= 0:
            return 0.0
        with self._lock:
            now = time.time()
            last = self._last_access.get(host, 0.0)
            remaining = self.min_delay - (now - last)
            if remaining > 0:
                time.sleep(remaining)
                waited = remaining
            else:
                waited = 0.0
            self._last_access[host] = time.time()
        return waited


class RobotsGate:
    """robots.txt compliance with per-host parser caching, fail-open policy.

    Network failures to obtain robots.txt are treated as allowed (matching
    the repo's existing fail-open posture for policy data), but the fetched
    RULES are cached per host so each host is probed once per process while
    every URL is still evaluated individually against those rules.
    """

    def __init__(self, user_agent: str = "AetherosResearch"):
        self.user_agent = user_agent
        self._parsers: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self._unreachable: set = set()
        self._lock = threading.Lock()

    def allowed(self, url: str, fetcher=None) -> Tuple[bool, str]:
        """Returns (allowed, detail). fetcher(url)->str injectable for tests."""
        parsed = urlparse(url)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        if not host:
            return True, "no-host"
        robots_url = f"{scheme}://{host}/robots.txt"
        with self._lock:
            if robots_url in self._parsers:
                return (
                    self._parsers[robots_url].can_fetch(self.user_agent, url),
                    "cached_rules",
                )
            if robots_url in self._unreachable:
                return True, "cached_fail_open"
        parser = urllib.robotparser.RobotFileParser()
        body = None
        if fetcher is not None:
            try:
                body = fetcher(robots_url)
            except Exception:
                body = None
        if body is None and fetcher is not None:
            with self._lock:
                self._unreachable.add(robots_url)
            return True, "robots_unreachable_fail_open"
        if body is None:
            return True, "no_fetcher_allow"
        parser.parse(body.splitlines())
        allowed = parser.can_fetch(self.user_agent, url)
        with self._lock:
            self._parsers[robots_url] = parser
        return allowed, "robots_evaluated"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS page_cache (
    page_key TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'UNKNOWN'
);
"""


class PageCache:
    """SQLite page cache honoring freshness TTLs by source type."""

    def __init__(self, db_path, policy: Optional[FreshnessPolicy] = None):
        from pathlib import Path

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.policy = policy or FreshnessPolicy()
        self._lock = threading.Lock()

    def get_fresh(
        self,
        page_key: str,
        source_type: SourceType = SourceType.UNKNOWN,
        force_refresh: bool = False,
        now: Optional[float] = None,
    ) -> Optional[Dict]:
        """Return a cached page only when younger than its type's TTL."""
        if force_refresh:
            return None
        now = time.time() if now is None else now
        row = self._conn.execute(
            "SELECT url, title, content, content_hash, fetched_at, source_type"
            " FROM page_cache WHERE page_key=?",
            (page_key,),
        ).fetchone()
        if not row:
            return None
        url, title, content, content_hash, fetched_at, stored_type = row
        effective_type = SourceType(stored_type) if stored_type in {
            t.value for t in SourceType
        } else source_type
        age = now - fetched_at
        if age > self.policy.ttl_for(effective_type):
            return None
        return {
            "url": url,
            "title": title,
            "content": content,
            "content_hash": content_hash,
            "fetched_at": fetched_at,
            "age": age,
        }

    def put(
        self,
        page_key: str,
        url: str,
        title: str,
        content: str,
        content_hash: str,
        source_type: SourceType = SourceType.UNKNOWN,
        fetched_at: Optional[float] = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO page_cache"
                " (page_key, url, title, content, content_hash, fetched_at,"
                "  source_type) VALUES (?,?,?,?,?,?,?)",
                (
                    page_key,
                    url,
                    title,
                    content,
                    content_hash,
                    fetched_at if fetched_at is not None else time.time(),
                    source_type.value,
                ),
            )
            self._conn.commit()

    def purge_older_than(self, cutoff: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM page_cache WHERE fetched_at < ?", (cutoff,)
            )
            self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self._conn.close()


class FetchPipeline:
    """Cache-first fetch orchestration: cache → politeness → provider.

    The caller supplies the actual network callable so this class stays
    fully testable offline.
    """

    def __init__(
        self,
        cache: Optional[PageCache],
        robots: Optional[RobotsGate] = None,
        limiter: Optional[PolitenessLimiter] = None,
    ):
        self.cache = cache
        self.robots = robots
        self.limiter = limiter

    def fetch(
        self,
        url: str,
        page_key: str,
        source_type: SourceType,
        force_refresh: bool = False,
        network_fetch=None,
        robots_fetcher=None,
    ) -> Tuple[Optional[Dict], str]:
        """Returns (page_dict_or_None, provenance_string).

        Provenance is one of: cache_hit, network_fetch, robots_blocked,
        fetch_failed, no_fetcher.
        """
        hit = self.cache.get_fresh(page_key, source_type, force_refresh) if self.cache else None
        if hit is not None:
            return hit, "cache_hit"
        if self.robots is not None:
            allowed, detail = self.robots.allowed(url, fetcher=robots_fetcher)
            if not allowed:
                return None, f"robots_blocked:{detail}"
        if self.limiter is not None:
            from agent.research.urlnorm import normalize_url

            host = urlparse(normalize_url(url)).hostname or ""
            self.limiter.wait(host)
        if network_fetch is None:
            return None, "no_fetcher"
        try:
            title, content = network_fetch(url)
        except Exception:
            return None, "fetch_failed"
        from agent.research.models import compute_content_hash

        page = {
            "url": url,
            "title": title,
            "content": content,
            "content_hash": compute_content_hash(content),
            "fetched_at": time.time(),
        }
        if self.cache is not None:
            self.cache.put(
                page_key, url, title, content, page["content_hash"], source_type
            )
        return page, "network_fetch"
