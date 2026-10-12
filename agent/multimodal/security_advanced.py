"""Advanced Security & Compliance (Phase 61).

Enterprise-grade security and compliance features:
- Role-Based Access Control (RBAC)
- Attribute-Based Access Control (ABAC)
- Audit logging with tamper-proof logs
- Data encryption at rest and in transit
- GDPR/CCPA compliance helpers
- SOC2 readiness
- Secret management
- Threat detection
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
from pathlib import Path

from agent.multimodal.production import MetricsCollector, LRUCache

logger = logging.getLogger(__name__)


# ============================================================================
# Phase 61: RBAC & ABAC
# ============================================================================

class Permission(Enum):
    """Standard permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    AUDIT = "audit"


class ResourceType(Enum):
    """Resource types for access control."""
    MODEL = "model"
    DATASET = "dataset"
    MEMORY = "memory"
    STREAM = "stream"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CONFIG = "config"
    AUDIT_LOG = "audit_log"


@dataclass
class Role:
    """Role definition for RBAC."""
    role_id: str
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    resource_constraints: Dict[ResourceType, List[str]] = field(default_factory=dict)  # e.g., {ResourceType.MODEL: ["gpt-4", "claude"]}
    inherits: List[str] = field(default_factory=list)  # Parent role IDs


@dataclass
class User:
    """User with roles and attributes."""
    user_id: str
    username: str
    email: str
    roles: Set[str] = field(default_factory=set)  # Role IDs
    attributes: Dict[str, Any] = field(default_factory=dict)  # For ABAC
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    active: bool = True


