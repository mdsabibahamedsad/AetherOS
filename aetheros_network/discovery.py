"""Agent discovery (Master 46 sections 8-9).

Sources: direct URL, manual import, private/org/curated registries (JSON
files), explicit LAN registry. mDNS/DNS-SD is NOT implemented — discovery
over-config without verification is how spoofing happens; document the gap
instead of faking it.

Every discovery result is DISCOVERED, never trusted.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import A2A_AGENT_CARD_PATH
from .agent_card import AgentCard, parse_agent_card, validate_agent_card
from .identity import AgentIdentity, new_agent_id
from .policy import check_url_allowed
from .transport import A2ATransport, TransportConfig, TransportError


@dataclass
class DiscoveryResult:
    agent_id: str
    card: Dict[str, Any]
    identity: Dict[str, Any]
    source: str
    verification: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _identity_from_card(card: AgentCard, source: str,
                        organization_id: str = "") -> AgentIdentity:
    host = urlparse(card.url).hostname or "unknown"
    org = organization_id or (card.provider.get("organization") if card.provider else "") or "external"
    return AgentIdentity(
        agent_id=new_agent_id(str(org)),
        canonical_name=card.name,
        display_name=card.name,
        organization_id=str(org),
        issuer=f"discovery:{source}",
        endpoints=[card.url],
        protocols=[f"A2A/{card.protocol_version}"],
        trust_level="discovered",
    )


def discover_from_url(url: str, transport_config: Optional[TransportConfig] = None,
                      organization_id: str = "") -> DiscoveryResult:
    """Fetch + parse + structurally validate an Agent Card. No trust implied."""
    base = url.strip()
    if base.endswith(A2A_AGENT_CARD_PATH):
        base = base[: -len(A2A_AGENT_CARD_PATH)]
    transport = A2ATransport(base, transport_config)
    errors: List[str] = []
    warnings: List[str] = []
    verification: Dict[str, Any] = {"tls_ok": base.startswith("https://")}
    try:
        raw = transport.fetch_agent_card()
    except TransportError as e:
        return DiscoveryResult(
            agent_id="", card={}, identity={},
            source="direct_url",
            verification={"tls_ok": False, "error": str(e), "kind": e.kind},
            errors=[str(e)], warnings=[],
        )
    verification["fetch_latency_ms"] = raw.pop("_aetheros_fetch_latency_ms", None)
    try:
        card = parse_agent_card(raw, source_url=base + A2A_AGENT_CARD_PATH)
    except ValueError as e:
        return DiscoveryResult(
            agent_id="", card={}, identity={}, source="direct_url",
            verification=verification, errors=[str(e)], warnings=[],
        )
    errors, warnings = validate_agent_card(card)
    identity = _identity_from_card(card, "direct_url", organization_id)
    verification["endpoint_mismatch"] = any("endpoint substitution" in w for w in warnings)
    return DiscoveryResult(
        agent_id=identity.agent_id, card=card.to_dict(),
        identity=identity.to_dict(), source="direct_url",
        verification=verification, errors=errors, warnings=warnings,
    )


def import_card_file(path: Path, organization_id: str = "") -> DiscoveryResult:
    """Manual import of a card JSON file (air-gapped pairing)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return DiscoveryResult(agent_id="", card={}, identity={},
                               source="manual", verification={},
                               errors=[f"cannot read card file: {e}"], warnings=[])
    try:
        card = parse_agent_card(raw, source_url=f"file:{path}")
    except ValueError as e:
        return DiscoveryResult(agent_id="", card={}, identity={},
                               source="manual", verification={},
                               errors=[str(e)], warnings=[])
    errors, warnings = validate_agent_card(card)
    identity = _identity_from_card(card, "manual", organization_id)
    return DiscoveryResult(
        agent_id=identity.agent_id, card=card.to_dict(),
        identity=identity.to_dict(), source="manual",
        verification={"tls_ok": False, "manual_import": True},
        errors=errors, warnings=warnings,
    )


def discover_from_registry_file(path: Path, kind: str = "private_registry",
                                organization_id: str = "") -> List[DiscoveryResult]:
    """Read a registry file: {"agents": [{"url": ...} | {"card": {...}}]}.
    URLs are fetched live; embedded cards are parsed without network I/O."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [DiscoveryResult(agent_id="", card={}, identity={},
                                source=kind, verification={},
                                errors=[f"cannot read registry file: {e}"], warnings=[])]
    results: List[DiscoveryResult] = []
    entries = data.get("agents", []) if isinstance(data, dict) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "card" in entry and isinstance(entry["card"], dict):
            try:
                card = parse_agent_card(entry["card"], source_url=f"registry:{path}")
            except ValueError as e:
                results.append(DiscoveryResult(
                    agent_id="", card={}, identity={}, source=kind,
                    verification={}, errors=[str(e)], warnings=[]))
                continue
            errors, warnings = validate_agent_card(card)
            identity = _identity_from_card(card, kind, organization_id)
            results.append(DiscoveryResult(
                agent_id=identity.agent_id, card=card.to_dict(),
                identity=identity.to_dict(), source=kind,
                verification={"tls_ok": False, "registry_embedded": True},
                errors=errors, warnings=warnings,
            ))
        elif "url" in entry:
            results.append(discover_from_url(str(entry["url"]), None, organization_id))
    return results
