"""Data classification + DLP (§20-21), network policy (§25).

DLP reuses the battle-tested ``aetheros_security.dlp`` scanner where
available and adds flow-level decisions (ALLOW/MASK/REDACT/BLOCK/
REQUIRE_APPROVAL). Secrets are never logged — findings carry types and
spans only. Network policy enforces default-deny with SSRF guards
(private ranges, localhost, cloud metadata 169.254.169.254, redirect
abuse hooks).
"""

from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    from aetheros_security.dlp import DLPManager  # type: ignore
    _HAS_DLP = True
except Exception:
    _HAS_DLP = False


class FlowDecision(str, Enum):
    ALLOW = "ALLOW"
    MASK = "MASK"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "api_key"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"), "aws_key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{8,}"), "github_token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private_key"),
    (re.compile(r"(?i)password\s*[:=]\s*\S{4,}"), "password"),
    (re.compile(r"\b\d{13,19}\b"), "card_candidate"),
]


@dataclass
class DLPFinding:
    kind: str
    span: tuple[int, int]  # offsets only — never the secret itself


@dataclass
class DLPResult:
    decision: FlowDecision
    findings: List[DLPFinding] = field(default_factory=list)
    reason: str = ""


def scan_for_secrets(text: str) -> List[DLPFinding]:
    out: List[DLPFinding] = []
    for rx, kind in _SECRET_PATTERNS:
        for m in rx.finditer(text or ""):
            out.append(DLPFinding(kind, (m.start(), m.end())))
    if _HAS_DLP:
        try:
            mgr = DLPManager()
            res = mgr.scan_text(text or "")
            if getattr(res, "detected", False):
                for f in getattr(res, "findings", []) or []:
                    kind = getattr(f, "type", getattr(f, "kind", "sensitive"))
                    out.append(DLPFinding(str(kind), (0, 0)))
        except Exception:
            pass
    return out


def redact(text: str, findings: List[DLPFinding]) -> str:
    """Replace secret spans with [REDACTED] (operates from the end)."""
    chars = list(text)
    for f in sorted(findings, key=lambda x: x.span[0], reverse=True):
        s, e = f.span
        if 0 <= s < e <= len(chars):
            chars[s:e] = list("[REDACTED]")
    return "".join(chars)


def evaluate_flow(source_class: str, dest: str, text: str = "",
                  dest_trust: str = "T1") -> DLPResult:
    """Flow decision for source-class → destination (§21 examples)."""
    findings = scan_for_secrets(text) if text else []
    src = source_class.lower()
    untrusted = dest_trust in ("T0", "T1")
    if findings and src in ("secret", "restricted") and untrusted:
        return DLPResult(FlowDecision.BLOCK, findings,
                         "secret/restricted → untrusted destination blocked")
    if findings and untrusted:
        return DLPResult(FlowDecision.REQUIRE_APPROVAL, findings,
                         "sensitive content → untrusted destination needs approval")
    if findings:
        return DLPResult(FlowDecision.REDACT, findings,
                         "sensitive content redacted")
    if src in ("secret", "restricted") and untrusted:
        return DLPResult(FlowDecision.REQUIRE_APPROVAL, [],
                         "classified data → untrusted destination needs approval")
    return DLPResult(FlowDecision.ALLOW, [], "flow allowed")


# ---------------------------------------------------------------------------
# Network policy (§25)
# ---------------------------------------------------------------------------

_METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal",
                   "metadata.google", "instance-data"}
_BLOCKED_SUFFIXES = (".internal", ".local", ".corp")


class NetworkPolicy:
    def __init__(self, default_allow: bool = False):
        self.default_allow = default_allow
        self.allow: List[str] = []
        self.deny: List[str] = []

    def check_url(self, url: str) -> tuple[bool, str]:
        """Returns (allowed, reason). SSRF guards enforced first."""
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            return False, "unparseable URL"
        if not host:
            return False, "empty host"
        if host in _METADATA_HOSTS:
            return False, "cloud metadata endpoint blocked"
        if host in ("localhost", "::1") or host.endswith(_BLOCKED_SUFFIXES):
            return False, "localhost/internal host blocked"
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False, "private/loopback/link-local IP blocked"
        except ValueError:
            pass  # hostname, not literal IP
        import fnmatch
        for pat in self.deny:
            if fnmatch.fnmatchcase(host, pat.lower()):
                return False, f"denied by policy: {pat}"
        for pat in self.allow:
            if fnmatch.fnmatchcase(host, pat.lower()):
                return True, f"allowed by policy: {pat}"
        return (True, "default allow") if self.default_allow else (
            False, "default deny")
