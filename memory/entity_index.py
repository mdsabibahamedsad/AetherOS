"""
Entity Index — extracts and indexes entities from memory content.

Automatically identifies classes, functions, packages, repositories,
people, organizations, models, APIs, documents, tasks, and other entities.
Stores entity metadata and relationships for graph traversal.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)

# Entity type constants
ENTITY_TYPE_CLASS = "class"
ENTITY_TYPE_FUNCTION = "function"
ENTITY_TYPE_PACKAGE = "package"
ENTITY_TYPE_REPOSITORY = "repository"
ENTITY_TYPE_PERSON = "person"
ENTITY_TYPE_ORGANIZATION = "organization"
ENTITY_TYPE_MODEL = "model"
ENTITY_TYPE_API = "api"
ENTITY_TYPE_DOCUMENT = "document"
ENTITY_TYPE_TASK = "task"
ENTITY_TYPE_CONCEPT = "concept"
ENTITY_TYPE_TOOL = "tool"
ENTITY_TYPE_PROJECT = "project"
ENTITY_TYPE_FILE = "file"
ENTITY_TYPE_PLUGIN = "plugin"


@dataclass
class Entity:
    """A named entity extracted from memory content.

    Attributes:
        id: Unique entity ID
        name: Entity name
        type: Entity type (class, function, package, etc.)
        aliases: Alternative names for this entity
        description: Description of the entity
        source: Where this entity was found
        metadata: Additional metadata
        confidence: Extraction confidence (0.0 - 1.0)
        first_seen: When first seen
        last_seen: When last seen
        mention_count: How many times mentioned
        tags: Categorization tags
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    type: str = ENTITY_TYPE_CONCEPT
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.7
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    mention_count: int = 1
    tags: List[str] = field(default_factory=list)


# Patterns for entity extraction
_ENTITY_PATTERNS = {
    ENTITY_TYPE_CLASS: [
        r"class\s+(\w+)",
        r"(?:new\s+)(\w+)(?:\s*\(|\s+instance)",
    ],
    ENTITY_TYPE_FUNCTION: [
        r"def\s+(\w+)\s*\(",
        r"function\s+(\w+)\s*\(",
        r"(?:async\s+)?function\s+(\w+)\s*\(",
    ],
    ENTITY_TYPE_PACKAGE: [
        r"(?:import|from)\s+(\w+(?:\.\w+)*)",
        r"(?:require|using)\s+['\"](\w+(?:[/-]\w+)*)['\"]",
    ],
    ENTITY_TYPE_API: [
        r"(?:GET|POST|PUT|DELETE|PATCH)\s+(/\S+)",
        r"api(?:\.|\s*)(\w+)",
    ],
    ENTITY_TYPE_REPOSITORY: [
        r"(?:github\.com|gitlab\.com|bitbucket\.org)/([\w.-]+/[\w.-]+)",
    ],
    ENTITY_TYPE_FILE: [
        r"(?:open|read|write|create)\s+['\"]([\w./\\-]+\.[\w]+)['\"]",
    ],
    ENTITY_TYPE_TASK: [
        r"(?:TODO|FIXME|HACK|XXX)\s*:\s*(.+)",
    ],
    ENTITY_TYPE_PERSON: [
        r"@(\w+)",
        r"(?:author|by|credit)\s*:\s*(\w+\s+\w+)",
    ],
}


