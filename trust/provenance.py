"""Provenance + signed receipts (§49-50, §115, §156): CLAIM->SOURCE,
ACTION->POLICY/AUTHORITY/APPROVAL, RESULT->ACTION, DECISION->EVIDENCE
graph over M50 ProvenanceGraph; Ed25519-signed ExecutionReceipts;
completeness checker (proposal/decision/authority/execution/result/
verification); 'why did AetherOS do this' explainer from real traces."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from aetheros_control_plane.crypto_keys import KeyStore
from aetheros_control_plane.provenance_audit import AuditLog, ProvenanceGraph

from .models import ExecutionReceipt, new_id


def _h(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class ProvenanceEngine:
    def __init__(self, keys: Optional[KeyStore] = None,
                 key_id: str = ""):
        self.keys = keys or KeyStore()
        self.key_id = key_id
        self.graph = ProvenanceGraph()
        self.receipts: Dict[str, ExecutionReceipt] = {}

    # -- graph -----------------------------------------------------------
    def link_claim_source(self, claim: str, source: str,
                          evidence: str = "") -> None:
        self.graph.add(claim, evidence or "unverified")
        self.graph.add(source, "source")
        self.graph.link(claim, "derived_from", source)

    def link_action(self, action_id: str, policy: str, authority: str,
                    approval: str = "") -> None:
        self.graph.add(action_id, "action")
        self.graph.link(action_id, "governed_by", policy)
        self.graph.link(action_id, "authorized_by", authority)
        if approval:
            self.graph.link(action_id, "approved_by", approval)

    def link_result(self, result_id: str, action_id: str,
                    verification: str = "") -> None:
        self.graph.add(result_id, "result")
        self.graph.link(result_id, "produced_by", action_id)
        if verification:
            self.graph.link(result_id, "verified_by", verification)

    # -- signed receipts ---------------------------------------------------
    def issue_receipt(self, action_id: str, actor: str, capability: str,
                      policy_id: str, policy_version: str, policy_hash: str,
                      authority_hash: str, inputs: Any, result: Any,
                      verification: str,
                      semantics: str = "at-least-once") -> ExecutionReceipt:
        receipt = ExecutionReceipt(
            receipt_id=new_id("rcpt"), action_id=action_id, actor=actor,
            capability=capability, policy_id=policy_id,
            policy_version=policy_version, policy_hash=policy_hash,
            authority_hash=authority_hash, input_hash=_h(inputs),
            result_hash=_h(result), verification=verification,
            execution_semantics=semantics, key_id=self.key_id)
        body = {k: v for k, v in receipt.__dict__.items()
                if k != "signature"}
        sig = ""
        if self.key_id:
            sig = self.keys.sign(
                self.key_id,
                json.dumps(body, sort_keys=True,
                           default=str).encode())
        receipt = ExecutionReceipt(**{**body, "signature": sig})
        self.receipts[receipt.receipt_id] = receipt
        return receipt

    def verify_receipt(self, receipt: ExecutionReceipt) -> bool:
        if not receipt.signature or not receipt.key_id:
            return False
        body = {k: v for k, v in receipt.__dict__.items()
                if k != "signature"}
        try:
            from aetheros_control_plane.crypto_keys import (
                KeyResolver, SignatureVerifier)
            resolver = KeyResolver()
            resolver.attach(self.keys)
            return SignatureVerifier(resolver).verify(
                receipt.key_id,
                json.dumps(body, sort_keys=True,
                           default=str).encode(), receipt.signature)
        except Exception:
            return False

    # -- completeness + explanation -----------------------------------------
    @staticmethod
    def completeness(record: Dict[str, bool]) -> Dict[str, Any]:
        required = ("proposal", "decision", "authority", "execution",
                    "result", "verification")
        missing = [k for k in required if not record.get(k)]
        return {"complete": not missing, "missing": missing}

    def explain(self, action_id: str) -> Dict[str, Any]:
        """'Why did AetherOS do this' from the recorded graph (§156)."""
        nodes = getattr(self.graph, "nodes", {})
        edges = getattr(self.graph, "edges", [])
        related = [{"src": s, "rel": r, "dst": d} for s, r, d in edges
                   if action_id in (s, d)]
        return {"action": action_id,
                "recorded": bool(action_id in nodes or related),
                "relations": related,
                "note": "explanation derived only from recorded trace"}
