# AetherOS Memory Operating System (Memory OS)
# This module implements the core Memory OS architecture as specified in Master Prompt 9.
# It provides a unified memory system that includes working memory, episodic memory,
# semantic memory, procedural memory, and other specialized memory layers.

# The architecture follows the specification:
#                  AETHEROS MEMORY OS
#                         ?
#          +--------------+--------------+ 
#          ?              ?              ? 
#       WORKING         PERSISTENT      KNOWLEDGE
#        MEMORY           MEMORY          MEMORY
#          ?              ?              ?
#          +--------------+--------------+ 
#                         ? 
#                 MEMORY ORCHESTRATOR
#                         ? 
#               RETRIEVAL + RANKING
#                         ? 
#                 CONTEXT ASSEMBLER
#                         ? 
#                  AGENT
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
from abc import ABC, abstractmethod

from agent.memory_provider import MemoryProvider
from agent.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    """Types of memory in the Memory OS."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    USER = "user"
    PROJECT = "project"
    TASK = "task"
    AGENT = "agent"
    ORGANIZATION = "organization"

class MemoryScope(Enum):
    """Scopes of memory in the Memory OS."""
    SESSION = "session"      # Temporary, lasts for a single interaction
    USER = "user"            # User-specific, persists across sessions
    PROJECT = "project"      # Project-specific, shared among team members
    TASK = "task"            # Task-specific, related to a particular task
    AGENT = "agent"          # Agent-specific, related to the agent's operation
    ORGANIZATION = "organization"  # Organization-wide, shared across the organization

class TrustLevel(Enum):
    """Trust levels for memory entries."""
    UNTRUSTED = "untrusted"    # Information from unverified sources
    UNVERIFIED = "unverified"  # Information not yet verified
    TRUSTED = "trusted"        # Information from trusted sources
    VERIFIED = "verified"      # Information that has been verified

class ImportanceLevel(Enum):
    """Importance levels for memory entries."""
    LOW = "low"        # Low importance information
    NORMAL = "normal"  # Normal importance information
    HIGH = "high"      # High importance information
    CRITICAL = "critical"  # Critical importance information

class WriteType(Enum):
    """Write types for memory entries."""
    AUTO_SAVE = "auto_save"    # Automatically saved
    MANUAL = "manual"          # Manually written
    IMPORT = "import"          # Imported from external source
    BACKUP = "backup"          # Backup copy

@dataclass
class MemoryEntry:
    """Base class for all memory entries."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.SEMANTIC
    scope: MemoryScope = MemoryScope.USER
    trust_level: TrustLevel = TrustLevel.UNVERIFIED
    importance_level: ImportanceLevel = ImportanceLevel.NORMAL
    write_type: WriteType = WriteType.AUTO_SAVE
    timestamp: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    source: str = ""  # e.g., "user_input", "agent_deduction", "external_source"
    confidence: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # type -> [ids]
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if the memory entry has expired."""
        return self.expires_at is not None and time.time() > self.expires_at

    def access(self):
        """Record an access to this memory entry."""
        self.access_count += 1
        self.last_accessed = time.time()

    def get_relevance_score(self, query: str = "") -> float:
        """Calculate a relevance score for this memory entry based on various factors."""
        score = 0.0
        
        # Base confidence score
        score += self.confidence * 0.3
        
        # Importance level weight
        importance_weights = {
            ImportanceLevel.LOW: 0.1,
            ImportanceLevel.NORMAL: 0.2,
            ImportanceLevel.HIGH: 0.4,
            ImportanceLevel.CRITICAL: 0.8
        }
        score += importance_weights.get(self.importance_level, 0.2) * 0.2
        
        # Trust level weight
        trust_weights = {
            TrustLevel.UNTRUSTED: 0.0,
            TrustLevel.UNVERIFIED: 0.2,
            TrustLevel.TRUSTED: 0.6,
            TrustLevel.VERIFIED: 1.0
        }
        score += trust_weights.get(self.trust_level, 0.2) * 0.2
        
        # Query matching (if query provided)
        if query:
            query_lower = query.lower()
            content_lower = self.content.lower()
            
            # Exact phrase match
            if query_lower in content_lower:
                score += 0.3
            
            # Word overlap
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            if query_words and content_words:
                overlap = len(query_words.intersection(content_words))
                score += (overlap / len(query_words)) * 0.2
        
        # Recency bonus (more recent gets higher score)
        time_diff = time.time() - self.timestamp
        # Normalize to last 30 days
        recency_score = max(0, 1 - (time_diff / (30 * 24 * 3600)))
        score += recency_score * 0.1
        
        # Frequency bonus
        frequency_score = min(1.0, self.access_count / 10.0)  # Cap at 10 accesses
        score += frequency_score * 0.1
        
        return min(1.0, score)  # Cap at 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the memory entry to a dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "scope": self.scope.value,
            "trust_level": self.trust_level.value,
            "importance_level": self.importance_level.value,
            "write_type": self.write_type.value,
            "timestamp": self.timestamp,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "relationships": self.relationships,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create a memory entry from a dictionary."""
        entry = cls()
        entry.id = data.get("id", str(uuid.uuid4()))
        entry.content = data.get("content", "")
        entry.memory_type = MemoryType(data.get("memory_type", MemoryType.SEMANTIC.value))
        entry.scope = MemoryScope(data.get("scope", MemoryScope.USER.value))
        entry.trust_level = TrustLevel(data.get("trust_level", TrustLevel.UNVERIFIED.value))
        entry.importance_level = ImportanceLevel(data.get("importance_level", ImportanceLevel.NORMAL.value))
        entry.write_type = WriteType(data.get("write_type", WriteType.AUTO_SAVE.value))
        entry.timestamp = data.get("timestamp", time.time())
        entry.updated_at = data.get("updated_at", time.time())
        entry.expires_at = data.get("expires_at")
        entry.source = data.get("source", "")
        entry.confidence = data.get("confidence", 0.5)
        entry.metadata = data.get("metadata", {})
        entry.tags = set(data.get("tags", []))
        entry.relationships = data.get("relationships", {})
        entry.access_count = data.get("access_count", 0)
        entry.last_accessed = data.get("last_accessed", time.time())
        return entry

