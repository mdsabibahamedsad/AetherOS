"""Canonical marketplace data model (spec section 2 + 91).

Identity / Agent / Service / Capability / Offer / Contract / Task /
Transaction / Reputation are SEPARATE concepts — never collapsed.

Conventions:
- Money is integer minor units (amount_minor) + 3-letter currency.
- Every record carries schema_version; from_dict validates + migrates.
- IDs are unguessable (secrets.token_hex), never sequential.
- Timestamps are float epoch seconds (UTC).
"""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1"

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_ID_RESERVED = ("", "null", "undefined", "unknown")


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8)}"


def now() -> float:
    return time.time()


def check_currency(code: str) -> str:
    if not isinstance(code, str) or not _CURRENCY_RE.match(code):
        raise ValueError(f"invalid currency code: {code!r} (expected e.g. 'USD')")
    return code


def check_amount_minor(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"amount_minor must be a non-negative int, got {value!r}")
    return value


def _require_version(data: Dict[str, Any], current: str = SCHEMA_VERSION) -> None:
    ver = data.get("schema_version", "1")
    if ver != current:
        raise ValueError(f"unsupported schema_version {ver!r} (expected {current!r})")


def _from_dict(cls, data: Dict[str, Any]):
    _require_version(data)
    known = set(cls.__dataclass_fields__)
    return cls(**{k: v for k, v in data.items() if k in known})


# ---------------------------------------------------------------------------
# Identity / Agent
# ---------------------------------------------------------------------------

@dataclass
class MarketplaceIdentity:
    """Marketplace-side identity, BOUND to (not replacing) network identity.

    Binding fields (agent_id, agent_card_hash, endpoint, public_key_fp)
    must reconcile with the A2A Agent Card + aetheros_network identity.
    Mismatch => BLOCK or re-verification (spec 104/105).
    """

    schema_version: str = SCHEMA_VERSION
    identity_id: str = ""
    agent_id: str = ""            # aetheros_network agent id (A2A identity)
    organization_id: str = ""
    display_name: str = ""
    issuer: str = ""              # who vouched: marketplace / org / self
    agent_card_hash: str = ""     # sha256 of canonical card JSON at bind time
    endpoint: str = ""            # bound endpoint URL
    public_key_fp: str = ""       # bound signing-key fingerprint
    verification_status: str = "unknown"  # verified|unverified|expired|revoked|unknown
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.identity_id or self.identity_id in _ID_RESERVED:
            errors.append("identity_id required")
        if not self.agent_id:
            errors.append("agent_id required (bind to A2A identity)")
        if self.verification_status not in ("verified", "unverified", "expired", "revoked", "unknown"):
            errors.append(f"bad verification_status: {self.verification_status!r}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplaceIdentity":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Capability / Service / Offer
# ---------------------------------------------------------------------------

@dataclass
class Capability:
    """One machine-checkable capability within the taxonomy (section 3)."""

    schema_version: str = SCHEMA_VERSION
    capability_id: str = ""       # taxonomy path, e.g. "research.web_search"
    input_modes: List[str] = field(default_factory=list)
    output_modes: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)  # A2A, MCP, local
    data_classes: List[str] = field(default_factory=list)  # accepted classes
    version: str = "1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Capability":
        return _from_dict(cls, data)


@dataclass
class AgentService:
    schema_version: str = SCHEMA_VERSION
    service_id: str = ""
    agent_id: str = ""
    name: str = ""
    description: str = ""
    capabilities: List[Dict[str, Any]] = field(default_factory=list)  # Capability dicts
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    supported_protocols: List[str] = field(default_factory=list)
    supported_modalities: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    availability: str = "unknown"  # available|limited|unavailable|unknown
    pricing_model: str = "unknown"  # free|per_task|per_minute|per_token|subscription|quote
    sla: Dict[str, Any] = field(default_factory=dict)
    security_requirements: List[str] = field(default_factory=list)
    data_requirements: List[str] = field(default_factory=list)
    geographic_restrictions: List[str] = field(default_factory=list)
    version: str = "1"
    status: str = "draft"  # draft|published|unpublished|suspended|revoked
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.service_id:
            errors.append("service_id required")
        if not self.agent_id:
            errors.append("agent_id required")
        if not self.name:
            errors.append("name required")
        if self.status not in ("draft", "published", "unpublished", "suspended", "revoked"):
            errors.append(f"bad status: {self.status!r}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentService":
        return _from_dict(cls, data)


@dataclass
class Offer:
    schema_version: str = SCHEMA_VERSION
    offer_id: str = ""
    service_id: str = ""
    agent_id: str = ""
    price_minor: int = 0
    currency: str = "USD"
    quota: Dict[str, Any] = field(default_factory=dict)
    sla: Dict[str, Any] = field(default_factory=dict)
    expires_at: float = 0.0
    conditions: List[str] = field(default_factory=list)
    cancellation_policy: str = ""
    refund_policy: str = ""
    signature: str = ""           # hex signature over canonical offer bytes (optional)
    signer_fp: str = ""           # fingerprint of signing key
    status: str = "open"          # open|withdrawn|expired|consumed
    created_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.offer_id or not self.service_id or not self.agent_id:
            errors.append("offer_id/service_id/agent_id required")
        try:
            check_amount_minor(self.price_minor)
            check_currency(self.currency)
        except ValueError as e:
            errors.append(str(e))
        if self.status not in ("open", "withdrawn", "expired", "consumed"):
            errors.append(f"bad status: {self.status!r}")
        return errors

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at) and now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Offer":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Quote / Contract
# ---------------------------------------------------------------------------

