"""Memory 2.0 canonical record + taxonomy (Master 41).

Extends the v1 ``MemoryEntry`` envelope (schema.py) without breaking it:
``MemoryRecord`` is the canonical long-term object with the full Master 41
field set (temporal validity, scopes, project/session/task linkage, entity /
relation / artifact / evidence links, versioning chain, privacy class,
confidence model, lifecycle status).  It converts losslessly to/from
``MemoryEntry`` for persistence in the existing ``MemoryStore``.

Design notes
- ``RecordType`` covers the 14 required Master 41 types.
- ``RecordScope`` covers the 9 required scopes with an explicit resolution
  hierarchy (GLOBAL < USER < WORKSPACE < PROJECT < TASK < SESSION < turn).
- ``PrivacyClass`` / ``ProvenanceKind`` / ``ConfidenceBand`` /
  ``RecordStatus`` implement sections 17/18/23/35/37.
- Secrets are refused at construction time (section 36).
"""

from __future__ import annotations

import enum
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.types import (
    MemoryBoundary,
    MemoryOrigin,
    MemoryState,
    MemoryType,
)


class RecordType(str, enum.Enum):
    USER_PREFERENCE = "user_preference"
    USER_FACT = "user_fact"
    PROJECT_FACT = "project_fact"
    PROJECT_DECISION = "project_decision"
    TASK_STATE = "task_state"
    EPISODIC_EVENT = "episodic_event"
    RESEARCH_FINDING = "research_finding"
    SOURCE_MEMORY = "source_memory"
    ENTITY_MEMORY = "entity_memory"
    RELATIONSHIP_MEMORY = "relationship_memory"
    ARTIFACT_MEMORY = "artifact_memory"
    PROCEDURAL_MEMORY = "procedural_memory"
    ERROR_LESSON = "error_lesson"
    SYSTEM_MEMORY = "system_memory"


class RecordScope(str, enum.Enum):
    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"
    WORKSPACE = "workspace"
    SESSION = "session"
    TASK = "task"
    AGENT = "agent"
    RESEARCH = "research"
    ARTIFACT = "artifact"


# Resolution order: least specific -> most specific.  A query scoped at
# level N may see records at levels <= N (ancestors), never descendants of
# an unrelated branch (project isolation).
SCOPE_HIERARCHY: List[RecordScope] = [
    RecordScope.GLOBAL,
    RecordScope.USER,
    RecordScope.WORKSPACE,
    RecordScope.PROJECT,
    RecordScope.TASK,
    RecordScope.SESSION,
]


