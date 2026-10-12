"""AetherOS Master 18 unified memory layer.

Composes storage, security firewall, entity resolution, knowledge graph,
lifecycle, hybrid retrieval and working memory into one facade
(:class:`MemoryManager`). Composes existing infrastructure (research bridge
records, computer-use pattern memory, checkpoints, cron scheduler, AES-GCM
encryption); registers no model tools.
"""

from agent.memory_os.entities import EntityRegistry
from agent.memory_os.graph import KnowledgeGraph
from agent.memory_os.lifecycle import Lifecycle
from agent.memory_os.manager import Controls, MemoryManager, StoreOutcome
from agent.memory_os.models import (
    Confidence,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    PreferenceKind,
    Provenance,
    RelationshipType,
    Sensitivity,
    SourceType,
)
from agent.memory_os.retrieval import RetrievalHit, RetrievalResult, Retriever, WorkingMemory
from agent.memory_os.security import (
    AccessContext,
    AccessDenied,
    ActorKind,
    FirewallViolation,
    SecretDetected,
)

__all__ = [
    "EntityRegistry",
    "KnowledgeGraph",
    "Lifecycle",
    "MemoryManager",
    "Controls",
    "StoreOutcome",
    "MemoryItem",
    "MemoryType",
    "MemoryScope",
    "MemoryStatus",
    "Confidence",
    "Sensitivity",
    "SourceType",
    "PreferenceKind",
    "Provenance",
    "RelationshipType",
    "Retriever",
    "RetrievalHit",
    "RetrievalResult",
    "WorkingMemory",
    "AccessContext",
    "AccessDenied",
    "ActorKind",
    "SecretDetected",
    "FirewallViolation",
]
