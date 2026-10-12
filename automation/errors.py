"""
Error classification for automations (Master 13 Phases 26-29).

Classifies failure text into a fixed category set so retry/failure policies
can be policy-driven instead of string-matching all over the codebase:

    transient | auth | permission | network | tool | model | resource |
    configuration | logic | user | security | unknown

Default retryable set: {transient, network, resource}. Auth/permission/
security failures are NEVER retried automatically (Phase 93: do not hammer
dead credentials).
"""

from __future__ import annotations

import re
from typing import List

CATEGORIES = (
    "transient",
    "auth",
    "permission",
    "network",
    "tool",
    "model",
    "resource",
    "configuration",
    "logic",
    "user",
    "security",
    "unknown",
)

RETRYABLE = frozenset({"transient", "network", "resource"})

# Ordered most-specific first; first hit wins.
_PATTERNS: List[tuple] = [
    ("security", r"injection|blocked by (policy|security)|policy violation"),
    ("auth", r"401|invalid[_ ]api[_ ]key|unauthorized|authentication|expired token"),
    ("permission", r"403|forbidden|permission denied|access denied|eacces"),
    ("user", r"cancell|interrupt(ed)? by user|aborted by user"),
    ("configuration", r"config(uration)? |yaml|missing required|not configured|invalid value|no module named"),
    ("resource", r"no space left|out of memory|emfile|too many open files|disk quota|memoryerror"),
    ("model", r"context length|context window|model overloaded|unsupported (model|parameter)"),
    ("tool", r"tool call failed|schema validation|invalid (parameters|arguments)|unknown tool"),
    ("network", r"timed? ?out|connection (refused|reset|error)|getaddrinfo|name resolution|unreachable|ssl|eof occurred"),
    ("transient", r"429|rate limit|temporar|try again|overloaded|502|503|504"),
]

_COMPILED = [(cat, re.compile(pattern, re.IGNORECASE)) for cat, pattern in _PATTERNS]


def classify(error_text: str) -> str:
    """Classify one error message into exactly one category."""
    text = str(error_text or "")
    for category, pattern in _COMPILED:
        if pattern.search(text):
            return category
    return "unknown"


def is_retryable(error_text: str, extra_retryable: tuple = ()) -> bool:
    category = classify(error_text)
    if category in RETRYABLE:
        return True
    return category in set(extra_retryable)
