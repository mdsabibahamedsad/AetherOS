"""Canonical AgentRegistry for remote/federated agents (Master 46 section 10).

Stores discovery, identity, metadata, trust, capabilities, health,
endpoints, permissions, policies, connections, task history, revocation,
and organization membership for REMOTE agents only. Local agents stay in
the existing local registries (agent/orchestration/agent_registry.py,
aetheros_swarm/registry.py, aetheros_comm/identity.py) — this registry
references them by id where they overlap instead of duplicating them.

Removing an agent marks it REMOVED but preserves audit history.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agent_card import AgentCard
from .identity import AgentIdentity


@dataclass
class RegistryRecord:
    identity: Dict[str, Any]
    card: Dict[str, Any]
    source: str = "manual"  # direct_url | lan | private_registry | org_registry | curated | manual
    provenance: Dict[str, Any] = field(default_factory=dict)
    health: str = "unknown"  # online | degraded | busy | offline | unavailable | auth_error | rate_limited | untrusted | revoked
    last_seen: float = 0.0
    latency_ms: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    permissions: List[str] = field(default_factory=list)
    removed: bool = False
    first_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class AgentRegistry:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._records: Dict[str, RegistryRecord] = {}
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for agent_id, rec in data.get("records", {}).items():
                    self._records[agent_id] = RegistryRecord.from_dict(rec)
            except (ValueError, OSError):
                self._records = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(
            {"records": {k: v.to_dict() for k, v in self._records.items()}},
            indent=2,
        ), encoding="utf-8")
        tmp.replace(self._path)

    def upsert(self, agent_id: str, identity: AgentIdentity, card: AgentCard,
               source: str, provenance: Optional[Dict[str, Any]] = None) -> RegistryRecord:
        """Insert or update. Sensitive card changes force re-verification
        flag via provenance['reverify_required'] (section 117)."""
        existing = self._records.get(agent_id)
        reverify = False
        if existing and not existing.removed:
            old = existing.card
            new = card.to_dict()
            for key in ("url", "auth_schemes", "provider"):
                if old.get(key) != new.get(key):
                    reverify = True
            old_caps = {s.get("id") for s in old.get("skills", [])}
            new_caps = {s.id for s in card.skills}
            if new_caps - old_caps:
                reverify = True
        prov = dict(provenance or {})
        if reverify:
            prov["reverify_required"] = True
            prov["reverify_at"] = time.time()
        rec = RegistryRecord(
            identity=identity.to_dict(),
            card=card.to_dict(),
            source=source,
            provenance=prov,
            health=existing.health if existing else "unknown",
            last_seen=existing.last_seen if existing else 0.0,
            latency_ms=existing.latency_ms if existing else None,
            failure_count=existing.failure_count if existing else 0,
            success_count=existing.success_count if existing else 0,
            permissions=list(existing.permissions) if existing else [],
            first_seen=existing.first_seen if existing else time.time(),
        )
        self._records[agent_id] = rec
        self.save()
        return rec

    def get(self, agent_id: str) -> Optional[RegistryRecord]:
        rec = self._records.get(agent_id)
        return rec if rec and not rec.removed else None

    def get_including_removed(self, agent_id: str) -> Optional[RegistryRecord]:
        return self._records.get(agent_id)

    def list(self, include_removed: bool = False) -> List[Dict[str, Any]]:
        out = []
        for agent_id, rec in self._records.items():
            if rec.removed and not include_removed:
                continue
            d = rec.to_dict()
            d["agent_id"] = agent_id
            out.append(d)
        return out

    def remove(self, agent_id: str) -> bool:
        """Mark REMOVED; audit history is preserved (section 119)."""
        rec = self._records.get(agent_id)
        if rec is None:
            return False
        rec.removed = True
        rec.health = "unavailable"
        self.save()
        return True

    def record_heartbeat(self, agent_id: str, health: str,
                         latency_ms: Optional[float] = None,
                         success: bool = True) -> None:
        rec = self._records.get(agent_id)
        if rec is None:
            return
        rec.health = health
        rec.last_seen = time.time()
        if latency_ms is not None:
            rec.latency_ms = latency_ms
        if success:
            rec.success_count += 1
        else:
            rec.failure_count += 1
        self.save()

    def record_task_outcome(self, agent_id: str, success: bool) -> None:
        rec = self._records.get(agent_id)
        if rec is None:
            return
        if success:
            rec.success_count += 1
        else:
            rec.failure_count += 1
        self.save()
