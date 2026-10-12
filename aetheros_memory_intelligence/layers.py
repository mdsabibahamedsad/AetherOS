"""Memory layers L0-L10 (Master 41 section 2).

Each layer declares purpose, storage, retrieval/write/retention policy,
default confidence, privacy class and deletion behavior.  The registry is
data (not code branches) so policy can be inspected and configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from aetheros_memory_intelligence.record import PrivacyClass, RecordScope, RecordType


@dataclass(frozen=True)
class MemoryLayer:
    level: int
    name: str
    purpose: str
    storage: str
    retrieval_policy: str
    write_policy: str
    retention_policy: str
    default_confidence: float
    privacy_class: PrivacyClass
    deletion_behavior: str
    record_types: tuple
    scopes: tuple


LAYERS: List[MemoryLayer] = [
    MemoryLayer(0, "working", "Current-turn scratch (model context only).",
                "in-memory turn buffer", "always included when referenced",
                "turn-local writes only", "dropped at turn end", 0.0,
                PrivacyClass.INTERNAL, "discard",
                (RecordType.EPISODIC_EVENT,), (RecordScope.SESSION,)),
    MemoryLayer(1, "session", "Current session transient context.",
                "fabric store (session scope)", "session id match",
                "session events above noise threshold", "end of session + 7d", 0.4,
                PrivacyClass.INTERNAL, "expire",
                (RecordType.EPISODIC_EVENT, RecordType.TASK_STATE,), (RecordScope.SESSION,)),
    MemoryLayer(2, "episodic", "Important events from previous sessions.",
                "fabric store + timeline index", "temporal + importance ranked",
                "importance-filtered (writer gate)", "90d default, pinned kept", 0.55,
                PrivacyClass.INTERNAL, "archive",
                (RecordType.EPISODIC_EVENT,), (RecordScope.USER, RecordScope.SESSION,)),
    MemoryLayer(3, "semantic", "Stable facts and concepts.",
                "fabric store + hybrid index", "hybrid retrieval",
                "deduplicated + corroborated writes", "until superseded", 0.6,
                PrivacyClass.INTERNAL, "supersede (keep history)",
                (RecordType.USER_FACT, RecordType.ENTITY_MEMORY,
                 RecordType.RELATIONSHIP_MEMORY, RecordType.SOURCE_MEMORY,),
                (RecordScope.GLOBAL, RecordScope.USER, RecordScope.WORKSPACE,)),
    MemoryLayer(4, "project", "Per-project state, decisions, constraints.",
                "fabric store (project scope)", "project id match required",
                "project-scoped writes only", "project lifetime + archive", 0.65,
                PrivacyClass.INTERNAL, "archive with project",
                (RecordType.PROJECT_FACT, RecordType.PROJECT_DECISION,
                 RecordType.TASK_STATE,), (RecordScope.PROJECT, RecordScope.TASK,)),
    MemoryLayer(5, "preference", "User preferences (explicit > inferred).",
                "fabric store (user scope)", "user id match, explicit first",
                "explicit auto-store; inferred suggest/confirm", "until changed/deleted", 0.7,
                PrivacyClass.PRIVATE, "tombstone on delete",
                (RecordType.USER_PREFERENCE,), (RecordScope.USER,)),
    MemoryLayer(6, "graph", "Entity/relationship knowledge graph.",
                "graph store + adjacency index", "traversal + entity filter",
                "extracted entities/relations with provenance", "until contradicted", 0.6,
                PrivacyClass.INTERNAL, "tombstone node + drop edges",
                (RecordType.ENTITY_MEMORY, RecordType.RELATIONSHIP_MEMORY,),
                (RecordScope.USER, RecordScope.PROJECT, RecordScope.GLOBAL,)),
    MemoryLayer(7, "research", "Validated research claims + evidence links.",
                "fabric store + evidence refs", "freshness-aware reuse",
                "research pipeline writes only", "source-freshness based", 0.7,
                PrivacyClass.INTERNAL, "keep claim, mark stale",
                (RecordType.RESEARCH_FINDING, RecordType.SOURCE_MEMORY,),
                (RecordScope.RESEARCH, RecordScope.PROJECT,)),
    MemoryLayer(8, "artifact", "Generated/modified file lineage.",
                "fabric store + artifact refs", "task/artifact id match",
                "tool-observed writes on verify", "until artifact deleted", 0.75,
                PrivacyClass.INTERNAL, "cascade tombstone",
                (RecordType.ARTIFACT_MEMORY,), (RecordScope.ARTIFACT, RecordScope.TASK,)),
    MemoryLayer(9, "procedural", "Learned workflows and error lessons.",
                "fabric store (user/project)", "task-similarity ranked",
                "validated runs only, never auto-execute", "until superseded", 0.6,
                PrivacyClass.INTERNAL, "supersede",
                (RecordType.PROCEDURAL_MEMORY, RecordType.ERROR_LESSON,),
                (RecordScope.USER, RecordScope.PROJECT, RecordScope.TASK,)),
    MemoryLayer(10, "system", "Operational/system state.",
                "fabric store (system boundary)", "agent/system actors only",
                "system-generated only", "short TTL + rotation", 0.8,
                PrivacyClass.INTERNAL, "expire",
                (RecordType.SYSTEM_MEMORY,), (RecordScope.AGENT,)),
]

_BY_LEVEL: Dict[int, MemoryLayer] = {layer.level: layer for layer in LAYERS}
_BY_NAME: Dict[str, MemoryLayer] = {layer.name: layer for layer in LAYERS}


def get_layer(level: int) -> MemoryLayer:
    return _BY_LEVEL[level]


def get_layer_by_name(name: str) -> MemoryLayer:
    return _BY_NAME[name]


def layer_for_record(record_type: RecordType) -> MemoryLayer:
    for layer in LAYERS:
        if record_type in layer.record_types:
            return layer
    return _BY_LEVEL[3]
