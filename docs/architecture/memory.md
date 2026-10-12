# AetherOS Memory, Knowledge & Learning Engine

## Architecture

The memory system is the **cognitive layer** of the AetherOS operating system. It provides a unified, modular system that enables AetherOS to remember, organize, retrieve, summarize, learn, and improve across conversations, projects, and autonomous workflows.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MemoryManager (Unified API)                    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Storage Layer                           │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │    │
│  │  │ShortTerm │ │LongTerm  │ │Episodic  │ │Semantic      │ │    │
│  │  │(Working) │ │(Durable) │ │(Events)  │ │(Facts)       │ │    │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │    │
│  │  │Procdural│ │Workspace │ │Project   │ │Cache/Store   │ │    │
│  │  │(How-to) │ │(Scoped)  │ │(Scoped)  │ │(Backend)     │ │    │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Knowledge Layer                          │    │
│  │  ┌──────────┐ ┌────────────────┐ ┌────────────────────┐ │    │
│  │  │Entity    │ │Relationship    │ │KnowledgeGraph      │ │    │
│  │  │Index     │ │Index           │ │(Unified Graph)     │ │    │
│  │  └──────────┘ └────────────────┘ └────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Intelligence Layer                       │    │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐  │    │
│  │  │Retrieval │ │Learning      │ │Reflection          │  │    │
│  │  │Engine    │ │Engine        │ │Engine              │  │    │
│  │  └──────────┘ └──────────────┘ └────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Lifecycle Layer                         │    │
│  │  ┌──────────┐ ┌────────────┐ ┌──────┐ ┌───────┐       │    │
│  │  │Retention │ │Consolidation│ │GC   │ │Export │       │    │
│  │  │Policies  │ │Engine       │ │     │ │Import │       │    │
│  │  └──────────┘ └────────────┘ └──────┘ └───────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Existing Aetheros      │
        │  Systems                │
        │  (MemoryProvider,       │
        │   MemoryManager,        │
        │   SessionDB, etc.)      │
        └─────────────────────────┘
```

## Module Responsibilities

### Storage Layer

| Module | Responsibility |
|--------|---------------|
| `memory_store.py` | Core CRUD backend with in-memory + SQLite persistence. Handles scoping, indexing, and entry lifecycle. |
| `short_term.py` | Ephemeral working memory with limited capacity (100 entries default). LRU eviction. Auto-expiry (1h TTL). |
| `long_term.py` | Durable memory that survives across sessions. Entries are promoted from STM or created directly. |
| `episodic.py` | Records experiences as `Episode` objects with temporal context, action, outcome. Supports timeline retrieval. |
| `semantic.py` | Stores structured facts as (subject, predicate, object) triples with confidence scores. |
| `procedural.py` | Captures how-to knowledge, strategies, and procedures. Tracks success rates per procedure. |
| `workspace_memory.py` | Workspace-scoped memory. Each workspace is an isolated namespace. |
| `project_memory.py` | Project-scoped memory. Persists across workspace sessions. Includes decision records. |
| `cache.py` | In-memory LRU cache with TTL. Provides fast access to frequently used entries. |
| `embeddings.py` | Generates vector embeddings using local models or API. Falls back to hash-based embeddings. |

### Knowledge Layer

| Module | Responsibility |
|--------|---------------|
| `entity_index.py` | Extracts and indexes entities from text (classes, functions, people, APIs, etc.). Pattern-based extraction. |
| `relationship_index.py` | Manages typed relationships between entities (depends_on, contains, imports, etc.). BFS path finding. |
| `knowledge_graph.py` | Unified graph connecting entities and relationships. Supports subgraph extraction, path finding, and connected component analysis. |

### Intelligence Layer

| Module | Responsibility |
|--------|---------------|
| `retrieval.py` | Hybrid retrieval combining keyword, semantic (embedding), and graph traversal. Weighted scoring with recency boost. |
| `ranking.py` | Configurable relevance ranking using importance, recency, frequency, and tag match signals. |
| `summarizer.py` | Extractive text summarization with sentence scoring. Configurable LLM-based summarizer. |
| `learning_engine.py` | Continuous learning from tool results, agent outcomes, user corrections. Feeds insights to episodic, semantic, procedural memory. |
| `reflection.py` | Post-workflow analysis. Records lessons, updates procedural memory with strategies and anti-patterns. |

### Lifecycle Layer

| Module | Responsibility |
|--------|---------------|
| `retention.py` | Configurable policies (TTL, importance threshold, max entries). 6 built-in policies for different memory types. |
| `consolidation.py` | Merges duplicates, compresses large conversations, promotes important STM to LTM. Auto-consolidation on timer. |
| `garbage_collection.py` | Applies retention policies, removes expired entries, archives inactive memory. Auto-GC on timer. |
| `exporters.py` | Exports memory to JSON, Markdown, CSV, and YAML formats with versioned metadata. |
| `importers.py` | Imports from JSON (AetherOS format), SQLite, Markdown, and CSV with validation. |

### Unified Interface

| Module | Responsibility |
|--------|---------------|
| `memory_manager.py` | `MemoryManager` — single entry point for all memory operations. Initializes, orchestrates, and wires all subsystems. Exposes high-level `remember()`, `recall()`, `search()`, `learn()`, `reflect()`, `export()`, `import()`, and `stats()` APIs. |
| `__init__.py` | Public API exports for all modules. |

## Memory Lifecycle

```
Input → ShortTerm (STM) → Consolidation → LongTerm (LTM) → Archive/Delete
         │                   │
         │  High importance  │  Retention policy
         ▼                   ▼
     Immediate recall    Knowledge Graph sync
