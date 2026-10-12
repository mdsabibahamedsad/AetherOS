"""
Cross-domain data-flow tracking and URL suspicion heuristics
(Master 15 Phases 26, 27, 70, 71).

Two responsibilities, both PURE (no I/O):

1. :func:`record_transfer` / dataclass ``DataTransfer`` — normalized record of
   data moving from a source context to a destination, with an automatic
   exfiltration verdict: credential/financial/sensitive-classified payloads
   crossing to a DIFFERENT registrable domain than their origin are flagged
   unless explicitly authorized.

2. :func:`check_suspicious_url` — cheap pre-navigation/download checks for
   phishing indicators: punycode hosts, embedded credentials ('@' in
   authority), raw IP literals, excessive subdomain depth, and brand-token
   mismatch against caller-supplied trusted domains.

Heuristics are advisory signals layered UNDER the hard guarantees that already
exist in tools/url_safety.py + tools/website_policy.py; they never unblock
anything those layers reject.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Local import kept lazy-free: action.py is dependency-light.
from aetheros_computer.action import FieldClassification, classify_field


# ---------------------------------------------------------------------------
# Data transfers (Phases 26-27)
# ---------------------------------------------------------------------------

SENSITIVE_CLASSES = frozenset({
    FieldClassification.CREDENTIAL.value,
    FieldClassification.FINANCIAL.value,
    FieldClassification.SENSITIVE.value,
})


@dataclass
class DataTransfer:
    source_domain: str = ""
    destination_domain: str = ""
    payload_fields: Dict[str, str] = field(default_factory=dict)  # name -> classification
    reason: str = ""
    authorized: bool = False
    timestamp: float = field(default_factory=time.time)

    @property
    def has_sensitive(self) -> bool:
        return any(c in SENSITIVE_CLASSES for c in self.payload_fields.values())

    @property
    def cross_domain(self) -> bool:
        return bool(
            self.source_domain
            and self.destination_domain
            and _registrable(self.source_domain) != _registrable(self.destination_domain)
        )

    @property
    def exfiltration_suspect(self) -> bool:
        """Sensitive payload crossing domains without explicit authorization."""
        return self.has_sensitive and self.cross_domain and not self.authorized


def build_transfer(
    source_url: str,
    destination_url: str,
    field_names: List[str],
    reason: str = "",
    authorized: bool = False,
) -> DataTransfer:
    """Build a transfer record, classifying each payload field by name."""
    classified = {name: classify_field(name).value for name in field_names}
    return DataTransfer(
        source_domain=_host_of(source_url),
        destination_domain=_host_of(destination_url),
        payload_fields=classified,
        reason=reason,
        authorized=authorized,
    )


def _host_of(url: str) -> str:
    try:
        return (urlparse(str(url)).hostname or "").lower()
    except Exception:
        return ""


def _registrable(host: str) -> str:
    """Cheap registrable-domain approximation: last two labels."""
    parts = host.split(".") if host else []
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


# ---------------------------------------------------------------------------
# Suspicious-URL heuristics (Phase 71)
# ---------------------------------------------------------------------------

MAX_NORMAL_SUBDOMAIN_DEPTH = 5


def check_suspicious_url(
    url: str,
    trusted_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return {'suspicious': bool, 'reasons': [..], 'score': int}.

    Signals (each adds weight):
      - punycode host (``xn--``)                       weight 3
      - credentials embedded in authority (user@host)  weight 3
      - raw IP literal host                            weight 2
      - subdomain depth > MAX_NORMAL_SUBDOMAIN_DEPTH   weight 2
      - brand-token mismatch vs trusted_domains        weight 3
    Score >= 3 => suspicious. Purely advisory; never blocks by itself.
    """
    reasons: List[str] = []
    score = 0
    try:
        parsed = urlparse(str(url))
    except Exception:
        return {"suspicious": True, "reasons": ["unparseable url"], "score": 9}

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        if parsed.scheme:
            reasons.append(f"non-http scheme: {scheme}")
            score += 2

    host = (parsed.hostname or "").lower()

    # '@' in authority means userinfo — classic obfuscation.
    netloc = parsed.netloc or ""
    if "@" in netloc:
        reasons.append("credentials embedded in URL authority")
        score += 3

    if host.startswith("xn--") or ".xn--" in host:
        reasons.append("punycode host")
        score += 3

    if _is_ip_literal(host):
        reasons.append("raw IP literal host")
        score += 2

    labels = [l for l in host.split(".") if l]
    if len(labels) > MAX_NORMAL_SUBDOMAIN_DEPTH + 1:  # +1 for registrable itself
        reasons.append(f"excessive subdomain depth ({len(labels)} labels)")
        score += 2

    if trusted_domains:
        trusted = [_registrable(d.lower().strip()) for d in trusted_domains if d.strip()]
        reg = _registrable(host)
        if reg and trusted and reg not in trusted:
            # Brand-token check: does any trusted brand token appear in host?
            brands = [t.split(".")[0] for t in trusted if t]
            if brands and not any(b and b in host for b in brands):
                reasons.append(f"brand mismatch: '{reg}' not among trusted")
                score += 3

    return {"suspicious": score >= 3, "reasons": reasons, "score": score}


def _is_ip_literal(host: str) -> bool:
    if not host:
        return False
    if host.startswith("[") and host.endswith("]"):  # IPv6 literal
        return True
    parts = host.split(".")
    if len(parts) == 4:
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    return False


# ---------------------------------------------------------------------------
# Navigation / domain verification (Phases 69-70)
# ---------------------------------------------------------------------------

def verify_navigation(expected_url: str,
                      current_url: str,
                      require_https: bool = False) -> Dict[str, Any]:
    """Verify the page we landed on matches the intended destination.

    Compares registrable domains (not full URLs — path/query churn is normal),
    flags scheme downgrade http↔https, and reports phishing heuristics on the
    CURRENT url so a lookalike redirect fails verification.
    """
    expected_host = _host_of(expected_url)
    current_host = _host_of(current_url)
    reasons: List[str] = []

    if not current_host:
        return {"verified": False, "reasons": ["no current host"], "domain_match": False}

    if expected_host and _registrable(expected_host) != _registrable(current_host):
        reasons.append(f"domain mismatch: expected {expected_host}, got {current_host}")

    exp_scheme = urlparse(str(expected_url or "")).scheme.lower()
    cur_scheme = urlparse(str(current_url or "")).scheme.lower()
    if require_https and cur_scheme != "https":
        reasons.append(f"scheme downgraded to '{cur_scheme}'")
    if exp_scheme == "https" and cur_scheme == "http":
        reasons.append("https→http downgrade")

    verdict = check_suspicious_url(current_url,
                                   trusted_domains=[expected_host] if expected_host else None)
    if verdict.get("suspicious"):
        reasons.extend(f"phishing:{r}" for r in verdict["reasons"])

    return {
        "verified": not reasons,
        "reasons": reasons,
        "domain_match": bool(expected_host) and
                        _registrable(expected_host) == _registrable(current_host),
    }


__all__ = [
    "DataTransfer",
    "build_transfer",
    "check_suspicious_url",
    "verify_navigation",
    "SENSITIVE_CLASSES",
]