@dataclass
class Quote:
    schema_version: str = SCHEMA_VERSION
    quote_id: str = ""
    service_id: str = ""
    contract_id: str = ""
    agent_id: str = ""
    price_minor: int = 0
    currency: str = "USD"
    estimated_duration_s: float = 0.0
    included_retries: int = 0
    sla: Dict[str, Any] = field(default_factory=dict)
    fees_minor: int = 0
    expires_at: float = 0.0
    cancellation_policy: str = ""
    refund_policy: str = ""
    signature: str = ""
    signer_fp: str = ""
    idempotency_key: str = ""
    created_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.quote_id or not self.service_id or not self.agent_id:
            errors.append("quote_id/service_id/agent_id required")
        try:
            check_amount_minor(self.price_minor)
            check_amount_minor(self.fees_minor)
            check_currency(self.currency)
        except ValueError as e:
            errors.append(str(e))
        if not self.idempotency_key:
            errors.append("idempotency_key required")
        return errors

    @property
    def total_minor(self) -> int:
        return self.price_minor + self.fees_minor

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at) and now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quote":
        return _from_dict(cls, data)


CONTRACT_STATUSES = (
    "draft", "proposed", "negotiating", "approved", "active",
    "suspended", "completed", "cancelled", "expired", "disputed",
)

# Fields that negotiation may touch. Anything else (especially security
# constraints) is NOT negotiable — the policy floor always wins (sec 12).
NEGOTIABLE_FIELDS = {
    "price_minor", "deadline_at", "output_format", "scope_text",
    "sla", "retry_policy", "evidence_requirements", "delivery_format",
}


@dataclass
class DelegationContract:
    """Immutable once execution begins; amendments => new version (sec 11)."""

    schema_version: str = SCHEMA_VERSION
    contract_id: str = ""
    version: int = 1
    supersedes: str = ""          # previous contract_id when amended
    requester: str = "local"      # user/org/local identity
    provider_agent_id: str = ""
    provider_identity_id: str = ""
    service_id: str = ""
    offer_id: str = ""
    quote_id: str = ""
    task_summary: str = ""
    inputs_ref: str = ""          # evidence id holding minimized inputs
    allowed_data: List[str] = field(default_factory=list)
    prohibited_data: List[str] = field(default_factory=list)
    data_class: str = "INTERNAL"  # PUBLIC|INTERNAL|CONFIDENTIAL|PRIVATE|HIGHLY_SENSITIVE
    expected_output: str = ""
    success_criteria: List[str] = field(default_factory=list)
    sla: Dict[str, Any] = field(default_factory=dict)
    timeout_s: float = 300.0
    budget_minor: int = 0
    currency: str = "USD"
    price_minor: int = 0
    payment_conditions: str = ""
    cancellation_conditions: str = ""
    refund_conditions: str = ""
    verification_requirements: List[str] = field(default_factory=list)
    artifact_requirements: List[str] = field(default_factory=list)
    security_constraints: List[str] = field(default_factory=list)
    retention_rules: str = ""
    jurisdiction: str = ""
    expires_at: float = 0.0
    allow_fallback: bool = False
    max_delegation_depth: int = 1
    signatures: Dict[str, str] = field(default_factory=dict)  # party -> hex sig
    status: str = "draft"
    idempotency_key: str = ""
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.contract_id or not self.provider_agent_id or not self.service_id:
            errors.append("contract_id/provider_agent_id/service_id required")
        if self.status not in CONTRACT_STATUSES:
            errors.append(f"bad status: {self.status!r}")
        try:
            check_amount_minor(self.budget_minor)
            check_amount_minor(self.price_minor)
            check_currency(self.currency)
        except ValueError as e:
            errors.append(str(e))
        if self.price_minor > self.budget_minor and self.budget_minor:
            errors.append("price exceeds budget")
        if self.data_class not in ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "PRIVATE", "HIGHLY_SENSITIVE"):
            errors.append(f"bad data_class: {self.data_class!r}")
        if not self.idempotency_key:
            errors.append("idempotency_key required")
        return errors

    @property
    def is_locked(self) -> bool:
        return self.status in ("active", "completed", "cancelled", "disputed")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelegationContract":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Task / Evidence / Verification
