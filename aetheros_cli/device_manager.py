"""
Device management system for AetherOS Cloud Sync.

Provides device registration with fingerprinting, device authentication
(token + signature), session management with token rotation, device
revocation and renaming, online/offline status tracking, last active
tracking, per-device permissions, and audit logging.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEVICES_VERSION = 1
_SESSION_TOKEN_BYTES = 32
_DEFAULT_SESSION_TTL = 86400 * 7  # 7 days
_AUDIT_LOG_MAX = 1000


# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------

PERMISSION_SYNC = "sync"
PERMISSION_READ = "read"
PERMISSION_WRITE = "write"
PERMISSION_ADMIN = "admin"
PERMISSION_AGENT_CONTROL = "agent_control"
PERMISSION_REMOTE_ACCESS = "remote_access"

ALL_PERMISSIONS: Set[str] = {
    PERMISSION_SYNC,
    PERMISSION_READ,
    PERMISSION_WRITE,
    PERMISSION_ADMIN,
    PERMISSION_AGENT_CONTROL,
    PERMISSION_REMOTE_ACCESS,
}

DEFAULT_PERMISSIONS: Set[str] = {
    PERMISSION_SYNC,
    PERMISSION_READ,
    PERMISSION_WRITE,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DeviceInfo:
    """Describes a registered device in the AetherOS sync network."""
    device_id: str
    name: str
    os: str
    version: str
    last_active: float
    online: bool
    sync_status: str
    permissions: Set[str]
    public_key: str
    created_at: float
    fingerprint: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    is_revoked: bool = False
    revoked_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "os": self.os,
            "version": self.version,
            "last_active": self.last_active,
            "online": self.online,
            "sync_status": self.sync_status,
            "permissions": list(self.permissions),
            "public_key": self.public_key,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
            "tags": self.tags,
            "is_revoked": self.is_revoked,
            "revoked_at": self.revoked_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceInfo:
        return cls(
            device_id=data["device_id"],
            name=data.get("name", ""),
            os=data.get("os", ""),
            version=data.get("version", ""),
            last_active=data.get("last_active", 0.0),
            online=data.get("online", False),
            sync_status=data.get("sync_status", "idle"),
            permissions=set(data.get("permissions", [])),
            public_key=data.get("public_key", ""),
            created_at=data.get("created_at", 0.0),
            fingerprint=data.get("fingerprint", ""),
            tags=data.get("tags", {}),
            is_revoked=data.get("is_revoked", False),
            revoked_at=data.get("revoked_at", 0.0),
        )


@dataclass
class DeviceSession:
    """An active session for a registered device."""
    session_id: str
    device_id: str
    token: str
    created_at: float
    expires_at: float
    rotated_at: float = 0.0
    ip_address: str = ""
    user_agent: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "token": self.token,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "rotated_at": self.rotated_at,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceSession:
        return cls(
            session_id=data["session_id"],
            device_id=data["device_id"],
            token=data.get("token", ""),
            created_at=data.get("created_at", 0.0),
            expires_at=data.get("expires_at", 0.0),
            rotated_at=data.get("rotated_at", 0.0),
            ip_address=data.get("ip_address", ""),
            user_agent=data.get("user_agent", ""),
        )


@dataclass
class DeviceAuthChallenge:
    """A secure challenge for pairing a new device.

    The pairing flow:
      1. Primary device creates a challenge with a short-lived token.
      2. New device signs the challenge with its private key.
      3. Primary device verifies the signature and registers the device.
    """
    challenge_id: str
    device_name: str
    nonce: str
    created_at: float
    expires_at: float
    token: str
    claimed: bool = False
    claimed_by: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "device_name": self.device_name,
            "nonce": self.nonce,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "token": self.token,
            "claimed": self.claimed,
            "claimed_by": self.claimed_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceAuthChallenge:
        return cls(
            challenge_id=data["challenge_id"],
            device_name=data.get("device_name", ""),
            nonce=data.get("nonce", ""),
            created_at=data.get("created_at", 0.0),
            expires_at=data.get("expires_at", 0.0),
            token=data.get("token", ""),
            claimed=data.get("claimed", False),
            claimed_by=data.get("claimed_by", ""),
        )


@dataclass
class AuditEntry:
    """An audit log entry for device management actions."""
    action: str
    device_id: str
    actor_device_id: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "device_id": self.device_id,
            "actor_device_id": self.actor_device_id,
            "timestamp": self.timestamp,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEntry:
        return cls(
            id=data.get("id", ""),
            action=data["action"],
            device_id=data["device_id"],
            actor_device_id=data.get("actor_device_id", ""),
            timestamp=data["timestamp"],
            details=data.get("details", {}),
        )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _devices_dir() -> Path:
    return get_aetheros_home() / "sync" / "devices"


def _devices_db_path() -> Path:
    return _devices_dir() / "devices.json"


def _sessions_path() -> Path:
    return _devices_dir() / "sessions.json"


def _challenges_path() -> Path:
    return _devices_dir() / "challenges.json"


def _audit_log_path() -> Path:
    return _devices_dir() / "audit.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.error("Failed to save %s: %s", path.name, exc)
        raise


def _generate_token() -> str:
    return hashlib.sha256(os.urandom(64)).hexdigest()


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# DeviceManager
# ---------------------------------------------------------------------------


class DeviceManager:
    """Manages device registration, authentication, sessions, and permissions.

    Provides the full lifecycle for devices in the AetherOS sync network,
    including secure pairing via auth challenges, token-based sessions with
    rotation, device revocation, and audit logging.
    """

    def __init__(self, local_device_id: str) -> None:
        """Initialize the device manager.

        Args:
            local_device_id: The device ID of the local (this) device.
        """
        self._local_device_id = local_device_id
        self._devices: Dict[str, DeviceInfo] = {}
        self._sessions: Dict[str, DeviceSession] = {}
        self._challenges: Dict[str, DeviceAuthChallenge] = {}
        self._audit_log: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._session_token_ttl = _DEFAULT_SESSION_TTL

        self._devices_dir = _devices_dir()
        self._devices_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def local_device_id(self) -> str:
        return self._local_device_id

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_persisted(self) -> None:
        raw_devices = _load_json(_devices_db_path(), {})
        self._devices = {
            did: DeviceInfo.from_dict(d) for did, d in raw_devices.items()
        }

        raw_sessions = _load_json(_sessions_path(), {})
        self._sessions = {
            sid: DeviceSession.from_dict(s) for sid, s in raw_sessions.items()
        }

        raw_challenges = _load_json(_challenges_path(), {})
        self._challenges = {
            cid: DeviceAuthChallenge.from_dict(c)
            for cid, c in raw_challenges.items()
        }

        raw_audit = _load_json(_audit_log_path(), [])
        self._audit_log = [AuditEntry.from_dict(a) for a in raw_audit]

        logger.debug(
            "Loaded device state: %d devices, %d sessions, %d challenges, %d audit entries",
            len(self._devices), len(self._sessions),
            len(self._challenges), len(self._audit_log),
        )

    def _save(self) -> None:
        with self._lock:
            _save_json(_devices_db_path(), {
                did: d.to_dict() for did, d in self._devices.items()
            })
            _save_json(_sessions_path(), {
                sid: s.to_dict() for sid, s in self._sessions.items()
            })
            _save_json(_challenges_path(), {
                cid: c.to_dict() for cid, c in self._challenges.items()
            })
            audit_slice = self._audit_log[-_AUDIT_LOG_MAX:]
            _save_json(_audit_log_path(), [a.to_dict() for a in audit_slice])

    def _log_audit(
        self,
        action: str,
        device_id: str,
        actor_device_id: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = AuditEntry(
            action=action,
            device_id=device_id,
            actor_device_id=actor_device_id or self._local_device_id,
            timestamp=_now(),
            details=details or {},
        )
        self._audit_log.append(entry)
        logger.info("Audit: %s -> %s (%s)", entry.actor_device_id, action, device_id)

    # ------------------------------------------------------------------
    # Device registration
    # ------------------------------------------------------------------

    def register_device(
        self,
        name: str,
        public_key: str,
        os: str = "",
        version: str = "",
        fingerprint: str = "",
        permissions: Optional[Set[str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> DeviceInfo:
        """Register a new device in the sync network.

        Args:
            name: Human-readable device name.
            public_key: PEM-encoded RSA public key for the device.
            os: Operating system identifier.
            version: AetherOS version on the device.
            fingerprint: Optional SHA-256 fingerprint of the public key.
            permissions: Set of permission strings. Defaults to
                ``{sync, read, write}``.
            tags: Optional metadata tags.

        Returns:
            The newly created :class:`DeviceInfo`.

        Raises:
            ValueError: If a device with the same public key is already
                registered.
        """
        device_id = str(uuid.uuid4())

        with self._lock:
            for existing in self._devices.values():
                if existing.public_key == public_key and not existing.is_revoked:
                    raise ValueError(
                        "A device with this public key is already registered"
                    )

            if fingerprint and not fingerprint.strip():
                fingerprint = hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:16]

            info = DeviceInfo(
                device_id=device_id,
                name=name,
                os=os,
                version=version,
                last_active=_now(),
                online=False,
                sync_status="pending",
                permissions=permissions or set(DEFAULT_PERMISSIONS),
                public_key=public_key,
                created_at=_now(),
                fingerprint=fingerprint,
                tags=tags or {},
            )
            self._devices[device_id] = info

        self._save()
        self._log_audit("device_register", device_id, details={"name": name})
        logger.info("Registered device '%s' (%s)", name, device_id)
        return info

    def unregister_device(self, device_id: str) -> bool:
        """Remove a device registration entirely.

        This is a hard delete — unlike revocation, the device cannot
        re-register with the same ID.
        """
        with self._lock:
            if device_id not in self._devices:
                return False
            del self._devices[device_id]
            expired_sessions = [
                sid for sid, s in self._sessions.items()
                if s.device_id == device_id
            ]
            for sid in expired_sessions:
                del self._sessions[sid]

        self._save()
        self._log_audit("device_unregister", device_id)
        return True

    # ------------------------------------------------------------------
    # Device authentication
    # ------------------------------------------------------------------

    def create_auth_challenge(
        self,
        device_name: str,
        ttl: int = 300,
    ) -> DeviceAuthChallenge:
        """Create a secure pairing challenge for a new device.

        The challenge must be signed by the new device's private key
        and verified via :meth:`verify_auth_challenge`.

        Args:
            device_name: The name of the device requesting pairing.
            ttl: Challenge TTL in seconds (default: 300).

        Returns:
            A :class:`DeviceAuthChallenge`.
        """
        challenge_id = str(uuid.uuid4())
        nonce = hashlib.sha256(os.urandom(64)).hexdigest()
        now = _now()

        challenge = DeviceAuthChallenge(
            challenge_id=challenge_id,
            device_name=device_name,
            nonce=nonce,
            created_at=now,
            expires_at=now + ttl,
            token=_generate_token(),
        )
        with self._lock:
            self._challenges[challenge_id] = challenge

        self._save()
        logger.debug("Auth challenge created: %s for '%s'", challenge_id, device_name)
        return challenge

    def verify_auth_challenge(
        self,
        challenge_id: str,
        signature: str,
        public_key: str,
        verify_signature_fn: Optional[Any] = None,
    ) -> Optional[DeviceInfo]:
        """Verify a signed auth challenge and register the device.

        Args:
            challenge_id: The challenge ID to verify.
            signature: Base64-encoded signature of the challenge nonce.
            public_key: PEM-encoded public key of the requesting device.
            verify_signature_fn: Optional callable to verify the signature.
                If not provided, signature verification is skipped (the
                caller is responsible for verifying).

        Returns:
            The registered :class:`DeviceInfo` on success, or None.
        """
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if challenge is None:
                logger.warning("Unknown auth challenge: %s", challenge_id)
                return None
            if challenge.is_expired:
                logger.warning("Auth challenge expired: %s", challenge_id)
                return None
            if challenge.claimed:
                logger.warning("Auth challenge already claimed: %s", challenge_id)
                return None

            challenge.claimed = True
            challenge.claimed_by = public_key[:32]

        self._save()

        fingerprint = hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:16]
        info = self.register_device(
            name=challenge.device_name,
            public_key=public_key,
            fingerprint=fingerprint,
        )
        self._log_audit("auth_challenge_verified", info.device_id)
        return info

    def authenticate_device(
        self,
        device_id: str,
        token: str,
    ) -> Optional[DeviceSession]:
        """Authenticate a device using a session token.

        Args:
            device_id: The device's ID.
            token: The session token to validate.

        Returns:
            The active :class:`DeviceSession` on success, or None.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                logger.warning("Auth failed: unknown device %s", device_id)
                return None
            if device.is_revoked:
                logger.warning("Auth failed: revoked device %s", device_id)
                return None

            for session in self._sessions.values():
                if session.device_id == device_id and session.token == token:
                    if session.is_expired:
                        logger.debug("Auth failed: expired session for %s", device_id)
                        return None
                    session.expires_at = _now() + self._session_token_ttl
                    device.last_active = _now()
                    device.online = True
                    self._save()
                    return session

        logger.warning("Auth failed: invalid token for %s", device_id)
        return None

    def authenticate_device_by_signature(
        self,
        device_id: str,
        nonce: str,
        signature: str,
        verify_signature_fn: Any,
    ) -> bool:
        """Authenticate a device using a challenge-response signature.

        Args:
            device_id: The device's ID.
            nonce: A random nonce that was sent to the device.
            signature: The signed nonce returned by the device.
            verify_signature_fn: A callable ``fn(data, public_key) -> bool``.

        Returns:
            True if the signature is valid for the device's public key.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            if device.is_revoked:
                return False

        try:
            valid = verify_signature_fn(nonce.encode("utf-8"), device.public_key)
        except Exception as exc:
            logger.warning("Signature verification error for %s: %s", device_id, exc)
            return False

        if valid:
            self.update_last_active(device_id)
            self._log_audit("device_auth_signature", device_id)

        return valid

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        device_id: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> DeviceSession:
        """Create a new session token for a device.

        Previous sessions for the same device are NOT invalidated (multiple
        concurrent sessions are allowed).

        Args:
            device_id: The registered device ID.
            ip_address: Optional IP address of the connecting device.
            user_agent: Optional client user-agent string.

        Returns:
            The new :class:`DeviceSession`.
        """
        session_id = str(uuid.uuid4())
        now = _now()
        session = DeviceSession(
            session_id=session_id,
            device_id=device_id,
            token=_generate_token(),
            created_at=now,
            expires_at=now + self._session_token_ttl,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self._sessions[session_id] = session
            device = self._devices.get(device_id)
            if device:
                device.last_active = now
                device.online = True

        self._save()
        self._log_audit("session_created", device_id)
        logger.debug("Session created for %s: %s", device_id, session_id)
        return session

    def rotate_token(self, session_id: str) -> Optional[str]:
        """Rotate the token for an existing session.

        Returns the new token string, or None if the session was not found
        or has expired.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired:
                return None
            session.token = _generate_token()
            session.rotated_at = _now()
            session.expires_at = _now() + self._session_token_ttl

        self._save()
        self._log_audit("token_rotated", session.device_id)
        return session.token

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session by ID."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False
        self._save()
        self._log_audit("session_revoked", session.device_id)
        return True

    def revoke_all_sessions(self, device_id: str) -> int:
        """Revoke all sessions for a given device.

        Returns the number of sessions revoked.
        """
        count = 0
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if s.device_id == device_id
            ]
            for sid in expired:
                del self._sessions[sid]
                count += 1
        if count:
            self._save()
            self._log_audit("all_sessions_revoked", device_id)
        return count

    # ------------------------------------------------------------------
    # Device lifecycle
    # ------------------------------------------------------------------

    def revoke_device(self, device_id: str) -> bool:
        """Revoke a device, invalidating all its sessions.

        A revoked device cannot authenticate or sync until it is
        re-registered. Returns True if the device was found and revoked.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.is_revoked = True
            device.revoked_at = _now()
            device.online = False

            expired = [
                sid for sid, s in self._sessions.items()
                if s.device_id == device_id
            ]
            for sid in expired:
                del self._sessions[sid]

        self._save()
        self._log_audit("device_revoked", device_id)
        logger.info("Device revoked: %s (%s)", device.name, device_id)
        return True

    def rename_device(self, device_id: str, new_name: str) -> bool:
        """Rename a registered device.

        Returns True if the device was found and renamed.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            old_name = device.name
            device.name = new_name
        self._save()
        self._log_audit("device_renamed", device_id, details={"old_name": old_name, "new_name": new_name})
        logger.info("Device '%s' renamed to '%s'", device_id, new_name)
        return True

    def set_online_status(self, device_id: str, online: bool) -> bool:
        """Update the online/offline status for a device.

        Returns True if the device was found.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.online = online
            if online:
                device.last_active = _now()
        self._save()
        return True

    def update_last_active(self, device_id: str) -> bool:
        """Update the last-active timestamp for a device."""
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.last_active = _now()
        self._save()
        return True

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def check_permission(self, device_id: str, permission: str) -> bool:
        """Check whether a device has a specific permission.

        Returns True if the device exists, is not revoked, and has the
        requested permission.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            if device.is_revoked:
                return False
            return permission in device.permissions

    def set_permissions(self, device_id: str, permissions: Set[str]) -> bool:
        """Replace the permission set for a device.

        Returns True if the device was found.
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            old_perms = set(device.permissions)
            device.permissions = set(permissions)
        self._save()
        self._log_audit("permissions_updated", device_id, details={
            "old": list(old_perms), "new": list(permissions),
        })
        return True

    def grant_permission(self, device_id: str, permission: str) -> bool:
        """Grant a single permission to a device."""
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            if permission not in ALL_PERMISSIONS:
                raise ValueError(f"Unknown permission: '{permission}'")
            device.permissions.add(permission)
        self._save()
        self._log_audit("permission_granted", device_id, details={"permission": permission})
        return True

    def revoke_permission(self, device_id: str, permission: str) -> bool:
        """Revoke a single permission from a device."""
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.permissions.discard(permission)
        self._save()
        self._log_audit("permission_revoked", device_id, details={"permission": permission})
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_devices(self, include_revoked: bool = False) -> List[DeviceInfo]:
        """Return all registered devices.

        Args:
            include_revoked: If True, include revoked devices in the list.

        Returns:
            A list of :class:`DeviceInfo` objects.
        """
        with self._lock:
            results = list(self._devices.values())
        if not include_revoked:
            results = [d for d in results if not d.is_revoked]
        return sorted(results, key=lambda d: d.created_at, reverse=True)

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Return info for a specific device."""
        with self._lock:
            return self._devices.get(device_id)

    def get_device_by_fingerprint(self, fingerprint: str) -> Optional[DeviceInfo]:
        """Find a device by its public key fingerprint."""
        with self._lock:
            for device in self._devices.values():
                if device.fingerprint == fingerprint:
                    return device
        return None

    def get_active_sessions(self, device_id: Optional[str] = None) -> List[DeviceSession]:
        """Return active (non-expired) sessions.

        Args:
            device_id: If set, only return sessions for this device.
        """
        now = _now()
        with self._lock:
            results = [
                s for s in self._sessions.values()
                if s.expires_at > now
            ]
        if device_id:
            results = [s for s in results if s.device_id == device_id]
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def get_device_sessions(self, device_id: str) -> List[DeviceSession]:
        """Return all sessions (including expired) for a device."""
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.device_id == device_id
            ]

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def get_audit_log(
        self,
        device_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Return the audit log, optionally filtered by device.

        Args:
            device_id: If set, only return entries for this device.
            limit: Maximum number of entries (most recent first).

        Returns:
            A list of :class:`AuditEntry` objects.
        """
        with self._lock:
            results = list(self._audit_log)
        if device_id:
            results = [e for e in results if e.device_id == device_id]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def purge_expired_sessions(self) -> int:
        """Remove all expired sessions.

        Returns the number of sessions purged.
        """
        now = _now()
        count = 0
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if s.expires_at <= now
            ]
            for sid in expired:
                del self._sessions[sid]
                count += 1
        if count:
            self._save()
            logger.debug("Purged %d expired sessions", count)
        return count

    def purge_expired_challenges(self) -> int:
        """Remove all expired auth challenges."""
        now = _now()
        count = 0
        with self._lock:
            expired = [
                cid for cid, c in self._challenges.items()
                if c.expires_at <= now
            ]
            for cid in expired:
                del self._challenges[cid]
                count += 1
        if count:
            self._save()
        return count
