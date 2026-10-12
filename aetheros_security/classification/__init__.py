"""
Data Classification and Flow Control for AetherOS
=================================================

Assign every piece of data a deterministic classification and gate its
movement across agent/tool/provider/memory/file/network/UI boundaries.

Classifications (master security spec step 31)::

    PUBLIC            Safe for anyone
    INTERNAL          Safe within the org/workspace
    PRIVATE           Personal data, limited audience
    SENSITIVE         Protected data, needs access control
    HIGHLY_SENSITIVE  Protected data, strict handling rules
    SECRET            Credentials / keys / tokens

Flow control (steps 32-33)::

    from aetheros_security.classification import (
        DataClassification, classify_text, DataFlowGuard,
    )

    guard = DataFlowGuard()
    decision = guard.check_flow(
        classification=DataClassification.SENSITIVE,
        destination="web:send",
        source="memory",
        principal="research-agent",
    )

Flow decisions are deterministic. Sensitive/secret classifications never
leave through unapproved external destinations unless an explicit policy
permits the exact source -> destination path.

Usage::

    from aetheros_security.classification import (
        DataClassification, classify_content, get_data_flow_guard,
    )

    level = classify_content(text)          # heuristic keyword/pattern classifier
    decision = get_data_flow_guard().check_flow(...)
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataClassification(Enum):
    """Data classification levels (step 31)."""
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    HIGHLY_SENSITIVE = "highly_sensitive"
    SECRET = "secret"


_CLASS_ORDER = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.PRIVATE: 2,
    DataClassification.SENSITIVE: 3,
    DataClassification.HIGHLY_SENSITIVE: 4,
    DataClassification.SECRET: 5,
}


def classification_ge(left: DataClassification, right: DataClassification) -> bool:
    """Whether ``left`` is at least as sensitive as ``right``."""
    return _CLASS_ORDER.get(left, 0) >= _CLASS_ORDER.get(right, 0)


# ---------------------------------------------------------------------------
# Heuristic content classifier
# ---------------------------------------------------------------------------

#: Patterns that strongly indicate SECRET / HIGHLY_SENSITIVE material.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),            # OpenAI-style key
    re.compile(r"ghp_[A-Za-z0-9]{20,}", re.IGNORECASE),           # GitHub PAT
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),               # AWS access key id
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"Bearer [A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),   # bearer token
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.IGNORECASE),   # Slack token
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),     # JWT
]

_HIGHLY_SENSITIVE_PATTERNS = [
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\bpasswd\b", re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\b", re.IGNORECASE),
    re.compile(r"\bclient[_-]?secret\b", re.IGNORECASE),
    re.compile(r"\bprivate[_-]?key\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"\bcredential\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
]

_SENSITIVE_PATTERNS = [
    re.compile(r"\bssn\b", re.IGNORECASE),
    re.compile(r"\bsocial[ -]?security\b", re.IGNORECASE),
    re.compile(r"\bcredit[ -]?card\b", re.IGNORECASE),
    re.compile(r"\bcvv\b", re.IGNORECASE),
    re.compile(r"\bpan\b", re.IGNORECASE),
    re.compile(r"\bdate[ -]?of[ -]?birth\b", re.IGNORECASE),
    re.compile(r"\bmedical record\b", re.IGNORECASE),
    re.compile(r"\bhealth record\b", re.IGNORECASE),
    re.compile(r"\bpassport\b", re.IGNORECASE),
    re.compile(r"\bdrivers? license\b", re.IGNORECASE),
]

_PRIVATE_PATTERNS = [
    re.compile(r"\bemail\b", re.IGNORECASE),
    re.compile(r"\bphone\b", re.IGNORECASE),
    re.compile(r"\baddress\b", re.IGNORECASE),
    re.compile(r"\bbirthday\b", re.IGNORECASE),
    re.compile(r"\baddress\b", re.IGNORECASE),
    re.compile(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b"),                  # email address
]


class ClassificationError(Exception):
    """Raised for invalid classification operations."""


def classify_content(text: str,
                     classification: Optional[DataClassification] = None) -> DataClassification:
    """Classify text content using deterministic heuristics.

    Args:
        text: Content to classify.
        classification: Explicit override (skips heuristics).

    Returns:
        A :class:`DataClassification`.
    """
    if classification is not None:
        return classification
    if not text:
        return DataClassification.PUBLIC

    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return DataClassification.SECRET
    for pattern in _HIGHLY_SENSITIVE_PATTERNS:
        if pattern.search(text):
            return DataClassification.HIGHLY_SENSITIVE
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            return DataClassification.SENSITIVE
    for pattern in _PRIVATE_PATTERNS:
        if pattern.search(text):
            return DataClassification.PRIVATE
    return DataClassification.INTERNAL


def classify_value(value: Any, explicit: Optional[DataClassification] = None) -> DataClassification:
    """Classify an arbitrary value (string/dict/list/number)."""
    if explicit is not None:
        return explicit
    if isinstance(value, str):
        return classify_content(value)
    if isinstance(value, dict):
        return classify_content("\n".join(str(k) for k in value.keys()))
    if isinstance(value, (list, tuple, set)):
        return classify_content("\n".join(str(v) for v in value))
    return DataClassification.INTERNAL


# ---------------------------------------------------------------------------
# Flow control
# ---------------------------------------------------------------------------

#: Destinations that may carry SECRET/HIGHLY_SENSITIVE data only with policy.
_EXTERNAL_DESTINATIONS = {
    "web:send", "email:send", "message:send", "cloud:upload", "network:connect",
    "git:push", "webhook:send", "api:send", "publish", "deploy",
}

#: Internal destinations that never leave the trusted boundary.
_INTERNAL_DESTINATIONS = {
    "memory:write", "knowledge:write", "filesystem:write", "log",
    "ui:display", "tool:internal", "diagnostics",
}

#: Sources we never send sensitive data out of without policy.
_UNTRUSTED_SOURCES = {"memory", "knowledge", "tool:result", "web", "document"}


@dataclass
class FlowDecision:
    """Result of a data-flow check."""
    allowed: bool
    classification: DataClassification
    source: str
    destination: str
    principal: str = ""
    reason: str = ""
    checked_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "classification": self.classification.value,
            "source": self.source,
            "destination": self.destination,
            "principal": self.principal,
            "reason": self.reason,
            "checked_at": self.checked_at,
        }


class DataFlowGuard:
    """Deterministic data-exfiltration gate (steps 32-33).

    Rules:
        - PUBLIC / INTERNAL always flow.
        - PRIVATE flows within the system; external requires approval.
        - SENSITIVE / HIGHLY_SENSITIVE / SECRET to an external destination
          requires an explicit allow policy for the exact source->dest pair.
        - SECRET never flows to an untrusted external destination.
    """

    def __init__(self) -> None:
        self._allow_pairs: set = set()          # (source, destination) policy grants
        self._deny_pairs: set = set()
        self._allow_external_sensitive = False  # global switch; default off

    def allow_flow(self, source: str, destination: str) -> None:
        """Explicitly allow data of any classification on source->destination."""
        self._allow_pairs.add((source, destination))

    def deny_flow(self, source: str, destination: str) -> None:
        """Explicitly deny a source->destination path (wins over allow)."""
        self._deny_pairs.add((source, destination))

    def set_allow_external_sensitive(self, enabled: bool) -> None:
        self._allow_external_sensitive = bool(enabled)

    def check_flow(
        self,
        *,
        classification: DataClassification,
        source: str,
        destination: str,
        principal: str = "",
    ) -> FlowDecision:
        now = time.time()
        source = (source or "").lower()
        destination = (destination or "").lower()

        # Explicit deny always wins.
        if (source, destination) in self._deny_pairs:
            return FlowDecision(False, classification, source, destination,
                                principal, "denied by flow policy", now)

        external = destination in _EXTERNAL_DESTINATIONS or \
            (destination not in _INTERNAL_DESTINATIONS and "." in destination)

        # PUBLIC / INTERNAL always flow.
        if classification in (DataClassification.PUBLIC, DataClassification.INTERNAL):
            return FlowDecision(True, classification, source, destination,
                                principal, "low classification", now)

        # PRIVATE is fine internally, requires policy externally.
        if classification == DataClassification.PRIVATE:
            if not external:
                return FlowDecision(True, classification, source, destination,
                                    principal, "internal flow", now)
            if (source, destination) in self._allow_pairs:
                return FlowDecision(True, classification, source, destination,
                                    principal, "allowed by flow policy", now)
            return FlowDecision(False, classification, source, destination,
                                principal, "private data to external destination", now)

        # SENSITIVE+ external: explicit policy or global switch.
        if external:
            if classification == DataClassification.SECRET:
                return FlowDecision(False, classification, source, destination,
                                    principal, "secret data cannot leave", now)
            if (source, destination) in self._allow_pairs or self._allow_external_sensitive:
                return FlowDecision(True, classification, source, destination,
                                    principal, "allowed by flow policy", now)
            return FlowDecision(False, classification, source, destination,
                                principal, "sensitive data to external destination", now)

        # SENSITIVE+ internal is permitted (still audited by caller).
        return FlowDecision(True, classification, source, destination,
                            principal, "internal flow", now)

    def get_stats(self) -> Dict[str, int]:
        return {
            "allow_pairs": len(self._allow_pairs),
            "deny_pairs": len(self._deny_pairs),
        }


# Global data flow guard
_data_flow_guard: DataFlowGuard | None = None


def get_data_flow_guard() -> DataFlowGuard:
    """Return the global DataFlowGuard singleton."""
    global _data_flow_guard
    if _data_flow_guard is None:
        _data_flow_guard = DataFlowGuard()
    return _data_flow_guard