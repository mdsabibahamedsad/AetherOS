"""Trust levels and persistent trust store (Master 46 sections 11-13).

Trust level gates authorization. Discovery never implies trust:
new records start at DISCOVERED/UNVERIFIED and move only via explicit
verification or user/org approval. Reputation/history is informational
and never upgrades trust by itself.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TRUST_LEVELS = (
    "unknown",
    "discovered",
    "unverified",
    "verified",
    "user_trusted",
    "organization_trusted",
    "fully_trusted",
    "blocked",
    "revoked",
)

# Higher = more privilege. blocked/revoked are terminal denials.
_TRUST_RANK = {
    "unknown": 0,
    "discovered": 1,
    "unverified": 2,
    "verified": 3,
    "user_trusted": 4,
    "organization_trusted": 5,
    "fully_trusted": 6,
    "blocked": -1,
    "revoked": -2,
}

# Explicit transitions only. No silent upgrades.
_ALLOWED_TRANSITIONS = {
    "unknown": {"discovered", "unverified", "blocked"},
    "discovered": {"unverified", "verified", "blocked"},
    "unverified": {"verified", "user_trusted", "blocked", "revoked"},
    "verified": {"user_trusted", "organization_trusted", "blocked", "revoked", "unverified"},
    "user_trusted": {"fully_trusted", "blocked", "revoked", "verified"},
    "organization_trusted": {"fully_trusted", "blocked", "revoked", "verified"},
    "fully_trusted": {"blocked", "revoked", "verified"},
    "blocked": {"unverified", "revoked"},
    "revoked": set(),  # terminal: requires removal + fresh pairing
}


def can_transition(frm: str, to: str) -> bool:
    return to in _ALLOWED_TRANSITIONS.get(frm, set())


def trust_rank(level: str) -> int:
    return _TRUST_RANK.get(level, 0)


@dataclass
class TrustRecord:
    agent_id: str
    level: str = "discovered"
    verified_by: str = ""  # tls+issuer | signature | user | org | ...
    evidence: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class TrustStore:
    """JSON-persisted trust records with an append-only transition history."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._records: Dict[str, TrustRecord] = {}
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for agent_id, rec in data.get("records", {}).items():
                    self._records[agent_id] = TrustRecord.from_dict(rec)
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

    def get(self, agent_id: str) -> TrustRecord:
        rec = self._records.get(agent_id)
        if rec is None:
            rec = TrustRecord(agent_id=agent_id)
            self._records[agent_id] = rec
        return rec

    def level(self, agent_id: str) -> str:
        return self.get(agent_id).level

    def set_level(self, agent_id: str, to: str, by: str = "",
                  evidence: Optional[Dict[str, Any]] = None) -> TrustRecord:
        if to not in TRUST_LEVELS:
            raise ValueError(f"unknown trust level: {to!r}")
        rec = self.get(agent_id)
        frm = rec.level
        if to != frm and not can_transition(frm, to):
            raise ValueError(f"trust transition not allowed: {frm} -> {to}")
        rec.level = to
        rec.verified_by = by or rec.verified_by
        if evidence:
            rec.evidence.update(evidence)
        rec.updated_at = time.time()
        rec.history.append({
            "from": frm, "to": to, "by": by,
            "at": rec.updated_at,
        })
        self.save()
        return rec

    def is_blocked(self, agent_id: str) -> bool:
        return self.level(agent_id) in ("blocked", "revoked")

    def all_records(self) -> List[TrustRecord]:
        return list(self._records.values())
