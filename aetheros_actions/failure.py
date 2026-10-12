"""Failure classification for action execution (Step 82).

Maps an error/result to a :class:`~aetheros_actions.model.FailureKind` using
deterministic heuristics on the error text and the action context. Pure — no
I/O. Used by receipts and audit to distinguish retryable (TRANSIENT) from
deterministic (PERMANENT / VALIDATION / PERMISSION / UNAVAILABLE) failures.
"""

from __future__ import annotations

import re
from typing import Optional

from aetheros_actions.model import Action, FailureKind

# Substrings that mark a transient / retryable failure.
_TRANSIENT_MARKERS = (
    "timeout", "timed out", "timed-out", "retry", "retrying", "temporarily",
    "transient", "throttl", "rate limit", "rate-limit", "429", "503",
    "connection reset", "connection refused", "network", "resource busy",
    "resource contention", "another process", "lock",
)

# Substrings that mark a missing-prerequisite failure.
_UNAVAILABLE_MARKERS = (
    "not installed", "not found", "not available", "unavailable",
    "no element", "no window", "no matching", "requires", "needed",
    "backend unavailable", "no active window", "not supported",
)

# Substrings that mark an input/validation failure.
_VALIDATION_MARKERS = (
    "invalid", "malformed", "requires `", "requires x, y", "unknown action",
    "could not parse", "bad mode", "missing",
)

# Substrings that mark a permission/policy failure.
_PERMISSION_MARKERS = (
    "denied", "deny", "requires permission", "permission", "requires screen_read",
    "not granted", "authorization", "not authorized", "blocked", "refused",
    "untrusted", "quarantined",
)


def classify_failure(
    error: str = "",
    *,
    action: Optional[Action] = None,
) -> FailureKind:
    """Classify a failure from ``error`` (and optional ``action`` context)."""
    text = (error or "").lower()
    if action is not None and action.dry_run:
        return FailureKind.VALIDATION
    if not text:
        # No error message: we cannot tell — treat as UNKNOWN rather than guess.
        return FailureKind.UNKNOWN
    if any(marker in text for marker in _PERMISSION_MARKERS):
        return FailureKind.PERMISSION
    if any(marker in text for marker in _VALIDATION_MARKERS):
        return FailureKind.VALIDATION
    if any(marker in text for marker in _UNAVAILABLE_MARKERS):
        return FailureKind.UNAVAILABLE
    if any(marker in text for marker in _TRANSIENT_MARKERS):
        return FailureKind.TRANSIENT
    return FailureKind.UNKNOWN


def is_retryable(error: str = "") -> bool:
    """True when the failure looks transient and worth one bounded retry."""
    return classify_failure(error) is FailureKind.TRANSIENT