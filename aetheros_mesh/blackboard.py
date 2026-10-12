"""Mesh blackboard for shared state (Master 49 sections 29-30)."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from .models import MeshNode

logger = logging.getLogger(__name__)


@dataclass
class BlackboardEntry:
    """A single entry in the blackboard."""
    key: str
    value: Any
    version: int = 1
    source_agent: str = ""
    source_task: str = ""
    scope: str = "task"  # private, task, project, team, organization, mesh
    authorization: List[str] = field(default_factory=list)  # agent_ids or roles allowed to read
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at
    
    def can_read(self, agent_id: str, agent_roles: List[str] = None) -> bool:
        """Check if agent can read this entry."""
        if not self.authorization:
            return True  # Public by default
        
        if agent_id in self.authorization:
            return True
        
        if agent_roles:
            for role in agent_roles:
                if role in self.authorization:
                    return True
        
        return False
    
    def can_write(self, agent_id: str, agent_roles: List[str] = None) -> bool:
        """Check if agent can write (same as read for now)."""
        return self.can_read(agent_id, agent_roles)


class OptimisticLock:
    """Optimistic locking for blackboard entries."""
    
    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._versions: Dict[str, int] = {}
        self._global_lock = threading.Lock()
    
    def acquire(self, key: str, expected_version: int) -> bool:
        """Try to acquire lock for key at expected version."""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            
            lock = self._locks[key]
            if lock.acquire(blocking=False):
                try:
                    current_version = self._versions.get(key, 0)
                    if current_version == expected_version:
                        return True
                    else:
                        lock.release()
                        return False
                except Exception:
                    lock.release()
                    return False
            return False
    
    def release(self, key: str, new_version: int) -> None:
        """Release lock and update version."""
        with self._global_lock:
            if key in self._locks:
                self._versions[key] = new_version
                self._locks[key].release()
    
    def get_version(self, key: str) -> int:
        """Get current version."""
        return self._versions.get(key, 0)


class MeshBlackboard:
    """Shared blackboard for mesh coordination with locking and access control."""
    
    def __init__(self, home: Path = None, mesh_id: str = ""):
        self.home = Path(home) if home else Path.cwd()
        self.mesh_id = mesh_id
        self._entries: Dict[str, BlackboardEntry] = {}
        self._locks = OptimisticLock()
        self._subscriptions: Dict[str, List[Callable]] = {}  # key_pattern -> callbacks
        self._access_log: List[Dict[str, Any]] = []
        self._max_log_size = 10000
        
        # Persistence
        self._data_file = self.home / f"mesh_blackboard_{mesh_id}.json"
        self._load()
    
    def _load(self) -> None:
        """Load blackboard from disk."""
        if self._data_file.exists():
            try:
                data = json.loads(self._data_file.read_text(encoding="utf-8"))
                for entry_data in data.get("entries", []):
                    entry = BlackboardEntry(**entry_data)
                    if not entry.is_expired():
                        self._entries[entry.key] = entry
                logger.info(f"Loaded {len(self._entries)} blackboard entries")
            except Exception as e:
                logger.warning(f"Failed to load blackboard: {e}")
    
    def _save(self) -> None:
        """Save blackboard to disk."""
        try:
            self.home.mkdir(parents=True, exist_ok=True)
            data = {
                "entries": [asdict(e) for e in self._entries.values()],
                "mesh_id": self.mesh_id,
                "saved_at": time.time(),
            }
            tmp = self._data_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self._data_file)
        except Exception as e:
            logger.warning(f"Failed to save blackboard: {e}")
    
    def put(
        self,
        key: str,
        value: Any,
        source_agent: str = "",
        source_task: str = "",
        scope: str = "task",
        authorization: List[str] = None,
        ttl_s: float = 0,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        expected_version: int = None
    ) -> bool:
        """Write to blackboard with optimistic locking."""
        
        # Check authorization for write
        # (In real implementation, would verify agent identity)
        
        # Optimistic locking
        if expected_version is not None:
            if not self._locks.acquire(key, expected_version):
                raise ConcurrencyError(f"Version conflict for key {key}")
        
        try:
            now = time.time()
            expires = now + ttl_s if ttl_s > 0 else 0
            
            existing = self._entries.get(key)
            version = (existing.version + 1) if existing else 1
            
            entry = BlackboardEntry(
                key=key,
                value=value,
                version=version,
                source_agent=source_agent,
                source_task=source_task,
                scope=scope,
                authorization=authorization or [],
                created_at=existing.created_at if existing else now,
                updated_at=now,
                expires_at=expires,
                tags=tags or [],
                metadata=metadata or {},
            )
            
            self._entries[key] = entry
            
            # Log access
            self._log_access("write", key, source_agent, version)
            
            # Notify subscribers
            self._notify_subscribers(key, entry)
            
            # Release lock with new version
            if expected_version is not None:
                self._locks.release(key, version)
            
            # Periodic save
            if len(self._entries) % 10 == 0:
                self._save()
            
            return True
            
        except Exception as e:
            if expected_version is not None:
                self._locks.release(key, self._locks.get_version(key))
            raise
    
    def get(
        self,
        key: str,
        agent_id: str = "",
        agent_roles: List[str] = None
    ) -> Optional[Any]:
        """Read from blackboard with access control."""
        
        entry = self._entries.get(key)
        if not entry:
            return None
        
        if entry.is_expired():
            del self._entries[key]
            return None
        
        # Check read authorization
        if not entry.can_read(agent_id, agent_roles):
            self._log_access("denied_read", key, agent_id, entry.version)
            raise AuthorizationError(f"Agent {agent_id} not authorized to read {key}")
        
        # Log access
        self._log_access("read", key, agent_id, entry.version)
        
        return entry.value
    
    def get_entry(self, key: str) -> Optional[BlackboardEntry]:
        """Get full entry metadata."""
        entry = self._entries.get(key)
        if entry and entry.is_expired():
            del self._entries[key]
            return None
        return entry
    
    def get_version(self, key: str) -> int:
        """Get current version of a key."""
        return self._locks.get_version(key)
    
    def delete(self, key: str, agent_id: str = "") -> bool:
        """Delete an entry."""
        entry = self._entries.get(key)
        if not entry:
            return False
        
        if not entry.can_write(agent_id):
            raise AuthorizationError(f"Agent {agent_id} not authorized to delete {key}")
        
        del self._entries[key]
        self._log_access("delete", key, agent_id, entry.version)
        return True
    
    def compare_and_swap(
        self,
        key: str,
        expected_value: Any,
        new_value: Any,
        source_agent: str = "",
        source_task: str = "",
        **kwargs
    ) -> bool:
        """Atomic compare-and-swap operation."""
        entry = self._entries.get(key)
        if not entry:
            return False
        
        if entry.value != expected_value:
            return False
        
        return self.put(
            key, new_value,
            source_agent=source_agent,
            source_task=source_task,
            expected_version=entry.version,
            **kwargs
        )
    
    def increment(self, key: str, delta: int = 1, **kwargs) -> Optional[int]:
        """Atomically increment a numeric value."""
        entry = self._entries.get(key)
        if not entry:
            return None
        
        current = entry.value
        if not isinstance(current, (int, float)):
            return None
        
        new_value = current + delta
        if self.compare_and_swap(key, current, new_value, **kwargs):
            return new_value
        return None
    
    def append_to_list(self, key: str, item: Any, **kwargs) -> bool:
        """Atomically append to a list."""
        entry = self._entries.get(key)
        if not entry:
            return self.put(key, [item], **kwargs)
        
        current = entry.value
        if not isinstance(current, list):
            return False
        
        new_list = current + [item]
        return self.compare_and_swap(key, current, new_list, **kwargs)
    
    def get_view(
        self, 
        agent_id: str, 
        agent_roles: List[str] = None,
        scope: str = None
    ) -> Dict[str, Any]:
        """Get a view of the blackboard filtered by agent authorization and scope."""
        view = {}
        for key, entry in self._entries.items():
            if entry.is_expired():
                continue
            
            if scope and entry.scope != scope:
                continue
            
            if entry.can_read(agent_id, agent_roles):
                view[key] = entry.value
        
        return view
    
    def query(
        self,
        tags: List[str] = None,
        scope: str = None,
        source_agent: str = None,
        source_task: str = None,
        agent_id: str = "",
        agent_roles: List[str] = None,
    ) -> Dict[str, Any]:
        """Query blackboard entries by criteria."""
        results = {}
        
        for key, entry in self._entries.items():
            if entry.is_expired():
                continue
            
            if not entry.can_read(agent_id, agent_roles):
                continue
            
            if tags and not any(t in entry.tags for t in tags):
                continue
            
            if scope and entry.scope != scope:
                continue
            
            if source_agent and entry.source_agent != source_agent:
                continue
            
            if source_task and entry.source_task != source_task:
                continue
            
            results[key] = entry.value
        
        return results
    
    def subscribe(self, key_pattern: str, callback: Callable[[str, BlackboardEntry], None]) -> str:
        """Subscribe to key changes (pattern matching)."""
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        self._subscriptions.setdefault(key_pattern, []).append(callback)
        return sub_id
    
    def unsubscribe(self, key_pattern: str, callback: Callable) -> bool:
        """Unsubscribe from key changes."""
        if key_pattern in self._subscriptions:
            try:
                self._subscriptions[key_pattern].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def _notify_subscribers(self, key: str, entry: BlackboardEntry) -> None:
        """Notify subscribers of key changes."""
        for pattern, callbacks in self._subscriptions.items():
            if self._match_pattern(key, pattern):
                for callback in callbacks:
                    try:
                        callback(key, entry)
                    except Exception as e:
                        logger.debug(f"Subscriber callback failed: {e}")
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)."""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return key.endswith(pattern[1:])
        return key == pattern
    
    def _log_access(self, operation: str, key: str, agent_id: str, version: int) -> None:
        """Log access for audit."""
        self._access_log.append({
            "operation": operation,
            "key": key,
            "agent_id": agent_id,
            "version": version,
            "timestamp": time.time(),
        })
        
        # Trim log
        if len(self._access_log) > self._max_log_size:
            self._access_log = self._access_log[-self._max_log_size:]
    
    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent access log."""
        return self._access_log[-limit:]
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._entries.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._entries[key]
        
        if expired_keys:
            self._save()
        
        return len(expired_keys)
    
    def clear_scope(self, scope: str, agent_id: str = "") -> int:
        """Clear all entries in a scope (with authorization)."""
        keys_to_delete = [
            key for key, entry in self._entries.items()
            if entry.scope == scope and entry.can_write(agent_id)
        ]
        
        for key in keys_to_delete:
            del self._entries[key]
        
        if keys_to_delete:
            self._save()
        
        return len(keys_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get blackboard statistics."""
        scopes = {}
        for entry in self._entries.values():
            scopes[entry.scope] = scopes.get(entry.scope, 0) + 1
        
        return {
            "total_entries": len(self._entries),
            "scopes": scopes,
            "subscriptions": len(self._subscriptions),
            "access_log_size": len(self._access_log),
        }


class ConcurrencyError(Exception):
    """Raised when optimistic lock fails."""
    pass


class AuthorizationError(Exception):
    """Raised when access control denies operation."""
    pass


def create_blackboard(home: Path = None, mesh_id: str = "") -> MeshBlackboard:
    """Factory function to create a MeshBlackboard."""
    return MeshBlackboard(home, mesh_id)