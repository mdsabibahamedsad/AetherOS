"""Authorization, data classification, DLP, and SSRF defense (Master 46
sections 17-22, 78-87, 106-107).

Authentication != authorization. Every delegation evaluates identity,
trust, capability, data scope, risk, and policy — enforced below the UI,
never by prompt or display.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .trust import trust_rank

DATA_CLASSES = ("public", "internal", "private", "sensitive", "highly_sensitive")

# Capability -> {risk, default_approval, max_trust_needed}
PERMISSION_CATALOG: Dict[str, Dict[str, Any]] = {
    "agent.task.submit": {"risk": "medium", "approval": "auto_if_trusted", "min_rank": 3},
    "agent.task.read": {"risk": "low", "approval": "auto", "min_rank": 2},
    "agent.task.cancel": {"risk": "low", "approval": "auto", "min_rank": 2},
    "agent.task.stream": {"risk": "low", "approval": "auto", "min_rank": 2},
    "agent.artifact.read": {"risk": "medium", "approval": "auto_if_trusted", "min_rank": 3},
    "agent.artifact.write": {"risk": "high", "approval": "always", "min_rank": 4},
    "research.search": {"risk": "low", "approval": "auto", "min_rank": 2},
    "research.fetch": {"risk": "medium", "approval": "auto_if_trusted", "min_rank": 3},
    "memory.read.scoped": {"risk": "high", "approval": "always", "min_rank": 4},
    "memory.write.scoped": {"risk": "high", "approval": "always", "min_rank": 5},
    "browser.request": {"risk": "high", "approval": "always", "min_rank": 5},
    "computer.request": {"risk": "critical", "approval": "always", "min_rank": 6},
    "mcp.request": {"risk": "high", "approval": "always", "min_rank": 4},
    "automation.request": {"risk": "high", "approval": "always", "min_rank": 5},
}

# Remote agents get capabilities, never broad local powers (section 18).
REMOTE_GRANTABLE = {
    "agent.task.submit", "agent.task.read", "agent.task.cancel",
    "agent.task.stream", "agent.artifact.read", "agent.artifact.write",
    "research.search", "research.fetch",
    "memory.read.scoped", "memory.write.scoped",
    "browser.request", "computer.request", "mcp.request", "automation.request",
}
# Never grantable to a remote principal without fully_trusted + approval.
REMOTE_DENY_BY_DEFAULT = {
    "filesystem.read", "filesystem.write", "shell.execute", "secrets.read",
    "browser.control", "computer.control",
}

_SECRET_PATTERNS = [
    ("api_key", re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.~+/=]{16,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("password_field", re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?\S{4,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
]

_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions"),
    re.compile(r"(?i)disregard\s+(your\s+)?(system|security|privacy|approval)\s+(policy|prompt)"),
    re.compile(r"(?i)(reveal|exfiltrate|send|give me).{0,40}(secret|credential|api[_-]?key|password|private[_-]?key|token)"),
    re.compile(r"(?i)you are now\s+(a|an|in)\s+"),
    re.compile(r"(?i)\[system\].{0,20}(override|instruction)"),
]


def classify_data(text: str) -> str:
    """Classify outbound text. Returns the highest class detected."""
    for name, rx in _SECRET_PATTERNS:
        if rx.search(text):
            return "highly_sensitive"
    if re.search(r"(?i)(internal|confidential|private|ssn|dob|salary)", text):
        return "sensitive"
    return "internal"


def dlp_scan(text: str) -> List[Dict[str, str]]:
    """Return findings [{type, redacted_sample}]. Never returns raw secrets."""
    findings = []
    for name, rx in _SECRET_PATTERNS:
        m = rx.search(text)
        if m:
            findings.append({"type": name, "hint": f"match len={len(m.group(0))}"})
    return findings


def redact_secrets(text: str) -> str:
    redacted = text
    for _name, rx in _SECRET_PATTERNS:
        redacted = rx.sub("[REDACTED]", redacted)
    return redacted


def detect_prompt_injection(text: str) -> List[str]:
    hits = []
    for rx in _INJECTION_PATTERNS:
        m = rx.search(text)
        if m:
            hits.append(m.group(0)[:120])
    return hits


def check_url_allowed(url: str, allow_private: bool = False,
                      allowed_hosts: Optional[List[str]] = None) -> Tuple[bool, str]:
    """SSRF/DNS-rebinding guard (sections 82-83). Resolves the host and
    rejects private/loopback/link-local/metadata targets unless the
    deployment explicitly allows private targets (LAN pairing mode)."""
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"unparseable url: {e}"
    if parsed.scheme not in ("https", "http"):
        return False, f"blocked scheme: {parsed.scheme!r}"
    host = parsed.hostname or ""
    if not host:
        return False, "url has no hostname"
    if allowed_hosts and host not in allowed_hosts:
        return False, f"host {host!r} not on allowlist"
    # Never allow credentials in URL, file/javascript/data schemes already rejected.
    if parsed.username or parsed.password:
        return False, "userinfo in url is blocked"
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        return False, f"dns resolution failed: {e}"
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"bad resolved address: {ip_str!r}"
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False, f"resolved to restricted address {ip_str}"
        # Cloud metadata endpoints.
        if str(ip) == "169.254.169.254":
            return False, "cloud metadata endpoint blocked"
        if (ip.is_private and not allow_private) or (getattr(ip, "is_global", False) is False and not allow_private and not ip.is_loopback):
            # ip.is_private covers RFC1918; also block CGNAT/shared ranges explicitly.
            return False, f"resolved to private address {ip_str} (private targets require explicit pairing mode)"
    return True, "ok"


@dataclass
class AuthzDecision:
    allowed: bool
    reason: str
    approval_required: bool = False
    redacted: bool = False


def authorize_action(agent_trust: str, permission: str,
                     data_class: str = "internal",
                     granted_permissions: Optional[List[str]] = None) -> AuthzDecision:
    """Enforce capability + trust + data policy for one action."""
    if permission in REMOTE_DENY_BY_DEFAULT:
        return AuthzDecision(False, f"{permission} is never grantable to remote agents", False)
    spec = PERMISSION_CATALOG.get(permission)
    if spec is None:
        return AuthzDecision(False, f"unknown permission: {permission}", True)
    rank = trust_rank(agent_trust)
    if rank < 0:
        return AuthzDecision(False, f"agent is {agent_trust}", False)
    if granted_permissions is not None and permission not in granted_permissions:
        return AuthzDecision(False, f"permission {permission} not granted to this agent", True)
    if rank < spec["min_rank"]:
        return AuthzDecision(
            False,
            f"trust {agent_trust} (rank {rank}) below minimum {spec['min_rank']} for {permission}",
            True,
        )
    # Data policy: sensitive+ to below-fully-trusted requires approval.
    if data_class in ("sensitive", "highly_sensitive") and rank < 6:
        if data_class == "highly_sensitive" and rank < 4:
            return AuthzDecision(False, f"data class {data_class} blocked for trust {agent_trust}", True)
        return AuthzDecision(True, f"allowed with approval (data={data_class})", True)
    approval = spec["approval"]
    if approval == "always":
        return AuthzDecision(True, "allowed with approval", True)
    if approval == "auto_if_trusted":
        return AuthzDecision(True, "allowed (trusted)", rank < 4)
    return AuthzDecision(True, "allowed", False)
