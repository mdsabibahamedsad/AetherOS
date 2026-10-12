"""Poisoning & prompt-injection defense for the write path.

External content (web, email, files) must never be treated as instructions.
This module detects suspicious content before it becomes memory, strips
common injection framing, and returns a verdict the write pipeline acts on.

Detection signals (defense-in-depth, not a single magic check):

* classic injection phrasings ("ignore previous instructions", "you are now",
  "disregard all prior", "system prompt", "from now on you must")
* embedded instruction blocks inside fetched content
* encoding tricks (base64 blobs, heavy unicode obfuscation)
* secret-shaped tokens (the entry would store credentials)
"""

from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DefenseVerdict(str, Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class DefenseResult:
    verdict: DefenseVerdict = DefenseVerdict.SAFE
    reasons: List[str] = field(default_factory=list)
    sanitized_content: str = ""
    triggered_rules: List[str] = field(default_factory=list)


_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts?|commands|messages|context)\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?|messages)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\bfrom\s+now\s+on\s+you\s+(must|will|should)\b", re.IGNORECASE),
    re.compile(r"\brewrite\s+(your|the)\s+(system|initial)\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+prompt\s*[:=]", re.IGNORECASE),
    re.compile(r"\b<\|?system\|?>\b", re.IGNORECASE),
    re.compile(r"\bforget\s+(everything|all)\s+(above|before)\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+tell\s+(the\s+)?user\b", re.IGNORECASE),
    re.compile(r"\bsimulate\s+(an?\s+)?(admin|root|sudo|bypass|jailbreak)\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\b(ignore|disregard)\s+(this|the|all)\s+(message|text|block|section|command)\b", re.IGNORECASE),
]

_SECRET_PATTERNS = [
    re.compile(r"sk-\w{20,}", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+={0,2}", re.IGNORECASE),
    re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"),
    re.compile(r"(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+", re.IGNORECASE),
]

_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

_MAX_OBFUSCATION_RATIO = 0.4  # if >40% of chars are non-ASCII, flag it


class InjectionDefense:
    """Inspect inbound content before it enters memory."""

    def __init__(self, *, scan_secrets: bool = True) -> None:
        self.scan_secrets = scan_secrets

    def inspect(self, content: str, *, origin: str = "") -> DefenseResult:
        """Return a verdict for ``content`` with reasons + sanitized copy."""
        result = DefenseResult(verdict=DefenseVerdict.SAFE, sanitized_content=content)
        if not content or not content.strip():
            result.verdict = DefenseVerdict.BLOCKED
            result.reasons.append("empty content")
            return result

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                result.triggered_rules.append(pattern.pattern[:40])
                result.reasons.append("injection framing detected")

        # Encoding/obfuscation heuristics.
        if _BASE64_RE.search(content):
            result.triggered_rules.append("base64-blob")
            result.reasons.append("large base64 blob present")
        if self._obfuscation_ratio(content) > _MAX_OBFUSCATION_RATIO:
            result.triggered_rules.append("unicode-obfuscation")
            result.reasons.append("heavy non-ASCII obfuscation")

        if self.scan_secrets:
            for pattern in _SECRET_PATTERNS:
                if pattern.search(content):
                    result.triggered_rules.append("secret-shaped-token")
                    result.reasons.append("secret-shaped token present")
                    result.sanitized_content = pattern.sub("[REDACTED]", result.sanitized_content)

        # Sanitize: strip classic injection framing lines entirely.
        sanitized = result.sanitized_content
        for pattern in _INJECTION_PATTERNS:
            sanitized = pattern.sub("[filtered]", sanitized)
        result.sanitized_content = sanitized

        if result.triggered_rules:
            result.verdict = DefenseVerdict.SUSPICIOUS
        return result

    @staticmethod
    def _obfuscation_ratio(content: str) -> float:
        if not content:
            return 0.0
        non_ascii = 0
        for ch in content:
            if unicodedata.category(ch) not in ("Ll", "Lu", "Nd", "Po", "Zs", "Pd", "Pi", "Pf", "Ps", "Pe"):
                non_ascii += 1
        return non_ascii / len(content)


def classify_content_type(content: str) -> str:
    """Coarse content classification: fact / opinion / instruction / unknown.

    Used by the write pipeline to pick a memory type when the caller did not
    provide one and to down-weight opinion content.
    """
    text = content.strip()
    if not text:
        return "unknown"
    first = text[0]
    if any(first == c for c in ("#", "-", "*", "1.", "2.")):
        return "unknown"
    # Imperative sentence start -> looks instructional.
    if re.match(r"^(always|never|must|should|please|remember|note|do|don't)\b", text, re.IGNORECASE):
        return "instruction"
    # Hedge words -> opinion.
    if re.search(r"\b(i think|probably|maybe|perhaps|in my opinion|seems like|i prefer)\b", text, re.IGNORECASE):
        return "opinion"
    return "fact"