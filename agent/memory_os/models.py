"""Master 18 unified memory object model (P2, P7, P10, P12, P15-17, P28-30).

Types/scopes/statuses/confidence/source-taxonomy exactly as specified by
MASTER PROMPT 18. ``MemoryItem`` is the single persistent unit; every field
required by P15 is present and every item carries provenance (P31).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"
    PROJECT = "project"
    TASK = "task"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    RESEARCH = "research"
    TOOL = "tool"
    WORKFLOW = "workflow"
    UI_PATTERN = "ui_pattern"
    COMPUTER_USE = "computer_use"
    TEMPORAL = "temporal"
    SOURCE = "source"
    SYSTEM = "system"


class MemoryScope(str, Enum):
    SESSION = "session"
    TASK = "task"
    PROJECT = "project"
    USER = "user"
    ORGANIZATION = "organization"
    SYSTEM = "system"


class MemoryStatus(str, Enum):
    CANDIDATE = "candidate"          # awaiting approval for long-term retention
    ACTIVE = "active"
    SUPERSEDED = "superseded"        # replaced by a newer version of the truth
    ARCHIVED = "archived"
    EXPIRED = "expired"              # TTL/validity window elapsed
    QUARANTINED = "quarantined"      # firewall flagged; excluded from retrieval
    MERGED = "merged"                # folded into another item (dedup)
    FORGOTTEN = "forgotten"          # deleted; never returned by retrieval


class Confidence(str, Enum):
    CONFIRMED = "confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    USER_EXPLICIT = "user_explicit"
    USER_PROVIDED_FILE = "user_provided_file"
    SYSTEM = "system"
    PROJECT = "project"
    RESEARCH = "research"
    TOOL = "tool"
    WEB = "web"
    MODEL_INFERENCE = "model_inference"


#: Sources that are external/untrusted content for the memory firewall (P39-40).
UNTRUSTED_SOURCES = frozenset(
    {SourceType.WEB, SourceType.TOOL, SourceType.MODEL_INFERENCE}
)

#: Semi-trusted: derived by our own subsystems from user data.
DERIVED_SOURCES = frozenset({SourceType.PROJECT, SourceType.RESEARCH, SourceType.SYSTEM})


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"


class PreferenceKind(str, Enum):
    NONE = ""
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    TEMPORARY = "temporary"


class Resolution(str, Enum):
    SEPARATE = "separate"
    MERGED = "merged"
    UNCERTAIN = "uncertain"


class RelationshipType(str, Enum):
    OWNS = "owns"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    CREATED_BY = "created_by"
    AUTHORED_BY = "authored_by"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    LOCATED_IN = "located_in"
    BUILT_WITH = "built_with"
    REPLACED_BY = "replaced_by"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    MENTIONS = "mentions"
    DERIVED_FROM = "derived_from"


class FeedbackKind(str, Enum):
    USEFUL = "useful"
    INCORRECT = "incorrect"
    OUTDATED = "outdated"
    IRRELEVANT = "irrelevant"
    PRIVATE = "private"


CONFIDENCE_ORDER = {
    Confidence.UNKNOWN: 0.0,
    Confidence.LOW: 0.25,
    Confidence.MEDIUM: 0.5,
    Confidence.HIGH: 0.75,
    Confidence.CONFIRMED: 1.0,
}

#: Types whose content is durable policy/decision knowledge — exempt from decay.
DECAY_EXEMPT_TYPES = frozenset(
    {
        MemoryType.PREFERENCE,
        MemoryType.PROCEDURAL,
        MemoryType.WORKFLOW,
        MemoryType.SYSTEM,
    }
)

#: Types that may hold volatile facts requiring revalidation before reuse (P55).
VOLATILE_TYPES = frozenset({MemoryType.TEMPORAL, MemoryType.RESEARCH, MemoryType.SEMANTIC})


def _now() -> float:
    return time.time()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


@dataclass
class Provenance:
    """P31 — answers where/when/who/explicit-or-inferred/evidence."""

    origin_event: str = ""            # free-form event id or description
    actor: str = ""                   # who/what supplied it ("user", agent id, tool id)
    explicit: bool = False            # explicit user statement vs inferred
    evidence_ids: List[str] = field(default_factory=list)
    channel: str = ""                 # cli | gateway:<platform> | mcp:<server> | research | computer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_event": self.origin_event,
            "actor": self.actor,
            "explicit": self.explicit,
            "evidence_ids": list(self.evidence_ids),
            "channel": self.channel,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "Provenance":
        d = d or {}
        return cls(
            origin_event=str(d.get("origin_event", "")),
            actor=str(d.get("actor", "")),
            explicit=bool(d.get("explicit", False)),
            evidence_ids=[str(x) for x in d.get("evidence_ids", [])],
            channel=str(d.get("channel", "")),
        )


@dataclass
class MemoryItem:
    """The single persistent memory unit (P15) with lifecycle fields."""

    type: MemoryType = MemoryType.SEMANTIC
    content: str = ""
    summary: str = ""
    source_type: SourceType = SourceType.USER_EXPLICIT
    source_id: str = ""
    scope: MemoryScope = MemoryScope.USER
    owner: str = "default"
    project_id: str = ""
    task_id: str = ""
    entity_ids: List[str] = field(default_factory=list)
    relationship_ids: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    importance: float = 0.5           # 0..1 — never used as permission (P51)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    last_accessed_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    valid_from: Optional[float] = None
    valid_until: Optional[float] = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    content_hash: str = ""
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    preference_kind: PreferenceKind = PreferenceKind.NONE
    semantic_key: str = ""            # stable identity for conflict detection (P25)
    tags: List[str] = field(default_factory=list)
    allow_agents: bool = False        # P37/P38: explicit cross-agent sharing
    hint_only: bool = False           # e.g. computer-use/UI patterns: never authority
    revalidate_after: Optional[float] = None
    provenance: Provenance = field(default_factory=Provenance)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = content_hash(self.content)

    # -- validity / freshness -------------------------------------------------

    def temporally_valid(self, at: Optional[float] = None) -> bool:
        at = at if at is not None else _now()
        if self.valid_from is not None and at < self.valid_from:
            return False
        if self.valid_until is not None and at > self.valid_until:
            return False
        return True

    def is_expired(self, at: Optional[float] = None) -> bool:
        at = at if at is not None else _now()
        return self.expires_at is not None and at > self.expires_at

    def needs_revalidation(self, at: Optional[float] = None) -> bool:
        at = at if at is not None else _now()
        return (
            self.status == MemoryStatus.ACTIVE
            and self.revalidate_after is not None
            and at > self.revalidate_after
        )

    def touch_access(self) -> None:
        self.last_accessed_at = _now()

    # -- serialization ---------------------------------------------------------

    def to_row(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "type": self.type.value,
            "content": self.content,
            "summary": self.summary,
            "content_hash": self.content_hash,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "scope": self.scope.value,
            "owner": self.owner,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "confidence": self.confidence.value,
            "importance": self.importance,
            "sensitivity": self.sensitivity.value,
            "preference_kind": self.preference_kind.value,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed_at": self.last_accessed_at,
            "expires_at": self.expires_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "revalidate_after": self.revalidate_after,
            "semantic_key": self.semantic_key,
            "tags": json.dumps(self.tags),
            "entity_ids": json.dumps(self.entity_ids),
            "relationship_ids": json.dumps(self.relationship_ids),
            "allow_agents": int(self.allow_agents),
            "hint_only": int(self.hint_only),
            "provenance": json.dumps(self.provenance.to_dict()),
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "MemoryItem":
        try:
            tags = json.loads(row.get("tags") or "[]")
            entity_ids = json.loads(row.get("entity_ids") or "[]")
            relationship_ids = json.loads(row.get("relationship_ids") or "[]")
            prov = json.loads(row.get("provenance") or "{}")
            meta = json.loads(row.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            tags, entity_ids, relationship_ids, prov, meta = [], [], [], {}, {}
        return cls(
            memory_id=row["memory_id"],
            type=MemoryType(row["type"]),
            content=row["content"],
            summary=row.get("summary", ""),
            content_hash=row.get("content_hash") or "",
            source_type=SourceType(row["source_type"]),
            source_id=row.get("source_id", ""),
            scope=MemoryScope(row["scope"]),
            owner=row.get("owner", "default"),
            project_id=row.get("project_id", ""),
            task_id=row.get("task_id", ""),
            confidence=Confidence(row["confidence"]),
            importance=float(row.get("importance", 0.5)),
            sensitivity=Sensitivity(row["sensitivity"]),
            preference_kind=PreferenceKind(row.get("preference_kind") or ""),
            status=MemoryStatus(row["status"]),
            version=int(row.get("version", 1)),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
            last_accessed_at=float(row["last_accessed_at"]),
            expires_at=row.get("expires_at"),
            valid_from=row.get("valid_from"),
            valid_until=row.get("valid_until"),
            revalidate_after=row.get("revalidate_after"),
            semantic_key=row.get("semantic_key", ""),
            tags=[str(t) for t in tags],
            allow_agents=bool(row.get("allow_agents")),
            hint_only=bool(row.get("hint_only")),
            provenance=Provenance.from_dict(prov),
            metadata=meta if isinstance(meta, dict) else {},
        )

    def with_content(self, new_content: str) -> "MemoryItem":
        """Versioned copy: same identity, next version, fresh hash/timestamps."""
        clone = MemoryItem.from_row(self.to_row())
        clone.content = new_content
        clone.content_hash = content_hash(new_content)
        clone.version += 1
        clone.updated_at = _now()
        clone.summary = ""
        return clone


def classify_memory(
    *,
    source_type: SourceType,
    sensitivity: Sensitivity,
    status_hint: Optional[MemoryStatus] = None,
) -> List[str]:
    """P17 persistence-time classification labels (advisory, returned to caller)."""
    labels: List[str] = []
    if sensitivity == Sensitivity.SENSITIVE:
        labels.append("sensitive")
    if source_type in DERIVED_SOURCES:
        labels.append("derived")
    if source_type == SourceType.MODEL_INFERENCE:
        labels.append("uncertain")
    if status_hint == MemoryStatus.CANDIDATE:
        labels.append("temporary")
    else:
        labels.append("useful")
    if source_type in UNTRUSTED_SOURCES:
        labels.append("untrusted_origin")
    return labels
