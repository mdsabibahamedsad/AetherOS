"""Multi-provider contracts + milestones + conditional settlement (spec 23-27).

Contracts compose multiple providers with dependency graph.
Milestones gate execution. Settlement is conditional on verification.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.contracts import ContractEngine
from aetheros_agent_market import schemas as S

CONTRACT_STATUSES = (
    "draft", "proposed", "negotiating", "approved", "active",
    "suspended", "completed", "cancelled", "expired", "disputed",
)

NEGOTIABLE_FIELDS = {
    "price_minor", "deadline_at", "output_format", "scope_text",
    "sla", "retry_policy", "evidence_requirements", "delivery_format",
}

_FORBIDDEN_ASKS = {
    "unrestricted filesystem access": "filesystem",
    "disable security": "security",
    "raw secrets": "secrets",
    "bypass approval": "approval",
    "private keys": "secrets",
}


@dataclass
class Milestone:
    """A gated checkpoint within a multi-provider contract."""

    milestone_id: str = ""
    contract_id: str = ""
    sequence: int = 0
    description: str = ""
    provider_agent_id: str = ""
    expected_output: str = ""
    success_criteria: List[str] = field(default_factory=list)
    verification_requirements: List[str] = field(default_factory=list)
    artifact_requirements: List[str] = field(default_factory=list)
    max_duration_s: float = 0.0
    price_minor: int = 0
    currency: str = "USD"
    depends_on: List[str] = field(default_factory=list)  # milestone_ids
    status: str = "pending"  # pending|running|completed|failed|skipped
    result_ref: str = ""
    evidence_ref: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class CompositeContract:
    """A contract spanning multiple providers with dependency DAG."""

    contract_id: str = ""
    version: int = 1
    supersedes: str = ""
    requester: str = "local"
    provider_milestones: List[Milestone] = field(default_factory=list)
    allowed_data: List[str] = field(default_factory=list)
    prohibited_data: List[str] = field(default_factory=list)
    data_class: str = "INTERNAL"
    overall_sla: Dict[str, Any] = field(default_factory=dict)
    timeout_s: float = 300.0
    total_budget_minor: int = 0
    currency: str = "USD"
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
    signatures: Dict[str, str] = field(default_factory=dict)
    status: str = "draft"
    idempotency_key: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositeContract":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def is_locked(self) -> bool:
        return self.status in ("active", "completed", "cancelled", "disputed")

    def dependency_order(self) -> List[str]:
        """Topological order of milestone IDs."""
        deps = {m.milestone_id: set(m.depends_on) for m in self.provider_milestones}
        ready = [m.milestone_id for m in self.provider_milestones if not m.depends_on]
        order = []
        while ready:
            m_id = ready.pop(0)
            order.append(m_id)
            for m in self.provider_milestones:
                if m.milestone_id != m_id and m_id in m.depends_on:
                    m.depends_on.remove(m_id)
                    if not m.depends_on and m.milestone_id not in order:
                        ready.append(m.milestone_id)
        return order


class CompositeContractEngine:
    """Manage multi-milestone contracts with dependency DAG and conditional settlement."""

    def __init__(self, home: Path) -> None:
        self._store = JsonStore(Path(home) / "composite_contracts.json")
        self._milestones = JsonStore(Path(home) / "milestones.json")

    def create(self, contract: CompositeContract) -> CompositeContract:
        errors = contract.validate() if hasattr(contract, "validate") else []
        if not contract.contract_id:
            contract.contract_id = _new_id("cct")
        if not contract.idempotency_key:
            contract.idempotency_key = _new_id("idem")
        contract.status = "draft"
        contract.created_at = time.time()
        contract.updated_at = contract.created_at
        self._store.put(contract.contract_id, contract.to_dict())
        return contract

    def get(self, contract_id: str) -> Optional["CompositeContract"]:
        raw = self._store.get(contract_id)
        return CompositeContract.from_dict(raw) if raw else None

    def propose(self, contract_id: str) -> "CompositeContract":
        c = self._require(contract_id)
        c.status = "proposed"
        self._save(c)
        return c

    def approve(self, contract_id: str, by: str = "") -> "CompositeContract":
        c = self._require(contract_id)
        if c.status != "proposed":
            raise ValueError(f"only proposed contracts can be approved (is {c.status})")
        c.status = "approved"
        c.signatures[f"requester:{by or 'local'}"] = "approved"
        self._save(c)
        return c

    def activate(self, contract_id: str) -> "CompositeContract":
        c = self._require(contract_id)
        if c.status != "approved":
            raise ValueError(f"only approved contracts can activate (is {c.status})")
        c.status = "active"
        self._save(c)
        return c

    def add_milestone(self, contract_id: str, milestone: Milestone) -> Milestone:
        c = self._require(contract_id)
        if c.is_locked():
            raise PermissionError("contract is locked; cannot add milestones")
        if not milestone.milestone_id:
            milestone.milestone_id = _new_id("ms")
        milestone.contract_id = contract_id
        milestone.created_at = time.time()
        milestone.updated_at = milestone.created_at
        c.provider_milestones.append(milestone.to_dict())
        self._milestones.put(milestone.milestone_id, milestone.to_dict())
        self._save(c)
        return milestone

    def start_milestone(self, contract_id: str, milestone_id: str,
                        by: str = "") -> Milestone:
        c = self._require(contract_id)
        m = self._get_milestone(contract_id, milestone_id)
        if m.status != "pending":
            raise ValueError(f"milestone {m.status} cannot be started")
        for dep in m.depends_on:
            dep_m = self._get_milestone(contract_id, dep)
            if dep_m.status != "completed":
                raise ValueError(f"dependency {dep} not completed")
        m.status = "running"
        m.updated_at = time.time()
        self._save_milestone(m)
        self._save(c)
        return m

    def complete_milestone(self, contract_id: str, milestone_id: str,
                           result: Dict[str, Any], evidence_ref: str = "") -> Milestone:
        c = self._require(contract_id)
        m = self._get_milestone(contract_id, milestone_id)
        if m.status != "running":
            raise ValueError(f"milestone {m.status} cannot be completed")
        m.status = "completed"
        m.result_ref = str(result)
        m.evidence_ref = evidence_ref
        m.updated_at = time.time()
        self._save_milestone(m)
        if all(m.get("status") in ("completed", "skipped")
               for m in c.provider_milestones):
            c.status = "completed"
            self._save(c)
        return m

    def cancel_milestone(self, contract_id: str, milestone_id: str,
                         reason: str = "") -> Milestone:
        c = self._require(contract_id)
        m = self._get_milestone(contract_id, milestone_id)
        m.status = "skipped"
        m.updated_at = time.time()
        self._save_milestone(m)
        return m

    def _require(self, contract_id: str) -> CompositeContract:
        c = self.get(contract_id)
        if c is None:
            raise KeyError(f"unknown contract: {contract_id}")
        return c

    def _get_milestone(self, contract_id: str, milestone_id: str) -> Milestone:
        raw = self._milestones.get(milestone_id)
        if raw is None or raw.get("contract_id") != contract_id:
            raise KeyError(f"unknown milestone: {milestone_id}")
        return Milestone.from_dict(raw)

    def _save_milestone(self, m: Milestone) -> None:
        m.updated_at = time.time()
        self._milestones.put(m.milestone_id, m.to_dict())

    def _save(self, contract: CompositeContract) -> None:
        contract.updated_at = time.time()
        self._store.put(contract.contract_id, contract.to_dict())

    def negotiate(self, contract_id: str, proposal: Dict[str, Any],
                  from_agent: str = "") -> Dict[str, Any]:
        c = self._require(contract_id)
        if c.status not in ("proposed", "negotiating"):
            raise ValueError(f"contract {c.status} is not negotiable")
        rejected: Dict[str, str] = {}
        accepted: Dict[str, Any] = {}
        text = " ".join(str(v) for v in proposal.values()).lower()
        for phrase, kind in _FORBIDDEN_ASKS.items():
            if phrase in text:
                return {"accepted": {}, "rejected_fields": dict(proposal),
                        "reasons": [f"forbidden ask ({kind}): policy floor rejects"],
                        "amended_contract_id": ""}
        for key, value in proposal.items():
            if key in ("price_minor", "deadline_at", "output_format", "scope_text",
                       "sla", "retry_policy", "evidence_requirements", "delivery_format"):
                accepted[key] = value
            else:
                rejected[key] = "field not negotiable"
        if not accepted:
            c.status = "negotiating"
            self._save(c)
            return {"accepted": {}, "rejected_fields": rejected,
                    "reasons": [f"{k}: {v}" for k, v in rejected.items()],
                    "amended_contract_id": ""}
        amended = CompositeContract.from_dict(c.to_dict())
        for k, v in accepted.items():
            setattr(amended, k, v)
        amended.contract_id = _new_id("cct")
        amended.version = c.version + 1
        amended.supersedes = c.contract_id
        amended.status = "draft"
        amended.signatures = {}
        amended.idempotency_key = _new_id("idem")
        self._store.put(amended.contract_id, amended.to_dict())
        c.status = "negotiating"
        self._save(c)
        return {"accepted": accepted, "rejected_fields": rejected,
                "reasons": [f"{k}: {v}" for k, v in rejected.items()],
                "amended_contract_id": amended.contract_id}

    def _require(self, contract_id: str) -> CompositeContract:
        c = self.get(contract_id)
        if c is None:
            raise KeyError(f"unknown contract: {contract_id}")
        return c

    def _get_milestone(self, contract_id: str, milestone_id: str) -> Milestone:
        raw = self._milestones.get(milestone_id)
        if raw is None or raw.get("contract_id") != contract_id:
            raise KeyError(f"unknown milestone: {milestone_id}")
        return Milestone.from_dict(raw)

    def _save_milestone(self, m: Milestone) -> None:
        m.updated_at = time.time()
        self._milestones.put(m.milestone_id, m.to_dict())

    def _save(self, contract: CompositeContract) -> None:
        contract.updated_at = time.time()
        self._store.put(contract.contract_id, contract.to_dict())


class ConditionalSettlementEngine:
    """Authorize -> Execute -> Verify -> Capture. On failure: Void/Refund/Dispute."""

    def __init__(self, flow) -> None:
        self.flow = flow

    def authorize(self, quote: "Quote", idempotency_key: str) -> S.Transaction:
        provider = get_provider(flow=self.flow, task={"payment_provider": "credits"})
        return provider.authorize(quote, idempotency_key)

    def capture(self, tx: S.Transaction, idempotency_key: str) -> S.Transaction:
        provider = get_provider(flow=self.flow, task={"payment_provider": "credits"})
        return provider.capture(tx.transaction_id, idempotency_key)

    def refund(self, tx: S.Transaction, idempotency_key: str,
               reason: str = "") -> S.Transaction:
        provider = get_provider(flow=self.flow, task={"payment_provider": "credits"})
        return provider.refund(tx.transaction_id, None, idempotency_key, reason)

    def void(self, tx: S.Transaction, idempotency_key: str) -> S.Transaction:
        provider = get_provider(flow=self.flow, task={"payment_provider": "credits"})
        return provider.void(tx.transaction_id, idempotency_key)