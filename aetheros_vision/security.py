"""AetherOS Vision — security.

Local-first processing guarantees, secret masking before any upstream
processing, and upload consent enforcement. Nothing in this package uploads
media without explicit configuration permitting it.
"""

from __future__ import annotations

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Patterns used to mask common secrets before text leaves the machine.
_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|\bpw)\s*[=:]\s*\S+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),          # US SSN
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),        # card-like digit runs
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email addresses
]


def redact_sensitive_text(text: str) -> str:
    """Replace secret-like fragments in ``text`` with a placeholder."""
    if not text:
        return text
    masked = text
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(_mask_replace, masked)
    return masked


def _mask_replace(match: re.Match) -> str:
    return f"[REDACTED:{len(match.group(0))}]"


def requires_upload_consent(local_only: bool, processing: str = "cloud") -> bool:
    """Whether a given processing mode needs explicit consent to upload media.

    ``local_only=True`` forces every pipeline local. Otherwise only cloud
    processing (VLM description of a non-redacted image) is treated as an
    upload and requires consent.
    """
    if local_only:
        return False
    return processing != "local"


def assert_upload_allowed(local_only: bool, processing: str = "cloud") -> None:
    """Raise when an upload would violate the local-first policy."""
    if requires_upload_consent(local_only, processing):
        raise PermissionError(
            "This operation would upload image content. Set vision.local_only: true "
            "in config.yaml or grant explicit upload consent to proceed."
        )
