"""Capability as a first-class versioned object (spec sections 1-2).

A capability can be consumed, delegated, provided, composed, rented,
shared, licensed, benchmarked, verified, priced, restricted, revoked.
Capabilities are versioned; providers/consumers attach over time.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore

SCHEMA_VERSION = "1"
CAPABILITY_VERSION = "1"


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"


@dataclass
class CapabilityDefinition:
    """Canonical capability record. Versioned; history preserved."""

    schema_version: str = SCHEMA_VERSION
    capability_id: str = ""       # e.g. "ocr.document" (namespace.name)
    namespace: str = ""
    name: str = ""
    version: str = "1"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    modalities: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)  # capability_ids
    security_level: str = "standard"  # low|standard|high|critical
    data_requirements: List[str] = field(default_factory=list)
    compute_requirements: Dict[str, Any] = field(default_factory=dict)
    network_requirements: Dict[str, Any] = field(default_factory=dict)
    verification_methods: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)  # agent_ids
    consumers: List[str] = field(default_factory=list)  # agent_ids
    status: str = "active"  # active|deprecated|revoked
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def validate(self) -> List[str]:
        errors = []
        if not self.capability_id:
            errors.append("capability_id required")
        if not self.namespace or not self.name:
            errors.append("namespace and name required")
        if not self.version:
            errors.append("version required")
        if self.security_level not in ("low", "standard", "high", "critical"):
            errors.append(f"bad security_level: {self.security_level!r}")
        if self.status not in ("active", "deprecated", "revoked"):
            errors.append(f"bad status: {self.status!r}")
        if self.capability_id in self.prerequisites:
            errors.append("capability cannot require itself")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityDefinition":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


class CapabilityRegistry:
    """Versioned capability store. Old versions preserved, never mutated."""

    def __init__(self, home: Path) -> None:
        self._defs = JsonStore(Path(home) / "capability_defs.json")
        self._history = JsonStore(Path(home) / "capability_history.json")

    def _key(self, capability_id: str, version: str) -> str:
        return f"{capability_id}@{version}"

    def register(self, definition: CapabilityDefinition) -> CapabilityDefinition:
        errors = definition.validate()
        if errors:
            raise ValueError(f"invalid capability: {errors}")
        key = self._key(definition.capability_id, definition.version)
        if self._defs.get(key) is not None:
            raise ValueError(
                f"capability {key} already registered (register a new version instead)")
        now = _now()
        definition.created_at = definition.created_at or now
        definition.updated_at = now
        self._defs.put(key, definition.to_dict())
        hist = self._history.get(definition.capability_id) or []
        hist.append({"version": definition.version, "at": now,
                     "status": definition.status})
        self._history.put(definition.capability_id, hist)
        return definition

    def get(self, capability_id: str,
            version: str = "") -> Optional[CapabilityDefinition]:
        if version:
            raw = self._defs.get(self._key(capability_id, version))
            return CapabilityDefinition.from_dict(raw) if raw else None
        # Latest = max version by registration order.
        hist = self._history.get(capability_id) or []
        if not hist:
            return None
        return self.get(capability_id, hist[-1]["version"])

    def versions(self, capability_id: str) -> List[str]:
        return [h["version"] for h in (self._history.get(capability_id) or [])]

    def list(self, namespace: str = "", status: str = "") -> List[CapabilityDefinition]:
        out = []
        seen = set()
        for raw in self._defs.values():
            cid = raw.get("capability_id", "")
            if cid in seen:
                continue
            seen.add(cid)
            latest = self.get(cid)
            if latest is None:
                continue
            if namespace and latest.namespace != namespace:
                continue
            if status and latest.status != status:
                continue
            out.append(latest)
        return sorted(out, key=lambda d: d.capability_id)

    def attach_provider(self, capability_id: str, agent_id: str) -> None:
        latest = self.get(capability_id)
        if latest is None:
            raise KeyError(f"unknown capability: {capability_id}")
        if agent_id not in latest.providers:
            latest.providers.append(agent_id)
            latest.updated_at = _now()
            self._defs.put(self._key(capability_id, latest.version),
                           latest.to_dict())

    def attach_consumer(self, capability_id: str, agent_id: str) -> None:
        latest = self.get(capability_id)
        if latest is None:
            raise KeyError(f"unknown capability: {capability_id}")
        if agent_id not in latest.consumers:
            latest.consumers.append(agent_id)
            latest.updated_at = _now()
            self._defs.put(self._key(capability_id, latest.version),
                           latest.to_dict())

    def revoke(self, capability_id: str, reason: str = "") -> CapabilityDefinition:
        """Revocation creates a NEW terminal version; history preserved."""
        latest = self.get(capability_id)
        if latest is None:
            raise KeyError(f"unknown capability: {capability_id}")
        data = latest.to_dict()
        data["version"] = f"{latest.version}+revoked"
        data["status"] = "revoked"
        data["description"] = (data.get("description", "")
                               + f" [REVOKED: {reason[:200]}]").strip()
        revoked = CapabilityDefinition.from_dict(data)
        return self.register(revoked)
