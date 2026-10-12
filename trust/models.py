"""Canonical Trust Fabric models (§4). Reuses M50 models wherever they
exist (Identity, TrustLevel, PolicyDecision, ActionManifest,
ActionReceipt, DelegationGrant, Approval, AuditEvent) — this module
defines ONLY what M50 lacks. All security dataclasses are frozen
where mutation would be a vulnerability; no `Any` at boundaries.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Re-exported canonical M50 types (single source of truth, §4).
from aetheros_control_plane.models import (  # noqa
    ActionManifest,
    ActionReceipt,
    AuthDecision,
    DataClass,
    FailureCode,
    Identity,
    IdentityStatus,
    IdentityType,
    PolicyDecision,
    TrustLevel,
)


def _now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# §16 risk R0-R8 (M50 stops at R5; R6-R8 are new, mapped from M50 levels)
# ---------------------------------------------------------------------------

class Risk(str, Enum):
    R0_INFORMATIONAL = "R0"
    R1_READ_ONLY = "R1"
    R2_REVERSIBLE_LOCAL = "R2"
    R3_EXTERNAL_COMM = "R3"
    R4_CREDENTIAL_DATA = "R4"
    R5_FINANCIAL_LEGAL_ORG = "R5"
    R6_INFRA_MODIFICATION = "R6"
    R7_PHYSICAL_WORLD = "R7"
    R8_IRREVERSIBLE_CRITICAL = "R8"


_RISK_ORDER = {r: i for i, r in enumerate(Risk)}


def risk_at_least(level: Risk, minimum: Risk) -> bool:
    return _RISK_ORDER[level] >= _RISK_ORDER[minimum]


def risk_order(level: Risk) -> int:
    return _RISK_ORDER[level]


# ---------------------------------------------------------------------------
# §19 data classification (M50 DataClass has 6; HIGHLY_RESTRICTED added)
# ---------------------------------------------------------------------------

class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"
    HIGHLY_RESTRICTED = "highly_restricted"


_DATA_ORDER = {d: i for i, d in enumerate(DataClassification)}


def data_at_least(level: DataClassification,
                  minimum: DataClassification) -> bool:
    return _DATA_ORDER[level] >= _DATA_ORDER[minimum]


# ---------------------------------------------------------------------------
# §4 canonical objects missing from M50
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResourceDescriptor:
    kind: str  # filesystem|network|browser|memory|mcp|a2a|robot|secret|...
    pattern: str  # e.g. /workspace/**, https://api.example.com/*
    tenant_id: str = "default"


@dataclass(frozen=True)
class ActionProposal:
    """What the MODEL proposes, before any decision. Never authoritative."""
    proposal_id: str = ""
    identity_id: str = ""
    capability: str = ""
    resource: ResourceDescriptor = field(
        default_factory=lambda: ResourceDescriptor(kind="", pattern=""))
    purpose: str = ""
    data_classification: DataClassification = DataClassification.INTERNAL
    context: Dict[str, str] = field(default_factory=dict)
    at: float = field(default_factory=_now)


@dataclass(frozen=True)
class ExecutionContext:
    task_id: str = ""
    session_id: str = ""
    delegation_chain: Tuple[str, ...] = ()
    path: Tuple[str, ...] = ()  # preceding action ids in this task
    autonomy_level: int = 2
    governance_mode: str = "BALANCED"
    model_id: str = ""
    tool_id: str = ""


@dataclass(frozen=True)
class RiskAssessment:
    level: Risk
    impact: str = ""
    likelihood: str = ""
    irreversibility: bool = False
    blast_radius: Dict[str, int] = field(default_factory=dict)
    reasons: Tuple[str, ...] = ()
    at: float = field(default_factory=_now)


@dataclass(frozen=True)
class CapabilityToken:
    """Short-lived signed authority (§10). Validated independently by the
    tool runtime — never by the model."""
    token_id: str = ""
    subject: str = ""
    action: str = ""
    resource: str = ""
    purpose: str = ""
    issued_at: float = 0.0
    expires_at: float = 0.0
    max_uses: int = 1
    uses: int = 0
    data_limit: str = "INTERNAL"
    network_policy: str = "deny"
    approval_id: str = ""
    audience: str = ""  # exact tool/audience binding (§113)
    issuer: str = "trust-fabric"
    nonce: str = ""
    signature: str = ""


@dataclass(frozen=True)
class RevocationRecord:
    target_kind: str  # agent|delegation|capability|device|remote-agent|session
    target_id: str = ""
    reason: str = ""
    actor: str = ""
    at: float = field(default_factory=_now)
    propagated_to: Tuple[str, ...] = ()


@dataclass
class Incident:
    incident_id: str = ""
    kind: str = ""
    severity: str = "LOW"  # LOW|MEDIUM|HIGH|CRITICAL
    state: str = "DETECTED"  # §54 lifecycle
    actor: str = ""
    resources: Tuple[str, ...] = ()
    timeline: List[Dict[str, str]] = field(default_factory=list)
    containment: Tuple[str, ...] = ()
    evidence: Tuple[str, ...] = ()
    at: float = field(default_factory=_now)


@dataclass(frozen=True)
class TrustScore:
    """Advisory summary only (§56). NEVER overrides hard deny."""
    identity_id: str = ""
    score: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    at: float = field(default_factory=_now)


@dataclass(frozen=True)
class ExecutionReceipt:
    """Signed receipt (§50). Signature covers all hashed fields."""
    receipt_id: str = ""
    action_id: str = ""
    actor: str = ""
    capability: str = ""
    policy_id: str = ""
    policy_version: str = ""
    policy_hash: str = ""
    authority_hash: str = ""
    input_hash: str = ""
    result_hash: str = ""
    verification: str = ""
    execution_semantics: str = "at-least-once"  # §120 honesty
    timestamp: float = field(default_factory=_now)
    key_id: str = ""
    signature: str = ""


# ---------------------------------------------------------------------------
# §13 extended decisions, §59 modes, §60 autonomy, §213 error taxonomy
# ---------------------------------------------------------------------------

class ExtendedDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_STEP_UP_AUTH = "REQUIRE_STEP_UP_AUTH"
    SANDBOX_ONLY = "SANDBOX_ONLY"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    RATE_LIMIT = "RATE_LIMIT"
    DEFER = "DEFER"


class GovernanceMode(str, Enum):
    OPEN = "OPEN"
    BALANCED = "BALANCED"
    STRICT = "STRICT"
    ENTERPRISE = "ENTERPRISE"
    HIGH_SECURITY = "HIGH_SECURITY"
    AIR_GAPPED = "AIR_GAPPED"
    RESEARCH = "RESEARCH"
    DEVELOPMENT = "DEVELOPMENT"
    SIMULATION = "SIMULATION"
    EMERGENCY = "EMERGENCY"


class Autonomy(str, Enum):
    L0_OBSERVE = "L0"
    L1_SUGGEST = "L1"
    L2_EXECUTE_LOW_RISK = "L2"
    L3_EXECUTE_WITH_GUARDS = "L3"
    L4_AUTONOMOUS_BOUNDED = "L4"
    L5_FULL_AUTONOMY_WITH_POLICY = "L5"


class SecurityError(str, Enum):
    IDENTITY_INVALID = "IDENTITY_INVALID"
    AUTHORITY_MISSING = "AUTHORITY_MISSING"
    CAPABILITY_EXPIRED = "CAPABILITY_EXPIRED"
    CAPABILITY_REVOKED = "CAPABILITY_REVOKED"
    POLICY_DENIED = "POLICY_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    RISK_TOO_HIGH = "RISK_TOO_HIGH"
    DATA_POLICY_DENIED = "DATA_POLICY_DENIED"
    NETWORK_POLICY_DENIED = "NETWORK_POLICY_DENIED"
    SECRET_POLICY_DENIED = "SECRET_POLICY_DENIED"
    INCIDENT_CONTAINMENT = "INCIDENT_CONTAINMENT"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    TRUST_SERVICE_UNAVAILABLE = "TRUST_SERVICE_UNAVAILABLE"


class TrustError(Exception):
    """Typed, stable, auditable, non-secret-revealing (§212)."""

    def __init__(self, code: SecurityError, message: str):
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
