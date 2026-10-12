"""
Communication security: phishing detection + injection defense
(Master 16 Phases 19, 76-79).

Incoming messages (email, chat, SMS) are UNTRUSTED DATA. This module provides:
- Phishing/spoofing heuristics for message-level content
- Injection-pattern scanning for incoming communication text
- Link safety checks before opening URLs from messages

Pure evaluation — no side effects, no blocking I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Phishing / spoofing detection (Phase 76)
# ---------------------------------------------------------------------------

_PHISHING_PATTERNS = [
    (r"(?i)(verify|confirm|validate)\s+(your\s+)?(account|identity|email|password)", "credential_request"),
    (r"(?i)(urgent|immediate|act\s+now|expires?\s+(today|tomorrow|in\s+\d+\s+(hours?|days?)))", "urgency_manipulation"),
    (r"(?i)click\s+(here|this\s+link)\s+to\s+", "click_bait_link"),
    (r"(?i)(suspended|locked|compromised|unusual\s+(activity|login))", "account_threat"),
    (r"(?i)(wire\s+transfer|gift\s+card|cryptocurrency|bitcoin)\s+(request|payment)", "financial_scam"),
    (r"(?i)(you\s+have\s+(won|inherited)|lottery|prize\s+winner)", "lottery_scam"),
]

_SUSPICIOUS_TLD_PATTERNS = re.compile(
    r"\.(tk|ml|ga|cf|gq|xyz|top|club|work|link|click|loan|date|racing|download)"
)

_BRAND_IMPERSONATION = [
    "paypal", "amazon", "apple", "microsoft", "google", "netflix",
    "facebook", "instagram", "twitter", "linkedin", "dropbox",
    "office365", "outlook", "gmail", "dhl", "fedex", "usps",
]


@dataclass
class MessageThreatAssessment:
    is_phishing: bool = False
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)
    suspicious_links: List[Dict[str, str]] = field(default_factory=list)
    injection_detected: bool = False
    injection_patterns: List[str] = field(default_factory=list)


def assess_message_threat(
    subject: str,
    body: str,
    sender_address: str,
    sender_display_name: str = "",
    known_contacts: Optional[set] = None,
) -> MessageThreatAssessment:
    """Assess an inbound message for phishing/injection threats."""
    result = MessageThreatAssessment()
    full_text = f"{subject}\n{body}"

    # 1. Phishing pattern scan
    score = 0
    for pattern, label in _PHISHING_PATTERNS:
        if re.search(pattern, full_text):
            result.indicators.append(label)
            score += 2

    # 2. Suspicious link extraction
    urls = re.findall(r'https?://[^\s<>"\')\]]+', body)
    for url in urls:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        link_info: Dict[str, str] = {"url": url[:200], "host": host}

        # Suspicious TLD check
        if _SUSPICIOUS_TLD_PATTERNS.search(host):
            link_info["flag"] = "suspicious_tld"
            score += 2
            result.indicators.append(f"suspicious_tld:{host}")

        # Brand impersonation in subdomain (e.g., paypal.secure-login.tk)
        for brand in _BRAND_IMPERSONATION:
            if brand in host and not host.endswith(f".{brand}.com") and \
               not host.endswith(f"{brand}.com"):
                link_info["flag"] = f"brand_impersonation:{brand}"
                score += 3
                result.indicators.append(f"brand_impersonation:{brand}")
                break

        # IP literal instead of domain
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
            link_info["flag"] = "ip_literal"
            score += 2
            result.indicators.append("ip_literal_url")

        result.suspicious_links.append(link_info)

    # 3. Sender display-name vs address mismatch
    if sender_display_name and "@" in sender_display_name:
        dn_domain = sender_display_name.split("@")[-1].lower().strip(">")
        addr_domain = sender_address.split("@")[-1].lower() if "@" in sender_address else ""
        if dn_domain != addr_domain and dn_domain and addr_domain:
            result.indicators.append(f"display_name_mismatch:{dn_domain}_vs_{addr_domain}")
            score += 1

    # 4. Known-contact check — unknown sender increases suspicion with phishing patterns
    if known_contacts and sender_address.lower() not in {c.lower() for c in known_contacts}:
        if score > 0:
            score += 1  # unknown sender + existing indicators
            result.indicators.append("unknown_sender")

    result.confidence = min(score / 10.0, 1.0)
    result.is_phishing = score >= 4

    return result


# ---------------------------------------------------------------------------
# Prompt-injection defense for communication (Phases 19, 78)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"(?i)disregard\s+(all\s+|any\s+)?(previous|prior|your)\s+(instructions?|rules?|policies?)",
    r"(?i)you\s+are\s+now\s+(a|an|the)\s+",
    r"(?i)(system|assistant|ai)\s*:\s*",
    r"(?i)new\s+(instructions?|directives?|programming)\s*:",
    r"(?i)(send|forward|share|transfer|give\s+me)\s+(your|the|all)\s+"
    r"(api\s*)?(key|token|secret|password|credential)",
    r"(?i)reveal\s+(your|the)\s+(system\s+)?(prompt|instructions)",
]


def scan_for_injection(text: str) -> List[str]:
    """Scan message text for prompt-injection attempts."""
    hits = []
    for i, pattern in enumerate(_INJECTION_PATTERNS):
        if re.search(pattern, text):
            hits.append(f"injection_pattern_{i}")
    return hits


# ---------------------------------------------------------------------------
# Unified threat gate for inbound communication
# ---------------------------------------------------------------------------

class InboundVerdict:
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    PHISHING = "phishing"
    INJECTION = "injection"

    def __init__(self, assessment: MessageThreatAssessment,
                 injection_patterns: List[str]):
        self.assessment = assessment
        self.injection_patterns = injection_patterns
        if injection_patterns:
            self.verdict = self.INJECTION
        elif assessment.is_phishing:
            self.verdict = self.PHISHING
        elif assessment.indicators:
            self.verdict = self.SUSPICIOUS
        else:
            self.verdict = self.SAFE

    @property
    def should_warn(self) -> bool:
        return self.verdict in (self.SUSPICIOUS, self.PHISHING)

    @property
    def should_block_auto_actions(self) -> bool:
        return self.verdict in (self.PHISHING, self.INJECTION)


def evaluate_inbound(
    subject: str, body: str,
    sender_address: str, sender_display_name: str = "",
    known_contacts: Optional[set] = None,
) -> InboundVerdict:
    """Full inbound threat evaluation. Returns structured verdict."""
    assessment = assess_message_threat(
        subject, body, sender_address, sender_display_name, known_contacts)
    injections = scan_for_injection(body)
    return InboundVerdict(assessment, injections)


__all__ = [
    "MessageThreatAssessment", "assess_message_threat",
    "scan_for_injection", "InboundVerdict", "evaluate_inbound",
]