# ---------------------------------------------------------------------------

DELEGATION_TASK_STATUSES = (
    "created", "contract_pending", "approved", "delegated", "running",
    "evidence_received", "verifying", "verified", "settling",
    "completed", "failed", "cancelled", "refunded", "disputed",
)


@dataclass
class DelegationTask:
    schema_version: str = SCHEMA_VERSION
    delegation_id: str = ""
    contract_id: str = ""
    contract_version: int = 1
    root_task_id: str = ""        # recursion-defense chain root
    parent_agent_id: str = ""
    delegation_depth: int = 1
    delegation_chain: List[str] = field(default_factory=list)
    network_task_id: str = ""     # aetheros_network RemoteTask id
    status: str = "created"
    result_ref: str = ""
    verification_ref: str = ""
    transaction_ref: str = ""
    idempotency_key: str = ""
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.delegation_id or not self.contract_id:
            errors.append("delegation_id/contract_id required")
        if self.status not in DELEGATION_TASK_STATUSES:
            errors.append(f"bad status: {self.status!r}")
        if self.delegation_depth < 1:
            errors.append("delegation_depth must be >= 1")
        if not self.idempotency_key:
            errors.append("idempotency_key required")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelegationTask":
        return _from_dict(cls, data)


@dataclass
class Evidence:
    """Immutable, content-hashed provenance record (sec 20)."""

    schema_version: str = SCHEMA_VERSION
    evidence_id: str = ""
    kind: str = ""                # input|output|artifact|quote|verification|payment|event
    delegation_id: str = ""
    contract_id: str = ""
    task_id: str = ""
    actor: str = ""
    sha256: str = ""
    size_bytes: int = 0
    summary: str = ""             # redacted human summary, never secrets
    ref: str = ""                 # pointer to stored payload (path/key), not payload
    correlation_id: str = ""
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        return _from_dict(cls, data)


