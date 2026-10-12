"""
Communication send gate + recipient verification (Master 16 Phases 9, 14, 23-32).

The gate is the LAST LINE OF DEFENSE before any message leaves the system.
It composes:
- Recipient verification (lookalike detection, external warning)
- Sensitive-data scanning of body/attachments
- Side-effect classification → confirmation requirement
- Mass-message / BCC / reply-all safety checks
- Idempotency (duplicate-send prevention)

This module is PURE — it evaluates and returns verdicts; actual sending
delegates to existing gateway adapters / API providers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from aetheros_comms.model import (
    Channel, CommunicationMessage, Priority, Recipient,
    Sensitivity, SendStatus,
)


# ---------------------------------------------------------------------------
# Recipient verification (Phase 9)
# ---------------------------------------------------------------------------

# Common lookalike substitutions
_LOOKALIKE_MAP = {
    "0": "o", "1": "l", "3": "e", "5": "s", "8": "b",
    "rn": "m", "vv": "w", "cl": "d",
}

_KNOWN_INTERNAL_TLDS = frozenset({".corp", ".internal", ".local", ".lan"})


def _normalize_email_for_comparison(addr: str) -> str:
    """Lowercase, strip plus-tagging from the local part."""
    addr = addr.strip().lower()
    if "@" in addr:
        local, domain = addr.rsplit("@", 1)
        local = local.split("+")[0] if "+" in local else local
        return f"{local}@{domain}"
    return addr


def _looks_like_known(addr: str, known_addresses: Set[str]) -> Optional[str]:
    """Check whether addr is a lookalike of any known address.

    Returns the matched known address or None.
    """
    norm = _normalize_email_for_comparison(addr)
    for known in known_addresses:
        known_norm = _normalize_email_for_comparison(known)
        if norm == known_norm:
            continue  # exact match after normalization — not lookalike

        # Domain-only comparison
        _, addr_domain = norm.rsplit("@", 1) if "@" in norm else ("", norm)
        _, known_domain = known_norm.rsplit("@", 1) if "@" in known_norm else ("", known_norm)

        # Same local part but different domain → possible spoofing
        addr_local = norm.split("@")[0] if "@" in norm else norm
        known_local = known_norm.split("@")[0] if "@" in known_norm else known_norm
        if addr_local == known_local and addr_domain != known_domain:
            return known

        # Character-level similarity (edit distance approximation)
        if "@" in norm and "@" in known_norm:
            if _similar_enough(addr_domain, known_domain):
                return known
    return None


def _similar_enough(a: str, b: str, threshold: float = 0.85) -> bool:
    """Cheap similarity check via character-set overlap."""
    if not a or not b:
        return False
    sa, sb = set(a), set(b)
    overlap = len(sa & sb) / max(len(sa | sb), 1)
    return overlap >= threshold


def verify_recipients(
    msg: "CommunicationMessage",
    *,
    known_internal_domains: FrozenSet[str] = frozenset(),
    known_contacts: FrozenSet[str] = frozenset(),
) -> Tuple[List[Recipient], List[str]]:
    """Verify all recipients on a message. Returns (recipients, warnings).

    Mutates recipients in-place to set verified/external/risk_flags.
    """
    warnings: List[str] = []
    internal_set = set(known_internal_domains)
    contact_set = {_normalize_email_for_comparison(c) for c in known_contacts}

    for r in msg.all_recipient_objects:
        addr_lower = r.address.lower().strip()
        norm = _normalize_email_for_comparison(r.address)

        # External check: domain not in known internal domains
        domain = addr_lower.split("@")[-1] if "@" in addr_lower else ""
        if internal_set and domain and domain not in internal_set:
            if not any(domain.endswith(tld) for tld in _KNOWN_INTERNAL_TLDS):
                r.external = True

        # Known contact check
        if norm in contact_set:
            r.verified = True
        elif known_contacts:
            lookalike = _looks_like_known(r.address, known_contacts)
            if lookalike:
                r.risk_flags.append(f"lookalike:{lookalike}")
                warnings.append(
                    f"Possible lookalike address: '{r.address}' resembles '{lookalike}'"
                )
            elif contact_set:
                r.risk_flags.append("unknown_recipient")
        else:
            # No contact list to verify against; mark as unverified but don't flag
            pass

        # Display-name vs address mismatch (impersonation indicator)
        if r.display_name and "@" in r.display_name:
            dn_addr = _normalize_email_for_comparison(r.display_name)
            if dn_addr != norm and "@" in dn_addr:
                r.risk_flags.append("display_name_mismatch")
                warnings.append(
                    f"Display name '{r.display_name}' doesn't match address '{r.address}'"
                )

    return list(msg.all_recipient_objects), warnings


# ---------------------------------------------------------------------------
# Sensitive-data detection (Phase 23)
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = [
    (r"sk-[a-zA-Z0-9_-]{20,}", "api_key"),
    (r"ghp_[a-zA-Z0-9]{36}", "github_token"),
    (r"gho_[a-zA-Z0-9]{36}", "github_oauth"),
    (r"xox[bpars]-[a-zA-Z0-9-]+", "slack_token"),
    (r"AKIA[A-Z0-9]{16}", "aws_access_key"),
    (r"(?i)password\s*[=:]\s*\S+", "password_literal"),
    (r"(?i)(secret|token|credential)s?\s*[:=]\s*\S+", "secret_ref"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "credit_card"),
]


def scan_sensitive_data(text: str) -> List[Tuple[str, int]]:
    """Scan text for credential-shaped content. Returns [(type, offset)]."""
    findings: List[Tuple[str, int]] = []
    for pattern, label in _SENSITIVE_PATTERNS:
        for match in re.finditer(pattern, text):
            findings.append((label, match.start()))
    return findings


def check_message_sensitivity(msg: CommunicationMessage) -> Tuple[Sensitivity, List[str]]:
    """Determine effective sensitivity. Returns (level, findings_descriptions)."""
    # Use ordinal values for comparison since Sensitivity is a str Enum.
    _ORD = {s: i for i, s in enumerate([
        Sensitivity.PUBLIC, Sensitivity.INTERNAL, Sensitivity.CONFIDENTIAL,
        Sensitivity.SENSITIVE, Sensitivity.RESTRICTED])}
    max_level = msg.sensitivity
    descriptions: List[str] = []

    body_findings = scan_sensitive_data(msg.body)
    subject_findings = scan_sensitive_data(msg.subject) if msg.subject else []

    if body_findings or subject_findings:
        types = {f[0] for f in body_findings + subject_findings}
        descriptions.extend(sorted(types))
        if any(t in ("api_key", "github_token", "github_oauth", "slack_token",
                      "aws_access_key", "password_literal", "secret_ref") for t in types):
            if _ORD[max_level] < _ORD[Sensitivity.SENSITIVE]:
                max_level = Sensitivity.SENSITIVE
        if any(t in ("ssn", "credit_card") for t in types):
            if _ORD[max_level] < _ORD[Sensitivity.RESTRICTED]:
                max_level = Sensitivity.RESTRICTED

    for att in msg.attachments:
        if _ORD.get(att.sensitivity, 0) > _ORD.get(max_level, 0):
            max_level = att.sensitivity

    return max_level, descriptions


# ---------------------------------------------------------------------------
# Send gate verdict (Phases 14, 25-32)
# ---------------------------------------------------------------------------

@dataclass
class GateVerdict:
    allowed: bool
    requires_confirmation: bool = False
    warnings: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    risk_score: int = 0              # 0-10

    @property
    def blocked(self) -> bool:
        return bool(self.blocks)


def evaluate_send_gate(
    msg: CommunicationMessage,
    *,
    known_internal_domains: FrozenSet[str] = frozenset(),
    known_contacts: FrozenSet[str] = frozenset(),
    mass_threshold: int = 20,
    require_confirmation_external: bool = True,
    block_sensitive_to_external: bool = True,
) -> GateVerdict:
    """Evaluate whether a message may be sent. Returns a structured verdict."""
    verdict = GateVerdict(allowed=True)

    # 1. Basic validation
    if not msg.sender:
        verdict.blocks.append("no sender account specified")
    if not msg.all_recipient_addresses:
        verdict.blocks.append("no recipients")
    if not msg.body.strip() and not msg.attachments:
        verdict.blocks.append("empty body and no attachments")

    if verdict.blocked:
        verdict.allowed = False
        return verdict

    # 2. Recipient verification
    recipients, recip_warnings = verify_recipients(
        msg, known_internal_domains=known_internal_domains,
        known_contacts=known_contacts)
    verdict.warnings.extend(recip_warnings)
    has_lookalike = any("lookalike:" in r.risk_flags for r in recipients)
    if has_lookalike:
        verdict.requires_confirmation = True
        verdict.warnings.append("Lookalike address detected — confirmation required")

    # 3. Sensitivity scan
    effective_sens, sens_findings = check_message_sensitivity(msg)
    verdict.sensitivity = effective_sens
    if sens_findings:
        verdict.warnings.append(
            f"Sensitive content detected: {', '.join(sens_findings)}")

    # 4. External recipient check
    externals = [r for r in recipients if r.external]
    if externals and effective_sens in (Sensitivity.SENSITIVE, Sensitivity.RESTRICTED):
        if block_sensitive_to_external:
            verdict.blocks.append(
                f"Sensitive/restricted content with external recipients: "
                f"{[r.address for r in externals]}")
            verdict.allowed = False
            return verdict
        verdict.requires_confirmation = True
    elif externals and require_confirmation_external:
        verdict.requires_confirmation = True
        verdict.warnings.append(
            f"{len(externals)} external recipient(s): "
            f"{[r.address for r in externals]}")

    # 5. Mass-message check (Phase 27)
    total = msg.total_recipients
    if total > mass_threshold:
        verdict.requires_confirmation = True
        verdict.warnings.append(
            f"Mass communication: {total} recipients exceeds threshold ({mass_threshold})")

    # 6. BCC safety (Phase 28)
    if msg.bcc:
        verdict.warnings.append(
            f"BCC recipients present: {[r.address for r in msg.bcc]}"
        )
        verdict.requires_confirmation = True

    # 7. Reply-all safety (Phase 29)
    cc_count = len(msg.cc)
    to_count = len(msg.recipients)
    if cc_count > 5 and "reply" in (msg.metadata.get("_intent") or "").lower():
        verdict.warnings.append(
            f"Reply-all to large thread: {to_count} To + {cc_count} CC recipients")
        verdict.requires_confirmation = True

    # 8. Attachment protection (Phase 22)
    for att in msg.attachments:
        if att.scan_state == "flagged":
            verdict.blocks.append(f"Attachment flagged by scanner: {att.filename}")
            verdict.allowed = False
            return verdict
        if att.sensitivity in (Sensitivity.SENSITIVE, Sensitivity.RESTRICTED):
            verdict.requires_confirmation = True
            verdict.warnings.append(
                f"Sensitive attachment: {att.filename} ({att.sensitivity.value})")

    # 9. Compute risk score (0-10)
    score = 0
    if effective_sens == Sensitivity.SENSITIVE: score += 3
    elif effective_sens == Sensitivity.RESTRICTED: score += 5
    elif effective_sens == Sensitivity.CONFIDENTIAL: score += 2
    if externals: score += min(len(externals), 2)
    if has_lookalike: score += 3
    if total > mass_threshold: score += min((total - mass_threshold) // 10, 2)
    if sens_findings: score += 2
    verdict.risk_score = min(score, 10)

    # Final decision
    if verdict.blocks:
        verdict.allowed = False

    return verdict


def compute_idempotency_key(msg: CommunicationMessage) -> str:
    """Stable hash for duplicate-send prevention (Phase 32)."""
    h = hashlib.sha256()
    h.update(str(msg.sender).encode())
    for addr in sorted(msg.all_recipient_addresses):
        h.update(addr.encode())
    h.update(msg.subject.encode())
    h.update(msg.body[:500].encode())  # first 500 chars sufficient
    for att in sorted(msg.attachments, key=lambda a: a.filename):
        h.update(att.sha256.encode() if att.sha256 else att.filename.encode())
    return h.hexdigest()[:24]


__all__ = [
    "verify_recipients", "scan_sensitive_data", "check_message_sensitivity",
    "GateVerdict", "evaluate_send_gate", "compute_idempotency_key",
    "_normalize_email_for_comparison",
]
