"""URL canonicalization, domain intelligence, and source deduplication.

Tracking-parameter stripping uses a denylist so meaningful query parameters
are never discarded. Near-duplicate detection is shingle-based and
conservative; provenance of every variant is preserved by the caller.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_name",
        "utm_cid",
        "utm_reader",
        "utm_social",
        "utm_brand",
        "gclid",
        "gbraid",
        "wbraid",
        "dclid",
        "fbclid",
        "msclkid",
        "twclid",
        "ttclid",
        "li_fat_id",
        "mc_cid",
        "mc_eid",
        "igshid",
        "ref",
        "referrer",
        "ref_src",
        "ref_url",
        "cmpid",
        "spm_id_from",
        "vd_source",
        "share_source",
        "share_medium",
        "share_plt",
        "share_sign",
        "share_tag",
        "yclid",
        "_ga",
        "_gl",
        "mkt_tok",
        "everlytic",
        "trk_contact",
        "trk_msg",
        "trk_module",
        "trk_sid",
        "mc_ts",
        "ito",
    }
)

_MULTI_SLASH_RE = re.compile(r"/{2,}")
_DEFAULT_PORTS = {"http": 80, "https": 443}

# Minimal embedded two-level public suffixes; good enough without an
# external publicsuffix dependency. Longest suffix match wins.
_TWO_LEVEL_SUFFIXES = (
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "co.jp",
    "or.jp",
    "ne.jp",
    "com.au",
    "net.au",
    "org.au",
    "gov.au",
    "edu.au",
    "co.nz",
    "co.in",
    "co.za",
    "com.br",
    "com.cn",
    "com.mx",
    "com.tr",
    "com.sg",
    "com.hk",
    "co.kr",
    "com.tw",
    "com.ar",
    "com.co",
)


def normalize_url(url: str) -> str:
    """Canonical form: lower scheme/host, no www., no fragment, no default
    port, tracking params stripped, remaining params sorted, collapse stray
    duplicate slashes in the path."""
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return urlunparse(parsed._replace(fragment="")) if parsed.scheme else url
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    if not host:
        return urlunparse(parsed._replace(fragment=""))
    host = host.lower()
    if host.startswith("www.") and len(host) > 4:
        host = host[4:]
    try:
        port = parsed.port
    except ValueError:
        # Non-HTTP oddities (e.g. file://C:\path on Windows) pass through
        # intact rather than crashing the research pipeline.
        return urlunparse(parsed._replace(fragment=""))
    if port is not None and _DEFAULT_PORTS.get(scheme) != port:
        netloc = f"{host}:{port}"
    else:
        netloc = host
    userinfo = parsed.username or ""
    netloc = f"{userinfo}@{netloc}" if userinfo else netloc
    path = _MULTI_SLASH_RE.sub("/", parsed.path or "")
    if path != "/" and len(path) > 1 and path.endswith("/"):
        kept_params = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        if kept_params or not parsed.query:
            pass
        path = path.rstrip("/") or "/"
    pairs: List[Tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in TRACKING_PARAMS:
            continue
        pairs.append((key, value))
    pairs.sort()
    query = urlencode(pairs)
    return urlunparse((scheme, netloc, path, "", query, ""))


def dedup_key(url: str) -> str:
    """Key for same-page detection: canonical URL minus query entirely.

    Query-only variants of one page (pagination aside) usually mirror the
    same document; callers preserve each original URL as provenance.
    """
    canonical = normalize_url(url)
    parsed = urlparse(canonical)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", "")
    )


def registrable_domain(host_or_url: str) -> str:
    """Registrable domain (eTLD+1) using a minimal two-level suffix table."""
    host = host_or_url.strip().lower()
    if "://" in host:
        host = urlparse(host).hostname or ""
    host = host.removeprefix("www.")
    if not host:
        return ""
    for suffix in _TWO_LEVEL_SUFFIXES:
        if host.endswith("." + suffix):
            prefix = host[: -(len(suffix) + 1)]
            last = prefix.rsplit(".", 1)[-1]
            return f"{last}.{suffix}"
    parts = host.rsplit(".", 2)
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    return host


def is_subdomain_of(host: str, parent_domain: str) -> bool:
    host = (host or "").lower().removeprefix("www.")
    parent = (parent_domain or "").lower().removeprefix("www.")
    return host == parent or host.endswith("." + parent)


class SourceDeduplicator:
    """Tracks seen sources for one research task across search calls."""

    def __init__(self) -> None:
        self._by_dedup_key: Dict[str, str] = {}
        self._by_content_hash: Dict[str, List[str]] = {}

    def seen_url(self, url: str) -> Optional[str]:
        """Return the first-seen original URL if this page was already seen."""
        return self._by_dedup_key.get(dedup_key(url))

    def register_url(self, url: str) -> bool:
        """True if newly seen; False if a duplicate of a registered page."""
        key = dedup_key(url)
        if key in self._by_dedup_key:
            return False
        self._by_dedup_key[key] = url
        return True

    def register_content(self, content_hash: str, url: str) -> Tuple[bool, int]:
        """Register fetched-content hash; returns (is_new, copies_seen).

        Multiple distinct URLs with identical content are mirrors or
        syndicated copies — they must not count as independent corroboration.
        """
        seen = self._by_content_hash.setdefault(content_hash, [])
        seen.append(url)
        return len(seen) == 1, len(seen)

    def mirrors_of(self, content_hash: str) -> List[str]:
        return list(self._by_content_hash.get(content_hash, []))

    @property
    def unique_pages(self) -> int:
        return len(self._by_dedup_key)

    def independent_domains(self, domains: Iterable[str]) -> int:
        return len({registrable_domain(d) for d in domains if d})


def shingles(text: str, width: int = 5) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < width:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + width]) for i in range(len(words) - width + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union


def near_duplicate(text_a: str, text_b: str, threshold: float = 0.6) -> bool:
    """Near-duplicate check via shingle Jaccard similarity.

    Calibrated so a single-word edit in a ~30-word passage still matches
    while topically different texts stay well below the bar.
    """
    sa, sb = shingles(text_a), shingles(text_b)
    return jaccard(sa, sb) >= threshold