@dataclass
class VerificationResult:
    schema_version: str = SCHEMA_VERSION
    verification_id: str = ""
    delegation_id: str = ""
    contract_id: str = ""
    strategy: str = ""            # schema|artifact|hash|tests|sources|verifier_agent|...
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    evidence_ids: List[str] = field(default_factory=list)
    verifier: str = "local"       # local|agent:<id>
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Reputation / Trust signals
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    """One reputation metric with provenance — never a bare number (sec 7)."""

    value: float = 0.0
    confidence: float = 0.0       # 0..1
    sample_count: int = 0
    time_window_days: int = 30
    provenance: str = ""          # observed|user_feedback|verified|attestation|security

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReputationProfile:
    schema_version: str = SCHEMA_VERSION
    agent_id: str = ""
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> Metric dict
    flags: List[str] = field(default_factory=list)  # e.g. insufficient_evidence, under_review
    updated_at: float = field(default_factory=now)

    def get(self, name: str) -> Metric:
        raw = self.metrics.get(name)
        if not raw:
            return Metric()
        return Metric(**{k: v for k, v in raw.items() if k in Metric.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationProfile":
        return _from_dict(cls, data)


REPUTATION_METRICS = (
    "reliability", "task_success", "verified_success", "evidence_quality",
    "latency", "cost_efficiency", "security", "policy_compliance",
    "cancellation_rate", "sla_adherence", "interoperability",
    "user_satisfaction", "verification_confidence",
)

TRUST_DIMENSIONS = (
    "identity", "security", "execution", "economic",
    "evidence", "behavioral", "organizational",
)


@dataclass
class TrustSignal:
    schema_version: str = SCHEMA_VERSION
    signal_id: str = ""
    agent_id: str = ""
    dimension: str = ""           # one of TRUST_DIMENSIONS
    source: str = ""              # verification|outcome|security|org|user|...
    kind: str = ""                # e.g. tls_verified, task_success, incident
    value: float = 0.0            # -1..1
    confidence: float = 0.0
    evidence_ref: str = ""
    decay_half_life_days: float = 30.0
    created_at: float = field(default_factory=now)

    def decayed_value(self, at: Optional[float] = None) -> float:
        import math
        age_days = ((at or now()) - self.created_at) / 86400.0
        if age_days < 0:
            age_days = 0.0
        half = max(self.decay_half_life_days, 1e-6)
        return self.value * (0.5 ** (age_days / half))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustSignal":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Budget / Transaction / Ledger / Dispute / Incidents
# ---------------------------------------------------------------------------

@dataclass
class Budget:
    schema_version: str = SCHEMA_VERSION
    budget_id: str = ""
    scope: str = ""               # global|user|workspace|project|automation|agent|task|contract
    scope_id: str = ""
    currency: str = "USD"
    daily_limit_minor: int = 0    # 0 = no limit
    weekly_limit_minor: int = 0
    monthly_limit_minor: int = 0
    per_task_limit_minor: int = 0
    per_agent_limit_minor: int = 0
    approval_threshold_minor: int = 0  # above this => human approval
    auto_approve_limit_minor: int = 0  # at/below => may auto-proceed if policy allows
    spent_minor: int = 0
    reserved_minor: int = 0
    updated_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        return _from_dict(cls, data)


LEDGER_EVENTS = (
    "QUOTE_CREATED", "AUTHORIZATION_CREATED", "AUTHORIZATION_FAILED",
    "EXECUTION_STARTED", "EXECUTION_COMPLETED", "CAPTURED", "REFUNDED",
    "VOIDED", "DISPUTED", "ADJUSTED",
)

TRANSACTION_STATUSES = (
    "quoted", "authorized", "captured", "refunded", "voided",
    "failed", "disputed",
)


@dataclass
class Transaction:
    schema_version: str = SCHEMA_VERSION
    transaction_id: str = ""
    contract_id: str = ""
    delegation_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    provider: str = "none"        # none|credits|org_budget|external:<name>
    amount_minor: int = 0
    currency: str = "USD"
    status: str = "quoted"
    idempotency_key: str = ""
    provider_ref: str = ""
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if not self.transaction_id or not self.idempotency_key:
            errors.append("transaction_id/idempotency_key required")
        if self.status not in TRANSACTION_STATUSES:
            errors.append(f"bad status: {self.status!r}")
        try:
            check_amount_minor(self.amount_minor)
            check_currency(self.currency)
        except ValueError as e:
            errors.append(str(e))
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return _from_dict(cls, data)


@dataclass
class LedgerEntry:
    schema_version: str = SCHEMA_VERSION
    entry_id: str = ""
    event: str = ""               # one of LEDGER_EVENTS
    transaction_id: str = ""
    contract_id: str = ""
    delegation_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    amount_minor: int = 0
    currency: str = "USD"
    idempotency_key: str = ""
    prev_hash: str = ""
    entry_hash: str = ""          # sha256 over canonical entry bytes (set on append)
    note: str = ""
    created_at: float = field(default_factory=now)

    def canonical_bytes(self) -> bytes:
        import json
        d = asdict(self)
        d.pop("entry_hash", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry":
        return _from_dict(cls, data)


DISPUTE_REASONS = (
    "task_failure", "incorrect_output", "missing_artifact", "sla_violation",
    "unauthorized_behavior", "policy_violation", "security_incident",
    "overcharge", "duplicate_charge", "incomplete_execution",
)

DISPUTE_STATUSES = (
    "open", "under_review", "evidence_requested",
    "resolved", "refunded", "rejected", "escalated",
)


@dataclass
class Dispute:
    schema_version: str = SCHEMA_VERSION
    dispute_id: str = ""
    transaction_id: str = ""
    contract_id: str = ""
    delegation_id: str = ""
    agent_id: str = ""
    reason: str = ""
    description: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    status: str = "open"
    resolution: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def validate(self) -> List[str]:
        errors = []
        if self.reason not in DISPUTE_REASONS:
            errors.append(f"bad reason: {self.reason!r}")
        if self.status not in DISPUTE_STATUSES:
            errors.append(f"bad status: {self.status!r}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dispute":
        return _from_dict(cls, data)


@dataclass
class SecurityIncident:
    schema_version: str = SCHEMA_VERSION
    incident_id: str = ""
    agent_id: str = ""
    kind: str = ""                # prompt_injection|exfiltration|malicious_artifact|...
    severity: str = "medium"      # low|medium|high|critical
    evidence_ref: str = ""
    delegation_id: str = ""
    resolved: bool = False
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityIncident":
        return _from_dict(cls, data)