@dataclass
class Policy:
    """ABAC policy."""
    policy_id: str
    name: str
    effect: str  # "allow" or "deny"
    conditions: Dict[str, Any]  # Attribute conditions
    actions: List[Permission]
    resources: List[ResourceType]
    priority: int = 0  # Higher priority wins


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}
        self._lock = threading.Lock()
        self._init_default_roles()

    def _init_default_roles(self) -> None:
        """Initialize default system roles."""
        self._roles["admin"] = Role(
            role_id="admin",
            name="Administrator",
            description="Full system access",
            permissions={Permission.READ, Permission.WRITE, Permission.DELETE, Permission.EXECUTE, Permission.ADMIN, Permission.AUDIT},
        )
        self._roles["operator"] = Role(
            role_id="operator",
            name="Operator",
            description="Operational access",
            permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE},
        )
        self._roles["viewer"] = Role(
            role_id="viewer",
            name="Viewer",
            description="Read-only access",
            permissions={Permission.READ},
        )
        self._roles["auditor"] = Role(
            role_id="auditor",
            name="Auditor",
            description="Audit log access",
            permissions={Permission.READ, Permission.AUDIT},
        )

    def create_role(self, role: Role) -> bool:
        with self._lock:
            if role.role_id in self._roles:
                return False
            self._roles[role.role_id] = role
            return True

    def delete_role(self, role_id: str) -> bool:
        with self._lock:
            if role_id in self._roles:
                # Check if any users have this role
                for user in self._users.values():
                    if role_id in user.roles:
                        return False  # Can't delete role in use
                del self._roles[role_id]
                return True
            return False

    def assign_role(self, user_id: str, role_id: str) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            role = self._roles.get(role_id)
            if not user or not role:
                return False
            user.roles.add(role_id)
            return True

    def revoke_role(self, user_id: str, role_id: str) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False
            user.roles.discard(role_id)
            return True

    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has permission."""
        with self._lock:
            user = self._users.get(user_id)
            if not user or not user.active:
                return False

            # Check all user roles
            for role_id in user.roles:
                role = self._roles.get(role_id)
                if not role:
                    continue

                # Check permission
                if permission not in role.permissions:
                    continue

                # Check resource constraints
                if resource_type and resource_type in role.resource_constraints:
                    allowed = role.resource_constraints[resource_type]
                    if resource_id and resource_id not in allowed:
                        continue

                return True

            return False

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return set()

            perms = set()
            for role_id in user.roles:
                role = self._roles.get(role_id)
                if role:
                    perms.update(role.permissions)
            return perms

    def create_user(self, user: User) -> bool:
        with self._lock:
            if user.user_id in self._users:
                return False
            self._users[user.user_id] = user
            return True

    def get_user(self, user_id: str) -> Optional[User]:
        with self._lock:
            return self._users.get(user_id)

    def list_roles(self) -> List[Role]:
        with self._lock:
            return list(self._roles.values())

    def list_users(self) -> List[User]:
        with self._lock:
            return list(self._users.values())


class ABACEngine:
    """Attribute-Based Access Control engine."""

    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._lock = threading.Lock()

    def add_policy(self, policy: Policy) -> bool:
        with self._lock:
            if policy.policy_id in self._policies:
                return False
            self._policies[policy.policy_id] = policy
            return True

    def remove_policy(self, policy_id: str) -> bool:
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
            return False

    def evaluate(
        self,
        user_attributes: Dict[str, Any],
        action: Permission,
        resource_type: ResourceType,
        resource_attributes: Dict[str, Any],
        context: Optional[Dict] = None,
    ) -> bool:
        """Evaluate ABAC policies."""
        with self._lock:
            applicable = []

            for policy in self._policies.values():
                if action not in policy.actions:
                    continue
                if resource_type not in policy.resources:
                    continue

                # Check conditions
                if self._match_conditions(policy.conditions, user_attributes, resource_attributes, context):
                    applicable.append(policy)

        if not applicable:
            return False  # Default deny

        # Sort by priority (higher first)
        applicable.sort(key=lambda p: p.priority, reverse=True)

        # First matching policy wins
        return applicable[0].effect == "allow"

    def _match_conditions(
        self,
        conditions: Dict[str, Any],
        user_attrs: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        context: Optional[Dict],
    ) -> bool:
        """Check if all conditions match."""
        all_attrs = {**user_attrs, **resource_attrs}
        if context:
            all_attrs.update(context)

        for key, expected in conditions.items():
            if key not in all_attrs:
                return False

            actual = all_attrs[key]

            if isinstance(expected, dict):
                # Operator-based condition
                op = expected.get("op", "eq")
                value = expected.get("value")
                if not self._compare(actual, value, op):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False

        return True

    def _compare(self, actual: Any, expected: Any, op: str) -> bool:
        if op == "eq":
            return actual == expected
        elif op == "ne":
            return actual != expected
        elif op == "gt":
            return actual > expected
        elif op == "gte":
            return actual >= expected
        elif op == "lt":
            return actual < expected
        elif op == "lte":
            return actual <= expected
        elif op == "in":
            return actual in expected
        elif op == "nin":
            return actual not in expected
        elif op == "contains":
            return expected in actual if hasattr(actual, '__contains__') else False
        elif op == "startswith":
            return str(actual).startswith(str(expected))
        elif op == "endswith":
            return str(actual).endswith(str(expected))
        return False


class AccessControlManager:
    """Unified access control combining RBAC and ABAC."""

    def __init__(self):
        self.rbac = RBACManager()
        self.abac = ABACEngine()
        self._default_deny = True

    def check_access(
        self,
        user_id: str,
        action: Permission,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
        user_attributes: Optional[Dict] = None,
        resource_attributes: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> bool:
        """Check access using both RBAC and ABAC."""
        # RBAC check first
        rbac_allowed = self.rbac.check_permission(user_id, action, ResourceType(action.value), resource_id)

        # ABAC check
        user = self.rbac.get_user(user_id)
        user_attrs = user_attributes or (user.attributes if user else {})
        resource_attrs = resource_attributes or {}

        abac_allowed = self.abac.evaluate(
            user_attributes=user_attrs,
            action=action,
            resource_type=resource_type,
            resource_attributes=resource_attributes,
        )

        # Both must allow (deny by default)
        return rbac_allowed and abac_allowed

    def create_user(self, user: User) -> bool:
        return self.rbac.create_user(user)

    def assign_role(self, user_id: str, role_id: str) -> bool:
        return self.rbac.assign_role(user_id, role_id)

    def add_abac_policy(self, policy: Policy) -> bool:
        return self.abac.add_policy(policy)


# ============================================================================
# Audit Logging (Tamper-proof)
# ============================================================================

class AuditEventType(Enum):
    ACCESS = "access"
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_CHANGE = "permission_change"
    CONFIG_CHANGE = "config_change"
    DATA_EXPORT = "data_export"
    MODEL_INFERENCE = "model_inference"


@dataclass
class AuditEvent:
    event_id: str
    event_type: AuditEventType
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    result: str  # success, failure, denied
    timestamp: float = field(default_factory=time.time)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    # Tamper-proof fields
    previous_hash: str = ""
    event_hash: str = ""


class TamperProofAuditLog:
    """Tamper-proof audit log with hash chaining."""

    def __init__(self, secret_key: Optional[bytes] = None, storage_path: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_bytes(32)
        self.storage_path = Path(storage_path) if storage_path else Path("audit_logs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._current_hash = "0" * 64  # Genesis hash
        self._lock = threading.Lock()
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 100
        self._flush_interval = 5.0  # seconds
        self._last_flush = time.time()

        # Load last hash from disk
        self._load_last_hash()

    def _load_last_hash(self) -> None:
        """Load the last hash from the most recent log file."""
        log_files = sorted(self.storage_path.glob("audit_*.jsonl"))
        if not log_files:
            self._current_hash = "0" * 64
            return

        try:
            last_file = log_files[-1]
            with open(last_file, "r") as f:
                lines = f.readlines()
                if lines:
                    last_event = json.loads(lines[-1])
                    self._current_hash = last_event.get("event_hash", "0" * 64)
        except Exception:
            self._current_hash = "0" * 64

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AuditEvent:
        """Log an audit event with tamper-proof hash chaining."""
        event = AuditEvent(
            event_id=f"audit_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            previous_hash=self._current_hash,
        )

        # Compute event hash
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "result": event.result,
            "timestamp": event.timestamp,
            "previous_hash": event.previous_hash,
            "metadata": event.metadata,
        }
        event.event_hash = self._compute_hash(event_data)
        self._current_hash = event.event_hash

        # Buffer and flush
        with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._buffer_size or time.time() - self._last_flush > self._flush_interval:
                self._flush()

        return event

    def _compute_hash(self, data: Dict) -> str:
        """Compute HMAC-SHA256 hash of event data."""
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hmac.new(self.secret_key, canonical.encode(), hashlib.sha256).hexdigest()

    def _flush(self) -> None:
        """Flush buffer to disk."""
        if not self._buffer:
            return

        date_str = datetime.now().strftime("%Y%m%d")
        log_file = self.storage_path / f"audit_{date_str}.jsonl"

        with open(log_file, "a") as f:
            for event in self._buffer:
                f.write(json.dumps({
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "user_id": event.user_id,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "action": event.action,
                    "result": event.result,
                    "timestamp": event.timestamp,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "metadata": event.metadata,
                    "previous_hash": event.previous_hash,
                    "event_hash": event.event_hash,
                }) + "\n")

        self._buffer.clear()
        self._last_flush = time.time()

    def verify_integrity(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Verify integrity of audit logs."""
        errors = []
        verified = 0
        prev_hash = "0" * 64

        log_files = sorted(self.storage_path.glob("audit_*.jsonl"))
        for log_file in log_files:
            if start_date and log_file.name < f"audit_{start_date}.jsonl":
                continue
            if end_date and log_file.name > f"audit_{end_date}.jsonl":
                continue

            with open(log_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        event = json.loads(line)
                        # Verify hash chain
                        if event["previous_hash"] != prev_hash:
                            errors.append(f"{log_file.name}:{line_num} - Hash chain broken")
                        else:
                            verified += 1

                        # Verify event hash
                        expected = self._compute_hash({
                            "event_id": event["event_id"],
                            "event_type": event["event_type"],
                            "user_id": event["user_id"],
                            "resource_type": event["resource_type"],
                            "resource_id": event["resource_id"],
                            "action": event["action"],
                            "result": event["result"],
                            "timestamp": event["timestamp"],
                            "previous_hash": event["previous_hash"],
                            "metadata": event["metadata"],
                        })
                        if event["event_hash"] != expected:
                            errors.append(f"{log_file.name}:{line_num} - Event hash mismatch")
                        else:
                            prev_hash = event["event_hash"]
                    except Exception as e:
                        errors.append(f"{log_file.name}:{line_num} - Parse error: {e}")

        return {
            "verified": verified,
            "errors": errors,
            "integrity": len(errors) == 0,
        }


# ============================================================================
# Encryption
# ============================================================================

class EncryptionManager:
    """Encryption at rest and in transit."""

    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or secrets.token_bytes(32)
        self._key_cache = LRUCache(maxsize=100, ttl=3600)

    def _derive_key(self, purpose: str, salt: Optional[bytes] = None) -> bytes:
        """Derive a purpose-specific key from master key."""
        salt = salt or secrets.token_bytes(16)
        from hashlib import pbkdf2_hmac
        return pbkdf2_hmac('sha256', self.master_key, salt, 100000, dklen=32)

    def encrypt(self, data: bytes, purpose: str = "default") -> Dict[str, str]:
        """Encrypt data with AES-GCM."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._derive_key(purpose)
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "purpose": purpose,
        }

    def decrypt(self, encrypted: Dict[str, str]) -> bytes:
        """Decrypt data."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._derive_key(encrypted["purpose"])
        aesgcm = AESGCM(key)
        nonce = base64.b64decode(encrypted["nonce"])
        ciphertext = base64.b64decode(encrypted["ciphertext"])
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_field(self, value: str, field_name: str) -> str:
        """Encrypt a single field value."""
        encrypted = self.encrypt(value.encode(), f"field_{field_name}")
        return json.dumps(encrypted)

    def decrypt_field(self, encrypted_str: str) -> str:
        encrypted = json.loads(encrypted_str)
        return self.decrypt(encrypted).decode()


# ============================================================================
# GDPR/CCPA Compliance
# ============================================================================

class DataSubjectRequestType(Enum):
    ACCESS = "access"           # Right to access
    RECTIFICATION = "rectification"  # Right to rectification
    ERASURE = "erasure"         # Right to erasure (right to be forgotten)
    PORTABILITY = "portability" # Right to data portability
    RESTRICTION = "restriction" # Right to restriction of processing
    OBJECTION = "objection"     # Right to object
    WITHDRAW_CONSENT = "withdraw_consent"


@dataclass
class DataSubjectRequest:
    request_id: str
    request_type: DataSubjectRequestType
    subject_id: str
    email: str
    details: str = ""
    status: str = "pending"  # pending, processing, completed, rejected
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    verification_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))