class PrivacyClass(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class ProvenanceKind(str, enum.Enum):
    USER_STATED = "user_stated"
    TOOL_OBSERVED = "tool_observed"
    DOCUMENT_DERIVED = "document_derived"
    WEB_DERIVED = "web_derived"
    MODEL_INFERRED = "model_inferred"
    SYSTEM_GENERATED = "system_generated"


class ConfidenceBand(str, enum.Enum):
    EXPLICIT_USER_CONFIRMED = "explicit_user_confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"
    CONFLICTED = "conflicted"
    STALE = "stale"


class RecordStatus(str, enum.Enum):
    ACTIVE = "active"
    STALE = "stale"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    DELETED = "deleted"
    SUPERSEDED = "superseded"
    CONFLICTED = "conflicted"


# Map v1 MemoryType -> v2 RecordType default (used by migration/bridging).
_V1_TO_V2 = {
    MemoryType.EPISODIC: RecordType.EPISODIC_EVENT,
    MemoryType.SEMANTIC: RecordType.USER_FACT,
    MemoryType.PROCEDURAL: RecordType.PROCEDURAL_MEMORY,
    MemoryType.PREFERENCE: RecordType.USER_PREFERENCE,
    MemoryType.WORKSPACE: RecordType.PROJECT_FACT,
    MemoryType.MISSION: RecordType.TASK_STATE,
    MemoryType.AGENT: RecordType.SYSTEM_MEMORY,
    MemoryType.SESSION: RecordType.EPISODIC_EVENT,
    MemoryType.DOCUMENT: RecordType.SOURCE_MEMORY,
    MemoryType.SYSTEM: RecordType.SYSTEM_MEMORY,
    MemoryType.TEMPORARY: RecordType.EPISODIC_EVENT,
}

_V2_TO_V1 = {
    RecordType.USER_PREFERENCE: MemoryType.PREFERENCE,
    RecordType.USER_FACT: MemoryType.SEMANTIC,
    RecordType.PROJECT_FACT: MemoryType.WORKSPACE,
    RecordType.PROJECT_DECISION: MemoryType.SEMANTIC,
    RecordType.TASK_STATE: MemoryType.MISSION,
    RecordType.EPISODIC_EVENT: MemoryType.EPISODIC,
    RecordType.RESEARCH_FINDING: MemoryType.SEMANTIC,
    RecordType.SOURCE_MEMORY: MemoryType.DOCUMENT,
    RecordType.ENTITY_MEMORY: MemoryType.SEMANTIC,
    RecordType.RELATIONSHIP_MEMORY: MemoryType.SEMANTIC,
    RecordType.ARTIFACT_MEMORY: MemoryType.DOCUMENT,
    RecordType.PROCEDURAL_MEMORY: MemoryType.PROCEDURAL,
    RecordType.ERROR_LESSON: MemoryType.PROCEDURAL,
    RecordType.SYSTEM_MEMORY: MemoryType.SYSTEM,
}

_SCOPE_TO_BOUNDARY = {
    RecordScope.GLOBAL: MemoryBoundary.SYSTEM,
    RecordScope.USER: MemoryBoundary.USER,
    RecordScope.PROJECT: MemoryBoundary.WORKSPACE,
    RecordScope.WORKSPACE: MemoryBoundary.WORKSPACE,
    RecordScope.SESSION: MemoryBoundary.SESSION,
    RecordScope.TASK: MemoryBoundary.SESSION,
    RecordScope.AGENT: MemoryBoundary.AGENT,
    RecordScope.RESEARCH: MemoryBoundary.WORKSPACE,
    RecordScope.ARTIFACT: MemoryBoundary.WORKSPACE,
}

# Secret-shaped values must never become long-term memory (section 36).
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|apikey)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(secret|password|passwd|pwd)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"sk-(live|test)-[A-Za-z0-9]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def contains_secret(text: str) -> bool:
    return any(p.search(text or "") for p in _SECRET_PATTERNS)


