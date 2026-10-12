"""Private/public boundary and data-exfiltration defense (P16, P65-68).

Rules enforced here:
- Private/user-provided content NEVER flows into public web queries.
- Outbound queries/URLs are scanned for credential-shaped strings before
  any network use (defense against echoing secrets into search engines).
- Every source carries explicit visibility; reports must label it.

This module is pure/deterministic so the boundary is testable offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from agent.research.models import SourceVisibility

# Credential-shaped patterns (prefix-based, aligned with repo redaction).
_SECRET_PREFIXES = (
    "sk-ant",
    "sk-proj",
    "sk-or",
    "sk-",
    "xoxb-",
    "xoxp-",
    "ghp_",
    "gho_",
    "github_pat_",
    "glpat-",
    "AKIA",
    "AIza",
    "ya29.",
    "hf_",
    "r8_",
    "dop_v1",
    "shpat_",
)
_BEARER_RE = re.compile(
    r"(?i)\b(bearer|authorization|api[_-]?key|token|password|passwd|secret)"
    r"\s*[:=]\s*\S+"
)
_BEARER_SPACED_RE = re.compile(
    r"(?i)\b(bearer|api[_-]?key|access[_-]?token|password|secret)\s+[A-Za-z0-9_\-\.]{8,}"
)
_AWS_ACCESS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")
_LONG_HEX_RE = re.compile(r"\b[a-f0-9]{40,}\b", re.IGNORECASE)


class ExfilBlocked(Exception):
    """Raised when an outbound string carries credential-shaped content."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"outbound blocked: {reason}")


def scan_outbound(text: str) -> List[str]:
    """Return reasons an outbound query/URL is unsafe to send. Empty = safe."""
    reasons: List[str] = []
    if not text:
        return reasons
    for prefix in _SECRET_PREFIXES:
        idx = text.find(prefix)
        while idx != -1:
            candidate = text[idx : idx + len(prefix) + 12]
            tail = candidate[len(prefix) :]
            if re.match(r"^[A-Za-z0-9_\-\.]{6,}", tail):
                reasons.append(f"secret_prefix:{prefix}")
                break
            idx = text.find(prefix, idx + 1)
    if _BEARER_RE.search(text) or _BEARER_SPACED_RE.search(text):
        reasons.append("credential_assignment")
    if _AWS_ACCESS_KEY_RE.search(text):
        reasons.append("aws_access_key")
    if _LONG_HEX_RE.search(text):
        reasons.append("high_entropy_hex")
    return reasons


def guard_outbound_query(query: str) -> str:
    """Raise ExfilBlocked if unsafe; return the query unchanged otherwise."""
    reasons = scan_outbound(query)
    if reasons:
        raise ExfilBlocked(reasons[0])
    return query


PRIVATE_VISIBILITIES = frozenset(
    {SourceVisibility.PRIVATE, SourceVisibility.USER_PROVIDED}
)


class PrivateBoundary:
    """Ensures private-source content never reaches public providers."""

    def __init__(self):
        self._private_terms: List[str] = []

    def register_private_text(self, text: str) -> None:
        """Record distinctive terms from private documents for leak checks."""
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-\.]{5,}", text or ""):
            lowered = token.lower()
            if lowered not in self._private_terms:
                self._private_terms.append(lowered)

    def check_query(self, query: str) -> Tuple[bool, str]:
        """Block queries that quote distinctive private-document terms."""
        for term in self._private_terms:
            if term in (query or "").lower():
                return False, f"private_term:{term[:24]}"
        return True, ""

    @staticmethod
    def assert_public_only(queries: Iterable[str], visibility: SourceVisibility) -> None:
        if visibility in PRIVATE_VISIBILITIES:
            raise ValueError(
                "refusing to derive public web queries from private sources"
            )


def cross_source_permitted(source_kinds: Iterable[str]) -> bool:
    """P67: web+local+repo combinations are allowed by default in a single
    task because each evidence item keeps its own visibility label; callers
    must still pass user authorization via sources_allowed/scope."""
    return True


@dataclass
class BoundaryVerdict:
    outbound_ok: bool
    reason: str = ""
    visibility_split: str = ""


def evaluate_outbound(query: str, boundary: PrivateBoundary) -> BoundaryVerdict:
    try:
        guard_outbound_query(query)
    except ExfilBlocked as exc:
        return BoundaryVerdict(False, exc.reason)
    ok, reason = boundary.check_query(query)
    if not ok:
        return BoundaryVerdict(False, reason)
    return BoundaryVerdict(True)
