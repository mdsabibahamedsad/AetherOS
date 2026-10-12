"""A2A-compatible Agent Card handling (Master 46 sections 6-7).

The Agent Card is untrusted metadata until identity/trust checks succeed.
Card text is never executed; URLs/skills/schemes are validated, not trusted.

Supported card shape (A2A v1.0 core):

    {
      "protocolVersion": "1.0",
      "name": "...", "description": "...", "version": "...",
      "url": "https://agent.example/",
      "capabilities": {"streaming": true, ...},
      "skills": [{"id": "...", "name": "...", ...}],
      "defaultInputModes": [...], "defaultOutputModes": [...],
      "authentication": {"schemes": ["oauth2", ...]},
    }

Legacy v0.3 cards (``protocolVersions`` list / top-level ``endpoint``)
are accepted and normalized with the source version recorded — never
silently treated as v1.0.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import A2A_SUPPORTED_VERSIONS

_REQUIRED = ("name", "url", "version")
_ALLOWED_SCHEMES = ("https",)
_ALLOWED_AUTH_SCHEMES = {
    "oauth2", "oidc", "mtls", "apiKey", "bearer", "none",
}


@dataclass
class AgentSkill:
    id: str
    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentCard:
    """Normalized, validated Agent Card (still untrusted until verified)."""

    name: str
    url: str
    version: str
    protocol_version: str = "1.0"
    description: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    skills: List[AgentSkill] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=list)
    output_modes: List[str] = field(default_factory=list)
    auth_schemes: List[str] = field(default_factory=list)
    provider: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["skills"] = [s if isinstance(s, dict) else asdict(s) for s in self.skills]
        return d


def parse_agent_card(data: Dict[str, Any], source_url: str = "") -> AgentCard:
    """Parse raw JSON into a normalized AgentCard. Raises ValueError."""
    if not isinstance(data, dict):
        raise ValueError("agent card must be a JSON object")
    for key in _REQUIRED:
        if not data.get(key):
            raise ValueError(f"agent card missing required field: {key}")

    # Protocol version: v1.0 `protocolVersion` or legacy v0.3 `protocolVersions`.
    proto = str(data.get("protocolVersion") or "").strip()
    source_version = proto
    if not proto:
        legacy = data.get("protocolVersions") or []
        if isinstance(legacy, list) and legacy:
            proto = str(legacy[0])
            source_version = "0.3-legacy"
        else:
            proto = "unknown"
    if proto not in A2A_SUPPORTED_VERSIONS and proto != "unknown":
        raise ValueError(f"unsupported A2A protocol version: {proto!r}")

    url = str(data.get("url") or data.get("endpoint") or "")
    skills: List[AgentSkill] = []
    for s in data.get("skills") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or s.get("name") or "")
        if not sid:
            continue
        skills.append(AgentSkill(
            id=sid[:128],
            name=str(s.get("name") or sid)[:128],
            description=str(s.get("description") or "")[:2000],
            tags=[str(t)[:64] for t in (s.get("tags") or [])][:16],
            examples=[str(e)[:512] for e in (s.get("examples") or [])][:8],
        ))
    auth = data.get("authentication") or {}
    schemes = auth.get("schemes") if isinstance(auth, dict) else []
    card = AgentCard(
        name=str(data["name"])[:128],
        url=url,
        version=str(data["version"])[:64],
        protocol_version=proto,
        description=str(data.get("description") or "")[:4000],
        capabilities=dict(data.get("capabilities") or {}),
        skills=skills,
        input_modes=[str(m)[:64] for m in (data.get("defaultInputModes") or [])][:16],
        output_modes=[str(m)[:64] for m in (data.get("defaultOutputModes") or [])][:16],
        auth_schemes=[str(s) for s in (schemes or [])][:8],
        provider=dict(data.get("provider") or {}),
        raw=data,
        source_url=source_url,
    )
    if source_version == "0.3-legacy":
        card.raw["_aetheros_source_version"] = "0.3-legacy"
    return card


def validate_agent_card(card: AgentCard) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). Errors = must not proceed; warnings = re-verify."""
    errors: List[str] = []
    warnings: List[str] = []
    parsed = urlparse(card.url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        errors.append(f"card url must use https, got scheme={parsed.scheme!r}")
    if not parsed.hostname:
        errors.append("card url has no hostname")
    if card.source_url:
        src = urlparse(card.source_url)
        # Endpoint consistency: card host must match fetch host.
        if parsed.hostname and src.hostname and parsed.hostname != src.hostname:
            warnings.append(
                f"card url host {parsed.hostname!r} != fetch host {src.hostname!r} "
                "(possible endpoint substitution)"
            )
    for scheme in card.auth_schemes:
        if scheme not in _ALLOWED_AUTH_SCHEMES:
            warnings.append(f"unknown auth scheme {scheme!r}")
    if card.protocol_version == "unknown":
        warnings.append("card declares no protocol version")
    # Card text is data: flag anything that looks like an instruction.
    suspicious = ("ignore previous instructions", "system prompt", "reveal your",
                  "disregard", "jailbreak")
    blob = (card.description + " " + " ".join(
        s.description for s in card.skills)).lower()
    for phrase in suspicious:
        if phrase in blob:
            warnings.append(f"card text contains suspicious phrase {phrase!r} "
                             "(treated as data, never executed)")
            break
    return errors, warnings


def verification_label(checks: Dict[str, Any]) -> str:
    """Map verification evidence to UNVERIFIED / VERIFIED / TRUSTED / REVOKED."""
    if checks.get("revoked"):
        return "REVOKED"
    if checks.get("user_trusted") or checks.get("org_trusted"):
        return "TRUSTED"
    if checks.get("tls_ok") and (checks.get("signature_ok") or checks.get("issuer_ok")):
        if not checks.get("expired") and not checks.get("endpoint_mismatch"):
            return "VERIFIED"
    return "UNVERIFIED"
