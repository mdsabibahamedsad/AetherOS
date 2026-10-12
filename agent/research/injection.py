"""Web-content trust boundary: scan fetched research content for injection.

Web content is UNTRUSTED DATA — it can provide evidence, never authority.
This module composes ``tools.threat_patterns`` with scope "all" (classic
injection + exfiltration patterns, minimal false positives) plus invisible
unicode detection. Findings quarantine the source; they are surfaced as
warnings and never executed or obeyed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from tools import threat_patterns


INJECTION_SCOPE = "all"


@dataclass
class ContentScanResult:
    threats: List[str] = field(default_factory=list)
    quarantined: bool = False

    @property
    def clean(self) -> bool:
        return not self.threats

    def summary(self) -> str:
        if not self.threats:
            return "clean"
        return ",".join(sorted(set(self.threats)))


def scan_content(text: str) -> ContentScanResult:
    """Detect instruction-style payloads in untrusted web/document text."""
    findings = threat_patterns.scan_for_threats(text or "", scope=INJECTION_SCOPE)
    result = ContentScanResult(threats=findings)
    result.quarantined = bool(findings)
    return result


def safe_excerpt(text: str, max_chars: int = 240) -> str:
    """Quote-control excerpt: bounded length, whitespace-normalized.

    Long verbatim quotes are deliberately avoided; evidence stores hashes
    plus short locating excerpts only.
    """
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1].rstrip() + "\u2026"
