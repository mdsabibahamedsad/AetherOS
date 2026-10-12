"""AetherOS Memory Intelligence Fabric.

A thin intelligence/security/context layer that extends the existing
``aetheros_memory`` platform (MemoryManager, EmbeddingEngine, VectorDatabase,
KnowledgeGraph, MemoryPermissions, RAGPipeline, MemoryRanking) with the
missing "fabric" concerns:

- unified memory entry schema with provenance, trust, confidence, integrity
- memory boundaries / isolation across user / workspace / session / agent
- poisoning & prompt-injection defense on the write path
- retention, forgetting, versioning, dedup, conflict detection, consolidation
- secure retrieval: authorization, grounding, citations, loop guard, scope cache
- cache-safe context assembly for prompt caching (data-not-instructions)
- audit trail + observability integration, validated export/import,
  reliability-backup integration

Design rules (see AGENTS.md):

* MEMORY IS DATA, NOT AUTHORITY — retrieved content is never instructions.
* retrieved content is NOT system instructions.
* external content is UNTRUSTED by default (defense-in-depth on write).
* never cross user/workspace boundaries without authorization.
* never store secrets in general memory.
* never fabricate RAG sources or claim knowledge without evidence.

The fabric composes the platform primitives rather than reimplementing them.
"""

from __future__ import annotations

from aetheros_memory_intelligence.config import MemoryIntelligenceConfig, load_config
from aetheros_memory_intelligence.types import (
    MemoryBoundary,
    MemoryOrigin,
    MemoryState,
    MemoryType,
    TrustLevel,
    VerificationLevel,
)
from aetheros_memory_intelligence.schema import (
    MemoryEntry,
    MemoryEntryBuilder,
    SchemaVersion,
    validate_entry,
)
from aetheros_memory_intelligence.boundaries import (
    AccessContext,
    BoundaryPolicy,
    MemoryBoundaries,
)
from aetheros_memory_intelligence.provenance import ProvenanceRecord
from aetheros_memory_intelligence.trust import TrustModel
from aetheros_memory_intelligence.defense import (
    DefenseVerdict,
    InjectionDefense,
)
from aetheros_memory_intelligence.retention import RetentionPolicy
from aetheros_memory_intelligence.write_pipeline import (
    WriteOutcome,
    WritePipeline,
)
from aetheros_memory_intelligence.retrieval import (
    RetrievalResult,
    SecureRetriever,
)
from aetheros_memory_intelligence.context_engine import ContextAssembler
from aetheros_memory_intelligence.manager import MemoryIntelligence
from aetheros_memory_intelligence.store import MemoryStore
from aetheros_memory_intelligence.record import (
    MemoryRecord,
    RecordType,
    RecordScope,
    PrivacyClass,
    ProvenanceKind,
    ConfidenceBand,
    RecordStatus,
    SCOPE_HIERARCHY,
    scope_visible,
)
from aetheros_memory_intelligence.layers import LAYERS, get_layer, layer_for_record
from aetheros_memory_intelligence.graph_store import (
    Entity,
    EntityType,
    Relationship,
    RelationType,
    GraphStore,
)
from aetheros_memory_intelligence.scoring import ScoringWeights, score_record
from aetheros_memory_intelligence.hybrid import HybridRetriever, RetrievalQuery
from aetheros_memory_intelligence.writer import (
    MemoryWriter,
    WriteRequest,
    ForgettingEngine,
    Consolidator,
    DreamingLoop,
    supersede,
)
from aetheros_memory_intelligence.service import MemoryService, RecordStore
from aetheros_memory_intelligence.events import EventBus, MemoryEvent
from aetheros_memory_intelligence.budget import MemoryBudgetManager
from aetheros_memory_intelligence.quality import run_quality_checks, MemoryMetrics

__all__ = [
    "MemoryIntelligenceConfig",
    "load_config",
    "MemoryBoundary",
    "MemoryOrigin",
    "MemoryState",
    "MemoryType",
    "TrustLevel",
    "VerificationLevel",
    "MemoryEntry",
    "MemoryEntryBuilder",
    "SchemaVersion",
    "validate_entry",
    "AccessContext",
    "BoundaryPolicy",
    "MemoryBoundaries",
    "ProvenanceRecord",
    "TrustModel",
    "DefenseVerdict",
    "InjectionDefense",
    "RetentionPolicy",
    "WriteOutcome",
    "WritePipeline",
    "RetrievalResult",
    "SecureRetriever",
    "ContextAssembler",
    "MemoryIntelligence",
    "MemoryStore",
    "MemoryRecord",
    "RecordType",
    "RecordScope",
    "PrivacyClass",
    "ProvenanceKind",
    "ConfidenceBand",
    "RecordStatus",
    "LAYERS",
    "Entity",
    "EntityType",
    "Relationship",
    "RelationType",
    "GraphStore",
    "ScoringWeights",
    "HybridRetriever",
    "RetrievalQuery",
    "MemoryWriter",
    "WriteRequest",
    "ForgettingEngine",
    "Consolidator",
    "DreamingLoop",
    "MemoryService",
    "EventBus",
    "MemoryBudgetManager",
]