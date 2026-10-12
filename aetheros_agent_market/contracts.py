"""Delegation contracts + negotiation (spec sections 11 + 12).

Contracts are immutable once execution begins (status active+);
amendments create a new version superseding the old. Negotiation may
only touch NEGOTIABLE_FIELDS and NEVER weakens mandatory security
policy: security_constraints, data_class, allowed/prohibited data and
verification requirements are floors enforced deterministically.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

# Security floor: negotiation proposals touching these are REJECTED.
_SECURITY_FLOOR_FIELDS = {
    "security_constraints", "data_class", "allowed_data",
    "prohibited_data", "verification_requirements",
    "artifact_requirements", "max_delegation_depth",
}

# Dangerous asks the policy floor always rejects, whatever the price.
_FORBIDDEN_ASKS = {
    "unrestricted filesystem access": "filesystem",
    "disable security": "security",
    "raw secrets": "secrets",
    "bypass approval": "approval",
    "private keys": "secrets",
}


class ContractEngine:
    def __init__(self, home: Path) -> None:
        self._contracts = JsonStore(Path(home) / "contracts.json")

    def create(self, contract: S.DelegationContract) -> S.DelegationContract:
        errors = contract.validate()
        if errors:
            raise ValueError(f"invalid contract: {errors}")
        if not contract.contract_id:
            contract.contract_id = S.new_id("ct")
        if not contract.idempotency_key:
            contract.idempotency_key = S.new_id("idem")
        contract.status = "draft"
        contract.created_at = time.time()
        contract.updated_at = contract.created_at
        # Idempotency: same key returns the existing contract.
        for raw in self._contracts.values():
            if raw.get("idempotency_key") == contract.idempotency_key:
                return S.DelegationContract.from_dict(raw)
        self._contracts.put(contract.contract_id, contract.to_dict())
        return contract

    def get(self, contract_id: str) -> Optional[S.DelegationContract]:
        raw = self._contracts.get(contract_id)
        return S.DelegationContract.from_dict(raw) if raw else None

    def list(self, status: str = "") -> List[S.DelegationContract]:
        out = []
        for raw in self._contracts.values():
            c = S.DelegationContract.from_dict(raw)
            if status and c.status != status:
                continue
            out.append(c)
        return sorted(out, key=lambda c: c.created_at, reverse=True)

    def _save(self, contract: S.DelegationContract) -> None:
        contract.updated_at = time.time()
        self._contracts.put(contract.contract_id, contract.to_dict())

    def propose(self, contract_id: str) -> S.DelegationContract:
        c = self._require(contract_id)
        if c.status != "draft":
            raise ValueError(f"only draft contracts can be proposed (is {c.status})")
        c.status = "proposed"
        self._save(c)
        return c

    def approve(self, contract_id: str, by: str = "") -> S.DelegationContract:
        c = self._require(contract_id)
        if c.status not in ("proposed", "negotiating"):
            raise ValueError(f"only proposed/negotiating contracts can be approved (is {c.status})")
        if c.expires_at and time.time() > c.expires_at:
            raise ValueError("contract expired")
        c.status = "approved"
        c.signatures[f"requester:{by or 'local'}"] = "approved"
        self._save(c)
        return c

    def activate(self, contract_id: str) -> S.DelegationContract:
        """Lock the contract for execution. After this, no mutation."""
        c = self._require(contract_id)
        if c.status != "approved":
            raise ValueError(f"only approved contracts can activate (is {c.status})")
        c.status = "active"
        self._save(c)
        return c

    def cancel(self, contract_id: str, reason: str = "") -> S.DelegationContract:
        c = self._require(contract_id)
        if c.is_locked and c.status not in ("active",):
            raise ValueError(f"contract {c.status} cannot be cancelled")
        c.status = "cancelled"
        c.cancellation_conditions = (c.cancellation_conditions + f" | cancelled: {reason}")[:2000]
        self._save(c)
        return c

    def amend(self, contract_id: str, changes: Dict[str, Any],
              by: str = "") -> S.DelegationContract:
        """Amendments create a NEW version; the old record is untouched."""
        old = self._require(contract_id)
        for key in changes:
            if key in _SECURITY_FLOOR_FIELDS:
                raise PermissionError(
                    f"amendment to {key!r} rejected: security floor is not negotiable")
        data = old.to_dict()
        for key, value in changes.items():
            if key not in S.NEGOTIABLE_FIELDS and key not in ("task_summary", "scope_text"):
                raise ValueError(f"field {key!r} is not amendable")
            data[key] = value
        data["contract_id"] = S.new_id("ct")
        data["version"] = old.version + 1
        data["supersedes"] = old.contract_id
        data["status"] = "draft"
        data["signatures"] = {}
        data["idempotency_key"] = S.new_id("idem")
        new = S.DelegationContract.from_dict(data)
        errors = new.validate()
        if errors:
            raise ValueError(f"amended contract invalid: {errors}")
        self._contracts.put(new.contract_id, new.to_dict())
        return new

    def negotiate(self, contract_id: str, proposal: Dict[str, Any],
                  from_agent: str = "") -> Dict[str, Any]:
        """Evaluate a counter-proposal deterministically.

        Returns {accepted, rejected_fields, reasons, amended_contract_id}.
        Security-floor violations are rejected regardless of price (sec 12).
        """
        c = self._require(contract_id)
        if c.status not in ("proposed", "negotiating"):
            raise ValueError(f"contract {c.status} is not negotiable")
        rejected: Dict[str, str] = {}
        accepted: Dict[str, Any] = {}
        text = " ".join(str(v) for v in proposal.values()).lower()
        for phrase, kind in _FORBIDDEN_ASKS.items():
            if phrase in text:
                return {"accepted": {}, "rejected_fields": dict(proposal),
                        "reasons": [f"forbidden ask detected ({kind}): policy floor rejects"],
                        "amended_contract_id": ""}
        for key, value in proposal.items():
            if key in _SECURITY_FLOOR_FIELDS:
                rejected[key] = "security floor: not negotiable"
            elif key not in S.NEGOTIABLE_FIELDS:
                rejected[key] = "field not negotiable"
            else:
                accepted[key] = value
        if not accepted:
            c.status = "negotiating"
            self._save(c)
            return {"accepted": {}, "rejected_fields": rejected,
                    "reasons": [f"{k}: {v}" for k, v in rejected.items()],
                    "amended_contract_id": ""}
        amended = self.amend(contract_id, accepted, by=from_agent)
        c.status = "negotiating"
        self._save(c)
        return {"accepted": accepted, "rejected_fields": rejected,
                "reasons": [f"{k}: {v}" for k, v in rejected.items()],
                "amended_contract_id": amended.contract_id}

    def _require(self, contract_id: str) -> S.DelegationContract:
        c = self.get(contract_id)
        if c is None:
            raise KeyError(f"unknown contract: {contract_id}")
        return c
