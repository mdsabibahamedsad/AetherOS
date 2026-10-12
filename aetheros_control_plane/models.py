"""AetherOS Universal Agent Operating Fabric — shared data models.

Single source of truth for identity, trust, risk, policy, delegation,
execution, and audit types used by the control plane (§3, §7, §12, §20,
§31-34). Pure stdlib dataclasses/enums; no I/O here.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Identity (§3)
# ---------------------------------------------------------------------------

class IdentityType(str, Enum):
    AGENT = "agent"
    HUMAN = "human"
    SERVICE = "service"
    TOOL = "tool"
    EXTENSION = "extension"
    DEVICE = "device"
    ORGANIZATION = "organization"
    SESSION = "session"
    DELEGATED = "delegated"
    EXECUTION = "execution"


class IdentityStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"
    DECOMMISSIONED = "decommissioned"


class TrustLevel(str, Enum):
    """Configurable T0..T5 trust levels (§7). Ordered by value."""
    T0_UNKNOWN = "T0"
    T1_UNVERIFIED = "T1"
    T2_VERIFIED = "T2"
    T3_TRUSTED = "T3"
    T4_HIGH_TRUST = "T4"
    T5_SYSTEM_TRUST = "T5"


_TRUST_ORDER = {
    TrustLevel.T0_UNKNOWN: 0,
    TrustLevel.T1_UNVERIFIED: 1,
    TrustLevel.T2_VERIFIED: 2,
    TrustLevel.T3_TRUSTED: 3,
    TrustLevel.T4_HIGH_TRUST: 4,
    TrustLevel.T5_SYSTEM_TRUST: 5,
}


def trust_at_least(level: TrustLevel, minimum: TrustLevel) -> bool:
    return _TRUST_ORDER[level] >= _TRUST_ORDER[minimum]


@dataclass
class Identity:
    id: str
    type: IdentityType
    issuer: str = "aetheros-control-plane"
    subject: str = ""
    display_name: str = ""
    version: int = 1
    key_ids: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.T0_UNKNOWN
    organization: str = "default"
    tenant: str = "default"
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    status: IdentityStatus = IdentityStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def is_usable(self) -> bool:
        if self.status not in (IdentityStatus.CREATED, IdentityStatus.ACTIVE):
            return False
        if self.expires_at is not None and _now() > self.expires_at:
            return False
        return True


# ---------------------------------------------------------------------------
# Risk (§12), data classification (§20)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    R0_READ_ONLY = "R0"
    R1_LOCAL_REVERSIBLE = "R1"
    R2_EXTERNAL_SIDE_EFFECT = "R2"
    R3_SENSITIVE_DATA = "R3"
    R4_HIGH_IMPACT = "R4"
    R5_CRITICAL = "R5"


class DataClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SENSITIVE = "sensitive"
    SECRET = "secret"
    RESTRICTED = "restricted"


# ---------------------------------------------------------------------------
# Trust engine types (§6)
# ---------------------------------------------------------------------------

TRUST_DIMENSIONS = (
    "identity", "transport", "organization", "capability", "behavior",
    "provenance", "data_handling", "execution", "history", "policy",
)


class TrustOutcome(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_LIMITS = "ALLOW_WITH_LIMITS"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


@dataclass
class TrustEvidence:
    dimension: str
    score: float  # 0.0..1.0 per-dimension (not a global score)
    weight: float = 1.0
    reason: str = ""
    source: str = ""
    at: float = field(default_factory=_now)


@dataclass
class TrustAssessment:
    identity_id: str
    per_dimension: Dict[str, float] = field(default_factory=dict)
    outcome: TrustOutcome = TrustOutcome.DENY
    reasons: List[str] = field(default_factory=list)
    required_level: TrustLevel = TrustLevel.T2_VERIFIED
    actual_level: TrustLevel = TrustLevel.T0_UNKNOWN
    at: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Policy / authorization (§10-11)
# ---------------------------------------------------------------------------

class AuthDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    CHALLENGE_STEP_UP = "CHALLENGE_STEP_UP"


@dataclass
class PolicyDecision:
    decision: AuthDecision
    matched_rules: List[str] = field(default_factory=list)
    denied_rules: List[str] = field(default_factory=list)
    required_scopes: List[str] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)
    risk: RiskLevel = RiskLevel.R0_READ_ONLY
    trust_required: TrustLevel = TrustLevel.T1_UNVERIFIED
    expiration: Optional[float] = None
    obligations: List[str] = field(default_factory=list)
    explanation: str = ""
    policy_version: str = "v1"


# ---------------------------------------------------------------------------
# Failure codes (§91)
# ---------------------------------------------------------------------------

class FailureCode(str, Enum):
    IDENTITY_UNKNOWN = "IDENTITY_UNKNOWN"
    IDENTITY_REVOKED = "IDENTITY_REVOKED"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    TRUST_INSUFFICIENT = "TRUST_INSUFFICIENT"
    POLICY_DENIED = "POLICY_DENIED"
    SCOPE_MISSING = "SCOPE_MISSING"
    DELEGATION_INVALID = "DELEGATION_INVALID"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    DATA_POLICY_BLOCKED = "DATA_POLICY_BLOCKED"
    NETWORK_POLICY_BLOCKED = "NETWORK_POLICY_BLOCKED"
    SANDBOX_POLICY_BLOCKED = "SANDBOX_POLICY_BLOCKED"
    AGENT_QUARANTINED = "AGENT_QUARANTINED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    TASK_AUTHORITY_EXPIRED = "TASK_AUTHORITY_EXPIRED"


class ControlPlaneError(Exception):
    def __init__(self, code: FailureCode, message: str):
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Execution (§30-32)
# ---------------------------------------------------------------------------

@dataclass
class ActionManifest:
    action_id: str = field(default_factory=lambda: new_id("act"))
    task_id: str = ""
    agent_id: str = ""
    identity_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    risk: RiskLevel = RiskLevel.R0_READ_ONLY
    data_classes: List[str] = field(default_factory=list)
    network_targets: List[str] = field(default_factory=list)
    model: str = ""
    tools: List[str] = field(default_factory=list)
    delegation_id: str = ""
    approval_id: str = ""
    policy_version: str = "v1"
    sandbox: str = "default"
    expires_at: Optional[float] = None


@dataclass
class ActionReceipt:
    action_id: str
    request_hash: str
    identity_id: str
    delegation_chain: List[str] = field(default_factory=list)
    policy_decision: str = ""
    approval_id: str = ""
    execution_environment: str = ""
    tool: str = ""
    resource: str = ""
    result_hash: str = ""
    artifact_refs: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=_now)
    ended_at: float = field(default_factory=_now)
    verified: bool = False
    provenance: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool result envelope (§45)
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    data: Any = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    trust: str = "T1"
    source: str = ""
    classification: str = "internal"
    warnings: List[str] = field(default_factory=list)
    untrusted_instructions: List[str] = field(default_factory=list)