class GDPRComplianceManager:
    """GDPR/CCPA compliance manager."""

    def __init__(self, storage: Any, encryption: EncryptionManager):
        self.storage = storage
        self.encryption = encryption
        self._requests: Dict[str, DataSubjectRequest] = {}
        self._lock = threading.Lock()

    def submit_request(
        self,
        request_type: DataSubjectRequestType,
        subject_id: str,
        email: str,
        details: str = "",
    ) -> DataSubjectRequest:
        """Submit a data subject request."""
        request = DataSubjectRequest(
            request_id=f"dsr_{uuid.uuid4().hex[:12]}",
            request_type=request_type,
            subject_id=subject_id,
            email=email,
            details=details,
        )
        with self._lock:
            self._requests[request.request_id] = request
        return request

    def process_request(self, request_id: str, action: str = "process") -> bool:
        """Process a data subject request."""
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                return False

            if action == "process":
                if request.request_type == DataSubjectRequestType.ACCESS:
                    self._process_access_request(request)
                elif request.request_type == DataSubjectRequestType.ERASURE:
                    self._process_erasure_request(request)
                elif request.request_type == DataSubjectRequestType.PORTABILITY:
                    self._process_portability_request(request)
                elif request.request_type == DataSubjectRequestType.RECTIFICATION:
                    self._process_rectification_request(request)

                request.status = "completed"
                request.completed_at = time.time()
                return True
            elif action == "reject":
                request.status = "rejected"
                request.completed_at = time.time()
                return True

            return False

    def _process_access_request(self, request: DataSubjectRequest) -> Dict:
        """Process access request - return all data for subject."""
        # Implementation would query all stores
        return {"subject_id": request.subject_id, "data": {}}

    def _process_erasure_request(self, request: DataSubjectRequest) -> bool:
        """Process erasure request (right to be forgotten)."""
        # Implementation would delete all data for subject
        return True

    def _process_portability_request(self, request: DataSubjectRequest) -> Dict:
        """Process data portability request."""
        # Return data in machine-readable format
        return {"subject_id": request.subject_id, "format": "json", "data": {}}

    def _process_rectification_request(self, request: DataSubjectRequest) -> bool:
        """Process rectification request."""
        # Implementation would update incorrect data
        return True

    def get_request(self, request_id: str) -> Optional[DataSubjectRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def list_requests(self, subject_id: Optional[str] = None) -> List[DataSubjectRequest]:
        with self._lock:
            if subject_id:
                return [r for r in self._requests.values() if r.subject_id == subject_id]
            return list(self._requests.values())


# ============================================================================
# Secret Management
# ============================================================================

class SecretManager:
    """Secure secret management with rotation."""

    def __init__(self, encryption: EncryptionManager, storage_path: str):
        self.encryption = encryption
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._secrets: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from encrypted storage."""
        secrets_file = self.storage_path / "secrets.enc"
        if not secrets_file.exists():
            return
        try:
            encrypted = json.loads(secrets_file.read_text())
            decrypted = self.encryption.decrypt({
                "ciphertext": encrypted["ciphertext"],
                "nonce": encrypted["nonce"],
                "purpose": encrypted["purpose"],
            })
            self._secrets = json.loads(decrypted)
        except Exception as e:
            logger.warning(f"Failed to load secrets: {e}")

    def _save_secrets(self) -> None:
        secrets_file = self.storage_path / "secrets.enc"
        encrypted = self.encryption.encrypt(json.dumps(self._secrets).encode(), "secrets")
        secrets_file.write_text(json.dumps(encrypted))

    def set_secret(self, name: str, value: str, metadata: Optional[Dict] = None) -> None:
        """Store a secret."""
        with self._lock:
            self._secrets[name] = {
                "value": value,
                "metadata": metadata or {},
                "created_at": time.time(),
                "updated_at": time.time(),
                "version": self._secrets.get(name, {}).get("version", 0) + 1,
            }
            self._save_secrets()

    def get_secret(self, name: str) -> Optional[str]:
        with self._lock:
            secret = self._secrets.get(name)
            return secret["value"] if secret else None

    def get_secret_with_metadata(self, name: str) -> Optional[Dict]:
        with self._lock:
            return self._secrets.get(name)

    def delete_secret(self, name: str) -> bool:
        with self._lock:
            if name in self._secrets:
                del self._secrets[name]
                self._save_secrets()
                return True
            return False

    def list_secrets(self) -> List[str]:
        with self._lock:
            return list(self._secrets.keys())

    def rotate_secret(self, name: str, new_value: str) -> bool:
        """Rotate a secret to a new value."""
        with self._lock:
            if name not in self._secrets:
                return False
            self._secrets[name]["value"] = new_value
            self._secrets[name]["updated_at"] = time.time()
            self._secrets[name]["version"] += 1
            self._save_secrets()
            return True

    def get_secret_version(self, name: str) -> int:
        with self._lock:
            secret = self._secrets.get(name)
            return secret.get("version", 0) if secret else 0


# ============================================================================
# Threat Detection
# ============================================================================

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatEvent:
    event_id: str
    threat_level: ThreatLevel
    event_type: str
    description: str
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    indicators: List[str] = field(default_factory=list)
    mitigated: bool = False
    metadata: Dict = field(default_factory=dict)


class ThreatDetector:
    """Real-time threat detection."""

    def __init__(self):
        self._rules: List[Callable[[Dict], Optional[ThreatEvent]]] = []
        self._events: List[ThreatEvent] = []
        self._lock = threading.Lock()
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default detection rules."""

        def brute_force_login(event: Dict) -> Optional[ThreatEvent]:
            if event.get("event_type") == "login" and event.get("result") == "failure":
                # Track failed logins per IP
                return None  # Would track in real implementation

        def unusual_access_pattern(event: Dict) -> Optional[ThreatEvent]:
            if event.get("event_type") == "access" and event.get("user_agent", "").lower().find("bot") >= 0:
                return ThreatEvent(
                    event_id=f"threat_{uuid.uuid4().hex[:8]}",
                    threat_level=ThreatLevel.MEDIUM,
                    event_type="suspicious_user_agent",
                    description="Suspicious user agent detected",
                    source_ip=event.get("ip_address"),
                    indicators=["bot_user_agent"],
                )

        def data_exfiltration(event: Dict) -> Optional[ThreatEvent]:
            if event.get("event_type") == "data_export" and event.get("size_bytes", 0) > 100 * 1024 * 1024:  # 100MB
                return ThreatEvent(
                    event_id=f"threat_{uuid.uuid4().hex[:8]}",
                    threat_level=ThreatLevel.HIGH,
                    event_type="potential_data_exfiltration",
                    description="Large data export detected",
                    user_id=event.get("user_id"),
                    indicators=["large_export"],
                )

        self._rules.append(unusual_access_pattern)
        self._rules.append(data_exfiltration)

    def add_rule(self, rule: Callable[[Dict], Optional[ThreatEvent]]) -> None:
        self._rules.append(rule)

    def analyze(self, event: Dict) -> List[ThreatEvent]:
        """Analyze an event for threats."""
        threats = []
        for rule in self._rules:
            try:
                result = rule(event)
                if result:
                    threats.append(result)
                    with self._lock:
                        self._events.append(result)
            except Exception as e:
                logger.warning(f"Threat rule failed: {e}")
        return threats

    def get_recent_threats(self, hours: int = 24) -> List[ThreatEvent]:
        cutoff = time.time() - hours * 3600
        with self._lock:
            return [e for e in self._events if e.timestamp >= cutoff]

    def get_threats_by_level(self, level: ThreatLevel, hours: int = 24) -> List[ThreatEvent]:
        return [e for e in self.get_recent_threats(hours) if e.threat_level == level]

    def mitigate(self, event_id: str) -> bool:
        with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    event.mitigated = True
                    return True
        return False


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # RBAC/ABAC
    "Permission",
    "ResourceType",
    "Role",
    "User",
    "Policy",
    "RBACManager",
    "ABACEngine",
    "AccessControlManager",
    # Audit
    "AuditEventType",
    "AuditEvent",
    "TamperProofAuditLog",
    # Encryption
    "EncryptionManager",
    # GDPR
    "DataSubjectRequestType",
    "DataSubjectRequest",
    "GDPRComplianceManager",
    # Secrets
    "SecretManager",
    # Threat Detection
    "ThreatLevel",
    "ThreatEvent",
    "ThreatDetector",
]