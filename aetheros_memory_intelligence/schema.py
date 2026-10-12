"""Unified memory entry schema for the intelligence fabric.

A single ``MemoryEntry`` replaces the ad-hoc record layouts of the platform
with a versioned, validated envelope that carries provenance, trust,
confidence and integrity fields.  All fabric modules operate on this schema.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.types import (
    MemoryBoundary,
    MemoryOrigin,
    MemoryState,
    MemoryType,
)


class SchemaVersion:
    """Schema versioning for exported/imported entries."""

    CURRENT = 1
    MIN_SUPPORTED = 1

    @classmethod
    def validate(cls, version: Any) -> bool:
        try:
            v = int(version)
        except (TypeError, ValueError):
            return False
        return cls.MIN_SUPPORTED <= v <= cls.CURRENT


@dataclass
class MemoryEntry:
    """The unified memory entry.

    Field list is a strict allow-list: ``from_dict`` refuses unknown fields
    (defense against malformed/forged payloads on import).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.SEMANTIC
    boundary: MemoryBoundary = MemoryBoundary.USER
    origin: MemoryOrigin = MemoryOrigin.UNKNOWN
    state: MemoryState = MemoryState.ACTIVE

    content: str = ""
    summary: str = ""
    tags: List[str] = field(default_factory=list)

    # Scoping (owner/visibility).
    user_id: str = ""
    workspace_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    project_id: str = ""

    # Provenance & trust.
    source: str = ""                    # human-readable source reference
    source_uri: str = ""                # canonical URI/ref when available
    confidence: float = 0.0             # [0,1]
    trust: float = 0.0                  # [0,1]
    verification: str = "unverified"
    corroborated_by: List[str] = field(default_factory=list)

    # Integrity & lifecycle.
    checksum: str = ""
    version: int = 1
    ttl: float = 0.0                    # 0 = never expires
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0

    # Free-form metadata (non-sensitive); secrets must never be stored here.
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @classmethod
    def _ALLOWED_FIELDS(cls) -> set:
        return {f for f in cls.__dataclass_fields__}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SchemaVersion.CURRENT,
            "id": self.id,
            "memory_type": self.memory_type.value,
            "boundary": self.boundary.value,
            "origin": self.origin.value,
            "state": self.state.value,
            "content": self.content,
            "summary": self.summary,
            "tags": list(self.tags),
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "source": self.source,
            "source_uri": self.source_uri,
            "confidence": self.confidence,
            "trust": self.trust,
            "verification": self.verification,
            "corroborated_by": list(self.corroborated_by),
            "checksum": self.checksum,
            "version": self.version,
            "ttl": self.ttl,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Strict constructor.  Raises ValueError on unknown/illegal fields.

        This is intentionally strict: entries arriving from import/export or
        external sources must not smuggle unexpected fields in.
        """
        if not isinstance(data, dict):
            raise ValueError("entry must be a dict")
        allowed = cls._ALLOWED_FIELDS()
        unknown = set(data.keys()) - allowed - {"schema_version"}
        if unknown:
            raise ValueError(f"unknown entry fields: {sorted(unknown)}")
        if "schema_version" in data and not SchemaVersion.validate(data["schema_version"]):
            raise ValueError("unsupported schema version")

        entry = cls()
        for key in allowed:
            if key in data:
                val = data[key]
                if key == "memory_type":
                    entry.memory_type = MemoryType(val)
                elif key == "boundary":
                    entry.boundary = MemoryBoundary(val)
                elif key == "origin":
                    entry.origin = MemoryOrigin(val)
                elif key == "state":
                    entry.state = MemoryState(val)
                elif key == "tags":
                    entry.tags = [str(t) for t in (val or [])]
                elif key == "corroborated_by":
                    entry.corroborated_by = [str(c) for c in (val or [])]
                elif key == "metadata":
                    if not isinstance(val, dict):
                        raise ValueError("metadata must be a dict")
                    entry.metadata = dict(val)
                elif key in ("confidence", "trust", "ttl", "created_at",
                             "updated_at", "accessed_at"):
                    entry.__setattr__(key, float(val))
                elif key in ("version", "access_count"):
                    entry.__setattr__(key, int(val))
                else:
                    entry.__setattr__(key, val)
        return entry

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def compute_checksum(self) -> str:
        """Stable SHA-256 over the semantic payload (not the checksum itself)."""
        payload = self.to_dict()
        payload.pop("checksum", None)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        if not self.checksum:
            return False
        return self.checksum == self.compute_checksum()

    def seal(self) -> "MemoryEntry":
        """Compute and attach the checksum for the current payload."""
        self.checksum = self.compute_checksum()
        return self

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.updated_at) > self.ttl

    def touch(self) -> None:
        self.accessed_at = time.time()
        self.access_count += 1

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = time.time()
        self.seal()


class MemoryEntryBuilder:
    """Fluent builder that applies sensible defaults."""

    def __init__(self) -> None:
        self._entry = MemoryEntry()

    def type(self, t: MemoryType) -> "MemoryEntryBuilder":
        self._entry.memory_type = t
        return self

    def boundary(self, b: MemoryBoundary) -> "MemoryEntryBuilder":
        self._entry.boundary = b
        return self

    def origin(self, o: MemoryOrigin) -> "MemoryEntryBuilder":
        self._entry.origin = o
        return self

    def content(self, text: str) -> "MemoryEntryBuilder":
        self._entry.content = text
        return self

    def summary(self, text: str) -> "MemoryEntryBuilder":
        self._entry.summary = text
        return self

    def tags(self, tags: List[str]) -> "MemoryEntryBuilder":
        self._entry.tags = list(tags)
        return self

    def scope(self, *, user_id: str = "", workspace_id: str = "",
              session_id: str = "", agent_id: str = "", project_id: str = "") -> "MemoryEntryBuilder":
        self._entry.user_id = user_id
        self._entry.workspace_id = workspace_id
        self._entry.session_id = session_id
        self._entry.agent_id = agent_id
        self._entry.project_id = project_id
        return self

    def provenance(self, *, source: str = "", source_uri: str = "",
                   confidence: float = 0.0, trust: float = 0.0,
                   verification: str = "unverified") -> "MemoryEntryBuilder":
        self._entry.source = source
        self._entry.source_uri = source_uri
        self._entry.confidence = confidence
        self._entry.trust = trust
        self._entry.verification = verification
        return self

    def ttl(self, seconds: float) -> "MemoryEntryBuilder":
        self._entry.ttl = seconds
        return self

    def metadata(self, data: Dict[str, Any]) -> "MemoryEntryBuilder":
        self._entry.metadata = dict(data)
        return self

    def build(self) -> MemoryEntry:
        entry = self._entry
        entry.seal()
        return entry


def validate_entry(entry: MemoryEntry) -> List[str]:
    """Return a list of validation problems (empty list == valid)."""
    problems: List[str] = []
    if not entry.content.strip():
        problems.append("content is empty")
    if not 0.0 <= entry.trust <= 1.0:
        problems.append("trust out of range")
    if not 0.0 <= entry.confidence <= 1.0:
        problems.append("confidence out of range")
    if entry.memory_type.is_high_privilege and entry.boundary == MemoryBoundary.USER:
        pass  # high-privilege type at user boundary is allowed (scoped owner)
    if entry.checksum and not entry.verify_integrity():
        problems.append("checksum mismatch")
    return problems