```

1. **Creation**: Memory enters via `remember()` → routed to the appropriate type
2. **Short-term**: Lives in STM with 1h TTL. Evicted by LRU when over capacity
3. **Consolidation**: Periodic cycles merge duplicates, compress large entries, promote important STM to LTM
4. **Long-term**: Durable storage. Retention policies determine when to archive or delete
5. **Knowledge Graph**: Entities and relationships extracted from memory entries populate the graph
6. **Learning**: Tool results, agent outcomes, and user corrections feed the learning engine
7. **Reflection**: After workflows, reflection records lessons and updates procedural memory
8. **GC**: Periodic garbage collection applies retention policies and removes expired entries
9. **Export/Import**: Memory can be exported to JSON/Markdown/CSV and re-imported later

## Data Flow

### Retrieval Pipeline

```
Query → RetrievalEngine
         ├── Keyword search (MemoryStore substring match)
         ├── Semantic search (EmbeddingProvider cosine similarity)
         └── Graph traversal (KnowledgeGraph related entities)
              ↓
         Merge results → Weighted scoring → Recency boost
              ↓
         Ranked RetrievalResults (deduplicated, sorted by score)
```

### Learning Flow

```
Observation → LearningEngine → EpisodicMemory (record episode)
                               SemanticMemory (learn fact)
                               ProceduralMemory (record procedure)
                               ReflectionEngine (trigger reflection)
                                    ↓
                               Insights available for planning
```

### Reflection Flow

```
Workflow Complete → ReflectionEngine → Store reflection
                     ├── Update procedural memory (strategies)
                     ├── Update semantic memory (lessons)
                     └── Notify hooks (learning engine)
```

## Extension Guide

### Adding a New Memory Type

1. Create a new module in `memory/` (e.g., `memory/social_memory.py`)
2. Implement it using `MemoryStore` as the backend
3. Add the module to `memory/__init__.py` exports
4. Wire it into `UnifiedMemoryConfig` and `MemoryManager.__init__()`

Example:
```python
# memory/social_memory.py
class SocialMemory:
    def __init__(self, store: MemoryStore):
        self._store = store
    
    def remember_user(self, user_id: str, preferences: dict):
        self._store.save(key=f"user:{user_id}", value=preferences, ...)
    
    def recall_user(self, user_id: str):
        return self._store.get_by_key(f"user:{user_id}", ...)

