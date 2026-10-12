"""
Memory Store — core storage backend for the AetherOS memory system.

Provides both in-memory and SQLite-backed storage for memory entries.
Handles serialization, scoping, and basic CRUD operations.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MemoryScope(Enum):
    """Scope/visibility of a memory entry."""
    GLOBAL = "global"
    WORKSPACE = "workspace"
    PROJECT = "project"
    CONVERSATION = "conversation"
    AGENT = "agent"
    USER = "user"
    SWARM = "swarm"
    PRIVATE = "private"
    MISSION = "mission"



class MemoryStatus(Enum):
    """Status of a memory entry."""
    ACTIVE = "active"        # Normal, retrievable memory
    INVALID = "invalid"      # Manually invalidated/corrected (kept for history)
    ARCHIVED = "archived"    # Moved to archive, not actively retrieved
    EXPIRED = "expired"      # Automatically expired due to time

@dataclass
class MemoryEntry:
    """A single entry in the memory store.

    Attributes:
        id: Unique entry ID
        key: Namespaced key for retrieval
        value: The stored value (JSON-serializable)
        memory_type: Type of memory (short_term, long_term, episodic, etc.)
        scope: Visibility scope
        namespace: Additional namespace for isolation
        tags: Tags for categorization
        metadata: Additional metadata
        importance: Importance score (0.0 - 1.0)
        confidence_level: Standardized confidence level (ConfidenceLevel enum)
        privacy_level: Standardized privacy level (PrivacyLevel enum)
        provenance_source: Standardized provenance source (ProvenanceSource enum)
        provenance_timestamp: When the provenance was established
        provenance_agent: Which agent/subsystem created this entry
        importance_override: Explicit importance score override (if set, overrides importance)
        version: Version of the memory entry format
        schema_version: Version of the memory schema used
        created_at: Creation timestamp
        updated_at: Last update timestamp
        expires_at: Optional expiry timestamp
        summary: Optional summary of the content
        source: Origin of the memory (e.g., 'user', 'agent', 'tool')
        source_type: Type of source (e.g., 'chat', 'file', 'web')
        source_id: ID of the source (e.g., message ID, file ID)
        owner_id: ID of the owner (user or agent)
        agent_id: ID of the agent that created this entry
        session_id: ID of the session this memory belongs to
        project_id: ID of the project this memory belongs to
        mission_id: ID of the mission this memory belongs to
        task_id: ID of the task this memory belongs to
        sensitivity: Sensitivity level (0.0 - 1.0) for security
        embedding_id: ID of the embedding in vector store (if applicable)
        status: Current status of the memory entry
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    key: str = ""
    value: Any = None
    memory_type: str = "general"
    scope: MemoryScope = MemoryScope.GLOBAL
    namespace: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    confidence_level: ConfidenceLevel = field(default_factory=lambda: DEFAULT_CONFIDENCE_LEVEL)
    privacy_level: PrivacyLevel = field(default_factory=lambda: DEFAULT_PRIVACY_LEVEL)
    provenance_source: ProvenanceSource = field(default_factory=lambda: DEFAULT_PROVENANCE_SOURCE)
    provenance_timestamp: float = field(default_factory=time.time)
    provenance_agent: str = ""
    importance_override: Optional[float] = None
    version: str = "1.0"
    schema_version: str = "1.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    owner_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    sensitivity: Optional[float] = None
    embedding_id: Optional[str] = None
    status: MemoryStatus = MemoryStatus.ACTIVE
class MemoryStore:
    """Core storage backend for memory entries.

    Supports both in-memory (default) and SQLite-backed storage.
    Entries are scoped by namespace and scope for isolation.

    Usage:
        store = MemoryStore()
        entry = store.save("user:preferences", {"theme": "dark"}, scope="user")
        results = store.search("preferences")
        entry = store.get(entry.id)
    """

    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.RLock()
        # In-memory storage
        self._entries: Dict[str, MemoryEntry] = {}
        # Indexes
        self._key_index: Dict[str, Set[str]] = {}  # key -> set of entry IDs
        self._namespace_index: Dict[str, Set[str]] = {}  # namespace -> entry IDs
        self._type_index: Dict[str, Set[str]] = {}  # memory_type -> entry IDs
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> entry IDs
        self._scope_index: Dict[str, Set[str]] = {}  # scope -> entry IDs

        self._db_path = db_path
        self._sqlite_conn = None
        if db_path:
            self._init_sqlite()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_sqlite(self) -> None:
        """Initialize SQLite backend."""
        try:
            import sqlite3
            self._sqlite_conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._sqlite_conn.execute("""
            self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    memory_type TEXT DEFAULT ''general'',
                    scope TEXT DEFAULT ''global'',
                    namespace TEXT DEFAULT '''',
                    tags TEXT DEFAULT ''[]'',
                    metadata TEXT DEFAULT ''{}'',
                    importance REAL DEFAULT 0.5,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL,
                    source TEXT,  -- origin of the memory
                    summary TEXT,
                    source_type TEXT,
                    source_id TEXT,
                    owner_id TEXT,
                    agent_id TEXT,
                    session_id TEXT,
                    project_id TEXT,
                    mission_id TEXT,
                    task_id TEXT,
                    sensitivity REAL,
                    embedding_id TEXT,
                    status TEXT DEFAULT ''active'',
                    provenance_source TEXT DEFAULT ''system''
                )
            """)