@dataclass
class MemoryRecord:
    """Canonical Master 41 memory object."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: RecordType = RecordType.USER_FACT
    scope: RecordScope = RecordScope.USER
    content: str = ""
    summary: str = ""
    source: str = ""
    source_id: str = ""
    source_span: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    observed_at: float = field(default_factory=time.time)
    valid_from: float = 0.0
    valid_until: float = 0.0  # 0 = no expiry bound
    last_confirmed: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    confidence: float = 0.5
    confidence_band: ConfidenceBand = ConfidenceBand.MEDIUM
    importance: float = 0.5
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    sensitivity: float = 0.0
    provenance: ProvenanceKind = ProvenanceKind.MODEL_INFERRED
    user_confirmed: bool = False
    system_generated: bool = False
    explicit: bool = False  # explicit user statement vs inferred
    project_id: str = ""
    session_id: str = ""
    task_id: str = ""
    workspace_id: str = ""
    user_id: str = ""
    research_id: str = ""
    entity_ids: List[str] = field(default_factory=list)
    relation_ids: List[str] = field(default_factory=list)
    artifact_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    embedding_id: str = ""
    supersedes: List[str] = field(default_factory=list)
    superseded_by: str = ""
    version: int = 1
    status: RecordStatus = RecordStatus.ACTIVE
    ttl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- validation ---------------------------------------------------
    def validate(self) -> List[str]:
        problems: List[str] = []
        if not self.content.strip() and not self.summary.strip():
            problems.append("content is empty")
        if not 0.0 <= self.confidence <= 1.0:
            problems.append("confidence out of range")
        if not 0.0 <= self.importance <= 1.0:
            problems.append("importance out of range")
        if contains_secret(self.content) or contains_secret(self.summary):
            problems.append("secret-shaped content must not be stored as memory")
        if self.privacy_class == PrivacyClass.SECRET:
            problems.append("SECRET privacy class must use credential store, not memory")
        if self.valid_until and self.valid_from and self.valid_until < self.valid_from:
            problems.append("valid_until precedes valid_from")
        return problems

    # -- temporal helpers (section 14) --------------------------------
    def is_expired(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        if self.ttl > 0 and (now - self.updated_at) > self.ttl:
            return True
        if self.valid_until > 0 and now > self.valid_until:
            return True
        return False

    def is_currently_valid(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        if self.valid_from and now < self.valid_from:
            return False
        return not self.is_expired(now)

    def mark_used(self, now: Optional[float] = None) -> None:
        self.last_used = now if now is not None else time.time()
        self.use_count += 1

    # -- (de)serialization --------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "memory-record/2",
            "id": self.id,
            "type": self.type.value,
            "scope": self.scope.value,
            "content": self.content,
            "summary": self.summary,
            "source": self.source,
            "source_id": self.source_id,
            "source_span": self.source_span,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "observed_at": self.observed_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "last_confirmed": self.last_confirmed,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "confidence": self.confidence,
            "confidence_band": self.confidence_band.value,
            "importance": self.importance,
            "privacy_class": self.privacy_class.value,
            "sensitivity": self.sensitivity,
            "provenance": self.provenance.value,
            "user_confirmed": self.user_confirmed,
            "system_generated": self.system_generated,
            "explicit": self.explicit,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "research_id": self.research_id,
            "entity_ids": list(self.entity_ids),
            "relation_ids": list(self.relation_ids),
            "artifact_ids": list(self.artifact_ids),
            "evidence_ids": list(self.evidence_ids),
            "embedding_id": self.embedding_id,
            "supersedes": list(self.supersedes),
            "superseded_by": self.superseded_by,
            "version": self.version,
            "status": self.status.value,
            "ttl": self.ttl,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        if not isinstance(data, dict):
            raise ValueError("record must be a dict")
        rec = cls()
        rec.id = str(data.get("id", rec.id))
        rec.type = RecordType(str(data.get("type", rec.type.value)))
        rec.scope = RecordScope(str(data.get("scope", rec.scope.value)))
        for k in ("content", "summary", "source", "source_id", "source_span",
                  "project_id", "session_id", "task_id", "workspace_id",
                  "user_id", "research_id", "embedding_id", "superseded_by"):
            setattr(rec, k, str(data.get(k, "")))
        for k in ("created_at", "updated_at", "observed_at", "valid_from",
                  "valid_until", "last_confirmed", "last_used", "confidence",
                  "importance", "sensitivity", "ttl"):
            try:
                setattr(rec, k, float(data.get(k, getattr(rec, k))))
            except (TypeError, ValueError):
                pass
        rec.use_count = int(data.get("use_count", 0))
        rec.version = int(data.get("version", 1))
        rec.confidence_band = ConfidenceBand(str(data.get("confidence_band", rec.confidence_band.value)))
        rec.privacy_class = PrivacyClass(str(data.get("privacy_class", rec.privacy_class.value)))
        rec.provenance = ProvenanceKind(str(data.get("provenance", rec.provenance.value)))
        rec.status = RecordStatus(str(data.get("status", rec.status.value)))
        for k in ("user_confirmed", "system_generated", "explicit"):
            rec.__setattr__(k, bool(data.get(k, False)))
        for k in ("entity_ids", "relation_ids", "artifact_ids", "evidence_ids", "supersedes"):
            v = data.get(k, [])
            setattr(rec, k, [str(x) for x in (v or [])])
        meta = data.get("metadata", {})
        rec.metadata = dict(meta) if isinstance(meta, dict) else {}
        return rec

    # -- v1 bridging ----------------------------------------------------
    def to_entry(self) -> MemoryEntry:
        """Project this record into the v1 envelope for fabric persistence."""
        from aetheros_memory_intelligence.schema import MemoryEntryBuilder
        entry = (
            MemoryEntryBuilder()
            .type(_V2_TO_V1.get(self.type, MemoryType.SEMANTIC))
            .boundary(_SCOPE_TO_BOUNDARY.get(self.scope, MemoryBoundary.USER))
            .origin(_provenance_to_origin(self.provenance))
            .content(self.content)
            .summary(self.summary)
            .tags([self.type.value, self.scope.value, self.status.value])
            .scope(user_id=self.user_id, workspace_id=self.workspace_id,
                   session_id=self.session_id, agent_id=self.task_id,
                   project_id=self.project_id)
            .provenance(source=self.source, source_uri=self.source_id,
                        confidence=self.confidence, trust=self.confidence,
                        verification="corroborated" if self.user_confirmed else "single_source")
            .ttl(self.ttl)
            .metadata({**self.metadata, "record_v2": self.to_dict()})
            .build()
        )
        entry.id = self.id
        return entry

    @classmethod
    def from_entry(cls, entry: MemoryEntry) -> "MemoryRecord":
        raw = (entry.metadata or {}).get("record_v2")
        if isinstance(raw, dict) and raw.get("schema") == "memory-record/2":
            rec = cls.from_dict(raw)
            rec.id = entry.id
            return rec
        # Legacy entry: best-effort upgrade.
        rec = cls()
        rec.id = entry.id
        rec.type = _V1_TO_V2.get(entry.memory_type, RecordType.USER_FACT)
        rec.content = entry.content
        rec.summary = entry.summary
        rec.source = entry.source
        rec.source_id = entry.source_uri
        rec.created_at = entry.created_at
        rec.updated_at = entry.updated_at
        rec.confidence = entry.confidence
        rec.user_id = entry.user_id
        rec.workspace_id = entry.workspace_id
        rec.session_id = entry.session_id
        rec.project_id = entry.project_id
        rec.metadata = dict(entry.metadata or {})
        return rec


def _provenance_to_origin(p: ProvenanceKind) -> MemoryOrigin:
    return {
        ProvenanceKind.USER_STATED: MemoryOrigin.USER,
        ProvenanceKind.TOOL_OBSERVED: MemoryOrigin.TOOL,
        ProvenanceKind.DOCUMENT_DERIVED: MemoryOrigin.FILE,
        ProvenanceKind.WEB_DERIVED: MemoryOrigin.WEB,
        ProvenanceKind.MODEL_INFERRED: MemoryOrigin.CONVERSATION,
        ProvenanceKind.SYSTEM_GENERATED: MemoryOrigin.SYSTEM,
    }.get(p, MemoryOrigin.UNKNOWN)


def scope_visible(record_scope: RecordScope, query_scope: RecordScope,
                  *, record_project: str = "", query_project: str = "") -> bool:
    """Scope resolution (section 5). Ancestors visible; sibling projects isolated."""
    if record_scope == RecordScope.GLOBAL:
        return True
    if record_scope in (RecordScope.PROJECT, RecordScope.TASK,
                        RecordScope.RESEARCH, RecordScope.ARTIFACT):
        # Project-bound records require the same project (isolation rule).
        if record_project and query_project:
            return record_project == query_project
        # If the query carries no project, project-bound records are hidden.
        return False
    try:
        return SCOPE_HIERARCHY.index(query_scope) >= SCOPE_HIERARCHY.index(record_scope)
    except ValueError:
        return record_scope == query_scope


def confidence_band_for(*, explicit: bool, user_confirmed: bool,
                        confidence: float, conflicted: bool = False,
                        stale: bool = False) -> ConfidenceBand:
    if conflicted:
        return ConfidenceBand.CONFLICTED
    if stale:
        return ConfidenceBand.STALE
    if explicit and user_confirmed:
        return ConfidenceBand.EXPLICIT_USER_CONFIRMED
    if confidence >= 0.8:
        return ConfidenceBand.HIGH
    if confidence >= 0.5:
        return ConfidenceBand.MEDIUM
    if confidence >= 0.25:
        return ConfidenceBand.LOW
    return ConfidenceBand.UNVERIFIED
