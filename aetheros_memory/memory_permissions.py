"""Memory Permissions — access control and data-at-rest obfuscation.

Manages permission levels, access checks, content encryption/decryption,
and sensitive data detection with redaction.
"""

from __future__ import annotations

import base64
import enum
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_memory.permissions")


class PermissionLevel(str, enum.Enum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    SHARED = "shared"
    TEMPORARY = "temporary"
    ENCRYPTED = "encrypted"
    PUBLIC = "public"
    SENSITIVE = "sensitive"


@dataclass
class PermissionEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str = ""
    level: PermissionLevel = PermissionLevel.PRIVATE
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    allowed_workspaces: List[str] = field(default_factory=list)
    encryption_key_hash: str = ""
    expires_at: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at


@dataclass
class AccessControl:
    user_id: str = ""
    workspace_id: str = ""
    roles: List[str] = field(default_factory=list)
    is_admin: bool = False


_SENSITIVE_PATTERNS: List[re.Pattern] = [
    re.compile(r'sk-\w{20,}', re.IGNORECASE),
    re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+={0,2}', re.IGNORECASE),
    re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----'),
    re.compile(r'(?:mongodb(?:\+srv)?|postgresql|mysql|redis)://\S+', re.IGNORECASE),
    re.compile(r'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}', re.IGNORECASE),
    re.compile(r'(?:oauth|refresh_token|access_token)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:api[_-]?key|apikey)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:secret|client_secret)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
    re.compile(r'(?:token|auth_token)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:session|cookie)\s*[:=]\s*[A-Za-z0-9%]{20,}', re.IGNORECASE),
]


class MemoryPermissions:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._permissions: Dict[str, PermissionEntry] = {}
        self._encryption_keys: Dict[str, str] = {}

    def set_permission(
        self,
        memory_id: str,
        level: PermissionLevel = PermissionLevel.PRIVATE,
        allowed_users: Optional[List[str]] = None,
        allowed_roles: Optional[List[str]] = None,
        allowed_workspaces: Optional[List[str]] = None,
        encryption_key_hash: str = "",
        expires_at: float = 0.0,
    ) -> PermissionEntry:
        entry = PermissionEntry(
            memory_id=memory_id,
            level=level,
            allowed_users=allowed_users or [],
            allowed_roles=allowed_roles or [],
            allowed_workspaces=allowed_workspaces or [],
            encryption_key_hash=encryption_key_hash,
            expires_at=expires_at,
        )
        with self._lock:
            self._permissions[memory_id] = entry
        logger.debug("Permission set for memory %s: %s", memory_id, level.value)
        return entry

    def get_permission(self, memory_id: str) -> Optional[PermissionEntry]:
        with self._lock:
            entry = self._permissions.get(memory_id)
            if entry is None:
                return None
            if entry.is_expired:
                return None
            return entry

    def check_access(self, memory_id: str, access: AccessControl) -> bool:
        with self._lock:
            entry = self._permissions.get(memory_id)
            if entry is None:
                return False
            if entry.is_expired:
                return False
        if access.is_admin:
            return True
        if entry.level == PermissionLevel.PUBLIC:
            return True
        if entry.level == PermissionLevel.PRIVATE:
            return access.user_id in entry.allowed_users
        if entry.level == PermissionLevel.WORKSPACE:
            if access.workspace_id in entry.allowed_workspaces:
                return True
            return access.user_id in entry.allowed_users
        if entry.level == PermissionLevel.SHARED:
            if access.user_id in entry.allowed_users:
                return True
            if any(r in entry.allowed_roles for r in access.roles):
                return True
            if access.workspace_id in entry.allowed_workspaces:
                return True
            return False
        if entry.level in (PermissionLevel.ENCRYPTED, PermissionLevel.SENSITIVE):
            if access.user_id in entry.allowed_users:
                return True
            if any(r in entry.allowed_roles for r in access.roles):
                return True
            return False
        if entry.level == PermissionLevel.TEMPORARY:
            return True
        return False

    def check_access_batch(self, memory_ids: List[str], access: AccessControl) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for mid in memory_ids:
            results[mid] = self.check_access(mid, access)
        return results

    def filter_by_access(self, memory_ids: List[str], access: AccessControl) -> List[str]:
        accessible: List[str] = []
        for mid in memory_ids:
            if self.check_access(mid, access):
                accessible.append(mid)
        return accessible

    def encrypt_content(self, content: str, key: str) -> str:
        key_bytes = key.encode("utf-8")
        content_bytes = content.encode("utf-8")
        key_len = len(key_bytes)
        xored = bytearray()
        for i, b in enumerate(content_bytes):
            xored.append(b ^ key_bytes[i % key_len])
        return base64.b64encode(bytes(xored)).decode("ascii")

    def decrypt_content(self, encrypted: str, key: str) -> str:
        key_bytes = key.encode("utf-8")
        encrypted_bytes = base64.b64decode(encrypted)
        key_len = len(key_bytes)
        xored = bytearray()
        for i, b in enumerate(encrypted_bytes):
            xored.append(b ^ key_bytes[i % key_len])
        return xored.decode("utf-8")

    def is_sensitive(self, content: str) -> bool:
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.search(content):
                return True
        return False

    def mask_sensitive(self, content: str) -> str:
        result = content
        for pattern in _SENSITIVE_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def expire_permission(self, memory_id: str) -> bool:
        with self._lock:
            entry = self._permissions.get(memory_id)
            if entry is None:
                return False
            entry.expires_at = time.time()
        return True

    def set_encryption_key(self, memory_id: str, key: str) -> bool:
        with self._lock:
            entry = self._permissions.get(memory_id)
            if entry is None:
                return False
            self._encryption_keys[memory_id] = key
            entry.encryption_key_hash = str(hash(key))
        logger.debug("Encryption key set for memory %s", memory_id)
        return True

    def delete_permission(self, memory_id: str) -> bool:
        with self._lock:
            existed = self._permissions.pop(memory_id, None) is not None
            self._encryption_keys.pop(memory_id, None)
        return existed

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            level_counts: Dict[str, int] = {}
            expired = 0
            now = time.time()
            for entry in self._permissions.values():
                level_counts[entry.level.value] = level_counts.get(entry.level.value, 0) + 1
                if entry.expires_at > 0 and now > entry.expires_at:
                    expired += 1
            return {
                "total_permissions": len(self._permissions),
                "by_level": level_counts,
                "expired": expired,
                "encryption_keys_count": len(self._encryption_keys),
            }
