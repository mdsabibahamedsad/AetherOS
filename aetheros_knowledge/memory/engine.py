"""
Memory Engine — personal, workspace, agent, project, temporary, long-term.

The Memory Engine is designed for quick storage and retrieval of key-value pairs
with associated metadata. It is optimized for:

1. Fast exact-key lookups (O(1) average case)
2. Storing agent preferences, workspace states, temporary caches
3. Managing memory with TTL (time-to-live) for automatic expiration
4. Importance-based retention and forgetting mechanisms
5. Scoped memory (personal, workspace, agent-specific, project-specific)

This system is NOT designed for:
- Semantic search over large text corpora
- Finding relevant passages in documents
- Understanding natural language queries
- Storing large documents or media files

For those use cases, use the RAG (Retrieval-Augmented Generation) system instead.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.models import MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class MemoryEngine:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self._auto_confirm = False
        self._pending_preferences: list[dict] = []

    # --- Personal Memory ---
    def remember_personal(self, key: str, value: Any,
                           tags: list[str] = None,
                           importance: float = 0.7) -> MemoryEntry:
        return self._store_memory(MemoryType.PERSONAL, key, value, tags, importance)

    def recall_personal(self, key: str) -> Optional[MemoryEntry]:
        return self.store.get_memory(key, MemoryType.PERSONAL)

    def list_personal(self) -> list[MemoryEntry]:
        return self.store.list_memory(MemoryType.PERSONAL)

    def forget_personal(self, key: str, secure: bool = False, audit_reason: Optional[str] = None):
        self.store.delete_memory(key, MemoryType.PERSONAL, secure=secure, audit_reason=audit_reason)

    # --- Workspace Memory ---
    def remember_workspace(self, key: str, value: Any,
                            tags: list[str] = None,
                            importance: float = 0.6) -> MemoryEntry:
        return self._store_memory(MemoryType.WORKSPACE, key, value, tags, importance)

    def recall_workspace(self, key: str) -> Optional[MemoryEntry]:
        return self.store.get_memory(key, MemoryType.WORKSPACE)

    def list_workspace(self) -> list[MemoryEntry]:
        return self.store.list_memory(MemoryType.WORKSPACE)

    def forget_workspace(self, key: str, secure: bool = False, audit_reason: Optional[str] = None):
        self.store.delete_memory(key, MemoryType.WORKSPACE, secure=secure, audit_reason=audit_reason)

    # --- Agent Memory ---
    def remember_agent(self, key: str, value: Any,
                        agent_id: str = "",
                        tags: list[str] = None,
                        importance: float = 0.5) -> MemoryEntry:
        return self._store_memory(MemoryType.AGENT, key, value, tags,
                                   importance, scope=agent_id)

    def recall_agent(self, key: str, agent_id: str = "") -> Optional[MemoryEntry]:
        entries = self.store.list_memory(MemoryType.AGENT, scope=agent_id)
        for e in entries:
            if e.key == key:
                return e
        return None

    def list_agent_memories(self, agent_id: str = "") -> list[MemoryEntry]:
        return self.store.list_memory(MemoryType.AGENT, scope=agent_id)

    def forget_agent(self, key: str, agent_id: str = "", secure: bool = False, audit_reason: Optional[str] = None):
        entries = self.store.list_memory(MemoryType.AGENT, scope=agent_id)
        for e in entries:
            if e.key == key:
                self.store.delete_memory(key, MemoryType.AGENT, secure=secure, audit_reason=audit_reason)
                return

    # --- Project Memory ---
    def remember_project(self, key: str, value: Any,
                          project_id: str = "",
                          tags: list[str] = None,
                          importance: float = 0.6) -> MemoryEntry:
        return self._store_memory(MemoryType.PROJECT, key, value, tags,
                                   importance, scope=project_id)

    def recall_project(self, key: str, project_id: str = "") -> Optional[MemoryEntry]:
        entries = self.store.list_memory(MemoryType.PROJECT, scope=project_id)
        for e in entries:
            if e.key == key:
                return e
        return None

    def list_project_memories(self, project_id: str = "") -> list[MemoryEntry]:
        return self.store.list_memory(MemoryType.PROJECT, scope=project_id)

    def forget_project(self, key: str, project_id: str = "", secure: bool = False, audit_reason: Optional[str] = None):
        entries = self.store.list_memory(MemoryType.PROJECT, scope=project_id)
        for e in entries:
            if e.key == key:
                self.store.delete_memory(key, MemoryType.PROJECT, secure=secure, audit_reason=audit_reason)
                return

    # --- Temporary Memory ---
    def remember_temporary(self, key: str, value: Any,
                            ttl_seconds: int = 3600,
                            tags: list[str] = None) -> MemoryEntry:
        return self._store_memory(MemoryType.TEMPORARY, key, value, tags,
                                   0.3, ttl_seconds=ttl_seconds)

    def recall_temporary(self, key: str) -> Optional[MemoryEntry]:
        entry = self.store.get_memory(key, MemoryType.TEMPORARY)
        if entry and entry.expires_at:
            try:
                exp = datetime.fromisoformat(entry.expires_at.replace("Z", "+00:00"))
                if exp < datetime.utcnow():
                    self.store.delete_memory(key, MemoryType.TEMPORARY)
                    return None
            except Exception:
                pass
        return entry

    def cleanup_expired(self) -> int:
        entries = self.store.list_memory(MemoryType.TEMPORARY)
        now = datetime.utcnow()
        count = 0
        for e in entries:
            if e.expires_at:
                try:
                    exp = datetime.fromisoformat(e.expires_at.replace("Z", "+00:00"))
                    if exp < now:
                        self.store.delete_memory(e.key, MemoryType.TEMPORARY)
                        count += 1
                except Exception:
                    pass
        return count

    # --- Long-Term Memory ---
    def remember_longterm(self, key: str, value: Any,
                           tags: list[str] = None,
                           importance: float = 0.8) -> MemoryEntry:
        return self._store_memory(MemoryType.LONG_TERM, key, value, tags, importance)

    def recall_longterm(self, key: str) -> Optional[MemoryEntry]:
        return self.store.get_memory(key, MemoryType.LONG_TERM)

    def list_longterm(self) -> list[MemoryEntry]:
        return self.store.list_memory(MemoryType.LONG_TERM)

    def forget_longterm(self, key: str, secure: bool = False, audit_reason: Optional[str] = None):
        self.store.delete_memory(key, MemoryType.LONG_TERM, secure=secure, audit_reason=audit_reason)

    # --- Combined ---
    def recall_all(self, key: str) -> list[MemoryEntry]:
        return self.store.search_memory(key)

    def search_all(self, query: str) -> list[MemoryEntry]:
        return self.store.search_memory(query)

    def clear_type(self, memory_type: MemoryType, secure: bool = False, audit_reason: Optional[str] = None):
        self.store.clear_memory_type(memory_type, secure=secure, audit_reason=audit_reason)

    def clear_all(self, secure: bool = False, audit_reason: Optional[str] = None):
        for mt in MemoryType:
            self.store.clear_memory_type(mt, secure=secure, audit_reason=audit_reason)

    def get_stats(self) -> dict:
        entries = []
        for mt in MemoryType:
            entries.extend(self.store.list_memory(mt))
        stats = {}
        for e in entries:
            mt = e.memory_type.value
            stats[mt] = stats.get(mt, 0) + 1
        return {"total": len(entries), "by_type": stats}

    def export_memory(self, memory_type: MemoryType = None) -> str:
        if memory_type:
            entries = self.store.list_memory(memory_type)
        else:
            entries = self.store.list_memory()
        data = []
        for e in entries:
            data.append({"key": e.key, "value": e.value,
                          "type": e.memory_type.value, "tags": e.tags,
                          "importance": e.importance})
        return json.dumps(data, indent=2, default=str)

    def import_memory(self, json_str: str) -> int:
        data = json.loads(json_str)
        count = 0
        for item in data:
            try:
                mt = MemoryType(item.get("type", "personal"))
                self._store_memory(mt, item["key"], item["value"],
                                    item.get("tags"), item.get("importance", 0.5))
                count += 1
            except Exception as e:
                logger.warning("Import memory error: %s", e)
        return count

    def backup(self) -> str:
        return self.export_memory()

    def restore(self, backup_json: str) -> int:
        return self.import_memory(backup_json)

    def reset(self):
        self.clear_all()

    # --- Memory Enhancement Methods ---
    def consolidate_memories(self, importance_threshold: float = 0.7, 
                           max_age_seconds: int = 86400,
                           secure: bool = False, audit_reason: Optional[str] = None) -> int:
        """
        Consolidate important temporary memories into long-term storage.
        
        This method moves important memories from temporary storage to long-term
        storage based on their importance score and age. This helps prevent
        important information from being lost when temporary memories expire.
        
        Args:
            importance_threshold: Minimum importance score (0.0-1.0) for consolidation
            max_age_seconds: Maximum age in seconds for memories to be considered
                           for consolidation (older memories are more likely to be
                           consolidated)
            secure: If True, perform additional secure deletion checks
            audit_reason: Reason for deletion (for audit log)
                           
        Returns:
            Number of memories consolidated
        """
        from datetime import datetime, timedelta
        
        # Get all temporary memories
        temp_memories = self.store.list_memory(MemoryType.TEMPORARY)
        if not temp_memories:
            return 0
            
        now = datetime.utcnow()
        consolidated_count = 0
        
        for memory in temp_memories:
            # Check importance
            if memory.importance < importance_threshold:
                continue
                
            # Check age
            try:
                created = datetime.fromisoformat(memory.created_at.replace("Z", "+00:00"))
                age_seconds = (now - created).total_seconds()
                if age_seconds > max_age_seconds:
                    continue  # Skip very old memories
            except Exception:
                # If we can't parse the date, skip consolidation for safety
                continue
                
# Consolidate to long-term memory
            # Use the same key but change the type to long-term
            long_term_key = f"consolidated_{memory.key}"
            self.remember_longterm(
                key=long_term_key,
                value=memory.value,
                tags=memory.tags + ["consolidated", f"from_{memory.memory_type.value}"],
                importance=memory.importance
            )

            # Delete the original temporary memory
            self.forget_temporary(memory.key, secure=secure, audit_reason=audit_reason)
            consolidated_count += 1
             
            logger.info(f"Consolidated {consolidated_count} temporary memories to long-term storage")
            return consolidated_count

    def forget_less_important(self, memory_type: MemoryType = None, 
                            keep_percentage: float = 0.3,
                            secure: bool = False, audit_reason: Optional[str] = None) -> int:
        """
        Forget less important memories when storage needs to be freed.
        
        This method removes less important memories based on their importance
        score, keeping only the top percentage most important memories.
        
        Args:
            memory_type: Specific memory type to operate on (None for all types)
            keep_percentage: Percentage of memories to keep (0.0-1.0)
                           
        Returns:
            Number of memories forgotten
        """
        if memory_type:
            memory_types = [memory_type]
        else:
            memory_types = list(MemoryType)
             
        total_forgotten = 0
         
        for mem_type in memory_types:
            memories = self.store.list_memory(mem_type)
            if len(memories) <= 1:  # Don't forget if there's only one or none
                continue
                 
            # Sort by importance (descending)
            sorted_memories = sorted(memories, key=lambda m: m.importance, reverse=True)
             
            # Calculate how many to keep
            keep_count = max(1, int(len(sorted_memories) * keep_percentage))
             
            # Forget the less important ones
            to_forget = sorted_memories[keep_count:]
            for memory in to_forget:
                # Skip protected memory types
                if mem_type in [MemoryType.PERSONAL, MemoryType.LONG_TERM]:
                    continue
                     
                self.store.delete_memory(memory.key, mem_type, secure=secure, audit_reason=audit_reason)
                total_forgotten += 1
                 
        if total_forgotten > 0:
            logger.info(f"Forgot {total_forgotten} less important memories")
        return total_forgotten

    # --- Auto Memory ---
    def enable_auto_memory(self):
        self._auto_confirm = True

    def disable_auto_memory(self):
        self._auto_confirm = False

    def suggest_preference(self, key: str, value: Any,
                            category: str = "preference") -> Optional[MemoryEntry]:
        if self._auto_confirm:
            return self.remember_personal(key, value,
                                           tags=[category], importance=0.6)
        self._pending_preferences.append({
            "key": key, "value": value, "category": category,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return None

    def confirm_pending(self, index: int = -1) -> Optional[MemoryEntry]:
        if index >= 0 and index < len(self._pending_preferences):
            pref = self._pending_preferences.pop(index)
        elif self._pending_preferences:
            pref = self._pending_preferences.pop()
        else:
            return None
        return self.remember_personal(pref["key"], pref["value"],
                                       tags=[pref["category"]], importance=0.6)

    def reject_pending(self, index: int = -1):
        if index >= 0 and index < len(self._pending_preferences):
            self._pending_preferences.pop(index)
        elif self._pending_preferences:
            self._pending_preferences.pop()

    def get_pending(self) -> list[dict]:
        return list(self._pending_preferences)

    # --- Internal ---
    def _store_memory(self, memory_type: MemoryType, key: str,
                       value: Any, tags: list[str] = None,
                       importance: float = 0.5,
                       scope: str = "",
                       ttl_seconds: int = None) -> MemoryEntry:
        existing = self.store.get_memory(key, memory_type)
        mid = existing.id if existing else str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        expires = None
        if ttl_seconds:
            expires = (datetime.utcnow() + timedelta(seconds=ttl_seconds)
                       ).isoformat() + "Z"
        entry = MemoryEntry(
            id=mid, memory_type=memory_type, key=str(key),
            value=value, scope=scope,
            tags=tags or [], importance=importance,
            ttl_seconds=ttl_seconds,
            created_at=existing.created_at if existing else now,
            updated_at=now, expires_at=expires)
        self.store.save_memory(entry)
        return entry