# In memory_manager.py:
self.social = SocialMemory(self._store)
```

### Adding a Custom Retention Policy

```python
from memory.retention import RetentionPolicy, RetentionAction

manager.retention.add_policy(RetentionPolicy(
    name="my_policy",
    memory_types=["long_term"],
    max_age_days=30.0,
    min_importance=0.5,
    action=RetentionAction.ARCHIVE,
))
```

### Plugin Integration

Plugins can register their own memory providers via the existing `MemoryProvider` ABC
and interact with the memory system through `MemoryManager`:

```python
# plugin.py
def register(ctx):
    from memory import get_memory_manager
    mm = get_memory_manager()
    mm.remember("plugin:config", my_config, memory_type="long_term")
    previous = mm.recall("plugin:config")
```

Or they can implement `MemoryProvider` for the existing Aetheros memory pipeline
(see `plugins/memory/` for examples).

## Migration Guide

### From Legacy Aetheros Memory

The existing `MemoryManager` (in `agent/memory_manager.py`) and `MemoryProvider`
ABC continue to work. The new memory system extends — not replaces — them.

To migrate existing memory:

```python
from memory.importers import MemoryImporter, ImportOptions
from memory.memory_store import MemoryStore

store = MemoryStore(db_path="aetheros_memory.db")
importer = MemoryImporter(store)
result = importer.import_from_file("legacy_export.json")
print(f"Imported {result.imported} entries")
```

To export for use elsewhere:

```python
from memory.exporters import MemoryExporter, ExportOptions

exporter = MemoryExporter(store)
exporter.to_json("export.json")
```

## Design Principles

1. **Extends, never replaces**: The new memory system integrates with existing
   `MemoryProvider`, `MemoryManager`, and `SessionDB` infrastructure.
2. **Backward compatible**: All existing memory APIs continue to work unchanged.
3. **Plugin-based extensibility**: New memory providers, embedding providers,
   retrievers, and knowledge graph extensions register through plugins.
4. **Privacy and isolation**: Memory is scoped by namespace, scope, and type.
   Workspace and project isolation enforced at the storage layer.
5. **Lazy loading**: Memory entries are loaded on demand. Large values and
   embeddings are cached after first access.
6. **No vendor lock-in**: Embedding providers, storage backends, and summarization
   can be swapped without changing the system architecture.
7. **Type hints throughout**: Every public API is fully typed.
8. **Comprehensive logging**: All subsystems log at appropriate levels.

## Memory Types Summary

| Memory Type | Duration | Capacity | Scope | Use Case |
|------------|----------|----------|-------|----------|
| Short-term | 1 hour | 100 entries | Conversation | Immediate context |
| Long-term | Forever | Unlimited | Global | Important facts |
| Episodic | 30 days | Unlimited | Global | Experiences |
| Semantic | Forever | Unlimited | Global | Structured facts |
| Procedural | Forever | Unlimited | Global | How-to knowledge |
| Workspace | Workspace lifetime | 1000 entries | Workspace | Workspace context |
| Project | Project lifetime | 1000 entries | Project | Project context |

## Security Model

- **Workspace isolation**: Each workspace has its own `namespace` prefix. Queries
  from one workspace cannot see another workspace's entries.
- **Project isolation**: Project memory is similarly namespace-isolated.
- **Scope gating**: `MemoryScope` enum controls visibility (GLOBAL, WORKSPACE,
  PROJECT, CONVERSATION, USER, etc.).
- **Permission-aware**: Integration with kernel `PermissionManager` via
  `MemoryManager` — all `recall()` and `search()` calls pass through permission
  checking when the kernel is active.
- **Audit logging**: All memory mutations are logged with source, timestamp, and
  operation type.
