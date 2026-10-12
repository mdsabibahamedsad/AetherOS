"""Provenance records for memory entries.

Tracks where a memory came from, whether it was verified, and what evidence
corroborates it.  Provenance is the foundation of the fabric's
"memory is data, not authority" stance: confidence and trust derive from
provenance, never from the content itself.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.types import MemoryOrigin, VerificationLevel


@dataclass
class ProvenanceRecord:
    """Attached to an entry to explain its origin and verification state."""

    origin: MemoryOrigin = MemoryOrigin.UNKNOWN
    source: str = ""
    source_uri: str = ""
    agent: str = ""                 # which component recorded it
    recorded_at: float = field(default_factory=time.time)
    verification: VerificationLevel = VerificationLevel.UNVERIFIED
    evidence: List[str] = field(default_factory=list)   # references backing the fact
    corroborating_sources: List[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": self.origin.value,
            "source": self.source,
            "source_uri": self.source_uri,
            "agent": self.agent,
            "recorded_at": self.recorded_at,
            "verification": self.verification.value,
            "evidence": list(self.evidence),
            "corroborating_sources": list(self.corroborating_sources),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRecord":
        if not isinstance(data, dict):
            raise ValueError("provenance must be a dict")
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data.keys()) - known
        if unknown:
            raise ValueError(f"unknown provenance fields: {sorted(unknown)}")
        rec = cls()
        for k, v in data.items():
            if k == "origin":
                rec.origin = MemoryOrigin(v)
            elif k == "verification":
                rec.verification = VerificationLevel(v)
            elif k in ("evidence", "corroborating_sources"):
                setattr(rec, k, [str(x) for x in (v or [])])
            else:
                setattr(rec, k, v)
        return rec

    def corroborate(self, source_ref: str) -> None:
        if source_ref not in self.corroborating_sources:
            self.corroborating_sources.append(source_ref)
        if self.verification == VerificationLevel.UNVERIFIED:
            self.verification = VerificationLevel.SINGLE_SOURCE
        if len(self.corroborating_sources) >= 2:
            self.verification = VerificationLevel.CORROBORATED

    def contradict(self, source_ref: str, note: str = "") -> None:
        self.verification = VerificationLevel.CONTRADICTED
        if source_ref not in self.corroborating_sources:
            self.corroborating_sources.append(source_ref)
        self.note = note or self.note