class MemoryLayer(ABC):
    """Abstract base class for memory layers."""
    def __init__(self, memory_type: MemoryType, scope: MemoryScope):
        self.memory_type = memory_type
        self.scope = scope
        self.entries: Dict[str, MemoryEntry] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def add(self, entry: MemoryEntry) -> str:
        """Add a memory entry to the layer."""
        pass

    @abstractmethod
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search for memory entries matching the query."""
        pass

    @abstractmethod
    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        pass

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        pass

    def get_all_entries(self) -> List[MemoryEntry]:
        """Get all entries in this layer."""
        return list(self.entries.values())

    def get_entry_count(self) -> int:
        """Get the number of entries in this layer."""
        return len(self.entries)

class EpisodicMemory(MemoryLayer):
    """Episodic memory for storing events and experiences."""
    def __init__(self):
        super().__init__(MemoryType.EPISODIC, MemoryScope.USER)

    def add(self, entry: MemoryEntry) -> str:
        """Add an episodic memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve an episodic memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search episodic memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by relevance score (highest first)
        results.sort(key=lambda e: e.get_relevance_score(query), reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update an episodic memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete an episodic memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from episodic memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class SemanticMemory(MemoryLayer):
    """Semantic memory for storing facts and knowledge."""
    def __init__(self):
        super().__init__(MemoryType.SEMANTIC, MemoryScope.USER)

    def add(self, entry: MemoryEntry) -> str:
        """Add a semantic memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a semantic memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search semantic memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by confidence and importance (highest first)
        results.sort(key=lambda e: (e.confidence, e.importance_level.value, e.get_relevance_score(query)), reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a semantic memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a semantic memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from semantic memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class ProceduralMemory(MemoryLayer):
    """Procedural memory for storing skills, workflows, and procedures."""
    def __init__(self):
        super().__init__(MemoryType.PROCEDURAL, MemoryScope.USER)

    def add(self, entry: MemoryEntry) -> str:
        """Add a procedural memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a procedural memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search procedural memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by confidence and importance (highest first)
        results.sort(key=lambda e: (e.confidence, e.importance_level.value, e.get_relevance_score(query)), reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a procedural memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a procedural memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from procedural memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class WorkingMemory(MemoryLayer):
    """Working memory for immediate reasoning and current context."""
    def __init__(self):
        super().__init__(MemoryType.WORKING, MemoryScope.SESSION)

    def add(self, entry: MemoryEntry) -> str:
        """Add a working memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a working memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search working memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first) for working memory
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a working memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a working memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from working memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class UserMemory(MemoryLayer):
    """User memory for storing user-specific information like preferences and personal details."""
    def __init__(self):
        super().__init__(MemoryType.USER, MemoryScope.USER)

    def add(self, entry: MemoryEntry) -> str:
        """Add a user memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a user memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search user memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a user memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a user memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from user memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class ProjectMemory(MemoryLayer):
    """Project memory for storing project-specific information like architecture, decisions, and conventions."""
    def __init__(self):
        super().__init__(MemoryType.PROJECT, MemoryScope.PROJECT)

    def add(self, entry: MemoryEntry) -> str:
        """Add a project memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a project memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search project memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a project memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a project memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from project memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class TaskMemory(MemoryLayer):
    """Task memory for storing task-specific information like goals, plans, and progress."""
    def __init__(self):
        super().__init__(MemoryType.TASK, MemoryScope.TASK)

    def add(self, entry: MemoryEntry) -> str:
        """Add a task memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a task memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search task memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete a task memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from task memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class AgentMemory(MemoryLayer):
    """Agent memory for storing agent-specific operational memory like successful patterns and failure history."""
    def __init__(self):
        super().__init__(MemoryType.AGENT, MemoryScope.AGENT)

    def add(self, entry: MemoryEntry) -> str:
        """Add an agent memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve an agent memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search agent memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update an agent memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete an agent memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from agent memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class OrganizationMemory(MemoryLayer):
    """Organization memory for storing organization-scoped information like policies and standards."""
    def __init__(self):
        super().__init__(MemoryType.ORGANIZATION, MemoryScope.ORGANIZATION)

    def add(self, entry: MemoryEntry) -> str:
        """Add an organization memory entry."""
        self.entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve an organization memory entry by ID."""
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search organization memory for entries matching the query."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            entry.access()  # Record access
            if query_lower in entry.content.lower():
                results.append(entry)
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update an organization memory entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        return True

    def delete(self, entry_id: str) -> bool:
        """Delete an organization memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from organization memory."""
        expired_ids = []
        for entry_id, entry in self.entries.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        for entry_id in expired_ids:
            del self.entries[entry_id]
        return len(expired_ids)

class MemoryOrchestrator:
    """Orchestrates all memory layers and provides unified interface for memory operations."""
    
    def __init__(self, agent_id: str = None, project_id: str = None, task_id: str = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.project_id = project_id
        self.task_id = task_id
        
        # Initialize all memory layers
        self.layers: Dict[MemoryType, MemoryLayer] = {}
        self._initialize_layers()
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _initialize_layers(self):
        """Initialize all memory layer instances."""
        self.layers[MemoryType.WORKING] = WorkingMemory()
        self.layers[MemoryType.EPISODIC] = EpisodicMemory()
        self.layers[MemoryType.SEMANTIC] = SemanticMemory()
        self.layers[MemoryType.PROCEDURAL] = ProceduralMemory()
        self.layers[MemoryType.USER] = UserMemory()
        self.layers[MemoryType.PROJECT] = ProjectMemory()
        self.layers[MemoryType.TASK] = TaskMemory()
        self.layers[MemoryType.AGENT] = AgentMemory()
        self.layers[MemoryType.ORGANIZATION] = OrganizationMemory()
    
    def add_memory(self, content: str, memory_type: MemoryType = MemoryType.SEMANTIC, 
                   scope: MemoryScope = MemoryScope.USER, **kwargs) -> str:
        """Add a memory entry to the specified layer."""
        # Create memory entry
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            scope=scope,
            **kwargs
        )
        
        # Add to appropriate layer
        layer = self.layers.get(memory_type)
        if layer is None:
            raise ValueError(f"Unsupported memory type: {memory_type}")
        
        return layer.add(entry)
    
    def get_memory(self, entry_id: str, memory_type: MemoryType = None) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID from the specified layer or search all layers."""
        if memory_type is not None:
            # Get from specific layer
            layer = self.layers.get(memory_type)
            if layer is None:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            return layer.get(entry_id)
        else:
            # Search all layers
            for layer in self.layers.values():
                entry = layer.get(entry_id)
                if entry is not None:
                    return entry
            return None
    
    def search_memory(self, query: str, memory_type: MemoryType = None, 
                      limit: int = 10) -> List[MemoryEntry]:
        """Search for memory entries matching the query with relevance scoring."""
        if memory_type is not None:
            # Search specific layer
            layer = self.layers.get(memory_type)
            if layer is None:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            return layer.search(query, limit)
        else:
            # Search all layers and merge results
            all_results = []
            for layer in self.layers.values():
                all_results.extend(layer.search(query, limit=limit*2))  # Get more to allow for re-ranking
            
            # Re-rank all results by relevance score
            all_results.sort(key=lambda e: e.get_relevance_score(query), reverse=True)
            return all_results[:limit]
    
    def update_memory(self, entry_id: str, updates: Dict[str, Any], 
                      memory_type: MemoryType = None) -> bool:
        """Update a memory entry."""
        if memory_type is not None:
            # Update specific layer
            layer = self.layers.get(memory_type)
            if layer is None:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            return layer.update(entry_id, updates)
        else:
            # Find and update in any layer
            for layer in self.layers.values():
                if layer.get(entry_id) is not None:
                    return layer.update(entry_id, updates)
            return False
    
    def delete_memory(self, entry_id: str, memory_type: MemoryType = None) -> bool:
        """Delete a memory entry."""
        if memory_type is not None:
            # Delete from specific layer
            layer = self.layers.get(memory_type)
            if layer is None:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            return layer.delete(entry_id)
        else:
            # Find and delete from any layer
            for layer in self.layers.values():
                if layer.get(entry_id) is not None:
                    return layer.delete(entry_id)
            return False
    
    def cleanup_expired(self) -> Dict[MemoryType, int]:
        """Remove expired entries from all memory layers."""
        results = {}
        for memory_type, layer in self.layers.items():
            count = layer.cleanup_expired()
            results[memory_type] = count
        return results
    
    def get_layer(self, memory_type: MemoryType) -> Optional[MemoryLayer]:
        """Get a specific memory layer by type."""
        return self.layers.get(memory_type)
    
    def get_all_layers(self) -> Dict[MemoryType, MemoryLayer]:
        """Get all memory layers."""
        return self.layers.copy()
    
    def get_context_for_prompt(self, query: str, max_tokens: int = 2000) -> str:
        """
        Assemble context from all memory layers for inclusion in an agent's prompt.
        This implements the 'CONTEXT ASSEMBLER' from the architecture diagram.
        """
        context_parts = []
        current_length = 0
        
        # Priority order: Working > Episodic > Semantic > Others
        priority_order = [
            MemoryType.WORKING,
            MemoryType.EPISODIC,
            MemoryType.SEMANTIC,
            MemoryType.PROCEDURAL,
            MemoryType.USER,
            MemoryType.PROJECT,
            MemoryType.TASK,
            MemoryType.AGENT,
            MemoryType.ORGANIZATION
        ]
        
        for mem_type in priority_order:
            layer = self.layers.get(mem_type)
            if layer is None:
                continue
                
            # Get relevant memories from this layer
            memories = layer.search(query, limit=10)
            
            for memory in memories:
                # Format the memory entry
                memory_text = f"[{mem_type.value.upper()}] {memory.content}"
                
                # Check if adding this would exceed our limit
                if current_length + len(memory_text) > max_tokens:
                    # Try to fit a truncated version
                    remaining_space = max_tokens - current_length
                    if remaining_space > 50:  # Only if we have reasonable space
                        truncated = memory_text[:remaining_space-3] + "..."
                        context_parts.append(truncated)
                        current_length += len(truncated)
                    break
                else:
                    context_parts.append(memory_text)
                    current_length += len(memory_text)
            
            # If we're already close to the limit, stop adding more layers
            if current_length >= max_tokens * 0.9:
                break
        
        return "\n".join(context_parts)
    
    def consolidate_memories(self):
        """
        Consolidate memories between layers - implementing parts of the 
        'RETRIEVAL + RANKING' system from the architecture diagram.
        This would typically move important temporary memories to more permanent storage.
        """
        # Move important working memories to episodic or semantic
        working_layer = self.layers.get(MemoryType.WORKING)
        if working_layer:
            # Get high-importance, recently accessed working memories
            candidates = []
            for entry in working_layer.get_all_entries():
                # Boost score for recently accessed and important items
                score = entry.get_relevance_score("")
                score = entry.get_relevance_score("")
                # Convert importance level to numeric value for scoring
                importance_map = {
                    ImportanceLevel.LOW: 0.0,
                    ImportanceLevel.NORMAL: 0.25,
                    ImportanceLevel.HIGH: 0.5,
                    ImportanceLevel.CRITICAL: 1.0
                }
                importance_value = importance_map.get(entry.importance_level, 0.0)
                score += importance_value * 0.1  # Boost by importance
                score += min(entry.access_count * 0.05, 0.3)  # Boost by frequency
            
            # Sort by score and take top items
            candidates.sort(key=lambda x: x[0], reverse=True)
            top_candidates = candidates[:5]  # Top 5 candidates for consolidation
            
            for score, entry_id, entry in top_candidates:
                # Decide where to consolidate based on content type
                # This is a simplified version - in practice this would be more sophisticated
                if any(word in entry.content.lower() for word in ["how to", "procedure", "step", "method"]):
                    # Move to procedural memory
                    target_layer = self.layers.get(MemoryType.PROCEDURAL)
                    if target_layer:
                        # Create a copy for the target layer
                        new_entry = MemoryEntry(
                            content=entry.content,
                            memory_type=MemoryType.PROCEDURAL,
                            scope=MemoryScope.USER,
                            importance_level=entry.importance_level,
                            trust_level=entry.trust_level,
                            confidence=min(entry.confidence + 0.1, 1.0),  # Slightly boost confidence
                            source=f"consolidated_from_{entry.memory_type.value}",
                            metadata={**entry.metadata, "consolidated_from": [entry_id]}
                        )
                        target_layer.add(new_entry)
                        
                elif any(word in entry.content.lower() for word in ["remember", "recall", "experience", "happened"]):
                    # Move to episodic memory
                    target_layer = self.layers.get(MemoryType.EPISODIC)
                    if target_layer:
                        new_entry = MemoryEntry(
                            content=entry.content,
                            memory_type=MemoryType.EPISODIC,
                            scope=MemoryScope.USER,
                            importance_level=entry.importance_level,
                            trust_level=entry.trust_level,
                            confidence=min(entry.confidence + 0.05, 1.0),
                            source=f"consolidated_from_{entry.memory_type.value}",
                            metadata={**entry.metadata, "consolidated_from": [entry_id]}
                        )
                        target_layer.add(new_entry)
                
                else:
                    # Default to semantic memory for facts and knowledge
                    target_layer = self.layers.get(MemoryType.SEMANTIC)
                    if target_layer:
                        new_entry = MemoryEntry(
                            content=entry.content,
                            memory_type=MemoryType.SEMANTIC,
                            scope=MemoryScope.USER,
                            importance_level=entry.importance_level,
                            trust_level=entry.trust_level,
                            confidence=entry.confidence,
                            source=f"consolidated_from_{entry.memory_type.value}",
                            metadata={**entry.metadata, "consolidated_from": [entry_id]}
                        )
                        target_layer.add(new_entry)
        
        self.logger.info("Memory consolidation completed")

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about memory usage across all layers.
        This provides analytics for monitoring and optimization.
        """
        stats = {
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "layers": {},
            "totals": {
                "entries": 0,
                "oldest_entry_age": 0,
                "newest_entry_age": 0,
                "total_access_count": 0,
                "average_confidence": 0.0,
                "memory_efficiency_score": 0.0
            }
        }
        
        all_entries = []
        layer_stats = {}
        
        for mem_type, layer in self.layers.items():
            entries = layer.get_all_entries()
            layer_count = len(entries)
            
            if entries:
                # Calculate layer-specific statistics
                timestamps = [e.timestamp for e in entries]
                access_counts = [e.access_count for e in entries]
                confidences = [e.confidence for e in entries]
                importance_levels = [e.importance_level.value for e in entries]
                
                layer_stats[mem_type.value] = {
                    "count": layer_count,
                    "oldest_entry": min(timestamps) if timestamps else 0,
                    "newest_entry": max(timestamps) if timestamps else 0,
                    "average_access_count": sum(access_counts) / len(access_counts) if access_counts else 0,
                    "average_confidence": sum(confidences) / len(confidences) if confidences else 0,
                    "importance_distribution": {
                        "low": sum(1 for i in importance_levels if i == ImportanceLevel.LOW.value),
                        "normal": sum(1 for i in importance_levels if i == ImportanceLevel.NORMAL.value),
                        "high": sum(1 for i in importance_levels if i == ImportanceLevel.HIGH.value),
                        "critical": sum(1 for i in importance_levels if i == ImportanceLevel.CRITICAL.value)
                    },
                    "trust_distribution": {
                        "untrusted": sum(1 for e in entries if e.trust_level == TrustLevel.UNTRUSTED),
                        "unverified": sum(1 for e in entries if e.trust_level == TrustLevel.UNVERIFIED),
                        "trusted": sum(1 for e in entries if e.trust_level == TrustLevel.TRUSTED),
                        "verified": sum(1 for e in entries if e.trust_level == TrustLevel.VERIFIED)
                    }
                }
                
                all_entries.extend(entries)
            else:
                layer_stats[mem_type.value] = {
                    "count": 0,
                    "oldest_entry": 0,
                    "newest_entry": 0,
                    "average_access_count": 0,
                    "average_confidence": 0,
                    "importance_distribution": {"low": 0, "normal": 0, "high": 0, "critical": 0},
                    "trust_distribution": {"untrusted": 0, "unverified": 0, "trusted": 0, "verified": 0}
                }
        
        # Calculate overall statistics
        if all_entries:
            timestamps = [e.timestamp for e in all_entries]
            access_counts = [e.access_count for e in all_entries]
            confidences = [e.confidence for e in all_entries]
            
            oldest_timestamp = min(timestamps) if timestamps else time.time()
            newest_timestamp = max(timestamps) if timestamps else time.time()
            
            stats["totals"] = {
                "entries": len(all_entries),
                "oldest_entry_age": time.time() - oldest_timestamp if oldest_timestamp else 0,
                "newest_entry_age": time.time() - newest_timestamp if newest_timestamp else 0,
                "total_access_count": sum(access_counts),
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "memory_efficiency_score": self._calculate_memory_efficiency(all_entries)
            }
        
        stats["layers"] = layer_stats
        return stats
    
    def _calculate_memory_efficiency(self, entries: List[MemoryEntry]) -> float:
        """Calculate an overall memory efficiency score (0.0 to 1.0)."""
        if not entries:
            return 0.0
        
        # Factors contributing to efficiency:
        # 1. High confidence entries
        # 2. Recently accessed entries
        # 3. Proper importance/trust alignment
        # 4. Low redundancy (simplified)
        
        confidence_score = sum(e.confidence for e in entries) / len(entries)
        
        # Recency score - average of how recent entries are (normalized to 30 days)
        now = time.time()
        recency_scores = []
        for e in entries:
            age_days = (now - e.timestamp) / (24 * 3600)
            recency_score = max(0, 1 - (age_days / 30))  # 1.0 for new, 0.0 for 30+ days old
            recency_scores.append(recency_score)
        recency_score = sum(recency_scores) / len(recency_scores) if recency_scores else 0
        
        # Importance-trust alignment score
        alignment_scores = []
        for e in entries:
            # High importance should have high trust
            importance_value = {
                ImportanceLevel.LOW: 0.25,
                ImportanceLevel.NORMAL: 0.5,
                ImportanceLevel.HIGH: 0.75,
                ImportanceLevel.CRITICAL: 1.0
            }[e.importance_level]
            
            trust_value = {
                TrustLevel.UNTRUSTED: 0.0,
                TrustLevel.UNVERIFIED: 0.33,
                TrustLevel.TRUSTED: 0.66,
                TrustLevel.VERIFIED: 1.0
            }[e.trust_level]
            
            # Alignment is better when importance and trust are similar
            alignment = 1.0 - abs(importance_value - trust_value)
            alignment_scores.append(alignment)
        
        alignment_score = sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0
        
        # Combine scores (weights can be adjusted)
        efficiency = (confidence_score * 0.4) + (recency_score * 0.3) + (alignment_score * 0.3)
        return min(1.0, max(0.0, efficiency))
    
    def optimize_memory(self, aggressive: bool = False) -> Dict[str, int]:
        """
        Optimize memory by removing low-value entries and consolidating fragments.
        
        Args:
            aggressive: If True, applies more aggressive optimization
            
        Returns:
            Dictionary with counts of removed/consolidated entries per layer
        """
        optimization_results = {}
        
        for mem_type, layer in self.layers.items():
            initial_count = layer.get_entry_count()
            
            # Get all entries for evaluation
            entries = layer.get_all_entries()
            entries_to_remove = []
            
            # Define thresholds for removal
            confidence_threshold = 0.1 if aggressive else 0.05
            importance_threshold = ImportanceLevel.LOW
            max_age_days = 30 if aggressive else 90  # Remove older entries when aggressive
            
            now = time.time()
            max_age_seconds = max_age_days * 24 * 3600
            
            for entry in entries:
                should_remove = False
                
                # Remove very low confidence entries
                if entry.confidence < confidence_threshold:
                    should_remove = True
                
                # Remove old low-importance entries
                elif (now - entry.timestamp) > max_age_seconds and \
                     entry.importance_level == ImportanceLevel.LOW:
                    should_remove = True
                
                # Remove unused entries that are also low trust
                elif (entry.access_count == 0 and 
                      entry.trust_level in [TrustLevel.UNTRUSTED, TrustLevel.UNVERIFIED] and
                      (now - entry.timestamp) > (7 * 24 * 3600)):  # 1 week unused
                    should_remove = True
                
                if should_remove:
                    entries_to_remove.append(entry.id)
            
            # Remove identified entries
            removed_count = 0
            for entry_id in entries_to_remove:
                if layer.delete(entry_id):
                    removed_count += 1
            
            optimization_results[mem_type.value] = {
                "initial_count": initial_count,
                "removed_count": removed_count,
                "final_count": layer.get_entry_count()
            }
        
        # Run consolidation after optimization
        self.consolidate_memories()
        
        return optimization_results
    
    def prepare_for_subagent(self, subagent_type: str, context_hints: List[str] = None) -> Dict[MemoryType, List[MemoryEntry]]:
        """
        Prepare and package memory layers for submission to a subagent.
        This supports the delegation system by providing relevant memories.
        
        Args:
            subagent_type: Type of subagent (e.g., "developer", "researcher", "writer")
            context_hints: Optional hints about what context the subagent needs
            
        Returns:
            Dictionary mapping memory types to lists of relevant memory entries
        """
        # Determine what memories to share based on subagent type
        # This is a simplified version - in practice this would be more sophisticated
        
        memories_for_subagent = {}
        context_hints = context_hints or []
        context_query = " ".join(context_hints) if context_hints else ""
        
        for mem_type, layer in self.layers.items():
            # Get relevant memories for this subagent
            if context_query:
                relevant_memories = layer.search(context_query, limit=20)
            else:
                # For specific subagent types, apply filters
                if subagent_type == "developer":
                    # Prioritize procedural, semantic, and project memories
                    if mem_type in [MemoryType.PROCEDURAL, MemoryType.SEMANTIC, MemoryType.PROJECT]:
                        relevant_memories = layer.get_all_entries()[:15]
                    else:
                        relevant_memories = layer.search("", limit=5)  # Just a few
                elif subagent_type == "researcher":
                    # Prioritize semantic, episodic, and user memories
                    if mem_type in [MemoryType.SEMANTIC, MemoryType.EPISODIC, MemoryType.USER]:
                        relevant_memories = layer.get_all_entries()[:15]
                    else:
                        relevant_memories = layer.search("", limit=5)
                elif subagent_type == "writer":
                    # Prioritize episodic, user, and semantic memories
                    if mem_type in [MemoryType.EPISODIC, MemoryType.USER, MemoryType.SEMANTIC]:
                        relevant_memories = layer.get_all_entries()[:15]
                    else:
                        relevant_memories = layer.search("", limit=5)
                else:
                    # Default: get some memories from each layer
                    relevant_memories = layer.search(context_query or "", limit=10)
            
            if relevant_memories:
                memories_for_subagent[mem_type] = relevant_memories
        
        return memories_for_subagent
    
    def integrate_with_agent_turn(self, user_input: str, agent_response: str) -> Dict[str, Any]:
        """
        Called by the agent's main loop to integrate memory operations with each turn.
        This is the primary integration point with run_agent.py.
        
        Args:
            user_input: The user's input for this turn
            agent_response: The agent's response for this turn
            
        Returns:
            Dictionary with insights and recommendations for the agent
        """
        integration_result = {
            "timestamp": time.time(),
            "turn_processed": True,
            "memories_added": 0,
            "insights": [],
            "suggestions": [],
            "context_for_next_turn": ""
        }
        
        # 1. Add user input to episodic and working memory
        try:
            user_entry_id = self.add_memory(
                content=f"User input: {user_input}",
                memory_type=MemoryType.EPISODIC,
                importance_level=ImportanceLevel.NORMAL,
                trust_level=TrustLevel.VERIFIED,  # User input is verified
                source="user_input",
                confidence=0.9
            )
            
            # Also add to working memory for immediate context
            self.add_memory(
                content=f"User input: {user_input}",
                memory_type=MemoryType.WORKING,
                importance_level=ImportanceLevel.HIGH,
                trust_level=TrustLevel.VERIFIED,
                source="user_input",
                confidence=0.95,
                write_type=WriteType.MANUAL
            )
            
            integration_result["memories_added"] += 2
        except Exception as e:
            self.logger.error(f"Failed to add user input to memory: {e}")
            integration_result["insights"].append(f"Memory error: {str(e)}")
        
        # 2. Add agent response to episodic and agent memory
        try:
            agent_entry_id = self.add_memory(
                content=f"Agent response: {agent_response}",
                memory_type=MemoryType.EPISODIC,
                importance_level=ImportanceLevel.NORMAL,
                trust_level=TrustLevel.TRUSTED,  # Agent output is trusted
                source="agent_output",
                confidence=0.8
            )
            
            # Add to agent memory for operational learning
            self.add_memory(
                content=f"Agent response: {agent_response}",
                memory_type=MemoryType.AGENT,
                importance_level=ImportanceLevel.NORMAL,
                trust_level=TrustLevel.TRUSTED,
                source="agent_output",
                confidence=0.85,
                write_type=WriteType.MANUAL
            )
            
            integration_result["memories_added"] += 2
        except Exception as e:
            self.logger.error(f"Failed to add agent response to memory: {e}")
            integration_result["insights"].append(f"Memory error: {str(e)}")
        
        # 3. Extract and store key information as semantic memories
        try:
            # Simple keyword extraction - in practice this would use NLP
            key_phrases = self._extract_key_information(user_input + " " + agent_response)
            for phrase in key_phrases[:3]:  # Limit to top 3 phrases
                self.add_memory(
                    content=phrase,
                    memory_type=MemoryType.SEMANTIC,
                    importance_level=ImportanceLevel.HIGH if len(phrase) > 20 else ImportanceLevel.NORMAL,
                    trust_level=TrustLevel.TRUSTED,
                    source="turn_extraction",
                    confidence=0.7
                )
                integration_result["memories_added"] += 1
        except Exception as e:
            self.logger.debug(f"Key information extraction failed (non-critical): {e}")
        
        # 4. Generate insights based on memory patterns
        try:
            insights = self._generate_turn_insights(user_input, agent_response)
            integration_result["insights"].extend(insights)
        except Exception as e:
            self.logger.debug(f"Insight generation failed: {e}")
        
        # 5. Generate suggestions for next turn
        try:
            suggestions = self._generate_turn_suggestions(user_input, agent_response)
            integration_result["suggestions"].extend(suggestions)
        except Exception as e:
            self.logger.debug(f"Suggestion generation failed: {e}")
        
        # 6. Prepare context for next turn
        try:
            context = self.get_context_for_prompt(
                query=user_input, 
                max_tokens=1500  # Leave room for user input and agent thinking
            )
            integration_result["context_for_next_turn"] = context
        except Exception as e:
            self.logger.error(f"Context preparation failed: {e}")
            integration_result["context_for_next_turn"] = ""
        
        # 7. Periodic optimization (every 10 turns or so)
        # In a real implementation, we'd track turn count, but for now we'll do a light check
        if len(user_input + agent_response) > 200:  # Only for substantial turns
            try:
                # Light optimization - just check if we should consolidate
                working_layer = self.layers.get(MemoryType.WORKING)
                if working_layer and working_layer.get_entry_count() > 20:
                    # Light consolidation without full optimization
                    pass  # The consolidate_memories method is already called elsewhere as needed
            except Exception as e:
                self.logger.debug(f"Periodic optimization check failed: {e}")
        
        return integration_result
    
    def _extract_key_information(self, text: str) -> List[str]:
        """Extract key information phrases from text for semantic storage."""
        # Simple implementation - in practice this would use NLP techniques
        import re
        
        # Look for sentences with key indicators
        sentences = re.split(r'[.!?]+', text)
        key_phrases = []
        
        key_indicators = [
            "is", "are", "was", "were",  # Definitions
            "means", "refers to", "defined as",
            "important", "key", "critical", "essential",
            "always", "never", "must", "should",
            "because", "therefore", "thus", "hence"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Too short
                continue
                
            # Check if it contains key indicators
            if any(indicator in sentence.lower() for indicator in key_indicators):
                # Clean up the sentence
                clean_sentence = re.sub(r'\s+', ' ', sentence).strip()
                if clean_sentence and clean_sentence not in key_phrases:
                    key_phrases.append(clean_sentence)
        
        # Also look for quoted text or code-like patterns
        quoted_matches = re.findall(r'"([^"]*)"', text)
        for match in quoted_matches:
            if len(match) > 5 and match not in key_phrases:
                key_phrases.append(match)
        
        # Limit and return
        return key_phrases[:5]
    
    def _generate_turn_insights(self, user_input: str, agent_response: str) -> List[str]:
        """Generate insights about the turn based on memory patterns."""
        insights = []
        
        try:
            # Check if user is asking about similar topics recently
            recent_episodic = []
            episodic_layer = self.layers.get(MemoryType.EPISODIC)
            if episodic_layer:
                # Get recent episodic memories
                recent_memories = episodic_layer.get_all_entries()
                recent_memories.sort(key=lambda e: e.timestamp, reverse=True)
                recent_episodic = [e for e in recent_memories[:10] if (time.time() - e.timestamp) < (3600)]  # Last hour
            
            if len(recent_episodic) > 3:
                insights.append("User has been active in this topic area recently")
            
            # Check for repetitive patterns
            if len(user_input) > 20 and len(agent_response) > 20:
                # Simple similarity check - in practice this would be more sophisticated
                user_words = set(user_input.lower().split())
                agent_words = set(agent_response.lower().split())
                if user_words and agent_words:
                    overlap = len(user_words.intersection(agent_words))
                    if overlap > len(user_words) * 0.3:  # Significant overlap
                        insights.append("Turn shows good alignment between query and response")
            
        except Exception as e:
            self.logger.debug(f"Insight generation error: {e}")
        
        return insights
    
    def _generate_turn_suggestions(self, user_input: str, agent_response: str) -> List[str]:
        """Generate suggestions for improving future turns."""
        suggestions = []
        
        try:
            # Suggest adding more context if the exchange was very short
            if len(user_input) < 10 and len(agent_response) < 20:
                suggestions.append("Consider providing more context for better assistance")
            
            # Suggest checking procedural memory for how-to questions
            if any(word in user_input.lower() for word in ["how", "what", "why", "help"]):
                procedural_layer = self.layers.get(MemoryType.PROCEDURAL)
                if procedural_layer and procedural_layer.get_entry_count() > 0:
                    suggestions.append("Relevant procedures may be available in memory")
            
            # Suggest using semantic memory for fact-based questions
            if any(word in user_input.lower() for word in ["what is", "who is", "when did", "where is"]):
                semantic_layer = self.layers.get(MemoryType.SEMANTIC)
                if semantic_layer and semantic_layer.get_entry_count() > 0:
                    suggestions.append("Factual information may be available in semantic memory")
                    
        except Exception as e:
            self.logger.debug(f"Suggestion generation error: {e}")
        
        return suggestions

    def shutdown(self):
        """Perform cleanup operations when the memory system is shutting down."""
        self.logger.info(f"Shutting down memory system for agent {self.agent_id}")
        
        # Final optimization before shutdown
        try:
            optimization_results = self.optimize_memory(aggressive=False)
            self.logger.info(f"Shutdown optimization completed: {optimization_results}")
        except Exception as e:
            self.logger.error(f"Error during shutdown optimization: {e}")
        
        # Log final statistics
        try:
            final_stats = self.get_memory_statistics()
            self.logger.info(f"Final memory statistics: {final_stats['totals']['entries']} total entries")
        except Exception as e:
            self.logger.error(f"Error getting final statistics: {e}")