class EntityIndex:
    """Extracts, indexes, and manages entities from memory content.

    Automatically scans memory content for known entity patterns and
    maintains an index of all discovered entities with metadata.

    Usage:
        index = EntityIndex(store)
        index.extract_from_text("def hello_world(): pass")
        entities = index.search("hello_world")
        entities_by_type = index.get_by_type("function")
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"entity:{id(self)}"
        self._lock = threading.RLock()
        # In-memory cache for fast lookups
        self._entities: Dict[str, Entity] = {}

    # ------------------------------------------------------------------
    # Entity registration
    # ------------------------------------------------------------------

    def register(self, name: str, entity_type: str,
                 description: str = "",
                 aliases: List[str] = None,
                 source: str = "",
                 confidence: float = 0.7,
                 metadata: Dict[str, Any] = None,
                 tags: List[str] = None) -> Entity:
        """Register or update an entity."""
        normalized_name = name.strip()

        # Check for existing entity
        existing = self._find_by_name(normalized_name)
        if existing:
            existing.last_seen = time.time()
            existing.mention_count += 1
            existing.confidence = max(existing.confidence, confidence)
            if description and not existing.description:
                existing.description = description
            if aliases:
                existing.aliases.extend(a for a in aliases if a not in existing.aliases)
            entity = existing
        else:
            entity = Entity(
                name=normalized_name,
                type=entity_type,
                aliases=aliases or [],
                description=description,
                source=source,
                confidence=confidence,
                metadata=metadata or {},
                tags=tags or [],
            )
            self._entities[entity.id] = entity

        # Persist
        self._store.save(
            key=f"entity:{entity.id}",
            value=entity,
            memory_type="entity",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=[entity_type] + entity.tags,
            metadata={
                "name": entity.name,
                "type": entity.type,
                "confidence": entity.confidence,
                "mention_count": entity.mention_count,
            },
            importance=min(0.5 + entity.confidence * 0.3, 1.0),
            source=f"entity:{source}" if source else "entity",
        )
        return entity

    def register_entity(self, entity: Entity) -> Entity:
        """Register a pre-built Entity object."""
        return self.register(
            entity.name, entity.type,
            description=entity.description,
            aliases=entity.aliases, source=entity.source,
            confidence=entity.confidence, metadata=entity.metadata,
            tags=entity.tags,
        )

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def extract_from_text(self, text: str, source: str = "") -> List[Entity]:
        """Extract entities from text using pattern matching.

        Scans text for known entity patterns and registers any
        discovered entities.

        Returns list of newly discovered entities.
        """
        if not text:
            return []

        discovered = []
        for entity_type, patterns in _ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    name = match.group(1).strip()
                    if len(name) > 1 and not self._is_common_word(name):
                        entity = self.register(
                            name=name, entity_type=entity_type,
                            source=source, confidence=0.6,
                        )
                        if entity not in discovered:
                            discovered.append(entity)
        return discovered

    def extract_from_entity(self, entity_id: str) -> List[Entity]:
        """Extract entities from an existing entity's description."""
        entity = self.get(entity_id)
        if not entity or not entity.description:
            return []
        return self.extract_from_text(entity.description, source=entity.name)

    def extract_from_entry(self, entry: MemoryEntry) -> List[Entity]:
        """Extract entities from a memory entry."""
        entities = []
        # Extract from key
        entities.extend(self.extract_from_text(entry.key, source=entry.key))
        # Extract from string values
        if isinstance(entry.value, str):
            entities.extend(self.extract_from_text(entry.value, source=entry.key))
        elif isinstance(entry.value, dict):
            for v in entry.value.values():
                if isinstance(v, str):
                    entities.extend(self.extract_from_text(v, source=entry.key))
        return entities

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity:
                return entity
        # Fall back to store
        entry = self._store.get_by_key(
            f"entity:{entity_id}",
            scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        if entry and isinstance(entry.value, Entity):
            with self._lock:
                self._entities[entity_id] = entry.value
            return entry.value
        return None

    def find_by_name(self, name: str) -> Optional[Entity]:
        """Find an entity by its exact name."""
        normalized = name.strip().lower()
        with self._lock:
            for entity in self._entities.values():
                if entity.name.lower() == normalized:
                    return entity
                for alias in entity.aliases:
                    if alias.lower() == normalized:
                        return entity
        return None

    def search(self, query: str, limit: int = 50) -> List[Entity]:
        """Search for entities by name, alias, or description."""
        query = query.lower()
        results = []
        with self._lock:
            for entity in self._entities.values():
                if (query in entity.name.lower()
                        or query in entity.description.lower()
                        or any(query in a.lower() for a in entity.aliases)):
                    results.append(entity)
        results.sort(key=lambda e: (e.mention_count, e.confidence), reverse=True)
        return results[:limit]

    def get_by_type(self, entity_type: str, limit: int = 50) -> List[Entity]:
        """Get all entities of a given type."""
        with self._lock:
            entities = [
                e for e in self._entities.values() if e.type == entity_type
            ]
        entities.sort(key=lambda e: e.mention_count, reverse=True)
        return entities[:limit]

    def get_mentions(self, name: str) -> int:
        """Get how many times an entity has been mentioned."""
        entity = self.find_by_name(name)
        return entity.mention_count if entity else 0

    def get_all_types(self) -> List[str]:
        """Get all entity types that have been indexed."""
        with self._lock:
            return list({e.type for e in self._entities.values()})

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def bulk_register(self, entities: List[Entity]) -> int:
        """Register multiple entities at once. Returns count."""
        count = 0
        for entity in entities:
            self.register_entity(entity)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_by_name(self, name: str) -> Optional[Entity]:
        """Find an existing entity by exact name."""
        normalized = name.strip().lower()
        with self._lock:
            for entity in self._entities.values():
                if entity.name.lower() == normalized:
                    return entity
                for alias in entity.aliases:
                    if alias.lower() == normalized:
                        return entity
        return None

    @staticmethod
    def _is_common_word(word: str) -> bool:
        """Check if a word is too common to be an entity."""
        common_words = {
            "the", "this", "that", "with", "from", "class", "function",
            "import", "return", "print", "true", "false", "none", "null",
            "self", "init", "str", "int", "list", "dict", "tuple", "set",
            "error", "name", "type", "file", "path", "data",
        }
        return word.lower() in common_words

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        with self._lock:
            count = len(self._entities)
            self._entities.clear()
        self._store.clear_namespace(self._namespace)
        return count

    def count(self) -> int:
        with self._lock:
            return len(self._entities)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type: Dict[str, int] = {}
            for e in self._entities.values():
                by_type[e.type] = by_type.get(e.type, 0) + 1
            return {
                "total_entities": len(self._entities),
                "by_type": by_type,
            }
