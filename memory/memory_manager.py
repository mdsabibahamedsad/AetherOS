"""
Memory Manager — unified interface for the AetherOS Memory, Knowledge & Learning Engine.

The MemoryManager orchestrates all memory subsystems:

  ┌──────────────────────────────────────────────────┐
  │                  MemoryManager                    │
  │                                                    │
  │  Storage     │  Retrieval  │  Knowledge  │ Learn   │
  │  ─────────   │  ────────   │  ────────   │ ─────   │
  │  ShortTerm   │  Keyword    │  EntityIdx  │ Observe │
  │  LongTerm    │  Semantic   │  RelIdx     │ Reflect │
  │  Episodic    │  Graph      │  Knowledge  │ Improve │
  │  Semantic    │  Hybrid     │  Graph      │         │
  │  Procedural  │  Ranking    │             │         │
  │  Workspace   │             │             │         │
  │  Project     │             │             │         │
  ├──────────────┴─────────────┴─────────────┴─────────┤
  │  Retention │ GC │ Cache │ Export │ Import           │
  └────────────────────────────────────────────────────┘
              │
              ▼
    Existing Aetheros Systems
    (MemoryProvider, MemoryManager, MemoryStore, etc.)
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.cache import MemoryCache
from memory.embeddings import EmbeddingProvider, EmbeddingConfig
from memory.retrieval import RetrievalEngine, RetrievalResult
from memory.summarizer import Summarizer
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.episodic import EpisodicMemory, Episode
from memory.semantic import SemanticMemory, Fact
from memory.procedural import ProceduralMemory, Procedure
from memory.workspace_memory import WorkspaceMemory
from memory.project_memory import ProjectMemory
from memory.knowledge_graph import (
    KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
    NodeType, RelationType,
)
from memory.entity_index import EntityIndex, Entity
from memory.relationship_index import RelationshipIndex
from memory.learning_engine import LearningEngine, LearningSample
from memory.reflection import ReflectionEngine, Reflection
from memory.consolidation import ConsolidationEngine
from memory.ranking import RankingEngine
from memory.retention import RetentionEngine, RetentionPolicy
from memory.garbage_collection import GarbageCollector
from memory.exporters import MemoryExporter, ExportOptions
from memory.importers import MemoryImporter, ImportOptions, ImportResult

logger = logging.getLogger(__name__)


@dataclass
class UnifiedMemoryConfig:
    """Configuration for the unified memory system.

    Attributes:
        namespace: Global namespace for all memory types
        workspace_id: Default workspace ID
        project_id: Default project ID
        stm_capacity: Short-term memory capacity (entries)
        ltm_namespace: Long-term memory namespace
        auto_consolidate: Whether to run auto consolidation
        auto_gc: Whether to run garbage collection
        consolidation_interval: Auto-consolidation interval in minutes
        gc_interval: Auto-GC interval in minutes
        enable_learning: Whether learning engine is active
        enable_reflection: Whether reflection engine is active
        enable_knowledge_graph: Whether knowledge graph is active
        embedder: Embedding provider (None = use default)
        retention_policies: Custom retention policies
    """
    namespace: str = "default"
    workspace_id: str = "default"
    project_id: str = "default"
    stm_capacity: int = 200
    ltm_namespace: str = ""
    auto_consolidate: bool = True
    auto_gc: bool = True
    consolidation_interval: float = 30.0
    gc_interval: float = 30.0
    enable_learning: bool = True
    enable_reflection: bool = True
    enable_knowledge_graph: bool = True
    embedder: Optional[EmbeddingProvider] = None
    retention_policies: Optional[List[RetentionPolicy]] = None


class MemoryManager:
    """Unified interface for the entire AetherOS Memory System.

    Orchestrates all memory types, the knowledge graph, learning engine,
    reflection, consolidation, GC, and import/export.

    Usage:
        manager = MemoryManager()
        manager.initialize()

        # Memory operations
        manager.remember("user_pref", {"theme": "dark"}, memory_type="long_term")
        value = manager.recall("user_pref")
        results = manager.search("deployment")

        # Knowledge graph
        manager.add_knowledge_node("MyProject", NodeType.PROJECT)
        manager.add_relationship("A", "B", RelationType.DEPENDS_ON)

        # Learning
        manager.learn(category="tool_selection",
                      observation="web_search works best for fact lookup")

        # Reflection
        manager.reflect(goal="Build auth", outcome="success",
                        successes=["Implemented JWT"])

        # Export/Import
        manager.export_to_json("export.json")
        manager.import_from_file("import.json")

        # Maintenance
        manager.consolidate()
        manager.stats()
    """

    def __init__(self, config: Optional[UnifiedMemoryConfig] = None):
        self.config = config or UnifiedMemoryConfig()
        self._lock = threading.RLock()

        # Core storage
        self._store: Optional[MemoryStore] = None
        self._cache: Optional[MemoryCache] = None

        # Embedding provider
        self._embedder: Optional[EmbeddingProvider] = None

        # Memory types
        self.stm: Optional[ShortTermMemory] = None
        self.ltm: Optional[LongTermMemory] = None
        self.episodic: Optional[EpisodicMemory] = None
        self.semantic: Optional[SemanticMemory] = None
        self.procedural: Optional[ProceduralMemory] = None
        self.workspace: Optional[WorkspaceMemory] = None
        self.project: Optional[ProjectMemory] = None

        # Knowledge graph
        self.entity_index: Optional[EntityIndex] = None
        self.relationship_index: Optional[RelationshipIndex] = None
        self.knowledge_graph: Optional[KnowledgeGraph] = None

        # Retrieval
        self.retrieval: Optional[RetrievalEngine] = None
        self.ranking: Optional[RankingEngine] = None
        self.summarizer: Optional[Summarizer] = None

        # Learning & Reflection
        self.learning: Optional[LearningEngine] = None
        self.reflection: Optional[ReflectionEngine] = None

        # Maintenance
        self.consolidation: Optional[ConsolidationEngine] = None
        self.retention: Optional[RetentionEngine] = None
        self.gc: Optional[GarbageCollector] = None

        # Import/Export
        self.exporter: Optional[MemoryExporter] = None
        self.importer: Optional[MemoryImporter] = None

        # State
        self._initialized = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, store: Optional[MemoryStore] = None,
                   db_path: Optional[str] = None) -> bool:
        """Initialize the memory manager and all subsystems.

        Call this before using any memory operations.

        Args:
            store: Optional existing MemoryStore (creates one if None)
            db_path: Optional SQLite path for persistent storage

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        try:
            # 1. Core storage
            self._store = store or MemoryStore(db_path=db_path)
            self._cache = MemoryCache()

            # 2. Embedding provider
            self._embedder = self.config.embedder or EmbeddingProvider()
            self._embedder.initialize()

            # 3. Memory types
            self.stm = ShortTermMemory(
                self._store, capacity=self.config.stm_capacity,
                namespace=self.config.namespace,
            )
            self.ltm = LongTermMemory(
                self._store,
                namespace=self.config.ltm_namespace or self.config.namespace,
            )
            self.episodic = EpisodicMemory(self._store, namespace=self.config.namespace)
            self.semantic = SemanticMemory(self._store, namespace=self.config.namespace)
            self.procedural = ProceduralMemory(self._store, namespace=self.config.namespace)
            self.workspace = WorkspaceMemory(self._store, self.config.workspace_id)
            self.project = ProjectMemory(self._store, self.config.project_id)

            # 4. Knowledge graph (if enabled)
            if self.config.enable_knowledge_graph:
                self.entity_index = EntityIndex(self._store, namespace=self.config.namespace)
                self.relationship_index = RelationshipIndex(
                    self._store, namespace=self.config.namespace,
                )
                self.knowledge_graph = KnowledgeGraph(
                    self.entity_index, self.relationship_index, self._store,
                )
                self.knowledge_graph.sync()

            # 5. Retrieval & ranking
            self.retrieval = RetrievalEngine(
                self._store, embedder=self._embedder,
                knowledge_graph=self.knowledge_graph,
            )
            self.ranking = RankingEngine()
            self.summarizer = Summarizer()

            # 6. Learning & Reflection
            if self.config.enable_learning:
                self.learning = LearningEngine(
                    self._store, episodic_memory=self.episodic,
                    semantic_memory=self.semantic,
                    procedural_memory=self.procedural,
                    reflection_engine=self.reflection,
                )

            if self.config.enable_reflection:
                self.reflection = ReflectionEngine(
                    self._store, procedural_memory=self.procedural,
                    semantic_memory=self.semantic,
                )

            # 7. Maintenance
            self.retention = RetentionEngine()
            if self.config.retention_policies:
                for policy in self.config.retention_policies:
                    self.retention.add_policy(policy)

            self.consolidation = ConsolidationEngine(self._store, self.summarizer)
            self.gc = GarbageCollector(self._store, self.retention)

            # Wire GC promote callback
            def _promote_to_ltm(entry: MemoryEntry) -> None:
                if self.ltm:
                    self.ltm.store(
                        key=entry.key, value=entry.value,
                        tags=entry.tags, metadata=entry.metadata,
                        importance=entry.importance, source="gc_promotion",
                    )
            self.gc.set_promote_callback(_promote_to_ltm)

            # 8. Import/Export
            self.exporter = MemoryExporter(self._store)
            self.importer = MemoryImporter(self._store)

            # 9. Start background services
            if self.config.auto_consolidate:
                self.consolidation.start_auto(self.config.consolidation_interval)
            if self.config.auto_gc:
                self.gc.start_auto(self.config.gc_interval)

            self._initialized = True
            logger.info(
                "MemoryManager: initialized with %d memory types, KG=%s, "
                "learn=%s, reflect=%s",
                self._count_memory_types(),
                self.config.enable_knowledge_graph,
                self.config.enable_learning,
                self.config.enable_reflection,
            )
            return True

        except Exception as exc:
            logger.error("MemoryManager: initialization failed: %s", exc)
            return False

    def _count_memory_types(self) -> int:
        """Count how many memory type modules are available."""
        return sum(1 for m in [
            self.stm, self.ltm, self.episodic, self.semantic,
            self.procedural, self.workspace, self.project,
        ] if m is not None)

    # ------------------------------------------------------------------
    # Core memory operations (convenience)
    # ------------------------------------------------------------------

    def remember(self, key: str, value: Any,
                 memory_type: str = "long_term",
                 scope: MemoryScope = MemoryScope.GLOBAL,
                 namespace: str = "",
                 tags: List[str] = None,
                 importance: float = 0.5,
                 ttl: Optional[float] = None) -> MemoryEntry:
        """Store a memory using the most appropriate memory type.

        Convenience method that routes to the correct subsystem
        based on memory_type.

        Args:
            key: Memory key
            value: Memory value
            memory_type: short_term, long_term, episodic, semantic,
                        procedural, workspace, project
            scope: Visibility scope
            namespace: Additional namespace
            tags: Categorization tags
            importance: Importance score (0.0 - 1.0)
            ttl: Time-to-live in seconds (for short_term)

        Returns:
            The stored MemoryEntry
        """
        if not self._initialized:
            raise RuntimeError("MemoryManager not initialized. Call initialize() first.")

        if memory_type == "short_term" and self.stm:
            return self.stm.add(key, value, tags=tags, importance=importance, ttl=ttl or 3600)
        elif memory_type == "long_term" and self.ltm:
            return self.ltm.store(key, value, tags=tags, importance=importance)
        elif memory_type == "workspace" and self.workspace:
            return self.workspace.set(key, value, tags=tags, importance=importance)
        elif memory_type == "project" and self.project:
            return self.project.set(key, value, tags=tags, importance=importance)
        else:
            # Fall back to direct store
            return self._store.save(
                key=key, value=value, memory_type=memory_type,
                scope=scope, namespace=namespace,
                tags=tags or [], importance=importance,
                source="memory_manager",
            )

    def recall(self, key: str,
              memory_type: str = "long_term") -> Any:
        """Recall a value from the most appropriate memory type.

        Searches long_term, short_term, workspace, project in that order
        by default, or restricts to a specific memory type.

        Args:
            key: The key to recall
            memory_type: Optional restriction to a specific memory type

        Returns:
            The stored value, or None if not found
        """
        if not self._initialized:
            raise RuntimeError("MemoryManager not initialized.")

        # Check specific type
        if memory_type == "short_term" and self.stm:
            return self.stm.get(key)
        elif memory_type == "long_term" and self.ltm:
            return self.ltm.recall(key)
        elif memory_type == "workspace" and self.workspace:
            return self.workspace.get(key)
        elif memory_type == "project" and self.project:
            return self.project.get(key)

        # Fall through all types
        for mem in [self.ltm, self.stm, self.workspace, self.project]:
            if mem:
                try:
                    if hasattr(mem, "get"):
                        result = mem.get(key)
                    elif hasattr(mem, "recall"):
                        result = mem.recall(key)
                    else:
                        continue
                    if result is not None:
                        return result
                except Exception:
                    continue

        return None

    def forget(self, key: str,
               memory_type: str = "") -> bool:
        """Delete a memory by key.

        Args:
            key: The key to delete
            memory_type: Optional restriction to a specific memory type

        Returns:
            True if the entry was found and deleted
        """
        if memory_type == "short_term" and self.stm:
            return self.stm.delete(key)
        elif memory_type == "long_term" and self.ltm:
            return self.ltm.forget(key)
        elif memory_type == "workspace" and self.workspace:
            return self.workspace.delete(key)
        elif memory_type == "project" and self.project:
            return self.project.delete(key)

        # Search all types — try both 'delete' and 'forget' methods
        for mem in [self.ltm, self.stm, self.workspace, self.project]:
            if not mem:
                continue
            # Try 'delete' method first
            if hasattr(mem, "delete"):
                try:
                    if mem.delete(key):
                        return True
                except Exception:
                    pass
            # Then try 'forget' method
            if hasattr(mem, "forget"):
                try:
                    if mem.forget(key):
                        return True
                except Exception:
                    pass

        return False

    # ------------------------------------------------------------------
    # Search / Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str = "",
               memory_type: Optional[str] = None,
               limit: int = 20,
               include_semantic: bool = True,
               include_graph: bool = True) -> List[RetrievalResult]:
        """Unified search across all memory types.

        Uses the hybrid retrieval engine (keyword + semantic + graph).

        Args:
            query: Search query
            memory_type: Filter by memory type
            limit: Maximum results
            include_semantic: Include embedding-based search
            include_graph: Include knowledge graph traversal

        Returns:
            Ranked list of RetrievalResult
        """
        if not self._initialized or not self.retrieval:
            return []

        return self.retrieval.search(
            query=query, memory_type=memory_type, limit=limit,
            include_semantic=include_semantic,
            include_graph=include_graph,
        )

    def search_facts(self, query: str, limit: int = 20) -> List[Fact]:
        """Search semantic memory for facts."""
        if not self.semantic:
            return []
        return self.semantic.search(query, limit=limit)

    def search_episodes(self, query: str, limit: int = 20) -> List[Episode]:
        """Search episodic memory for episodes."""
        if not self.episodic:
            return []
        return self.episodic.find_similar(query, limit=limit)

    def search_procedures(self, query: str, limit: int = 10) -> List[Procedure]:
        """Search procedural memory for procedures."""
        if not self.procedural:
            return []
        return self.procedural.find_by_context(query, limit=limit)

    # ------------------------------------------------------------------
    # Knowledge Graph
    # ------------------------------------------------------------------

    def add_knowledge_node(self, name: str,
                           node_type: NodeType = NodeType.ENTITY,
                           description: str = "",
                           importance: float = 0.5) -> Optional[KnowledgeNode]:
        """Add a node to the knowledge graph."""
        if not self.knowledge_graph:
            return None
        return self.knowledge_graph.add_node(
            name=name, node_type=node_type,
            description=description, importance=importance,
        )

    def add_relationship(self, source_id: str, target_id: str,
                         relation_type: RelationType = RelationType.RELATED_TO,
                         weight: float = 1.0) -> Optional[KnowledgeRelation]:
        """Add a relationship between two knowledge graph nodes."""
        if not self.knowledge_graph:
            return None
        return self.knowledge_graph.add_relation(
            source_id=source_id, target_id=target_id,
            relation_type=relation_type, weight=weight,
        )

    def get_subgraph(self, center_id: str,
                     depth: int = 2) -> Dict[str, Any]:
        """Extract a subgraph centered on a node."""
        if not self.knowledge_graph:
            return {"nodes": [], "edges": []}
        return self.knowledge_graph.get_subgraph(center_id, depth=depth)

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """Find the shortest path between two nodes."""
        if not self.knowledge_graph:
            return None
        return self.knowledge_graph.find_path(from_id, to_id)

    def register_entity(self, name: str, entity_type: str = "concept",
                        description: str = "",
                        source: str = "") -> Optional[Entity]:
        """Register an entity in the entity index."""
        if not self.entity_index:
            return None
        return self.entity_index.register(
            name=name, entity_type=entity_type,
            description=description, source=source,
        )

    # ------------------------------------------------------------------
    # Learning & Reflection
    # ------------------------------------------------------------------

    def learn(self, category: str, observation: str,
              outcome: str = "success",
              confidence: float = 0.7,
              context: str = "") -> None:
        """Record a learning observation."""
        if not self.learning:
            return
        self.learning.observe(LearningSample(
            category=category, observation=observation,
            outcome=outcome, confidence=confidence, context=context,
        ))

    def reflect(self, goal: str, outcome: str,
                successes: List[str] = None,
                failures: List[str] = None,
                lessons: List[str] = None,
                duration_seconds: float = 0.0,
                task_count: int = 0) -> Optional[Reflection]:
        """Record a reflection on a completed workflow."""
        if not self.reflection:
            return None
        return self.reflection.reflect_on_workflow(
            goal=goal, outcome=outcome,
            successes=successes, failures=failures,
            lessons=lessons, duration_seconds=duration_seconds,
            task_count=task_count,
        )

    def get_insights(self, category: str = "",
                     limit: int = 20) -> List[Dict[str, Any]]:
        """Get learning insights, optionally filtered by category."""
        if not self.learning:
            return []
        return self.learning.get_insights(category=category, limit=limit)

    def get_lessons(self, limit: int = 50) -> List[str]:
        """Get all recorded lessons from reflections."""
        if not self.reflection:
            return []
        return self.reflection.get_lessons(limit=limit)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def consolidate(self) -> Dict[str, Any]:
        """Run a full consolidation cycle."""
        if not self.consolidation:
            return {"error": "Consolidation not available"}
        return self.consolidation.consolidate()

    def run_gc(self) -> Dict[str, Any]:
        """Run garbage collection."""
        if not self.gc:
            return {"error": "GC not available"}
        return self.gc.run()

    def summarize(self, text: str, max_chars: int = 500,
                  style: str = "paragraph") -> str:
        """Generate a summary of the given text."""
        if not self.summarizer:
            return text[:max_chars]
        return self.summarizer.summarize(text, max_chars=max_chars, style=style)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_to_json(self, output_path: Optional[str] = None) -> str:
        """Export all memory to JSON format."""
        if not self.exporter:
            return ""
        return self.exporter.to_json(output_path=output_path)

    def export_to_markdown(self, output_path: Optional[str] = None) -> str:
        """Export all memory to Markdown format."""
        if not self.exporter:
            return ""
        return self.exporter.to_markdown(output_path=output_path)

    def export_to_csv(self, output_path: Optional[str] = None) -> str:
        """Export all memory to CSV format."""
        if not self.exporter:
            return ""
        return self.exporter.to_csv(output_path=output_path)

    def import_from_file(self, file_path: str,
                         options: Optional[ImportOptions] = None) -> ImportResult:
        """Import memory from a file."""
        if not self.importer:
            return ImportResult(errors=1, error_messages=["Importer not available"])
        return self.importer.import_from_file(file_path, options=options)

    def import_from_json(self, json_str: str) -> ImportResult:
        """Import memory from JSON string."""
        if not self.importer:
            return ImportResult(errors=1, error_messages=["Importer not available"])
        return self.importer.import_from_json(json_str)

    # ------------------------------------------------------------------
    # Status & Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics."""
        store_stats = self._store.stats() if self._store else {}
        cache_stats = self._cache.stats() if self._cache else {}

        stats = {
            "initialized": self._initialized,
            "store": store_stats,
            "cache": cache_stats,
            "memory_types": {
                "short_term": self.stm.count() if self.stm else 0,
                "long_term": self.ltm.count() if self.ltm else 0,
                "episodic": self.episodic.count() if self.episodic else 0,
                "semantic": self.semantic.count() if self.semantic else 0,
                "procedural": self.procedural.count() if self.procedural else 0,
                "workspace": self.workspace.count() if self.workspace else 0,
                "project": self.project.count() if self.project else 0,
            },
        }

        if self.knowledge_graph:
            stats["knowledge_graph"] = self.knowledge_graph.stats()

        if self.learning:
            stats["learning"] = self.learning.get_stats()

        if self.reflection:
            stats["reflection"] = self.reflection.get_stats()

        if self.consolidation:
            stats["consolidation"] = self.consolidation.get_stats()

        if self.gc:
            stats["gc"] = self.gc.get_stats()

        if self.retrieval:
            stats["retrieval"] = self.retrieval.stats()

        return stats

    def status(self) -> str:
        """Return a human-readable status string."""
        s = self.stats()
        lines = [
            "Memory System Status",
            "====================",
            f"  Initialized: {s['initialized']}",
            f"  Total entries: {sum(s['memory_types'].values())}",
            f"  Cache: {s['cache'].get('size', 0)} entries ({s['cache'].get('hit_ratio', 0):.0%} hit ratio)",
        ]

        for mtype, count in s.get("memory_types", {}).items():
            if count > 0:
                lines.append(f"  {mtype}: {count}")

        if "knowledge_graph" in s:
            kg = s["knowledge_graph"]
            lines.append(f"  Knowledge Graph: {kg.get('nodes', 0)} nodes, "
                        f"{kg.get('edges', 0)} edges")

        if "learning" in s:
            l = s["learning"]
            lines.append(f"  Learning: {l.get('total_samples', 0)} samples")

        if "reflection" in s:
            r = s["reflection"]
            lines.append(f"  Reflections: {r.get('total_reflections', 0)} "
                        f"({r.get('successes', 0)} successes, "
                        f"{r.get('failures', 0)} failures)")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Cleanly shut down all memory subsystems."""
        logger.info("MemoryManager: shutting down...")

        # Stop background services
        if self.consolidation:
            self.consolidation.stop_auto()
        if self.gc:
            self.gc.stop_auto()
        if self._embedder:
            self._embedder.clear_cache()
        if self._cache:
            self._cache.clear()

        self._initialized = False

        # Load from SQLite if available
        if self._store:
            try:
                self._store.load_from_sqlite()
            except Exception:
                pass

        logger.info("MemoryManager: shutdown complete")

    def clear_all(self) -> int:
        """Clear all memory across all types. Returns total cleared."""
        count = 0
        for mem in [self.stm, self.ltm, self.episodic,
                    self.semantic, self.procedural]:
            if mem and hasattr(mem, "clear"):
                count += mem.clear()
        if self.workspace:
            count += self.workspace.clear()
        if self.project:
            count += self.project.clear()
        if self.entity_index:
            count += self.entity_index.clear()
        if self.relationship_index:
            count += self.relationship_index.clear()
        if self.knowledge_graph:
            self.knowledge_graph.clear()
        if self._cache:
            self._cache.clear()
        return count
