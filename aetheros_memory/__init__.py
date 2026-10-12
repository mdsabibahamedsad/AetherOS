"""AetherOS Memory, Knowledge Graph & RAG Engine.

Production-grade memory platform with embeddings, vector search,
knowledge graphs, multi-stage RAG, context retrieval, memory editing,
research library, code intelligence, and workspace intelligence.
"""

from aetheros_memory.embedding_engine import (
    EmbeddingEngine, EmbeddingProvider, EmbeddingConfig,
    OpenAIEmbedder, GeminiEmbedder, CohereEmbedder,
    JinaEmbedder, VoyageEmbedder, LocalEmbedder,
)
from aetheros_memory.vector_database import (
    VectorDatabase, VectorDBConfig, VectorDBType, SearchResult,
    SQLiteVecBackend, LanceDBBackend, ChromaBackend,
    QdrantBackend, FAISSBackend,
)
from aetheros_memory.knowledge_graph import (
    KnowledgeGraph, GraphEntity, GraphRelationship,
    EntityType, RelationshipType, GraphQuery,
)
from aetheros_memory.memory_manager import (
    MemoryManager, MemoryManagerConfig, MemoryCategory, MemoryStats,
    BackupManifest, ArchiveEntry,
)
from aetheros_memory.memory_pipeline import (
    MemoryPipeline, PipelineConfig, Fact,
    Category, ExtractedFact,
)
from aetheros_memory.rag_pipeline import (
    RAGPipeline, RAGConfig, RAGResult,
    QueryExpansion, RetrievedContext,
)
from aetheros_memory.context_retrieval import (
    ContextRetrieval, RetrievalConfig, RetrievalBundle,
)
from aetheros_memory.memory_ranking import (
    MemoryRanking, RankingConfig, RankedMemory,
    ScoringFactor,
)
from aetheros_memory.memory_editor import (
    MemoryEditor, EditOperation, EditResult,
    MergeResult,
)
from aetheros_memory.research_library import (
    ResearchLibrary, ResearchSession, ResearchSource,
    ResearchCollection, SourceType,
)
from aetheros_memory.code_intelligence import (
    CodeIntelligence, CodeEntity, CodeRelationship,
    CodeEntityType, ArchitecturePattern,
)
from aetheros_memory.workspace_intelligence import (
    WorkspaceIntelligence, WorkspaceKnowledge,
    Goal, PinnedDocument,
)
from aetheros_memory.automatic_summarization import (
    AutomaticSummarization, SummarizationConfig,
    SummaryResult, CompressionLevel,
)
from aetheros_memory.memory_permissions import (
    MemoryPermissions, PermissionLevel,
    PermissionEntry, AccessControl,
)
from aetheros_memory.memory_visualization import (
    MemoryVisualization, GraphLayout, TimelineEntry,
    CollectionEntry, VisualizationData,
)
from aetheros_memory.performance import (
    MemoryPerformance, BackgroundIndexer,
    CacheLayer, BatchProcessor,
    CompactionEngine,
)

__all__ = [
    "EmbeddingEngine", "EmbeddingProvider", "EmbeddingConfig",
    "OpenAIEmbedder", "GeminiEmbedder", "CohereEmbedder",
    "JinaEmbedder", "VoyageEmbedder", "LocalEmbedder",
    "VectorDatabase", "VectorDBConfig", "VectorDBType", "SearchResult",
    "SQLiteVecBackend", "LanceDBBackend", "ChromaBackend",
    "QdrantBackend", "FAISSBackend",
    "KnowledgeGraph", "GraphEntity", "GraphRelationship",
    "EntityType", "RelationshipType", "GraphQuery",
    "MemoryManager", "MemoryManagerConfig", "MemoryCategory", "MemoryStats",
    "BackupManifest", "ArchiveEntry",
    "MemoryPipeline", "PipelineConfig", "Fact",
    "Category", "ExtractedFact",
    "RAGPipeline", "RAGConfig", "RAGResult",
    "QueryExpansion", "RetrievedContext",
    "ContextRetrieval", "RetrievalConfig", "RetrievalBundle",
    "MemoryRanking", "RankingConfig", "RankedMemory",
    "ScoringFactor",
    "MemoryEditor", "EditOperation", "EditResult",
    "MergeResult",
    "ResearchLibrary", "ResearchSession", "ResearchSource",
    "ResearchCollection", "SourceType",
    "CodeIntelligence", "CodeEntity", "CodeRelationship",
    "CodeEntityType", "ArchitecturePattern",
    "WorkspaceIntelligence", "WorkspaceKnowledge",
    "Goal", "PinnedDocument",
    "AutomaticSummarization", "SummarizationConfig",
    "SummaryResult", "CompressionLevel",
    "MemoryPermissions", "PermissionLevel",
    "PermissionEntry", "AccessControl",
    "MemoryVisualization", "GraphLayout", "TimelineEntry",
    "CollectionEntry", "VisualizationData",
    "MemoryPerformance", "BackgroundIndexer",
    "CacheLayer", "BatchProcessor", "CompactionEngine",
]